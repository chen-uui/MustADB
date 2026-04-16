#!/usr/bin/env python
import inspect
import json
import os
import sys
import tempfile
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.django_settings")

import django

django.setup()

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from pdf_processor import views_user_upload
from pdf_processor import views_review
from pdf_processor.batch_extraction_service import BatchExtractionService
from pdf_processor.management.commands.reprocess_pdfs import Command as ReprocessCommand
from pdf_processor.management.commands.sync_pdfs import Command as SyncCommand
from pdf_processor.models import PDFDocument, ProcessingTask
from pdf_processor.services.upload_storage_service import UploadStorageService
from pdf_processor.views.direct_processing_views import DirectProcessingViewSet
from pdf_processor.weaviate_views import WeaviatePDFViewSet


def result(name, status, details=None):
    return {
        "name": name,
        "status": status,
        "details": details or {},
    }


def make_fake_pdf_utils():
    module = ModuleType("pdf_processor.pdf_utils")

    class FakePDFUtils:
        @staticmethod
        def extract_text_and_metadata(file_path):
            stem = Path(file_path).stem
            return {
                "text": "sample text",
                "metadata": {
                    "title": f"title-{stem}",
                    "authors": "tester",
                    "year": "2024",
                    "journal": "Journal",
                    "doi": "10.1234/example",
                    "abstract": "",
                    "keywords": "",
                },
            }

    class FakeGlobalConfig:
        CHUNK_SIZE = 700
        CHUNK_OVERLAP = 80

    module.PDFUtils = FakePDFUtils
    module.GlobalConfig = FakeGlobalConfig
    return module


def make_fake_fitz():
    module = ModuleType("fitz")

    class FakeDoc:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def __len__(self):
            return 2

        def close(self):
            return None

    def open_file(_path):
        return FakeDoc()

    module.open = open_file
    return module


class FakeThread:
    def __init__(self, target=None, args=None, kwargs=None, daemon=None):
        self._target = target
        self._args = args or ()
        self._kwargs = kwargs or {}
        self.daemon = daemon

    def start(self):
        if self._target:
            self._target(*self._args, **self._kwargs)


class FakeProcessor:
    def __init__(self):
        self.calls = []

    def process_single_document(self, pdf_path, document_id=None, metadata=None):
        self.calls.append(
            {
                "pdf_path": pdf_path,
                "document_id": document_id,
                "metadata": metadata or {},
            }
        )
        return {
            "status": "success",
            "total_pages": 2,
            "total_chunks": 1,
        }


class FakeQuerySet:
    def __init__(self, first_value=None):
        self._first_value = first_value

    def first(self):
        return self._first_value


