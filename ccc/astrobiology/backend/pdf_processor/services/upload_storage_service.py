from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from django.conf import settings


MEDIA_UPLOADS = "media_uploads"
PDF_LIBRARY = "pdf_library"


@dataclass(frozen=True)
class DuplicateInspection:
    original_filename: str
    sha1: str
    duplicate_detected: bool = False
    duplicate_sha1: Optional[str] = None
    duplicate_document_id: Optional[str] = None
    filename_conflict: bool = False
    filename_conflict_document_id: Optional[str] = None
    filename_conflict_same_content: Optional[bool] = None


@dataclass(frozen=True)
class StoredUpload:
    storage_key: str
    original_filename: str
    stored_filename: str
    file_path: str
    file_size: int
    sha1: str
    duplicate_detected: bool = False
    duplicate_sha1: Optional[str] = None
    duplicate_document_id: Optional[str] = None
    filename_conflict: bool = False
    filename_conflict_document_id: Optional[str] = None
    filename_conflict_same_content: Optional[bool] = None


class UploadStorageService:
    """Centralize upload path resolution and file persistence policy."""

    @staticmethod
    def _backend_base_dir() -> Path:
        return Path(getattr(settings, "BASE_DIR")).resolve()

    @classmethod
    def resolve_media_upload_dir(cls) -> Path:
        return (Path(settings.MEDIA_ROOT).resolve() / "uploads").resolve()

    @classmethod
    def resolve_pdf_storage_dir(cls) -> Path:
        raw_path = getattr(settings, "PDF_STORAGE_PATH", None)
        if raw_path:
            return Path(raw_path).expanduser().resolve()
        return (cls._backend_base_dir().parent / "data" / "pdfs").resolve()

    @classmethod
    def resolve_storage_dir(cls, storage_key: str) -> Path:
        if storage_key == MEDIA_UPLOADS:
            return cls.resolve_media_upload_dir()
        if storage_key == PDF_LIBRARY:
            return cls.resolve_pdf_storage_dir()
        raise ValueError(f"Unsupported storage key: {storage_key}")

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        return Path(filename).name

    @classmethod
    def build_stored_filename(cls, original_filename: str, naming_strategy: str) -> str:
        safe_name = cls._sanitize_filename(original_filename)
        suffix = Path(safe_name).suffix
        if naming_strategy == "uuid":
            return f"{uuid.uuid4()}{suffix}"
        if naming_strategy == "original":
            return safe_name
        raise ValueError(f"Unsupported naming strategy: {naming_strategy}")

    @classmethod
    def save_uploaded_file(
        cls,
        uploaded_file,
        *,
        storage_key: str,
        naming_strategy: str,
        precomputed_inspection: Optional[DuplicateInspection] = None,
    ) -> StoredUpload:
        target_dir = cls.resolve_storage_dir(storage_key)
        target_dir.mkdir(parents=True, exist_ok=True)

        original_filename = cls._sanitize_filename(uploaded_file.name)
        stored_filename = cls.build_stored_filename(original_filename, naming_strategy)
        target_path = target_dir / stored_filename

        with open(target_path, "wb+") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        file_size = int(getattr(uploaded_file, "size", target_path.stat().st_size))
        inspection = precomputed_inspection or cls.inspect_uploaded_file(uploaded_file)
        return StoredUpload(
            storage_key=storage_key,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=str(target_path),
            file_size=file_size,
            sha1=inspection.sha1,
            duplicate_detected=inspection.duplicate_detected,
            duplicate_sha1=inspection.duplicate_sha1,
            duplicate_document_id=inspection.duplicate_document_id,
            filename_conflict=inspection.filename_conflict,
            filename_conflict_document_id=inspection.filename_conflict_document_id,
            filename_conflict_same_content=inspection.filename_conflict_same_content,
        )

    @staticmethod
    def _reset_uploaded_file(uploaded_file) -> None:
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
            return
        file_obj = getattr(uploaded_file, "file", None)
        if file_obj and hasattr(file_obj, "seek"):
            file_obj.seek(0)

    @classmethod
    def calculate_upload_sha1(cls, uploaded_file) -> str:
        hasher = hashlib.sha1()
        for chunk in uploaded_file.chunks():
            hasher.update(chunk)
        cls._reset_uploaded_file(uploaded_file)
        return hasher.hexdigest()

    @staticmethod
    def resolve_content_document(document):
        """Return the canonical content record for a duplicate chain."""
        current = document
        visited = set()

        while current is not None:
            current_id = getattr(current, "id", None)
            if current_id in visited:
                break
            visited.add(current_id)

            parent = getattr(current, "duplicate_of", None)
            if parent is None:
                return current
            current = parent

        return current

    @staticmethod
    def normalize_sync_path(raw_path) -> Optional[str]:
        if not raw_path:
            return None

        try:
            return str(Path(raw_path).expanduser().resolve())
        except Exception:
            try:
                return str(Path(raw_path).expanduser())
            except Exception:
                return str(raw_path)

    @classmethod
    def is_sync_managed_path(cls, raw_path, sync_root) -> bool:
        normalized_path = cls.normalize_sync_path(raw_path)
        normalized_root = cls.normalize_sync_path(sync_root)
        if not normalized_path or not normalized_root:
            return False

        try:
            path_obj = Path(normalized_path)
            root_obj = Path(normalized_root)
            path_obj.relative_to(root_obj)
            return True
        except Exception:
            return False

    @staticmethod
    def build_sync_title_from_path(file_path) -> str:
        """Build the sync title from a PDF path using the current sync-safe rules."""
        clean_title = Path(file_path).stem
        uuid_pattern = (
            r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\s"
        )

        if re.match(uuid_pattern, clean_title):
            clean_title = clean_title[37:].strip()

        clean_title = re.sub(r"\.pdf$", "", clean_title, flags=re.IGNORECASE)
        return clean_title.replace("_", " ").strip()

    @classmethod
    def build_sync_document_defaults(cls, file_path) -> dict:
        return {
            "title": cls.build_sync_title_from_path(file_path),
            "file_path": str(file_path),
            "file_size": Path(file_path).stat().st_size,
            "category": "未分类",
            "processed": False,
        }

    @classmethod
    def inspect_duplicate_markers(cls, original_filename: str, sha1: str) -> DuplicateInspection:
        from pdf_processor.models import PDFDocument

        filename_doc = PDFDocument.objects.filter(filename=original_filename).first()
        duplicate_doc = None
        if sha1:
            # Prefer the row that owns the physical file. If the first hit is a
            # duplicate review action, walk back to the canonical parent so all
            # entry points report the same duplicate target.
            duplicate_doc = PDFDocument.objects.filter(sha1=sha1, duplicate_of__isnull=True).first()
            if duplicate_doc is None:
                duplicate_doc = PDFDocument.objects.filter(sha1=sha1).first()
            duplicate_doc = cls.resolve_content_document(duplicate_doc)

        filename_conflict_same_content = None
        if filename_doc is not None and getattr(filename_doc, "sha1", None):
            filename_conflict_same_content = filename_doc.sha1 == sha1

        return DuplicateInspection(
            original_filename=original_filename,
            sha1=sha1,
            duplicate_detected=duplicate_doc is not None,
            duplicate_sha1=sha1 if duplicate_doc is not None else None,
            duplicate_document_id=str(duplicate_doc.id) if duplicate_doc is not None else None,
            filename_conflict=filename_doc is not None,
            filename_conflict_document_id=str(filename_doc.id) if filename_doc is not None else None,
            filename_conflict_same_content=filename_conflict_same_content,
        )

    @classmethod
    def inspect_uploaded_file(cls, uploaded_file) -> DuplicateInspection:
        original_filename = cls._sanitize_filename(uploaded_file.name)
        sha1 = cls.calculate_upload_sha1(uploaded_file)
        return cls.inspect_duplicate_markers(original_filename, sha1)

    @staticmethod
    def log_duplicate_inspection(logger, source: str, inspection: DuplicateInspection) -> None:
        # Keep these tokens stable for smoke checks and operational triage.
        if inspection.duplicate_detected:
            logger.info(
                "[%s] upload duplicate_detected=True filename=%s sha1=%s duplicate_document_id=%s",
                source,
                inspection.original_filename,
                inspection.sha1,
                inspection.duplicate_document_id,
            )

        if inspection.filename_conflict:
            logger.info(
                "[%s] upload filename_conflict=True filename=%s sha1=%s filename_conflict_document_id=%s filename_conflict_same_content=%s",
                source,
                inspection.original_filename,
                inspection.sha1,
                inspection.filename_conflict_document_id,
                inspection.filename_conflict_same_content,
            )
