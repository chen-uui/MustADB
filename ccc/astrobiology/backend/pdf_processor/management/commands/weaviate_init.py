"""
Initialize Weaviate and ingest PDF documents.
"""

import logging

from django.core.management.base import BaseCommand

from pdf_processor.models import PDFDocument
from pdf_processor.weaviate_services import WeaviateConfig, WeaviateDocumentProcessor

logger = logging.getLogger(__name__)
class Command(BaseCommand):
    help = "Initialize Weaviate and process PDF documents."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reprocess",
            action="store_true",
            help="Reprocess all documents instead of only unprocessed ones.",
        )
        parser.add_argument(
            "--workers",
            type=int,
            default=2,
            help="Worker count for batch processing.",
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            default=None,
            help="Chunk size override for this run.",
        )
        parser.add_argument(
            "--chunk-overlap",
            type=int,
            default=None,
            help="Chunk overlap override for this run.",
        )
        parser.add_argument(
            "--collection-name",
            type=str,
            default=None,
            help="Weaviate collection name for this run.",
        )
        parser.add_argument(
            "--test",
            action="store_true",
            help="Process only one document.",
        )

    def handle(self, *args, **options):
        try:
            self.stdout.write(self.style.SUCCESS("Starting Weaviate initialization"))

            from pdf_processor.pdf_utils import GlobalConfig

            chunk_size = options["chunk_size"] or GlobalConfig.CHUNK_SIZE
            chunk_overlap = options["chunk_overlap"] or GlobalConfig.CHUNK_OVERLAP

            weaviate_config = WeaviateConfig(
                collection_name=str(options.get("collection_name") or "").strip()
                or WeaviateConfig.collection_name,
            )
            processor = WeaviateDocumentProcessor(weaviate_config)
            processor.vector_service.create_collection_if_not_exists(weaviate_config.collection_name)

            stats = processor.get_system_stats()
            self.stdout.write(f"collection_name={weaviate_config.collection_name}")
            self.stdout.write(f"system_stats={stats}")

            if options["reprocess"]:
                pdf_docs = PDFDocument.objects.all()
                self.stdout.write(f"selected_docs={pdf_docs.count()} source=all")
            else:
                pdf_docs = PDFDocument.objects.filter(processed=False)
                self.stdout.write(f"selected_docs={pdf_docs.count()} source=unprocessed")

            if options["test"]:
                pdf_docs = pdf_docs[:1]
                self.stdout.write("test_mode=true")

            if not pdf_docs.exists():
                self.stdout.write(self.style.WARNING("No documents to process"))
                return

            pdf_paths = [doc.file_path for doc in pdf_docs]
            metadata_list = [
                {
                    "id": str(doc.id),
                    "title": doc.title,
                    "authors": doc.authors or "",
                    "year": str(doc.year) if doc.year else "",
                    "journal": doc.journal or "",
                    "doi": doc.doi or "",
                    "category": doc.category,
                    "upload_date": str(doc.upload_date),
                    "file_path": doc.file_path,
                }
                for doc in pdf_docs
            ]

            results = processor.process_documents_batch(
                pdf_paths,
                max_workers=options["workers"],
                metadata_list=metadata_list,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

            success_count = 0
            for doc, result in zip(pdf_docs, results):
                if result.get("status") == "success":
                    doc.processed = True
                    doc.page_count = result.get("total_pages", 0)
                    doc.save()
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"processed={doc.title} chunks={result['total_chunks']}")
                    )
                else:
                    doc.processed = False
                    doc.save()
                    self.stdout.write(
                        self.style.ERROR(f"failed={doc.title} error={result.get('error', 'unknown')}")
                    )

            final_stats = processor.get_system_stats()
            self.stdout.write(self.style.SUCCESS("Weaviate initialization completed"))
            self.stdout.write(f"success_count={success_count}")
            self.stdout.write(f"failure_count={len(results) - success_count}")
            self.stdout.write(f"total_chunks={final_stats.get('total_chunks', 0)}")
            self.stdout.write(f"unique_documents={final_stats.get('unique_documents', 0)}")

            test_results = processor.search_documents("test", n_results=1)
            self.stdout.write(f"search_smoke_result_count={len(test_results)}")

            processor.close()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Interrupted"))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"Initialization failed: {exc}"))
            logger.exception("Weaviate initialization failed")
            raise
