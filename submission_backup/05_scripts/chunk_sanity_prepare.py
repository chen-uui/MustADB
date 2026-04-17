import csv
import shutil
from collections import OrderedDict
from pathlib import Path
from pdf_processor.models import PDFDocument
qrels = Path(r"backend/evaluation/retrieval_qrels_seed.csv")
out_dir = Path(r"backend/runs/chunk_sanity_input_qrels_20260402")
out_dir.mkdir(parents=True, exist_ok=True)
ids = OrderedDict()
with qrels.open('r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        doc_id = (row.get('doc_id') or '').strip()
        if doc_id:
            ids.setdefault(doc_id, None)
manifest = []
for doc in PDFDocument.objects.filter(id__in=list(ids.keys())).only('id', 'file_path'):
    src = Path(doc.file_path)
    if not src.exists():
        continue
    dst = out_dir / src.name
    if not dst.exists():
        shutil.copy2(src, dst)
    manifest.append(f"{doc.id}\t{src}\t{dst}")
(out_dir / 'manifest.tsv').write_text('\n'.join(manifest), encoding='utf-8')
print(f"out_dir={out_dir}")
print(f"copied={len(manifest)}")
print(f"manifest={out_dir / 'manifest.tsv'}")
