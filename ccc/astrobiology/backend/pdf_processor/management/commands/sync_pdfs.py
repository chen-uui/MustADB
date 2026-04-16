"""Sync PDF files from storage into database records."""

import os
import time
from pathlib import Path
from django.core.management.base import BaseCommand
from pdf_processor.models import PDFDocument
from pdf_processor.services.upload_storage_service import UploadStorageService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Synchronize PDF files into database records."

    def add_arguments(self, parser):
        parser.add_argument(
            '--watch',
            action='store_true',
            help='Continuously watch the PDF directory for changes.',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=30,
            help='Polling interval in seconds (default: 30).',
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run synchronization once and exit.',
        )

    def resolve_pdf_dir(self):
        """Use the shared helper as the single sync directory source."""
        return UploadStorageService.resolve_pdf_storage_dir()

    def normalize_sync_path(self, raw_path):
        return UploadStorageService.normalize_sync_path(raw_path)

    def collect_sync_folder_files(self):
        """Build the file-system sync view keyed by canonical file_path."""
        folder_files = {}
        for file_path in self.pdf_dir.glob('*.pdf'):
            normalized_path = self.normalize_sync_path(file_path)
            if normalized_path:
                folder_files[normalized_path] = file_path
        return folder_files

    def collect_sync_canonical_records(self):
        """Collect canonical records for sync; duplicate child rows stay transparent."""
        db_files = {}
        orphan_children = []
        ignored_paths = set()

        documents = PDFDocument.objects.all().select_related('duplicate_of').only(
            'id',
            'filename',
            'file_path',
            'file_size',
            'sha1',
            'duplicate_of',
        )

        for doc in documents:
            if getattr(doc, 'duplicate_of', None) is not None:
                canonical_doc = UploadStorageService.resolve_content_document(doc)
                canonical_id = getattr(canonical_doc, 'id', None)
                canonical_path = self.normalize_sync_path(getattr(canonical_doc, 'file_path', None))
                child_path = self.normalize_sync_path(getattr(doc, 'file_path', None))

                if canonical_doc is doc or canonical_doc is None or canonical_id is None or not canonical_path:
                    orphan_children.append(doc)
                    if child_path:
                        ignored_paths.add(child_path)
                    continue

                if not UploadStorageService.is_sync_managed_path(canonical_path, self.pdf_dir):
                    if child_path:
                        ignored_paths.add(child_path)
                continue

            canonical_path = self.normalize_sync_path(getattr(doc, 'file_path', None))
            if not canonical_path or not UploadStorageService.is_sync_managed_path(canonical_path, self.pdf_dir):
                continue

            db_files.setdefault(canonical_path, doc)

        return db_files, orphan_children, ignored_paths

    def handle(self, *args, **options):
        self.pdf_dir = self.resolve_pdf_dir()
        
        if options['once']:
            self.sync_once()
        elif options['watch']:
            self.watch_folder(options['interval'])
        else:
            self.sync_once()


    def sync_once(self):
        """Run synchronization once."""
        try:
            added, removed = self.sync_pdfs()

            if added > 0 or removed > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[SUCCESS] Sync complete: added {added} files, removed {removed} files"
                    )
                )
            else:
                self.stdout.write(self.style.SUCCESS("[SUCCESS] Files already in sync"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[ERROR] Sync failed: {str(e)}"))

    def watch_folder(self, interval):
        """Watch the folder for changes."""
        self.stdout.write(
            self.style.SUCCESS(f"[WATCH] Watching PDF directory: {self.pdf_dir}")
        )
        self.stdout.write(
            self.style.SUCCESS(f"[WATCH] Polling interval: {interval}s")
        )
        self.stdout.write(self.style.WARNING("Press Ctrl+C to stop watching"))

        try:
            while True:
                try:
                    added, removed = self.sync_pdfs()
                    if added > 0 or removed > 0:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"[RECOVERED] Auto-sync added {added} files and removed {removed} files"
                            )
                        )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"[ERROR] Sync error: {str(e)}")
                    )

                time.sleep(interval)

        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS("\n[SUCCESS] Folder watch stopped"))

    def sync_pdfs(self):
        """Sync PDF files from storage into database records."""
        if not self.pdf_dir.exists():
            raise ValueError(f'PDF directory does not exist: {self.pdf_dir}')

        # Collect the PDF files currently present on disk.
        folder_files = self.collect_sync_folder_files()
        
        db_files, orphan_children, ignored_paths = self.collect_sync_canonical_records()

        for orphan_child in orphan_children:
            logger.warning(
                'sync_pdfs_orphan_child document_id=%s duplicate_of=%s file_path=%s',
                getattr(orphan_child, 'id', None),
                getattr(getattr(orphan_child, 'duplicate_of', None), 'id', None),
                getattr(orphan_child, 'file_path', None),
            )
        
        added_count = 0
        removed_count = 0
        
        # Add new canonical files that do not yet have records.
        for file_key, file_path in folder_files.items():
            if file_key in ignored_paths:
                continue
            if file_key not in db_files:
                try:
                    filename = file_path.name
                    
                    doc = PDFDocument.objects.create(
                        filename=filename,
                        **UploadStorageService.build_sync_document_defaults(file_path),
                    )
                    added_count += 1
                    logger.info('Added synced file record: %s', filename)
                except Exception as e:
                    logger.error('Failed to add synced file %s: %s', filename, str(e))
        
        # Remove canonical records whose files no longer exist on disk.
        for file_key, doc in list(db_files.items()):
            if file_key not in folder_files:
                try:
                    doc.delete()
                    removed_count += 1
                    logger.info('Removed missing file record: %s', doc.filename)
                except Exception as e:
                    logger.error('Failed to remove missing record %s: %s', doc.filename, str(e))
        
        return added_count, removed_count