class FakeChainedQuerySet:
    def __init__(self, items):
        self._items = list(items)

    def __iter__(self):
        return iter(self._items)

    def select_related(self, *args, **kwargs):
        return self

    def only(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def count(self):
        return len(self._items)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self._items[key]
        return self._items[key]


def build_duplicate_inspection(**overrides):
    payload = {
        "original_filename": "sample.pdf",
        "sha1": "sha1-sample",
        "duplicate_detected": False,
        "duplicate_sha1": None,
        "duplicate_document_id": None,
        "filename_conflict": False,
        "filename_conflict_document_id": None,
        "filename_conflict_same_content": None,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def check_user_upload():
    created = {}
    factory = APIRequestFactory()
    fake_pdf_utils = make_fake_pdf_utils()
    fake_fitz = make_fake_fitz()

    class FakeManager:
        def filter(self, **kwargs):
            created["filter_kwargs"] = kwargs
            return FakeQuerySet()

        def create(self, **kwargs):
            created["create_kwargs"] = kwargs
            return SimpleNamespace(id="doc-user-1", title=kwargs["title"])

    with tempfile.TemporaryDirectory() as temp_dir:
        media_root = Path(temp_dir) / "media"
        upload = SimpleUploadedFile("sample.pdf", b"%PDF-1.4 sample", content_type="application/pdf")
        request = factory.post("/api/pdf/documents/user-upload/", {"files": [upload]}, format="multipart")

        with override_settings(MEDIA_ROOT=str(media_root)):
            with patch.dict(sys.modules, {"fitz": fake_fitz, "pdf_processor.pdf_utils": fake_pdf_utils}):
                with patch.object(views_user_upload.PDFDocument, "objects", FakeManager()):
                    response = views_user_upload.user_upload_pdfs(request)

        stored_path = Path(created["create_kwargs"]["file_path"])
        checks = [
            response.status_code == 200,
            created["create_kwargs"]["filename"] == "sample.pdf",
            created["create_kwargs"]["review_status"] == "pending",
            created["create_kwargs"]["processed"] is False,
            stored_path.exists(),
            stored_path.parent == media_root / "uploads",
            stored_path.name != "sample.pdf",
        ]
        return result(
            "user_upload_smoke",
            "pass" if all(checks) else "fail",
            {
                "response_status": response.status_code,
                "stored_path": str(stored_path),
                "record_filename": created["create_kwargs"].get("filename"),
                "review_status": created["create_kwargs"].get("review_status"),
                "processed": created["create_kwargs"].get("processed"),
            },
        )


def check_cross_entry_duplicate():
    existing_doc = SimpleNamespace(
        id="existing-doc",
        title="existing",
        filename="sample.pdf",
        upload_date=timezone.now(),
    )
    factory = APIRequestFactory()
    fake_processor = FakeProcessor()
    fake_pdf_utils = make_fake_pdf_utils()
    fake_fitz = make_fake_fitz()

    def fake_filter(self, **kwargs):
        return FakeQuerySet(existing_doc)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_pdf_root = Path(temp_dir) / "data" / "pdfs"
        request = factory.post(
            "/api/pdf/documents/upload/",
            {
                "file": SimpleUploadedFile("sample.pdf", b"%PDF-1.4 duplicate", content_type="application/pdf"),
                "title": "sample",
                "category": "general",
            },
            format="multipart",
        )

        with patch("pdf_processor.weaviate_views._GLOBAL_PROCESSOR", fake_processor):
            with override_settings(PDF_STORAGE_PATH=str(temp_pdf_root)):
                with patch.object(UploadStorageService, "inspect_uploaded_file", return_value=build_duplicate_inspection(original_filename="sample.pdf", sha1="sha1-sample")):
                    with patch.object(WeaviatePDFViewSet, "_filter_documents", fake_filter):
                        with patch.dict(sys.modules, {"fitz": fake_fitz, "pdf_processor.pdf_utils": fake_pdf_utils}):
                            response = WeaviatePDFViewSet.as_view({"post": "upload"})(request)

        response.render()
        payload = json.loads(response.content.decode("utf-8"))
        checks = [
            response.status_code == 200,
            payload.get("existing") is True,
            payload.get("document_id") == "existing-doc",
        ]
        return result(
            "cross_entry_duplicate_upload",
            "pass" if all(checks) else "fail",
            {
                "response_status": response.status_code,
                "payload": payload,
                "processor_calls": len(fake_processor.calls),
            },
        )


def check_direct_processing():
    created = {}
    factory = APIRequestFactory()

    class FakeTaskManager:
        def create(self, **kwargs):
            created["task_kwargs"] = kwargs
            return SimpleNamespace(task_id="task-1", status="pending", document_path=kwargs["document_path"])

    class FakeLogManager:
        def create(self, **kwargs):
            created.setdefault("logs", []).append(kwargs)
            return SimpleNamespace(id=1)

    class FakeProcessorFactory:
        def __call__(self):
            return SimpleNamespace()

    with tempfile.TemporaryDirectory() as temp_dir:
        media_root = Path(temp_dir) / "media"
        request = factory.post(
            "/api/direct-processing/process/",
            {"file": SimpleUploadedFile("direct.pdf", b"%PDF-1.4 direct", content_type="application/pdf")},
            format="multipart",
        )
        request.user = SimpleNamespace(is_authenticated=False)

        with override_settings(MEDIA_ROOT=str(media_root)):
            with patch.object(UploadStorageService, "inspect_uploaded_file", return_value=build_duplicate_inspection(original_filename="direct.pdf", sha1="sha1-direct")):
                with patch("pdf_processor.views.direct_processing_views.DirectDocumentProcessor", FakeProcessorFactory()):
                    with patch("pdf_processor.views.direct_processing_views.validate_pdf_file", return_value={"valid": True}):
                        with patch.object(DirectProcessingViewSet, "_process_document_async", lambda self, task: None):
                            with patch.object(ProcessingTask, "objects", FakeTaskManager()):
                                with patch("pdf_processor.views.direct_processing_views.ProcessingLog.objects", FakeLogManager()):
                                    viewset = DirectProcessingViewSet()
                                    response = viewset.process_document(request)

        payload = json.loads(response.content.decode("utf-8"))
        stored_path = Path(created["task_kwargs"]["document_path"])
        checks = [
            response.status_code == 200,
            payload.get("task_id") == "task-1",
            stored_path.exists(),
            stored_path.parent == media_root / "uploads",
            stored_path.name != "direct.pdf",
        ]
        return result(
            "direct_processing_smoke",
            "pass" if all(checks) else "fail",
            {
                "response_status": response.status_code,
                "payload": payload,
                "stored_path": str(stored_path),
            },
        )


def check_legacy_path_compatibility():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        legacy_media = temp_root / "media" / "uploads" / "legacy-media.pdf"
        legacy_library = temp_root / "data" / "pdfs" / "legacy-library.pdf"
        legacy_media.parent.mkdir(parents=True, exist_ok=True)
        legacy_library.parent.mkdir(parents=True, exist_ok=True)
        legacy_media.write_bytes(b"legacy-media")
        legacy_library.write_bytes(b"legacy-library")

        statuses = []
        for path_value in (legacy_media, legacy_library):
            statuses.append(path_value.exists() and path_value.read_bytes().startswith(b"legacy"))

    checks = all(statuses)
    return result(
        "legacy_path_compatibility",
        "pass" if checks else "fail",
        {"statuses": statuses},
    )


def check_weaviate_upload_smoke():
    created = {}
    factory = APIRequestFactory()
    fake_processor = FakeProcessor()
    fake_pdf_utils = make_fake_pdf_utils()
    fake_fitz = make_fake_fitz()

    class FakeDocument:
        def __init__(self, **kwargs):
            self.id = "weaviate-doc-1"
            self.upload_date = timezone.now()
            self.file_path = kwargs["file_path"]
            self.title = kwargs["title"]
            self.authors = kwargs.get("authors", "")
            self.year = kwargs.get("year")
            self.journal = kwargs.get("journal", "")
            self.doi = kwargs.get("doi", "")
            self.category = kwargs.get("category", "general")
            self.processed = kwargs.get("processed", False)
            self.page_count = kwargs.get("page_count", 0)
            self.saved = []

        def save(self):
            self.saved.append({"processed": self.processed, "page_count": self.page_count})

    def fake_filter(self, **kwargs):
        created["filter_kwargs"] = kwargs
        return FakeQuerySet()

    def fake_create(self, **kwargs):
        created["create_kwargs"] = kwargs
        document = FakeDocument(**kwargs)
        created["document"] = document
        return document

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_pdf_root = Path(temp_dir) / "data" / "pdfs"
        request = factory.post(
            "/api/pdf/documents/upload/",
            {
                "file": SimpleUploadedFile("library.pdf", b"%PDF-1.4 library", content_type="application/pdf"),
                "title": "library",
                "category": "general",
            },
            format="multipart",
        )

        with patch("pdf_processor.weaviate_views._GLOBAL_PROCESSOR", fake_processor):
            with override_settings(PDF_STORAGE_PATH=str(temp_pdf_root)):
                with patch.object(UploadStorageService, "inspect_uploaded_file", return_value=build_duplicate_inspection(original_filename="library.pdf", sha1="sha1-library")):
                    with patch.object(WeaviatePDFViewSet, "_filter_documents", fake_filter):
                        with patch.object(WeaviatePDFViewSet, "_create_document", fake_create):
                            with patch("threading.Thread", FakeThread):
                                with patch.dict(sys.modules, {"fitz": fake_fitz, "pdf_processor.pdf_utils": fake_pdf_utils}):
                                    response = WeaviatePDFViewSet.as_view({"post": "upload"})(request)

        response.render()
        payload = json.loads(response.content.decode("utf-8"))
        stored_path = Path(created["create_kwargs"]["file_path"])
        checks = [
            response.status_code == 201,
            stored_path.exists(),
            stored_path.name == "library.pdf",
            len(fake_processor.calls) == 1,
            created["document"].processed is True,
        ]
        return result(
            "weaviate_upload_smoke",
            "pass" if all(checks) else "fail",
            {
                "response_status": response.status_code,
                "payload": payload,
                "stored_path": str(stored_path),
                "processor_calls": len(fake_processor.calls),
            },
        )


def check_weaviate_same_name_same_content_existing():
    existing_doc = SimpleNamespace(
        id="same-name-doc",
        title="existing",
        filename="same-name.pdf",
        upload_date=timezone.now(),
    )
    factory = APIRequestFactory()
    fake_processor = FakeProcessor()
    fake_pdf_utils = make_fake_pdf_utils()
    fake_fitz = make_fake_fitz()

    def fake_filter(self, **kwargs):
        if kwargs.get("filename") == "same-name.pdf":
            return FakeQuerySet(existing_doc)
        return FakeQuerySet()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_pdf_root = Path(temp_dir) / "data" / "pdfs"
        request = factory.post(
            "/api/pdf/documents/upload/",
            {
                "file": SimpleUploadedFile("same-name.pdf", b"%PDF-1.4 same-name", content_type="application/pdf"),
                "title": "same-name",
                "category": "general",
            },
            format="multipart",
        )

        with patch("pdf_processor.weaviate_views._GLOBAL_PROCESSOR", fake_processor):
            with override_settings(PDF_STORAGE_PATH=str(temp_pdf_root)):
                with patch.object(UploadStorageService, "inspect_uploaded_file", return_value=build_duplicate_inspection(original_filename="same-name.pdf", sha1="sha1-same-name")):
                    with patch.object(WeaviatePDFViewSet, "_filter_documents", fake_filter):
                        with patch.dict(sys.modules, {"fitz": fake_fitz, "pdf_processor.pdf_utils": fake_pdf_utils}):
                            response = WeaviatePDFViewSet.as_view({"post": "upload"})(request)

        response.render()
        payload = json.loads(response.content.decode("utf-8"))
        checks = [
            response.status_code == 200,
            payload.get("existing") is True,
            payload.get("document_id") == "same-name-doc",
            len(fake_processor.calls) == 0,
        ]
        return result(
            "weaviate_same_name_same_content_existing",
            "pass" if all(checks) else "fail",
            {
                "response_status": response.status_code,
                "payload": payload,
                "processor_calls": len(fake_processor.calls),
            },
        )


def check_weaviate_different_name_same_content_duplicate_hit():
    duplicate_doc = SimpleNamespace(
        id="duplicate-doc",
        title="existing",
        filename="existing.pdf",
        upload_date=timezone.now(),
    )
    factory = APIRequestFactory()
    fake_processor = FakeProcessor()
    fake_pdf_utils = make_fake_pdf_utils()
    fake_fitz = make_fake_fitz()
    created = {"count": 0}

    def fake_filter(self, **kwargs):
        if kwargs.get("filename") == "new-name.pdf":
            return FakeQuerySet()
        return FakeQuerySet()

    def fake_create(self, **kwargs):
        created["count"] += 1
        payload = dict(kwargs)
        payload.setdefault("processed", False)
        payload.setdefault("page_count", 0)
        payload.setdefault("upload_date", timezone.now())
        payload["id"] = "new-doc"
        payload["save"] = lambda: None
        return SimpleNamespace(**payload)

    duplicate_inspection = build_duplicate_inspection(
        original_filename="new-name.pdf",
        duplicate_detected=True,
        duplicate_sha1="sha1-sample",
        duplicate_document_id="duplicate-doc",
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_pdf_root = Path(temp_dir) / "data" / "pdfs"
        request = factory.post(
            "/api/pdf/documents/upload/",
            {
                "file": SimpleUploadedFile("new-name.pdf", b"%PDF-1.4 duplicate", content_type="application/pdf"),
                "title": "new-name",
                "category": "general",
            },
            format="multipart",
        )

        with patch("pdf_processor.weaviate_views._GLOBAL_PROCESSOR", fake_processor):
            with override_settings(PDF_STORAGE_PATH=str(temp_pdf_root)):
                with patch.object(UploadStorageService, "inspect_uploaded_file", return_value=duplicate_inspection):
                    with patch.object(WeaviatePDFViewSet, "_filter_documents", fake_filter):
                        with patch.object(WeaviatePDFViewSet, "_get_document_or_none", return_value=duplicate_doc):
                            with patch.object(WeaviatePDFViewSet, "_create_document", fake_create):
                                with patch("threading.Thread", FakeThread):
                                    with patch.dict(sys.modules, {"fitz": fake_fitz, "pdf_processor.pdf_utils": fake_pdf_utils}):
                                        response = WeaviatePDFViewSet.as_view({"post": "upload"})(request)

        response.render()
        payload = json.loads(response.content.decode("utf-8"))
        checks = [
            response.status_code == 200,
            payload.get("existing") is True,
            payload.get("document_id") == "duplicate-doc",
            created["count"] == 0,
            len(fake_processor.calls) == 0,
        ]
        return result(
            "weaviate_different_name_same_content_duplicate_hit",
            "pass" if all(checks) else "fail",
            {
                "response_status": response.status_code,
                "payload": payload,
                "processor_calls": len(fake_processor.calls),
                "created_count": created["count"],
            },
        )


def check_weaviate_same_name_different_content_keeps_filename_guard():
    existing_doc = SimpleNamespace(
        id="filename-conflict-doc",
        title="existing",
        filename="conflict.pdf",
        upload_date=timezone.now(),
    )
    factory = APIRequestFactory()
    fake_processor = FakeProcessor()
    fake_pdf_utils = make_fake_pdf_utils()
    fake_fitz = make_fake_fitz()

    duplicate_inspection = build_duplicate_inspection(
        original_filename="conflict.pdf",
        duplicate_detected=False,
        filename_conflict=True,
        filename_conflict_document_id="filename-conflict-doc",
        filename_conflict_same_content=False,
    )

    def fake_filter(self, **kwargs):
        if kwargs.get("filename") == "conflict.pdf":
            return FakeQuerySet(existing_doc)
        return FakeQuerySet()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_pdf_root = Path(temp_dir) / "data" / "pdfs"
        request = factory.post(
            "/api/pdf/documents/upload/",
            {
                "file": SimpleUploadedFile("conflict.pdf", b"%PDF-1.4 different-content", content_type="application/pdf"),
                "title": "conflict",
                "category": "general",
            },
            format="multipart",
        )

        with patch("pdf_processor.weaviate_views._GLOBAL_PROCESSOR", fake_processor):
            with override_settings(PDF_STORAGE_PATH=str(temp_pdf_root)):
                with patch.object(UploadStorageService, "inspect_uploaded_file", return_value=duplicate_inspection):
                    with patch.object(WeaviatePDFViewSet, "_filter_documents", fake_filter):
                        with patch.dict(sys.modules, {"fitz": fake_fitz, "pdf_processor.pdf_utils": fake_pdf_utils}):
                            response = WeaviatePDFViewSet.as_view({"post": "upload"})(request)

        response.render()
        payload = json.loads(response.content.decode("utf-8"))
        checks = [
            response.status_code == 200,
            payload.get("existing") is True,
            payload.get("document_id") == "filename-conflict-doc",
            payload.get("duplicate_hit") in (None, False),
            len(fake_processor.calls) == 0,
        ]
        return result(
            "weaviate_same_name_different_content_keeps_filename_guard",
            "pass" if all(checks) else "fail",
            {
                "response_status": response.status_code,
                "payload": payload,
                "processor_calls": len(fake_processor.calls),
            },
        )


def check_user_then_weaviate_same_content_duplicate_hit():
    duplicate_doc = SimpleNamespace(
        id="user-doc",
        title="user-uploaded",
        filename="user-uploaded.pdf",
        upload_date=timezone.now(),
    )
    factory = APIRequestFactory()
    fake_processor = FakeProcessor()
    fake_pdf_utils = make_fake_pdf_utils()
    fake_fitz = make_fake_fitz()
    created = {"count": 0}

    def fake_filter(self, **kwargs):
        if kwargs.get("filename") == "weaviate-copy.pdf":
            return FakeQuerySet()
        return FakeQuerySet()

    def fake_create(self, **kwargs):
        created["count"] += 1
        payload = dict(kwargs)
        payload.setdefault("processed", False)
        payload.setdefault("page_count", 0)
        payload.setdefault("upload_date", timezone.now())
        payload["id"] = "new-doc"
        payload["save"] = lambda: None
        return SimpleNamespace(**payload)

    duplicate_inspection = build_duplicate_inspection(
        original_filename="weaviate-copy.pdf",
        duplicate_detected=True,
        duplicate_sha1="sha1-sample",
        duplicate_document_id="user-doc",
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_pdf_root = Path(temp_dir) / "data" / "pdfs"
        request = factory.post(
            "/api/pdf/documents/upload/",
            {
                "file": SimpleUploadedFile("weaviate-copy.pdf", b"%PDF-1.4 duplicate", content_type="application/pdf"),
                "title": "weaviate-copy",
                "category": "general",
            },
            format="multipart",
        )

        with patch("pdf_processor.weaviate_views._GLOBAL_PROCESSOR", fake_processor):
            with override_settings(PDF_STORAGE_PATH=str(temp_pdf_root)):
                with patch.object(UploadStorageService, "inspect_uploaded_file", return_value=duplicate_inspection):
                    with patch.object(WeaviatePDFViewSet, "_filter_documents", fake_filter):
                        with patch.object(WeaviatePDFViewSet, "_get_document_or_none", return_value=duplicate_doc):
                            with patch.object(WeaviatePDFViewSet, "_create_document", fake_create):
                                with patch("threading.Thread", FakeThread):
                                    with patch.dict(sys.modules, {"fitz": fake_fitz, "pdf_processor.pdf_utils": fake_pdf_utils}):
                                        response = WeaviatePDFViewSet.as_view({"post": "upload"})(request)

        response.render()
        payload = json.loads(response.content.decode("utf-8"))
        checks = [
            response.status_code == 200,
            payload.get("existing") is True,
            payload.get("document_id") == "user-doc",
            created["count"] == 0,
            len(fake_processor.calls) == 0,
        ]
        return result(
            "user_then_weaviate_same_content_duplicate_hit",
            "pass" if all(checks) else "fail",
            {
                "response_status": response.status_code,
                "payload": payload,
                "processor_calls": len(fake_processor.calls),
                "created_count": created["count"],
            },
        )


def check_reprocess_directory_source():
    source = inspect.getsource(ReprocessCommand.handle)
    uses_settings = "PDF_STORAGE_PATH" in source or "resolve_pdf_storage_dir" in source or "upload_storage_service" in source
    uses_relative = "../data/pdfs" in source
    status = "pass" if uses_settings and not uses_relative else "fail"
    return result(
        "reprocess_directory_source",
        status,
        {
            "uses_settings_or_helper": uses_settings,
            "uses_relative_path_literal": uses_relative,
        },
    )


def check_sync_directory_source():
    source = inspect.getsource(SyncCommand.handle)
    uses_helper = "resolve_pdf_storage_dir" in source or "UploadStorageService" in source
    uses_legacy_path = "Path(settings.BASE_DIR).parent / 'pdfs'" in source

    command = SyncCommand()
    resolved_dir = None
    if hasattr(command, "resolve_pdf_dir"):
        resolve_source = inspect.getsource(command.resolve_pdf_dir)
        uses_helper = uses_helper or "resolve_pdf_storage_dir" in resolve_source or "UploadStorageService" in resolve_source
        uses_legacy_path = uses_legacy_path or "Path(settings.BASE_DIR).parent / 'pdfs'" in resolve_source
        resolved_dir = str(command.resolve_pdf_dir())

    helper_dir = str(UploadStorageService.resolve_pdf_storage_dir())
    aligned = uses_helper and not uses_legacy_path
    if resolved_dir is not None:
        aligned = aligned and resolved_dir == helper_dir

    return result(
        "sync_directory_source",
        "pass" if aligned else "fail",
        {
            "uses_helper": uses_helper,
            "uses_legacy_path_literal": uses_legacy_path,
            "resolved_dir": resolved_dir,
            "helper_dir": helper_dir,
        },
    )


def check_sync_command_smoke():
    created = {}

    class FakeSyncManager:
        def all(self):
            return FakeChainedQuerySet([])

        def create(self, **kwargs):
            created["create_kwargs"] = kwargs
            return SimpleNamespace(id="sync-doc-1", file_path=kwargs["file_path"])

    with tempfile.TemporaryDirectory() as temp_dir:
        pdf_dir = Path(temp_dir) / "data" / "pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        sample_file = pdf_dir / "123e4567-e89b-12d3-a456-426614174000 Sample_sync.pdf"
        sample_file.write_bytes(b"%PDF-1.4 sync")

        command = SyncCommand()
        command.pdf_dir = pdf_dir

        with patch.object(PDFDocument, "objects", FakeSyncManager()):
            added, removed = command.sync_pdfs()

    checks = [
        added == 1,
        removed == 0,
        created["create_kwargs"]["filename"] == "123e4567-e89b-12d3-a456-426614174000 Sample_sync.pdf",
        created["create_kwargs"]["file_path"] == str(sample_file),
        created["create_kwargs"]["title"] == "Sample sync",
    ]
    return result(
        "sync_command_smoke",
        "pass" if all(checks) else "fail",
        {
            "added": added,
            "removed": removed,
            "create_kwargs": created.get("create_kwargs", {}),
        },
    )


def check_sync_files_add_smoke():
    created = {}

    class FakeDeleteQuerySet:
        def delete(self):
            return (0, {})

    with tempfile.TemporaryDirectory() as temp_dir:
        pdf_dir = Path(temp_dir) / "data" / "pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        sample_file = pdf_dir / "123e4567-e89b-12d3-a456-426614174000 Sample_sync.pdf"
        sample_file.write_bytes(b"%PDF-1.4 sync api")

        viewset = WeaviatePDFViewSet()
        viewset.processor = SimpleNamespace(vector_service=MagicMock())

        def fake_get_or_create_document(lookup, defaults):
            created["lookup"] = lookup
            created["defaults"] = defaults
            return SimpleNamespace(id="sync-api-doc", **defaults), True

        def fake_filter(self, **kwargs):
            if "id__in" in kwargs:
                return FakeDeleteQuerySet()
            return FakeChainedQuerySet([])

        with override_settings(PDF_STORAGE_PATH=str(pdf_dir)):
            with patch.object(WeaviatePDFViewSet, "_get_all_documents", return_value=FakeChainedQuerySet([])):
                with patch.object(WeaviatePDFViewSet, "_get_or_create_document", side_effect=fake_get_or_create_document):
                    with patch.object(WeaviatePDFViewSet, "_filter_documents", fake_filter):
                        with patch.object(WeaviatePDFViewSet, "_get_document_count", return_value=1):
                            response = viewset.sync_files(SimpleNamespace())

    payload = response.data
    defaults = created.get("defaults", {})
    checks = [
        response.status_code == 200,
        payload.get("added_count") == 1,
        payload.get("removed_count") == 0,
        created.get("lookup") == {"filename": "123e4567-e89b-12d3-a456-426614174000 Sample_sync.pdf"},
        defaults.get("title") == "Sample sync",
        defaults.get("file_path") == str(sample_file),
    ]
    return result(
        "sync_files_add_smoke",
        "pass" if all(checks) else "fail",
        {
            "response_status": response.status_code,
            "payload": payload,
            "lookup": created.get("lookup"),
            "defaults": defaults,
        },
    )


def check_extraction_legacy_unrouted_helpers():
    extraction_source = Path(BACKEND_DIR / "pdf_processor" / "views_extraction.py").read_text(encoding="utf-8")
    checks = [
        "def legacy_sync_extraction_to_meteorite(" in extraction_source,
        "def legacy_sync_batch_extractions(" in extraction_source,
        "def legacy_sync_recent_extractions(" in extraction_source,
        "def legacy_get_sync_statistics(" in extraction_source,
        "def legacy_cleanup_duplicate_meteorites(" in extraction_source,
        "def sync_extraction_to_meteorite(" not in extraction_source,
        "def sync_batch_extractions(" not in extraction_source,
    ]
    return result(
        "extraction_legacy_unrouted_helpers",
        "pass" if all(checks) else "fail",
        {
            "legacy_sync_single": "def legacy_sync_extraction_to_meteorite(" in extraction_source,
            "legacy_sync_batch": "def legacy_sync_batch_extractions(" in extraction_source,
            "legacy_sync_recent": "def legacy_sync_recent_extractions(" in extraction_source,
            "legacy_stats": "def legacy_get_sync_statistics(" in extraction_source,
            "legacy_cleanup": "def legacy_cleanup_duplicate_meteorites(" in extraction_source,
        },
    )


def check_direct_processing_legacy_unrouted_actions():
    source = inspect.getsource(DirectProcessingViewSet).replace("\r\n", "\n")
    checks = [
        "def legacy_submit_feedback(" in source,
        "def legacy_get_optimization_suggestions(" in source,
        "def legacy_optimize_system(" in source,
        "def legacy_get_system_performance(" in source,
        "@action(detail=False, methods=['post'])\n    def submit_feedback" not in source,
        "@action(detail=False, methods=['get'])\n    def get_optimization_suggestions" not in source,
        "@action(detail=False, methods=['post'])\n    def optimize_system" not in source,
        "@action(detail=False, methods=['get'])\n    def get_system_performance" not in source,
    ]
    return result(
        "direct_processing_legacy_unrouted_actions",
        "pass" if all(checks) else "fail",
        {
            "legacy_submit_feedback": "def legacy_submit_feedback(" in source,
            "legacy_get_optimization_suggestions": "def legacy_get_optimization_suggestions(" in source,
            "legacy_optimize_system": "def legacy_optimize_system(" in source,
            "legacy_get_system_performance": "def legacy_get_system_performance(" in source,
        },
    )


def check_batch_extraction_live_progress_updates():
    fake_task = SimpleNamespace(
        task_id="batch-progress-task",
        status="running",
        total_documents=0,
        processed_documents=0,
        successful_extractions=0,
        failed_extractions=0,
        results={},
        save_calls=[],
    )

    def fake_save(*args, **kwargs):
        fake_task.save_calls.append(kwargs.get("update_fields"))

    fake_task.save = fake_save

    class FakeTaskManager:
        def get(self, task_id):
            if task_id != fake_task.task_id:
                raise AssertionError(f"unexpected task_id {task_id}")
            return fake_task

    class FakeDocManager:
        def filter(self, **kwargs):
            doc_ids = kwargs.get("id__in", [])
            docs = [SimpleNamespace(id=doc_id, title=f"title-{doc_id}") for doc_id in doc_ids]
            return FakeChainedQuerySet(docs)

    service = BatchExtractionService()
    documents = [
        SimpleNamespace(id="doc-1", title="Doc One"),
        SimpleNamespace(id="doc-2", title="Doc Two"),
    ]

    with patch("pdf_processor.batch_extraction_service.time.sleep", lambda _seconds: None):
        with patch("pdf_processor.batch_extraction_service.DataExtractionTask.objects", FakeTaskManager()):
            with patch.object(PDFDocument, "objects", FakeDocManager()):
                with patch(
                    "pdf_processor.batch_extraction_service.rag_meteorite_extractor.extract_from_existing_documents",
                    side_effect=[
                        {"status": "completed", "results": [{"success": True, "document_id": "doc-1"}]},
                        {"status": "completed", "results": [{"success": True, "document_id": "doc-2"}]},
                    ],
                ):
                    extracted = service.extract_from_document_batch(
                        fake_task.task_id,
                        documents,
                        ["meteorite", "organic"],
                        batch_num=0,
                        total_batches=3,
                        total_docs=20,
                        processed_before_batch=0,
                    )

    latest_progress = fake_task.results.get("latest_progress", {})
    checks = [
        extracted == 2,
        latest_progress.get("current_batch") == 1,
        latest_progress.get("total_batches") == 3,
        latest_progress.get("processed_documents", 0) > 0,
        latest_progress.get("successful_extractions") == 2,
        latest_progress.get("progress_percentage", 0) > 0,
        bool(fake_task.save_calls),
    ]
    return result(
        "batch_extraction_live_progress_updates",
        "pass" if all(checks) else "fail",
        {
            "extracted": extracted,
            "latest_progress": latest_progress,
            "save_calls": fake_task.save_calls,
        },
    )


def check_sync_command_source_uses_canonical_mapping():
    source = inspect.getsource(SyncCommand.sync_pdfs)
    checks = [
        "collect_sync_folder_files" in source,
        "collect_sync_canonical_records" in source,
        "Path(doc.file_path).name" not in source,
        "f.name: f for f in self.pdf_dir.glob('*.pdf')" not in source,
    ]
    return result(
        "sync_command_source_uses_canonical_mapping",
        "pass" if all(checks) else "fail",
        {
            "uses_folder_helper": "collect_sync_folder_files" in source,
            "uses_db_helper": "collect_sync_canonical_records" in source,
            "uses_old_db_key": "Path(doc.file_path).name" in source,
            "uses_old_folder_key": "f.name: f for f in self.pdf_dir.glob('*.pdf')" in source,
        },
    )


def check_sync_command_duplicate_child_transparent():
    created = {"delete_calls": 0}

    with tempfile.TemporaryDirectory() as temp_dir:
        pdf_dir = Path(temp_dir) / "data" / "pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        sample_file = pdf_dir / "canonical-command.pdf"
        sample_file.write_bytes(b"%PDF-1.4 sync canonical command")

        class FakeDoc:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
                self.deleted = False

            def delete(self):
                self.deleted = True
                created["delete_calls"] += 1

        canonical = FakeDoc(
            id="canonical-command-doc",
            filename="canonical-command-alias.pdf",
            file_path=str(sample_file),
            file_size=sample_file.stat().st_size,
            sha1="sha1-command-canonical",
            duplicate_of=None,
        )
        child = FakeDoc(
            id="child-command-doc",
            filename="child-command-copy.pdf",
            file_path=str(sample_file),
            file_size=sample_file.stat().st_size,
            sha1="sha1-command-canonical",
            duplicate_of=canonical,
        )

        class FakeSyncManager:
            def all(self):
                return FakeChainedQuerySet([canonical, child])

            def create(self, **kwargs):
                created["create_kwargs"] = kwargs
                return FakeDoc(id="created-doc", duplicate_of=None, **kwargs)

        command = SyncCommand()
        command.pdf_dir = pdf_dir

        with patch.object(PDFDocument, "objects", FakeSyncManager()):
            added, removed = command.sync_pdfs()

    checks = [
        added == 0,
        removed == 0,
        "create_kwargs" not in created,
        created["delete_calls"] == 0,
        canonical.deleted is False,
        child.deleted is False,
    ]
    return result(
        "sync_command_duplicate_child_transparent",
        "pass" if all(checks) else "fail",
        {
            "added": added,
            "removed": removed,
            "created": created.get("create_kwargs"),
            "delete_calls": created["delete_calls"],
            "canonical_deleted": canonical.deleted,
            "child_deleted": child.deleted,
        },
    )


def check_sync_command_missing_canonical_removes_only_canonical():
    created = {"delete_calls": 0}

    with tempfile.TemporaryDirectory() as temp_dir:
        pdf_dir = Path(temp_dir) / "data" / "pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        missing_path = pdf_dir / "missing-command.pdf"

        class FakeDoc:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
                self.deleted = False

            def delete(self):
                self.deleted = True
                created["delete_calls"] += 1

        canonical = FakeDoc(
            id="canonical-command-missing",
            filename="canonical-command-missing.pdf",
            file_path=str(missing_path),
            file_size=123,
            sha1="sha1-command-missing",
            duplicate_of=None,
        )
        child = FakeDoc(
            id="child-command-missing",
            filename="child-command-missing.pdf",
            file_path=str(missing_path),
            file_size=123,
            sha1="sha1-command-missing",
            duplicate_of=canonical,
        )

        class FakeSyncManager:
            def all(self):
                return FakeChainedQuerySet([canonical, child])

            def create(self, **kwargs):
                created["create_kwargs"] = kwargs
                return FakeDoc(id="created-doc", duplicate_of=None, **kwargs)

        command = SyncCommand()
        command.pdf_dir = pdf_dir

        with patch.object(PDFDocument, "objects", FakeSyncManager()):
            added, removed = command.sync_pdfs()

    checks = [
        added == 0,
        removed == 1,
        created["delete_calls"] == 1,
        canonical.deleted is True,
        child.deleted is False,
    ]
    return result(
        "sync_command_missing_canonical_removes_only_canonical",
        "pass" if all(checks) else "fail",
        {
            "added": added,
            "removed": removed,
            "delete_calls": created["delete_calls"],
            "canonical_deleted": canonical.deleted,
            "child_deleted": child.deleted,
        },
    )


def check_sync_command_orphan_child_flagged_not_synced():
    with tempfile.TemporaryDirectory() as temp_dir:
        pdf_dir = Path(temp_dir) / "data" / "pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        orphan_file = pdf_dir / "orphan-command.pdf"
        orphan_file.write_bytes(b"%PDF-1.4 orphan command")

        broken_parent = SimpleNamespace(id="broken-command-parent", file_path="", duplicate_of=None)

        class FakeDoc:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
                self.deleted = False

            def delete(self):
                self.deleted = True

        orphan_child = FakeDoc(
            id="orphan-command-child",
            filename="orphan-command-child.pdf",
            file_path=str(orphan_file),
            file_size=orphan_file.stat().st_size,
            sha1="sha1-command-orphan",
            duplicate_of=broken_parent,
        )

        class FakeSyncManager:
            def all(self):
                return FakeChainedQuerySet([orphan_child])

            def create(self, **kwargs):
                raise AssertionError("orphan child should not create canonical records during sync")

        command = SyncCommand()
        command.pdf_dir = pdf_dir
        sync_logger = MagicMock()

        with patch("pdf_processor.management.commands.sync_pdfs.logger", sync_logger):
            with patch.object(PDFDocument, "objects", FakeSyncManager()):
                added, removed = command.sync_pdfs()

    warning_calls = " ".join(str(call) for call in sync_logger.warning.call_args_list)
    checks = [
        added == 0,
        removed == 0,
        orphan_child.deleted is False,
        "sync_pdfs_orphan_child" in warning_calls,
        "orphan-command-child" in warning_calls,
    ]
    return result(
        "sync_command_orphan_child_flagged_not_synced",
        "pass" if all(checks) else "fail",
        {
            "added": added,
            "removed": removed,
            "orphan_deleted": orphan_child.deleted,
            "warning_calls": warning_calls,
        },
    )


def check_sync_files_source_uses_canonical_mapping():
    source = inspect.getsource(WeaviatePDFViewSet.sync_files)
    checks = [
        "_collect_sync_folder_files" in source,
        "_collect_sync_canonical_records" in source,
        "Path(doc['file_path']).name" not in source,
        "folder_files[f.name]" not in source,
    ]
    return result(
        "sync_files_source_uses_canonical_mapping",
        "pass" if all(checks) else "fail",
        {
            "uses_folder_helper": "_collect_sync_folder_files" in source,
            "uses_db_helper": "_collect_sync_canonical_records" in source,
            "uses_old_db_key": "Path(doc['file_path']).name" in source,
            "uses_old_folder_key": "folder_files[f.name]" in source,
        },
    )


def check_sync_files_duplicate_child_transparent():
    created = {"delete_ids": None}

    class FakeDeleteQuerySet:
        def delete(self):
            created["delete_ids"] = []
            return (0, {})

    with tempfile.TemporaryDirectory() as temp_dir:
        pdf_dir = Path(temp_dir) / "data" / "pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        sample_file = pdf_dir / "canonical-sync.pdf"
        sample_file.write_bytes(b"%PDF-1.4 sync canonical")

        canonical = SimpleNamespace(
            id="canonical-sync-doc",
            filename="canonical-alias.pdf",
            file_path=str(sample_file),
            file_size=sample_file.stat().st_size,
            sha1="sha1-canonical-sync",
            duplicate_of=None,
        )
        child = SimpleNamespace(
            id="child-sync-doc",
            filename="review-copy.pdf",
            file_path=str(sample_file),
            file_size=sample_file.stat().st_size,
            sha1="sha1-canonical-sync",
            duplicate_of=canonical,
        )

        create_mock = MagicMock()
        vector_service = MagicMock()
        viewset = WeaviatePDFViewSet()
        viewset.processor = SimpleNamespace(vector_service=vector_service)

        def fake_filter(self, **kwargs):
            if "id__in" in kwargs:
                created["delete_ids"] = list(kwargs["id__in"])
                return FakeDeleteQuerySet()
            return FakeChainedQuerySet([])

        with override_settings(PDF_STORAGE_PATH=str(pdf_dir)):
            with patch.object(WeaviatePDFViewSet, "_get_all_documents", return_value=FakeChainedQuerySet([canonical, child])):
                with patch.object(WeaviatePDFViewSet, "_get_or_create_document", create_mock):
                    with patch.object(WeaviatePDFViewSet, "_filter_documents", fake_filter):
                        with patch.object(WeaviatePDFViewSet, "_get_document_count", return_value=2):
                            response = viewset.sync_files(SimpleNamespace())

    payload = response.data
    checks = [
        response.status_code == 200,
        payload.get("added_count") == 0,
        payload.get("removed_count") == 0,
        payload.get("db_count_before") == 1,
        create_mock.call_count == 0,
        vector_service.delete_document.call_count == 0,
        created["delete_ids"] is None,
    ]
    return result(
        "sync_files_duplicate_child_transparent",
        "pass" if all(checks) else "fail",
        {
            "response_status": response.status_code,
            "payload": payload,
            "create_calls": create_mock.call_count,
            "vector_delete_calls": vector_service.delete_document.call_count,
            "delete_ids": created["delete_ids"],
        },
    )


def check_sync_files_missing_canonical_removes_only_canonical():
    created = {"delete_ids": None}

    class FakeDeleteQuerySet:
        def __init__(self, doc_ids):
            self._doc_ids = list(doc_ids)

        def delete(self):
            return (len(self._doc_ids), {})

    with tempfile.TemporaryDirectory() as temp_dir:
        pdf_dir = Path(temp_dir) / "data" / "pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        missing_path = pdf_dir / "missing-sync.pdf"

        canonical = SimpleNamespace(
            id="canonical-missing-doc",
            filename="canonical-missing.pdf",
            file_path=str(missing_path),
            file_size=123,
            sha1="sha1-missing",
            duplicate_of=None,
        )
        child = SimpleNamespace(
            id="child-missing-doc",
            filename="child-missing.pdf",
            file_path=str(missing_path),
            file_size=123,
            sha1="sha1-missing",
            duplicate_of=canonical,
        )

        vector_service = MagicMock()
        viewset = WeaviatePDFViewSet()
        viewset.processor = SimpleNamespace(vector_service=vector_service)

        def fake_filter(self, **kwargs):
            if "id__in" in kwargs:
                created["delete_ids"] = list(kwargs["id__in"])
                return FakeDeleteQuerySet(kwargs["id__in"])
            return FakeChainedQuerySet([])

        with override_settings(PDF_STORAGE_PATH=str(pdf_dir)):
            with patch.object(WeaviatePDFViewSet, "_get_all_documents", return_value=FakeChainedQuerySet([canonical, child])):
                with patch.object(WeaviatePDFViewSet, "_filter_documents", fake_filter):
                    with patch.object(WeaviatePDFViewSet, "_get_document_count", return_value=1):
                        response = viewset.sync_files(SimpleNamespace())

    payload = response.data
    vector_delete_ids = [str(call.args[0]) for call in vector_service.delete_document.call_args_list]
    checks = [
        response.status_code == 200,
        payload.get("removed_count") == 1,
        created["delete_ids"] == ["canonical-missing-doc"],
        vector_delete_ids == ["canonical-missing-doc"],
    ]
    return result(
        "sync_files_missing_canonical_removes_only_canonical",
        "pass" if all(checks) else "fail",
        {
            "response_status": response.status_code,
            "payload": payload,
            "delete_ids": created["delete_ids"],
            "vector_delete_ids": vector_delete_ids,
        },
    )


def check_sync_files_orphan_child_flagged_not_synced():
    broken_parent = SimpleNamespace(
        id="broken-sync-parent",
        file_path="",
        duplicate_of=None,
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        pdf_dir = Path(temp_dir) / "data" / "pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        orphan_file = pdf_dir / "orphan-sync.pdf"
        orphan_file.write_bytes(b"%PDF-1.4 orphan sync")

        orphan_child = SimpleNamespace(
            id="orphan-sync-child",
            filename="orphan-sync-child.pdf",
            file_path=str(orphan_file),
            file_size=orphan_file.stat().st_size,
            sha1="sha1-orphan-sync",
            duplicate_of=broken_parent,
        )

        create_mock = MagicMock()
        vector_service = MagicMock()
        sync_logger = MagicMock()
        viewset = WeaviatePDFViewSet()
        viewset.processor = SimpleNamespace(vector_service=vector_service)

        def fake_filter(self, **kwargs):
            if "id__in" in kwargs:
                return FakeChainedQuerySet([])
            return FakeChainedQuerySet([])

        with override_settings(PDF_STORAGE_PATH=str(pdf_dir)):
            with patch("pdf_processor.weaviate_views.logger", sync_logger):
                with patch.object(WeaviatePDFViewSet, "_get_all_documents", return_value=FakeChainedQuerySet([orphan_child])):
                    with patch.object(WeaviatePDFViewSet, "_get_or_create_document", create_mock):
                        with patch.object(WeaviatePDFViewSet, "_filter_documents", fake_filter):
                            with patch.object(WeaviatePDFViewSet, "_get_document_count", return_value=1):
                                response = viewset.sync_files(SimpleNamespace())

    payload = response.data
    warning_calls = " ".join(str(call) for call in sync_logger.warning.call_args_list)
    checks = [
        response.status_code == 200,
        payload.get("added_count") == 0,
        payload.get("removed_count") == 0,
        create_mock.call_count == 0,
        vector_service.delete_document.call_count == 0,
        "sync_files_orphan_child" in warning_calls,
        "orphan-sync-child" in warning_calls,
    ]
    return result(
        "sync_files_orphan_child_flagged_not_synced",
        "pass" if all(checks) else "fail",
        {
            "response_status": response.status_code,
            "payload": payload,
            "create_calls": create_mock.call_count,
            "vector_delete_calls": vector_service.delete_document.call_count,
            "warning_calls": warning_calls,
        },
    )


def check_same_name_different_content_identification():
    if not hasattr(UploadStorageService, "inspect_duplicate_markers"):
        return result(
            "same_name_different_content_identification",
            "fail",
            {"missing": "UploadStorageService.inspect_duplicate_markers"},
        )

    existing_doc = SimpleNamespace(id="conflict-doc", sha1="other-sha1", filename="conflict.pdf")

    class FakeManager:
        def filter(self, **kwargs):
            if kwargs.get("filename") == "conflict.pdf":
                return FakeQuerySet(existing_doc)
            if kwargs.get("sha1") == "sha1-sample":
                return FakeQuerySet()
            return FakeQuerySet()

    with patch.object(PDFDocument, "objects", FakeManager()):
        inspection = UploadStorageService.inspect_duplicate_markers("conflict.pdf", "sha1-sample")

    checks = [
        inspection.filename_conflict is True,
        inspection.duplicate_detected is False,
        inspection.filename_conflict_document_id == "conflict-doc",
        inspection.filename_conflict_same_content is False,
    ]
    return result(
        "same_name_different_content_identification",
        "pass" if all(checks) else "fail",
        {
            "filename_conflict": getattr(inspection, "filename_conflict", None),
            "duplicate_detected": getattr(inspection, "duplicate_detected", None),
            "filename_conflict_document_id": getattr(inspection, "filename_conflict_document_id", None),
            "filename_conflict_same_content": getattr(inspection, "filename_conflict_same_content", None),
        },
    )


def check_different_name_same_content_identification():
    if not hasattr(UploadStorageService, "inspect_duplicate_markers"):
        return result(
            "different_name_same_content_identification",
            "fail",
            {"missing": "UploadStorageService.inspect_duplicate_markers"},
        )

    existing_doc = SimpleNamespace(id="duplicate-doc", sha1="sha1-sample", filename="existing.pdf")

    class FakeManager:
        def filter(self, **kwargs):
            if kwargs.get("filename") == "new-name.pdf":
                return FakeQuerySet()
            if kwargs.get("sha1") == "sha1-sample":
                return FakeQuerySet(existing_doc)
            return FakeQuerySet()

    with patch.object(PDFDocument, "objects", FakeManager()):
        inspection = UploadStorageService.inspect_duplicate_markers("new-name.pdf", "sha1-sample")

    checks = [
        inspection.duplicate_detected is True,
        inspection.duplicate_document_id == "duplicate-doc",
        inspection.filename_conflict is False,
    ]
    return result(
        "different_name_same_content_identification",
        "pass" if all(checks) else "fail",
        {
            "duplicate_detected": getattr(inspection, "duplicate_detected", None),
            "duplicate_document_id": getattr(inspection, "duplicate_document_id", None),
            "filename_conflict": getattr(inspection, "filename_conflict", None),
        },
    )


def check_user_vs_direct_duplicate_logging():
    if not hasattr(UploadStorageService, "inspect_uploaded_file"):
        return result(
            "user_vs_direct_duplicate_logging",
            "fail",
            {"missing": "UploadStorageService.inspect_uploaded_file"},
        )

    created = {}
    factory = APIRequestFactory()
    request = factory.post(
        "/api/direct-processing/process/",
        {"file": SimpleUploadedFile("direct.pdf", b"%PDF-1.4 direct", content_type="application/pdf")},
        format="multipart",
    )
    request.user = SimpleNamespace(is_authenticated=False)

    class FakeTaskManager:
        def create(self, **kwargs):
            created["task_kwargs"] = kwargs
            return SimpleNamespace(task_id="task-1", status="pending", document_path=kwargs["document_path"])

    class FakeLogManager:
        def create(self, **kwargs):
            created.setdefault("logs", []).append(kwargs)
            return SimpleNamespace(id=1)

    duplicate_inspection = build_duplicate_inspection(
        original_filename="direct.pdf",
        duplicate_detected=True,
        duplicate_sha1="sha1-sample",
        duplicate_document_id="existing-user-doc",
    )

    direct_logger = MagicMock()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "direct.pdf"
        temp_file.write_bytes(b"%PDF-1.4 direct")

        with patch("pdf_processor.views.direct_processing_views.logger", direct_logger):
            with patch.object(UploadStorageService, "inspect_uploaded_file", return_value=duplicate_inspection):
                with patch.object(DirectProcessingViewSet, "_save_uploaded_file", return_value=str(temp_file)):
                    with patch("pdf_processor.views.direct_processing_views.validate_pdf_file", return_value={"valid": True}):
                        with patch.object(DirectProcessingViewSet, "_process_document_async", lambda self, task: None):
                            with patch.object(ProcessingTask, "objects", FakeTaskManager()):
                                with patch("pdf_processor.views.direct_processing_views.ProcessingLog.objects", FakeLogManager()):
                                    with patch("pdf_processor.views.direct_processing_views.DirectDocumentProcessor", return_value=SimpleNamespace()):
                                        viewset = DirectProcessingViewSet()
                                        response = viewset.process_document(request)

    info_calls = " ".join(str(call) for call in direct_logger.info.call_args_list)
    checks = [
        response.status_code == 200,
        "existing-user-doc" in info_calls,
    ]
    return result(
        "user_vs_direct_duplicate_logging",
        "pass" if all(checks) else "fail",
        {
            "response_status": response.status_code,
            "info_calls": info_calls,
        },
    )


def check_user_vs_weaviate_duplicate_logging():
    if not hasattr(UploadStorageService, "inspect_uploaded_file"):
        return result(
            "user_vs_weaviate_duplicate_logging",
            "fail",
            {"missing": "UploadStorageService.inspect_uploaded_file"},
        )

    created = {}
    factory = APIRequestFactory()
    fake_processor = FakeProcessor()
    fake_pdf_utils = make_fake_pdf_utils()
    fake_fitz = make_fake_fitz()

    class FakeDocument:
        def __init__(self, **kwargs):
            self.id = "weaviate-doc-1"
            self.upload_date = timezone.now()
            self.file_path = kwargs["file_path"]
            self.title = kwargs["title"]
            self.authors = kwargs.get("authors", "")
            self.year = kwargs.get("year")
            self.journal = kwargs.get("journal", "")
            self.doi = kwargs.get("doi", "")
            self.category = kwargs.get("category", "general")
            self.processed = kwargs.get("processed", False)
            self.page_count = kwargs.get("page_count", 0)

        def save(self):
            return None

    def fake_filter(self, **kwargs):
        created["filter_kwargs"] = kwargs
        return FakeQuerySet()

    def fake_create(self, **kwargs):
        created["create_kwargs"] = kwargs
        return FakeDocument(**kwargs)

    duplicate_inspection = build_duplicate_inspection(
        original_filename="library-copy.pdf",
        duplicate_detected=True,
        duplicate_sha1="sha1-sample",
        duplicate_document_id="existing-user-doc",
    )
    duplicate_doc = SimpleNamespace(
        id="existing-user-doc",
        title="existing-user",
        filename="existing-user.pdf",
        upload_date=timezone.now(),
    )

    weaviate_logger = MagicMock()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_pdf_root = Path(temp_dir) / "data" / "pdfs"
        request = factory.post(
            "/api/pdf/documents/upload/",
            {
                "file": SimpleUploadedFile("library-copy.pdf", b"%PDF-1.4 library", content_type="application/pdf"),
                "title": "library",
                "category": "general",
            },
            format="multipart",
        )

        with patch("pdf_processor.weaviate_views.logger", weaviate_logger):
            with patch("pdf_processor.weaviate_views._GLOBAL_PROCESSOR", fake_processor):
                with override_settings(PDF_STORAGE_PATH=str(temp_pdf_root)):
                    with patch.object(UploadStorageService, "inspect_uploaded_file", return_value=duplicate_inspection):
                        with patch.object(WeaviatePDFViewSet, "_filter_documents", fake_filter):
                            with patch.object(WeaviatePDFViewSet, "_get_document_or_none", return_value=duplicate_doc):
                                with patch.object(WeaviatePDFViewSet, "_create_document", fake_create):
                                    with patch("threading.Thread", FakeThread):
                                        with patch.dict(sys.modules, {"fitz": fake_fitz, "pdf_processor.pdf_utils": fake_pdf_utils}):
                                            response = WeaviatePDFViewSet.as_view({"post": "upload"})(request)

    response.render()
    payload = json.loads(response.content.decode("utf-8"))
    info_calls = " ".join(str(call) for call in weaviate_logger.info.call_args_list)
    checks = [
        response.status_code == 200,
        payload.get("existing") is True,
        payload.get("document_id") == "existing-user-doc",
        "weaviate_existing_hit" in info_calls,
        "existing-user-doc" in info_calls,
    ]
    return result(
        "user_vs_weaviate_duplicate_logging",
        "pass" if all(checks) else "fail",
        {
            "response_status": response.status_code,
            "payload": payload,
            "info_calls": info_calls,
        },
    )


def check_user_same_name_same_content_keeps_filename_guard():
    existing_doc = SimpleNamespace(id="same-name-doc", filename="same-name.pdf", sha1="sha1-sample")
    factory = APIRequestFactory()
    duplicate_inspection = build_duplicate_inspection(
        original_filename="same-name.pdf",
        duplicate_detected=True,
        duplicate_sha1="sha1-sample",
        duplicate_document_id="same-name-doc",
        filename_conflict=True,
        filename_conflict_document_id="same-name-doc",
        filename_conflict_same_content=True,
    )

    class FakeManager:
        def filter(self, **kwargs):
            if kwargs.get("filename") == "same-name.pdf":
                return FakeQuerySet(existing_doc)
            return FakeQuerySet()

    request = factory.post(
        "/api/pdf/documents/user-upload/",
        {"files": [SimpleUploadedFile("same-name.pdf", b"%PDF-1.4 same-name", content_type="application/pdf")]},
        format="multipart",
    )

    with patch.object(UploadStorageService, "inspect_uploaded_file", return_value=duplicate_inspection):
        with patch.object(UploadStorageService, "save_uploaded_file") as save_mock:
            with patch.object(views_user_upload.PDFDocument, "objects", FakeManager()):
                response = views_user_upload.user_upload_pdfs(request)

    checks = [
        response.status_code == 200,
        response.data["results"][0]["success"] is False,
        response.data["results"][0]["document_id"] == "same-name-doc",
        save_mock.call_count == 0,
    ]
    return result(
        "user_same_name_same_content_keeps_filename_guard",
        "pass" if all(checks) else "fail",
        {
            "response_status": response.status_code,
            "payload": response.data,
            "save_calls": save_mock.call_count,
        },
    )


def check_user_same_name_different_content_keeps_filename_guard():
    existing_doc = SimpleNamespace(id="conflict-doc", filename="conflict.pdf", sha1="other-sha1")
    factory = APIRequestFactory()
    duplicate_inspection = build_duplicate_inspection(
        original_filename="conflict.pdf",
        duplicate_detected=False,
        filename_conflict=True,
        filename_conflict_document_id="conflict-doc",
        filename_conflict_same_content=False,
    )

    class FakeManager:
        def filter(self, **kwargs):
            if kwargs.get("filename") == "conflict.pdf":
                return FakeQuerySet(existing_doc)
            return FakeQuerySet()

    request = factory.post(
        "/api/pdf/documents/user-upload/",
        {"files": [SimpleUploadedFile("conflict.pdf", b"%PDF-1.4 other-content", content_type="application/pdf")]},
        format="multipart",
    )

    user_upload_logger = MagicMock()

    with patch("pdf_processor.views_user_upload.logger", user_upload_logger):
        with patch.object(UploadStorageService, "inspect_uploaded_file", return_value=duplicate_inspection):
            with patch.object(UploadStorageService, "save_uploaded_file") as save_mock:
                with patch.object(views_user_upload.PDFDocument, "objects", FakeManager()):
                    response = views_user_upload.user_upload_pdfs(request)

    info_calls = " ".join(str(call) for call in user_upload_logger.info.call_args_list)
    checks = [
        response.status_code == 200,
        response.data["results"][0]["success"] is False,
        response.data["results"][0]["document_id"] == "conflict-doc",
        save_mock.call_count == 0,
        "filename_conflict=True" in info_calls,
    ]
    return result(
        "user_same_name_different_content_keeps_filename_guard",
        "pass" if all(checks) else "fail",
        {
            "response_status": response.status_code,
            "payload": response.data,
            "save_calls": save_mock.call_count,
            "info_calls": info_calls,
        },
    )


def check_user_different_name_same_content_pending_action():
    created = {}
    factory = APIRequestFactory()
    fake_pdf_utils = make_fake_pdf_utils()
    fake_fitz = make_fake_fitz()

    duplicate_doc = SimpleNamespace(
        id="canonical-doc",
        title="canonical-title",
        authors="canonical-author",
        year=2020,
        journal="Canonical Journal",
        doi="10.1234/canonical",
        file_path="",
        file_size=2048,
        page_count=6,
        sha1="sha1-sample",
        duplicate_of=None,
        review_status="approved",
    )

    duplicate_inspection = build_duplicate_inspection(
        original_filename="new-name.pdf",
        duplicate_detected=True,
        duplicate_sha1="sha1-sample",
        duplicate_document_id="canonical-doc",
        filename_conflict=False,
    )

    class FakeManager:
        def filter(self, **kwargs):
            if kwargs.get("filename") == "new-name.pdf":
                return FakeQuerySet()
            if kwargs.get("id") == "canonical-doc":
                return FakeQuerySet(duplicate_doc)
            return FakeQuerySet()

        def create(self, **kwargs):
            created["create_kwargs"] = kwargs
            return SimpleNamespace(id="pending-duplicate-doc", title=kwargs["title"])

    with tempfile.TemporaryDirectory() as temp_dir:
        existing_file = Path(temp_dir) / "canonical.pdf"
        existing_file.write_bytes(b"%PDF-1.4 canonical")
        duplicate_doc.file_path = str(existing_file)

        request = factory.post(
            "/api/pdf/documents/user-upload/",
            {"files": [SimpleUploadedFile("new-name.pdf", b"%PDF-1.4 canonical", content_type="application/pdf")]},
            format="multipart",
        )

        fake_stored_upload = SimpleNamespace(
            file_path=str(Path(temp_dir) / "uploads" / "new-name.pdf"),
            sha1="sha1-sample",
        )

        user_upload_logger = MagicMock()

        with patch("pdf_processor.views_user_upload.logger", user_upload_logger):
            with patch.dict(sys.modules, {"fitz": fake_fitz, "pdf_processor.pdf_utils": fake_pdf_utils}):
                with patch.object(UploadStorageService, "inspect_uploaded_file", return_value=duplicate_inspection):
                    with patch.object(UploadStorageService, "save_uploaded_file", return_value=fake_stored_upload) as save_mock:
                        with patch.object(views_user_upload.PDFDocument, "objects", FakeManager()):
                            response = views_user_upload.user_upload_pdfs(request)

    create_kwargs = created.get("create_kwargs", {})
    info_calls = " ".join(str(call) for call in user_upload_logger.info.call_args_list)
    checks = [
        response.status_code == 200,
        response.data["results"][0]["success"] is True,
        response.data["results"][0]["document_id"] == "pending-duplicate-doc",
        create_kwargs.get("file_path") == duplicate_doc.file_path,
        create_kwargs.get("sha1") == "sha1-sample",
        create_kwargs.get("filename") == "new-name.pdf",
        create_kwargs.get("review_status") == "pending",
        create_kwargs.get("duplicate_of") is duplicate_doc,
        save_mock.call_count == 0,
        "user_upload_duplicate_hit" in info_calls,
    ]
    return result(
        "user_different_name_same_content_pending_action",
        "pass" if all(checks) else "fail",
        {
            "response_status": response.status_code,
            "payload": response.data,
            "create_kwargs": {
                "file_path": create_kwargs.get("file_path"),
                "sha1": create_kwargs.get("sha1"),
                "filename": create_kwargs.get("filename"),
                "review_status": create_kwargs.get("review_status"),
                "duplicate_of": str(getattr(create_kwargs.get("duplicate_of"), "id", None)),
            },
            "save_calls": save_mock.call_count,
            "info_calls": info_calls,
        },
    )


def check_duplicate_hit_pending_reviews_visibility():
    duplicate_doc = SimpleNamespace(
        id="pending-duplicate-doc",
        title="duplicate pending",
        filename="new-name.pdf",
        authors="tester",
        year=2024,
        journal="Journal",
        file_size=2048,
        page_count=6,
        upload_date=timezone.now(),
        review_status="pending",
        review_notes="",
        uploaded_by=SimpleNamespace(username="alice"),
        reviewed_by=None,
        duplicate_of=SimpleNamespace(id="canonical-doc"),
    )

    class FakeDefaultManager:
        def filter(self, **kwargs):
            if kwargs.get("review_status") == "pending":
                return FakeChainedQuerySet([duplicate_doc])
            return FakeChainedQuerySet([])

    class FakePDFDocument:
        _default_manager = FakeDefaultManager()

    factory = APIRequestFactory()
    request = factory.get("/api/pdf/review/pending/?type=pdf&status=pending")
    reviewer = SimpleNamespace(is_authenticated=True, username="reviewer")
    force_authenticate(request, user=reviewer)

    with patch("pdf_processor.views_review.PDFDocument", FakePDFDocument):
        response = views_review.get_pending_reviews(request)

    pdfs = response.data.get("pdfs", [])
    first_pdf = pdfs[0] if pdfs else {}
    checks = [
        response.status_code == 200,
        len(pdfs) == 1,
        first_pdf.get("id") == "pending-duplicate-doc",
        first_pdf.get("filename") == "new-name.pdf",
        first_pdf.get("review_status") == "pending",
    ]
    return result(
        "duplicate_hit_pending_reviews_visibility",
        "pass" if all(checks) else "fail",
        {
            "response_status": response.status_code,
            "payload": response.data,
        },
    )


def check_duplicate_hit_approve_isolated():
    original_doc = SimpleNamespace(
        id="canonical-doc",
        review_status="approved",
        review_notes="old",
        reviewed_by="legacy",
        reviewed_at="old-time",
    )

    class FakeDoc:
        def __init__(self):
            self.id = "pending-duplicate-doc"
            self.review_status = "pending"
            self.review_notes = ""
            self.reviewed_by = None
            self.reviewed_at = None
            self.duplicate_of = original_doc
            self.saved = None

        def save(self, update_fields=None):
            self.saved = list(update_fields or [])

    target_doc = FakeDoc()

    class FakeLockedManager:
        def select_for_update(self):
            return self

        def get(self, id=None):
            return target_doc

    class FakePDFDocument:
        _default_manager = FakeLockedManager()

    reviewer = SimpleNamespace(username="reviewer")

    with patch("pdf_processor.views_review.PDFDocument", FakePDFDocument):
        response = views_review._approve_pdf("pending-duplicate-doc", reviewer, "approved-note")

    checks = [
        response.get("success") is True,
        target_doc.review_status == "approved",
        target_doc.review_notes == "approved-note",
        target_doc.reviewed_by is reviewer,
        original_doc.review_status == "approved",
        original_doc.review_notes == "old",
    ]
    return result(
        "duplicate_hit_approve_isolated",
        "pass" if all(checks) else "fail",
        {
            "response": response,
            "target_status": target_doc.review_status,
            "original_status": original_doc.review_status,
            "saved_fields": target_doc.saved,
        },
    )


def check_duplicate_hit_reject_isolated():
    original_doc = SimpleNamespace(
        id="canonical-doc",
        review_status="approved",
        review_notes="old",
        reviewed_by="legacy",
        reviewed_at="old-time",
    )

    class FakeDoc:
        def __init__(self):
            self.id = "pending-duplicate-doc"
            self.review_status = "pending"
            self.review_notes = ""
            self.reviewed_by = None
            self.reviewed_at = None
            self.duplicate_of = original_doc
            self.saved = None

        def save(self, update_fields=None):
            self.saved = list(update_fields or [])

    target_doc = FakeDoc()

    class FakeLockedManager:
        def select_for_update(self):
            return self

        def get(self, id=None):
            return target_doc

    class FakePDFDocument:
        _default_manager = FakeLockedManager()

    reviewer = SimpleNamespace(username="reviewer")

    with patch("pdf_processor.views_review.PDFDocument", FakePDFDocument):
        response = views_review._reject_pdf("pending-duplicate-doc", reviewer, "reject-note")

    checks = [
        response.get("success") is True,
        target_doc.review_status == "rejected",
        target_doc.review_notes == "reject-note",
        target_doc.reviewed_by is reviewer,
        original_doc.review_status == "approved",
        original_doc.review_notes == "old",
    ]
    return result(
        "duplicate_hit_reject_isolated",
        "pass" if all(checks) else "fail",
        {
            "response": response,
            "target_status": target_doc.review_status,
            "original_status": original_doc.review_status,
            "saved_fields": target_doc.saved,
        },
    )


def check_shared_file_path_download_compatibility():
    with tempfile.TemporaryDirectory() as temp_dir:
        shared_file = Path(temp_dir) / "shared.pdf"
        shared_file.write_bytes(b"%PDF-1.4 shared")

        document = SimpleNamespace(file_path=str(shared_file))
        viewset = WeaviatePDFViewSet()
        viewset.get_object = lambda: document

        response = viewset.download(SimpleNamespace(), pk="duplicate-doc")
        status_code = getattr(response, "status_code", None)
        content_disposition = response.get("Content-Disposition")
        if hasattr(response, "close"):
            response.close()

    checks = [
        status_code == 200,
        content_disposition == 'inline; filename="shared.pdf"',
    ]
    return result(
        "shared_file_path_download_compatibility",
        "pass" if all(checks) else "fail",
        {
            "status_code": status_code,
            "content_disposition": content_disposition,
        },
    )


def check_process_stale_canonical_gap_candidate():
    canonical = SimpleNamespace(
        id="canonical-gap-doc",
        duplicate_of=None,
        processed=True,
        file_path="D:/tmp/canonical-gap.pdf",
    )
    viewset = WeaviatePDFViewSet()
    viewset.processor = SimpleNamespace(
        vector_service=SimpleNamespace(
            has_document_vectors=lambda doc_id: False if doc_id == "canonical-gap-doc" else True
        )
    )

    def fake_filter(self, **kwargs):
        if kwargs == {"processed": False, "duplicate_of__isnull": True}:
            return FakeChainedQuerySet([])
        if kwargs == {"duplicate_of__isnull": False}:
            return FakeChainedQuerySet([])
        if kwargs == {"processed": True, "duplicate_of__isnull": True}:
            return FakeChainedQuerySet([canonical])
        return FakeChainedQuerySet([])

    with patch.object(WeaviatePDFViewSet, "_filter_documents", fake_filter):
        candidates = viewset._collect_stale_candidates()

    candidate_ids = [getattr(doc, "id", None) for doc in candidates]
    checks = [
        candidate_ids == ["canonical-gap-doc"],
    ]
    return result(
        "process_stale_canonical_gap_candidate",
        "pass" if all(checks) else "fail",
        {"candidate_ids": candidate_ids},
    )


def check_process_stale_duplicate_child_skips_when_canonical_healthy():
    canonical = SimpleNamespace(
        id="canonical-healthy-doc",
        duplicate_of=None,
        processed=True,
        file_path=__file__,
    )
    child = SimpleNamespace(
        id="child-healthy-doc",
        duplicate_of=canonical,
        processed=False,
        file_path=__file__,
    )
    viewset = WeaviatePDFViewSet()
    viewset.processor = SimpleNamespace(
        vector_service=SimpleNamespace(
            has_document_vectors=lambda doc_id: True
        )
    )

    def fake_filter(self, **kwargs):
        if kwargs == {"processed": False, "duplicate_of__isnull": True}:
            return FakeChainedQuerySet([])
        if kwargs == {"duplicate_of__isnull": False}:
            return FakeChainedQuerySet([child])
        if kwargs == {"processed": True, "duplicate_of__isnull": True}:
            return FakeChainedQuerySet([canonical])
        return FakeChainedQuerySet([])

    with patch.object(WeaviatePDFViewSet, "_filter_documents", fake_filter):
        candidates = viewset._collect_stale_candidates()

    candidate_ids = [getattr(doc, "id", None) for doc in candidates]
    checks = [
        candidate_ids == [],
    ]
    return result(
        "process_stale_duplicate_child_skips_when_canonical_healthy",
        "pass" if all(checks) else "fail",
        {"candidate_ids": candidate_ids},
    )


def check_process_stale_duplicate_child_delegates_to_canonical():
    canonical = SimpleNamespace(
        id="canonical-unprocessed-doc",
        duplicate_of=None,
        processed=False,
        file_path=__file__,
    )
    child = SimpleNamespace(
        id="child-unprocessed-doc",
        duplicate_of=canonical,
        processed=False,
        file_path=__file__,
    )
    viewset = WeaviatePDFViewSet()
    viewset.processor = SimpleNamespace(
        vector_service=SimpleNamespace(
            has_document_vectors=lambda doc_id: True
        )
    )

    def fake_filter(self, **kwargs):
        if kwargs == {"processed": False, "duplicate_of__isnull": True}:
            return FakeChainedQuerySet([canonical])
        if kwargs == {"duplicate_of__isnull": False}:
            return FakeChainedQuerySet([child])
        if kwargs == {"processed": True, "duplicate_of__isnull": True}:
            return FakeChainedQuerySet([])
        return FakeChainedQuerySet([])

    with patch.object(WeaviatePDFViewSet, "_filter_documents", fake_filter):
        candidates = viewset._collect_stale_candidates()

    candidate_ids = [getattr(doc, "id", None) for doc in candidates]
    checks = [
        candidate_ids == ["canonical-unprocessed-doc"],
    ]
    return result(
        "process_stale_duplicate_child_delegates_to_canonical",
        "pass" if all(checks) else "fail",
        {"candidate_ids": candidate_ids},
    )


def check_process_stale_orphan_child_flagged():
    broken_parent = SimpleNamespace(
        id="broken-parent-doc",
        duplicate_of=None,
        processed=True,
        file_path="",
    )
    orphan_child = SimpleNamespace(
        id="orphan-child-doc",
        duplicate_of=broken_parent,
        processed=False,
        file_path=__file__,
    )
    viewset = WeaviatePDFViewSet()
    viewset.processor = SimpleNamespace(
        vector_service=SimpleNamespace(
            has_document_vectors=lambda doc_id: True
        )
    )
    stale_logger = MagicMock()

    def fake_filter(self, **kwargs):
        if kwargs == {"processed": False, "duplicate_of__isnull": True}:
            return FakeChainedQuerySet([])
        if kwargs == {"duplicate_of__isnull": False}:
            return FakeChainedQuerySet([orphan_child])
        if kwargs == {"processed": True, "duplicate_of__isnull": True}:
            return FakeChainedQuerySet([])
        return FakeChainedQuerySet([])

    with patch("pdf_processor.weaviate_views.logger", stale_logger):
        with patch.object(WeaviatePDFViewSet, "_filter_documents", fake_filter):
            candidates = viewset._collect_stale_candidates()

    warning_calls = " ".join(str(call) for call in stale_logger.warning.call_args_list)
    candidate_ids = [getattr(doc, "id", None) for doc in candidates]
    checks = [
        candidate_ids == [],
        "process_stale_orphan_child" in warning_calls,
        "orphan-child-doc" in warning_calls,
    ]
    return result(
        "process_stale_orphan_child_flagged",
        "pass" if all(checks) else "fail",
        {
            "candidate_ids": candidate_ids,
            "warning_calls": warning_calls,
        },
    )


def check_delete_document_shared_file_keeps_physical_file():
    vector_service = MagicMock()

    class FakeReferenceQuerySet:
        def exclude(self, **kwargs):
            return self

        def exists(self):
            return True

    class FakeManager:
        def filter(self, **kwargs):
            return FakeReferenceQuerySet()

    with tempfile.TemporaryDirectory() as temp_dir:
        shared_file = Path(temp_dir) / "shared.pdf"
        shared_file.write_bytes(b"%PDF-1.4 shared")

        delete_calls = {"count": 0}

        class FakeDocument:
            id = "duplicate-doc-1"
            file_path = str(shared_file)

            def delete(self):
                delete_calls["count"] += 1

        viewset = WeaviatePDFViewSet()
        viewset.processor = SimpleNamespace(vector_service=vector_service)
        viewset.get_object = lambda: FakeDocument()

        with patch("pdf_processor.weaviate_views.PDFDocument.objects", FakeManager()):
            response = viewset.delete_document(SimpleNamespace(), pk="duplicate-doc-1")
        shared_file_exists = shared_file.exists()

    checks = [
        response.status_code == 200,
        shared_file_exists is True,
        delete_calls["count"] == 1,
        vector_service.delete_document.call_count == 1,
    ]
    return result(
        "delete_document_shared_file_keeps_physical_file",
        "pass" if all(checks) else "fail",
        {
            "response_status": response.status_code,
            "shared_file_exists": shared_file_exists,
            "delete_calls": delete_calls["count"],
            "vector_delete_calls": vector_service.delete_document.call_count,
        },
    )


def check_delete_document_last_reference_removes_physical_file():
    vector_service = MagicMock()

    class FakeReferenceQuerySet:
        def exclude(self, **kwargs):
            return self

        def exists(self):
            return False

    class FakeManager:
        def filter(self, **kwargs):
            return FakeReferenceQuerySet()

    with tempfile.TemporaryDirectory() as temp_dir:
        shared_file = Path(temp_dir) / "last-reference.pdf"
        shared_file.write_bytes(b"%PDF-1.4 last-ref")

        delete_calls = {"count": 0}

        class FakeDocument:
            id = "duplicate-doc-2"
            file_path = str(shared_file)

            def delete(self):
                delete_calls["count"] += 1

        viewset = WeaviatePDFViewSet()
        viewset.processor = SimpleNamespace(vector_service=vector_service)
        viewset.get_object = lambda: FakeDocument()

        with patch("pdf_processor.weaviate_views.PDFDocument.objects", FakeManager()):
            response = viewset.delete_document(SimpleNamespace(), pk="duplicate-doc-2")

        shared_file_exists = shared_file.exists()

    checks = [
        response.status_code == 200,
        shared_file_exists is False,
        delete_calls["count"] == 1,
        vector_service.delete_document.call_count == 1,
    ]
    return result(
        "delete_document_last_reference_removes_physical_file",
        "pass" if all(checks) else "fail",
        {
            "response_status": response.status_code,
            "shared_file_exists": shared_file_exists,
            "delete_calls": delete_calls["count"],
            "vector_delete_calls": vector_service.delete_document.call_count,
        },
    )


def check_collect_stale_candidates_not_action_exposed():
    mapping = getattr(WeaviatePDFViewSet._collect_stale_candidates, "mapping", None)
    checks = [mapping is None]
    return result(
        "collect_stale_candidates_not_action_exposed",
        "pass" if all(checks) else "fail",
        {"mapping": str(mapping)},
    )


def check_process_stale_collects_candidates_once():
    viewset = WeaviatePDFViewSet()
    viewset.processor = SimpleNamespace(vector_service=SimpleNamespace())

    with patch("pdf_processor.weaviate_views._PROCESSING_LOCK", False):
        with patch("pdf_processor.weaviate_views._CANCEL_REQUESTED", False):
            with patch.object(WeaviatePDFViewSet, "_collect_stale_candidates", return_value=[]) as collect_mock:
                response = viewset.process_stale(SimpleNamespace())

    checks = [
        response.status_code == 200,
        response.data.get("success") is True,
        collect_mock.call_count == 1,
    ]
    return result(
        "process_stale_collects_candidates_once",
        "pass" if all(checks) else "fail",
        {
            "response_status": response.status_code,
            "payload": response.data,
            "collect_call_count": collect_mock.call_count,
        },
    )


def check_process_stale_processing_smoke():
    class ImmediateThread:
        def __init__(self, target=None, daemon=None):
            self.target = target
            self.daemon = daemon

        def start(self):
            if self.target:
                self.target()

    class FakeDoc:
        def __init__(self):
            self.id = "stale-process-doc"
            self.title = "Stale Doc"
            self.authors = "tester"
            self.year = "2024"
            self.journal = "Journal"
            self.doi = "10.1234/test"
            self.category = "未分类"
            self.upload_date = timezone.now()
            self.file_path = __file__
            self.processed = False
            self.page_count = 0
            self.save_calls = 0

        def save(self):
            self.save_calls += 1

    doc = FakeDoc()
    processor = MagicMock()
    processor.process_single_document.return_value = {"status": "success", "total_pages": 7}

    viewset = WeaviatePDFViewSet()
    viewset.processor = SimpleNamespace(
        process_single_document=processor.process_single_document,
        vector_service=SimpleNamespace(),
    )

    with patch("pdf_processor.weaviate_views._PROCESSING_LOCK", False):
        with patch("pdf_processor.weaviate_views._CANCEL_REQUESTED", False):
            with patch.object(WeaviatePDFViewSet, "_collect_stale_candidates", return_value=[doc]):
                with patch("pdf_processor.weaviate_views.threading.Thread", ImmediateThread):
                    response = viewset.process_stale(SimpleNamespace())

    metadata = processor.process_single_document.call_args.kwargs.get("metadata", {})
    checks = [
        response.status_code == 200,
        response.data.get("success") is True,
        processor.process_single_document.call_count == 1,
        metadata.get("title") == "Stale Doc",
        metadata.get("category") == "未分类",
        doc.processed is True,
        doc.page_count == 7,
        doc.save_calls == 1,
    ]
    return result(
        "process_stale_processing_smoke",
        "pass" if all(checks) else "fail",
        {
            "response_status": response.status_code,
            "payload": response.data,
            "metadata": metadata,
            "processed": doc.processed,
            "page_count": doc.page_count,
            "save_calls": doc.save_calls,
        },
    )


def check_process_pending_canonical_candidate():
    canonical = SimpleNamespace(
        id="canonical-pending-doc",
        duplicate_of=None,
        processed=False,
        file_path=__file__,
    )
    viewset = WeaviatePDFViewSet()

    def fake_filter(self, **kwargs):
        if kwargs == {"processed": False, "duplicate_of__isnull": True}:
            return FakeChainedQuerySet([canonical])
        if kwargs == {"processed": False, "duplicate_of__isnull": False}:
            return FakeChainedQuerySet([])
        return FakeChainedQuerySet([])

    with patch.object(WeaviatePDFViewSet, "_filter_documents", fake_filter):
        candidates = viewset._collect_pending_candidates()

    candidate_ids = [getattr(doc, "id", None) for doc in candidates]
    checks = [candidate_ids == ["canonical-pending-doc"]]
    return result(
        "process_pending_canonical_candidate",
        "pass" if all(checks) else "fail",
        {"candidate_ids": candidate_ids},
    )


def check_process_pending_duplicate_child_skips_when_canonical_healthy():
    canonical = SimpleNamespace(
        id="canonical-pending-healthy-doc",
        duplicate_of=None,
        processed=True,
        file_path=__file__,
    )
    child = SimpleNamespace(
        id="child-pending-healthy-doc",
        duplicate_of=canonical,
        processed=False,
        file_path=__file__,
    )
    viewset = WeaviatePDFViewSet()

    def fake_filter(self, **kwargs):
        if kwargs == {"processed": False, "duplicate_of__isnull": True}:
            return FakeChainedQuerySet([])
        if kwargs == {"processed": False, "duplicate_of__isnull": False}:
            return FakeChainedQuerySet([child])
        return FakeChainedQuerySet([])

    with patch.object(WeaviatePDFViewSet, "_filter_documents", fake_filter):
        candidates = viewset._collect_pending_candidates()

    candidate_ids = [getattr(doc, "id", None) for doc in candidates]
    checks = [candidate_ids == []]
    return result(
        "process_pending_duplicate_child_skips_when_canonical_healthy",
        "pass" if all(checks) else "fail",
        {"candidate_ids": candidate_ids},
    )


def check_process_pending_duplicate_child_delegates_to_canonical():
    canonical = SimpleNamespace(
        id="canonical-pending-unprocessed-doc",
        duplicate_of=None,
        processed=False,
        file_path=__file__,
    )
    child = SimpleNamespace(
        id="child-pending-unprocessed-doc",
        duplicate_of=canonical,
        processed=False,
        file_path=__file__,
    )
    viewset = WeaviatePDFViewSet()

    def fake_filter(self, **kwargs):
        if kwargs == {"processed": False, "duplicate_of__isnull": True}:
            return FakeChainedQuerySet([canonical])
        if kwargs == {"processed": False, "duplicate_of__isnull": False}:
            return FakeChainedQuerySet([child])
        return FakeChainedQuerySet([])

    with patch.object(WeaviatePDFViewSet, "_filter_documents", fake_filter):
        candidates = viewset._collect_pending_candidates()

    candidate_ids = [getattr(doc, "id", None) for doc in candidates]
    checks = [candidate_ids == ["canonical-pending-unprocessed-doc"]]
    return result(
        "process_pending_duplicate_child_delegates_to_canonical",
        "pass" if all(checks) else "fail",
        {"candidate_ids": candidate_ids},
    )


def check_process_pending_orphan_child_flagged():
    broken_parent = SimpleNamespace(
        id="broken-pending-parent-doc",
        duplicate_of=None,
        processed=True,
        file_path="",
    )
    orphan_child = SimpleNamespace(
        id="orphan-pending-child-doc",
        duplicate_of=broken_parent,
        processed=False,
        file_path=__file__,
    )
    viewset = WeaviatePDFViewSet()
    pending_logger = MagicMock()

    def fake_filter(self, **kwargs):
        if kwargs == {"processed": False, "duplicate_of__isnull": True}:
            return FakeChainedQuerySet([])
        if kwargs == {"processed": False, "duplicate_of__isnull": False}:
            return FakeChainedQuerySet([orphan_child])
        return FakeChainedQuerySet([])

    with patch("pdf_processor.weaviate_views.logger", pending_logger):
        with patch.object(WeaviatePDFViewSet, "_filter_documents", fake_filter):
            candidates = viewset._collect_pending_candidates()

    warning_calls = " ".join(str(call) for call in pending_logger.warning.call_args_list)
    candidate_ids = [getattr(doc, "id", None) for doc in candidates]
    checks = [
        candidate_ids == [],
        "process_pending_orphan_child" in warning_calls,
        "orphan-pending-child-doc" in warning_calls,
    ]
    return result(
        "process_pending_orphan_child_flagged",
        "pass" if all(checks) else "fail",
        {
            "candidate_ids": candidate_ids,
            "warning_calls": warning_calls,
        },
    )


def check_process_pending_collects_candidates_once():
    viewset = WeaviatePDFViewSet()
    viewset.processor = SimpleNamespace()

    with patch("pdf_processor.weaviate_views._PROCESSING_LOCK", False):
        with patch("pdf_processor.weaviate_views._CANCEL_REQUESTED", False):
            with patch.object(WeaviatePDFViewSet, "_collect_pending_candidates", return_value=[]) as collect_mock:
                response = viewset.process_pending(SimpleNamespace())

    checks = [
        response.status_code == 200,
        response.data.get("success") is True,
        collect_mock.call_count == 1,
    ]
    return result(
        "process_pending_collects_candidates_once",
        "pass" if all(checks) else "fail",
        {
            "response_status": response.status_code,
            "payload": response.data,
            "collect_call_count": collect_mock.call_count,
        },
    )


def check_process_pending_processing_smoke():
    class ImmediateThread:
        def __init__(self, target=None, daemon=None):
            self.target = target
            self.daemon = daemon

        def start(self):
            if self.target:
                self.target()

    class FakeDoc:
        def __init__(self):
            self.id = "pending-process-doc"
            self.title = "Pending Doc"
            self.authors = "tester"
            self.year = "2024"
            self.journal = "Journal"
            self.doi = "10.1234/test"
            self.category = "未分类"
            self.upload_date = timezone.now()
            self.file_path = __file__
            self.processed = False
            self.page_count = 0
            self.save_calls = 0

        def save(self):
            self.save_calls += 1

    doc = FakeDoc()
    processor = MagicMock()
    processor.process_single_document.return_value = {"status": "success", "total_pages": 5}

    viewset = WeaviatePDFViewSet()
    viewset.processor = SimpleNamespace(process_single_document=processor.process_single_document)

    with patch("pdf_processor.weaviate_views._PROCESSING_LOCK", False):
        with patch("pdf_processor.weaviate_views._CANCEL_REQUESTED", False):
            with patch.object(WeaviatePDFViewSet, "_collect_pending_candidates", return_value=[doc]):
                with patch("threading.Thread", ImmediateThread):
                    response = viewset.process_pending(SimpleNamespace())

    metadata = processor.process_single_document.call_args.kwargs.get("metadata", {})
    checks = [
        response.status_code == 200,
        response.data.get("success") is True,
        response.data.get("status") == "processing",
        processor.process_single_document.call_count == 1,
        metadata.get("title") == "Pending Doc",
        metadata.get("category") == "未分类",
        doc.processed is True,
        doc.page_count == 5,
        doc.save_calls == 1,
    ]
    return result(
        "process_pending_processing_smoke",
        "pass" if all(checks) else "fail",
        {
            "response_status": response.status_code,
            "payload": response.data,
            "metadata": metadata,
            "processed": doc.processed,
            "page_count": doc.page_count,
            "save_calls": doc.save_calls,
        },
    )


def check_record_contract_fields():
    pdf_fields = {field.name for field in PDFDocument._meta.fields}
    task_fields = {field.name for field in ProcessingTask._meta.fields}
    required_pdf = {"filename", "file_path", "processed", "sha1", "review_status", "duplicate_of"}
    required_task = {"document_path", "options", "status"}
    checks = required_pdf.issubset(pdf_fields) and required_task.issubset(task_fields)
    return result(
        "record_contract_fields",
        "pass" if checks else "fail",
        {
            "pdf_fields_present": sorted(required_pdf & pdf_fields),
            "task_fields_present": sorted(required_task & task_fields),
        },
    )


def main():
    checks = [
        check_user_upload,
        check_user_same_name_same_content_keeps_filename_guard,
        check_user_same_name_different_content_keeps_filename_guard,
        check_user_different_name_same_content_pending_action,
        check_duplicate_hit_pending_reviews_visibility,
        check_duplicate_hit_approve_isolated,
        check_duplicate_hit_reject_isolated,
        check_shared_file_path_download_compatibility,
        check_delete_document_shared_file_keeps_physical_file,
        check_delete_document_last_reference_removes_physical_file,
        check_process_stale_canonical_gap_candidate,
        check_process_stale_duplicate_child_skips_when_canonical_healthy,
        check_process_stale_duplicate_child_delegates_to_canonical,
        check_process_stale_orphan_child_flagged,
        check_collect_stale_candidates_not_action_exposed,
        check_process_stale_collects_candidates_once,
        check_process_stale_processing_smoke,
        check_process_pending_canonical_candidate,
        check_process_pending_duplicate_child_skips_when_canonical_healthy,
        check_process_pending_duplicate_child_delegates_to_canonical,
        check_process_pending_orphan_child_flagged,
        check_process_pending_collects_candidates_once,
        check_process_pending_processing_smoke,
        check_sync_files_add_smoke,
        check_sync_files_source_uses_canonical_mapping,
        check_sync_files_duplicate_child_transparent,
        check_sync_files_missing_canonical_removes_only_canonical,
        check_sync_files_orphan_child_flagged_not_synced,
        check_cross_entry_duplicate,
        check_direct_processing,
        check_legacy_path_compatibility,
        check_weaviate_same_name_same_content_existing,
        check_weaviate_different_name_same_content_duplicate_hit,
        check_weaviate_same_name_different_content_keeps_filename_guard,
        check_user_then_weaviate_same_content_duplicate_hit,
        check_same_name_different_content_identification,
        check_different_name_same_content_identification,
        check_user_vs_direct_duplicate_logging,
        check_user_vs_weaviate_duplicate_logging,
        check_reprocess_directory_source,
        check_sync_directory_source,
        check_sync_command_source_uses_canonical_mapping,
        check_sync_command_duplicate_child_transparent,
        check_sync_command_missing_canonical_removes_only_canonical,
        check_sync_command_orphan_child_flagged_not_synced,
        check_extraction_legacy_unrouted_helpers,
        check_direct_processing_legacy_unrouted_actions,
        check_batch_extraction_live_progress_updates,
        check_sync_command_smoke,
        check_record_contract_fields,
        check_weaviate_upload_smoke,
    ]

    results = []
    for check in checks:
        try:
            results.append(check())
        except Exception as exc:
            results.append(
                result(
                    check.__name__,
                    "error",
                    {"error": str(exc)},
                )
            )

    summary = {
        "pass": sum(1 for item in results if item["status"] == "pass"),
        "fail": sum(1 for item in results if item["status"] == "fail"),
        "error": sum(1 for item in results if item["status"] == "error"),
    }
    payload = {
        "summary": summary,
        "results": results,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
