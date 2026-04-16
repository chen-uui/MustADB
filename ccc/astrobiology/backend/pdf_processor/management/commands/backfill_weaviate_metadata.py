from django.core.management.base import BaseCommand
from django.db.models import Q
import json
import logging
import time

from ...models import PDFDocument, DocumentChunk
from ...weaviate_services import WeaviateVectorService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Backfill Weaviate chunk metadata (title/authors/year/journal/doi) from PDFDocument fields"

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=2000, help='Max chunks per batch to process')
        parser.add_argument('--dry-run', action='store_true', help='Print actions without writing to Weaviate')
        parser.add_argument('--log-every', type=int, default=1000, help='Log progress every N updated chunks')
        parser.add_argument('--log-interval', type=float, default=2.0, help='Minimum seconds between progress logs')
        parser.add_argument('--no-doc-lines', action='store_true', help='Do not print per-document summary lines')
        parser.add_argument('--progress-only', action='store_true', help='Show single-line progress bar only')
        parser.add_argument('--quiet-http', action='store_true', help='Silence httpx/weaviate INFO logs during backfill')
        parser.add_argument('--resume', action='store_true', help='Resume from previous state file (skip processed docs)')
        parser.add_argument('--state-file', type=str, default='.backfill_weaviate_state.json', help='Path to state file for resume')

    def handle(self, *args, **options):
        limit = options['limit']
        dry_run = options['dry_run']

        # 降低 httpx / weaviate 客户端日志噪音（可选）
        if options.get('quiet_http'):
            try:
                logging.getLogger('httpx').setLevel(logging.WARNING)
                logging.getLogger('weaviate').setLevel(logging.WARNING)
            except Exception:
                pass

        service = WeaviateVectorService()
        collection = service.collection
        if not collection:
            self.stderr.write(self.style.ERROR('Weaviate collection not initialized'))
            return

        # 预估总量用于 ETA
        try:
            total_chunks = collection.aggregate.over_all(total_count=True).total_count or 0
        except Exception:
            total_chunks = 0

        start_ts = time.time()
        last_log_ts = start_ts
        log_every = int(options.get('log_every') or 1000)
        log_interval = float(options.get('log_interval') or 2.0)
        no_doc_lines = bool(options.get('no_doc_lines'))
        progress_only = bool(options.get('progress_only'))

        # 断点续传：读取 state 文件中的已处理文档
        processed_doc_ids = set()
        state_file = options.get('state_file')
        if options.get('resume') and state_file:
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    processed_doc_ids = set(data.get('processed_doc_ids', []))
                self.stdout.write(self.style.NOTICE(f"Resume enabled. Loaded {len(processed_doc_ids)} processed docs from {state_file}"))
            except FileNotFoundError:
                self.stdout.write(self.style.WARNING(f"State file not found: {state_file}. Starting fresh."))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Failed to load state file: {e}. Starting fresh."))

        # 取所有已处理文档，必要时跳过已处理
        docs_qs = PDFDocument.objects.filter(processed=True)
        if processed_doc_ids:
            docs_qs = docs_qs.exclude(id__in=list(processed_doc_ids))
        docs = docs_qs
        total_docs = docs.count()
        updated = 0
        skipped = 0
        processed_docs = 0

        if not progress_only:
            self.stdout.write(self.style.NOTICE(
                f"Starting backfill: docs={total_docs}, est_total_chunks={total_chunks}, batch_limit={limit}, dry_run={dry_run}"
            ))

        # 用于周期性保存 state
        def save_state():
            if not state_file:
                return
            try:
                with open(state_file, 'w', encoding='utf-8') as f:
                    json.dump({'processed_doc_ids': list(processed_doc_ids)}, f)
            except Exception:
                pass

        for doc in docs:
            meta = {
                'title': doc.title or '',
                'authors': (doc.authors or '').strip(),
                'year': str(doc.year) if doc.year else '',
                'journal': doc.journal or '',
                'doi': (doc.doi or '').strip(),
            }

            try:
                # 按 document_id 批量拉取 Weaviate 对象，并更新 properties
                from weaviate.collections.classes.filters import Filter
                where = Filter.by_property("document_id").equal(str(doc.id))
                offset = 0
                batch = 200
                doc_updated = 0
                while True:
                    resp = collection.query.fetch_objects(
                        limit=min(batch, limit),
                        offset=offset,
                        filters=where,
                        return_properties=[
                            "document_id", "document_title", "chunk_index", "chunk_text", "metadata"
                        ]
                    )
                    objects = getattr(resp, 'objects', []) or []
                    if not objects:
                        break

                    for obj in objects:
                        props = obj.properties or {}
                        # 合并 metadata：以数据库字段为准
                        try:
                            existing = props.get('metadata', '{}')
                            existing_meta = json.loads(existing) if isinstance(existing, str) else (existing or {})
                        except Exception:
                            existing_meta = {}

                        merged_meta = {**existing_meta, **{k: v for k, v in meta.items() if v}}

                        new_title = meta['title'] or props.get('document_title', '')

                        if dry_run:
                            logger.info(f"Would update {obj.uuid}: title='{new_title}'")
                        else:
                            collection.data.update(
                                uuid=str(obj.uuid),
                                properties={
                                    "document_title": new_title,
                                    "metadata": json.dumps(merged_meta)
                                }
                            )
                            updated += 1
                            doc_updated += 1

                            # 进度日志
                            now = time.time()
                            if (updated % log_every == 0) or (now - last_log_ts >= log_interval):
                                elapsed = max(0.001, now - start_ts)
                                rate = updated / elapsed
                                eta = (max(0, total_chunks - updated) / rate) / 60 if total_chunks > updated and rate > 0 else 0
                                if progress_only:
                                    # 单行进度条（覆盖同一行）
                                    bar_len = 30
                                    pct = 0.0
                                    if total_chunks > 0:
                                        pct = min(1.0, updated / total_chunks)
                                    filled = int(bar_len * pct)
                                    bar = '#' * filled + '-' * (bar_len - filled)
                                    line = f"[{bar}] {pct*100:5.1f}% | {updated:,} | {rate:.1f}/s | ETA {eta:.1f}m"
                                    self.stdout.write("\r" + line, ending='')
                                else:
                                    # 立即刷新输出，避免被缓冲
                                    self.stdout.write(
                                        f"progress: updated={updated:,} rate={rate:.1f}/s elapsed={elapsed/60:.1f}m ETA={eta:.1f}m",
                                        ending='\n'
                                    )
                                last_log_ts = now

                    offset += len(objects)

            except Exception as e:
                skipped += 1
                logger.warning(f"Skip doc {doc.id}: {e}")
                continue

            processed_docs += 1
            # 将该文档标记为已处理并保存 state（即使 doc_updated=0 也标记，避免反复扫描）
            processed_doc_ids.add(str(doc.id))
            if processed_docs % 50 == 0:
                save_state()

            if doc_updated > 0 and not no_doc_lines and not progress_only:
                self.stdout.write(
                    f"doc [{processed_docs}/{total_docs}] {doc.title[:80]} -> updated {doc_updated} chunks",
                    ending='\n'
                )

        total_elapsed = time.time() - start_ts
        # 结束时保存 state
        save_state()
        if progress_only:
            # 结束时换行，避免下一条输出顶在进度条行
            self.stdout.write("\n", ending='\n')
        self.stdout.write(self.style.SUCCESS(
            f"Backfill completed: updated={updated}, skipped={skipped}, elapsed={total_elapsed/60:.1f}m"
        ))


