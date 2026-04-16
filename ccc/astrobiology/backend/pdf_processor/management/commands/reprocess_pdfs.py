import hashlib
from pathlib import Path
from typing import Tuple

from django.core.management.base import BaseCommand, CommandError

from pdf_processor.management.commands.uuid_sync import Command as UUIDSyncCommand
from pdf_processor.models import PDFDocument
from pdf_processor.pdf_utils import GlobalConfig, PDFUtils
from pdf_processor.services.upload_storage_service import UploadStorageService
from pdf_processor.weaviate_services import WeaviateVectorService


class Command(BaseCommand):
    help = "Reprocess PDF files into Weaviate using the current or explicitly supplied chunk settings."

    DEFAULT_COLLECTION_NAME = "PDFDocument"

    def add_arguments(self, parser):
        parser.add_argument(
            "--pdf-dir",
            dest="pdf_dir",
            help="Override the PDF source directory for this run.",
        )
        parser.add_argument(
            "--file",
            dest="single_file",
            help="Process only one PDF file.",
        )
        parser.add_argument(
            "--max-files",
            dest="max_files",
            type=int,
            default=5,
            help="Maximum number of PDF files to process when no single file is specified.",
        )
        parser.add_argument(
            "--chunk-size",
            dest="chunk_size",
            type=int,
            default=None,
            help="Chunk size override for this run. Default: current configured chunk size.",
        )
        parser.add_argument(
            "--chunk-overlap",
            dest="chunk_overlap",
            type=int,
            default=None,
            help="Chunk overlap override for this run. Default: current configured overlap.",
        )
        parser.add_argument(
            "--collection-name",
            dest="collection_name",
            default=None,
            help="Weaviate collection name for this run. Default: PDFDocument.",
        )
        parser.add_argument(
            "--reset-collection",
            dest="reset_collection",
            action="store_true",
            help="Delete and recreate the target collection before writing.",
        )
        parser.add_argument(
            "--dry-run",
            dest="dry_run",
            action="store_true",
            help="Preview which files and document IDs would be processed without writing to Weaviate.",
        )

    def _resolve_source_dir(self, options) -> Path:
        raw_dir = options.get("pdf_dir")
        if raw_dir:
            return Path(raw_dir).expanduser().resolve()
        return UploadStorageService.resolve_pdf_storage_dir()

    def _resolve_pdf_paths(self, options) -> list[Path]:
        source_dir = self._resolve_source_dir(options)
        if not source_dir.exists():
            raise CommandError(f"PDF directory does not exist: {source_dir}")

        single_file = options.get("single_file")
        if single_file:
            candidate = Path(single_file).expanduser()
            if not candidate.is_absolute():
                candidate = (source_dir / candidate).resolve()
            else:
                candidate = candidate.resolve()

            if not candidate.exists():
                raise CommandError(f"PDF file does not exist: {candidate}")
            if candidate.suffix.lower() != ".pdf":
                raise CommandError(f"Not a PDF file: {candidate}")
            return [candidate]

        max_files = max(0, int(options.get("max_files", 5)))
        pdf_files = sorted(path for path in source_dir.iterdir() if path.suffix.lower() == ".pdf")
        if max_files:
            return pdf_files[:max_files]
        return pdf_files

    def _resolve_chunk_config(self, options) -> Tuple[int, int]:
        chunk_size = int(options.get("chunk_size") or GlobalConfig.CHUNK_SIZE)
        chunk_overlap = int(options.get("chunk_overlap") or GlobalConfig.CHUNK_OVERLAP)
        if chunk_size < 1:
            raise CommandError("--chunk-size must be >= 1")
        if chunk_overlap < 0:
            raise CommandError("--chunk-overlap must be >= 0")
        if chunk_overlap >= chunk_size:
            raise CommandError("--chunk-overlap must be smaller than --chunk-size")
        return chunk_size, chunk_overlap

    def _resolve_collection_name(self, options) -> Tuple[str, bool]:
        explicit_collection_name = str(options.get("collection_name") or "").strip()
        if explicit_collection_name:
            return explicit_collection_name, True
        return self.DEFAULT_COLLECTION_NAME, False

    @staticmethod
    def _calculate_file_sha1(pdf_path: Path) -> str:
        hasher = hashlib.sha1()
        with pdf_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @classmethod
    def _build_document_id(cls, pdf_path: Path) -> str:
        normalized_file_path = str(pdf_path.resolve())
        existing_document = PDFDocument.objects.filter(file_path=normalized_file_path).only("id").first()
        if existing_document is not None:
            return str(existing_document.id)

        filename_match = PDFDocument.objects.filter(filename=pdf_path.name).only("id").first()
        if filename_match is not None:
            return str(filename_match.id)

        normalized_path = str(pdf_path.resolve()).replace("\\", "/").lower()
        file_sha1 = cls._calculate_file_sha1(pdf_path)
        stable_key = f"{normalized_path}|{file_sha1}".encode("utf-8")
        return f"reprocess_{hashlib.sha1(stable_key).hexdigest()[:16]}"

    @staticmethod
    def _build_documents(chunks: list[str], document_id: str, title: str) -> list[dict]:
        documents = []
        for chunk_index, chunk in enumerate(chunks):
            documents.append(
                {
                    "content": chunk,
                    "document_id": document_id,
                    "title": title,
                    "page_number": 0,
                    "chunk_index": chunk_index,
                }
            )
        return documents

    @staticmethod
    def _preview_chunk_ids(document_id: str, chunk_count: int, limit: int = 3) -> str:
        preview = [f"{document_id}:{idx}" for idx in range(min(chunk_count, limit))]
        if chunk_count > limit:
            preview.append("...")
        return ", ".join(preview)

    def handle(self, *args, **options):
        chunk_size, chunk_overlap = self._resolve_chunk_config(options)
        collection_name, has_explicit_collection = self._resolve_collection_name(options)
        dry_run = bool(options.get("dry_run"))
        reset_collection = bool(options.get("reset_collection"))

        custom_chunking = (
            chunk_size != GlobalConfig.CHUNK_SIZE or chunk_overlap != GlobalConfig.CHUNK_OVERLAP
        )
        if custom_chunking and not dry_run and not has_explicit_collection:
            raise CommandError(
                "custom chunk settings require --collection-name to avoid modifying the default index"
            )

        self.stdout.write("Reprocessing PDF documents with the selected chunk settings")
        self.stdout.write("=" * 60)
        self.stdout.write(f"  CHUNK_SIZE: {chunk_size} token")
        self.stdout.write(f"  CHUNK_OVERLAP: {chunk_overlap} token")
        self.stdout.write(f"  Collection: {collection_name}")

        pdf_paths = self._resolve_pdf_paths(options)
        source_dir = self._resolve_source_dir(options)

        self.stdout.write(f"  Source directory: {source_dir}")
        self.stdout.write(f"  Selected PDF files: {len(pdf_paths)}")
        self.stdout.write(f"  Dry run: {'yes' if dry_run else 'no'}")
        self.stdout.write(f"  Reset collection: {'yes' if reset_collection else 'no'}")

        if not pdf_paths:
            self.stdout.write(self.style.WARNING("No PDF files found for reprocessing."))
            return

        weaviate_service = None if dry_run else WeaviateVectorService()
        if weaviate_service is not None:
            if reset_collection:
                self.stdout.write(f"  Resetting collection: {collection_name}")
                weaviate_service.delete_all_documents(collection_name=collection_name)
            else:
                weaviate_service.create_collection_if_not_exists(collection_name=collection_name)

        processed_count = 0
        failed_count = 0

        for index, pdf_path in enumerate(pdf_paths, 1):
            self.stdout.write(f"\nProcessing file {index}/{len(pdf_paths)}: {pdf_path.name}")

            try:
                result = PDFUtils.extract_text_and_metadata(str(pdf_path))
                text = result.get("text") or ""
                if not text.strip():
                    self.stdout.write(self.style.WARNING(f"  Skipped: no extractable text for {pdf_path.name}"))
                    failed_count += 1
                    continue

                chunks = UUIDSyncCommand().chunk_text(
                    text,
                    chunk_size=chunk_size,
                    overlap=chunk_overlap,
                )
                if not chunks:
                    self.stdout.write(self.style.WARNING(f"  Skipped: no chunks produced for {pdf_path.name}"))
                    failed_count += 1
                    continue

                document_id = self._build_document_id(pdf_path)
                title = result.get("metadata", {}).get("title") or pdf_path.name
                text_length = len(text)
                chunk_sizes_chars = [len(chunk) for chunk in chunks]
                chunk_sizes_tokens = [PDFUtils.count_tokens(chunk) for chunk in chunks]
                avg_chunk_size = sum(chunk_sizes_tokens) / len(chunk_sizes_tokens)
                min_chunk_size = min(chunk_sizes_tokens)
                max_chunk_size = max(chunk_sizes_tokens)

                self.stdout.write(f"  Text length: {text_length} characters")
                self.stdout.write(f"  Chunk count: {len(chunks)}")
                self.stdout.write(
                    f"  Chunk size (tokens): avg={avg_chunk_size:.0f}, min={min_chunk_size}, max={max_chunk_size}"
                )
                self.stdout.write(
                    f"  Chunk size (chars): avg={sum(chunk_sizes_chars) / len(chunk_sizes_chars):.0f}"
                )
                self.stdout.write(f"  Document ID: {document_id}")
                self.stdout.write(f"  Preview chunk IDs: {self._preview_chunk_ids(document_id, len(chunks))}")

                if dry_run:
                    self.stdout.write("  Dry run: skipped Weaviate write")
                    processed_count += 1
                    continue

                documents = self._build_documents(chunks, document_id, title)
                weaviate_service.add_documents_batch(documents, collection_name=collection_name)
                self.stdout.write("  Upload succeeded")
                processed_count += 1

            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"  Processing failed: {exc}"))
                failed_count += 1

        self.stdout.write("\nRun summary:")
        self.stdout.write(f"  Successfully processed: {processed_count}")
        self.stdout.write(f"  Failed: {failed_count}")
        self.stdout.write(f"  Collection: {collection_name}")
        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry-run completed without writing to Weaviate."))
        else:
            self.stdout.write(self.style.SUCCESS("PDF reprocessing completed."))
