import json
import time
import uuid
from pathlib import Path

from django.conf import settings
from django.test import Client
import fitz
from pdf_processor.models import PDFDocument

if 'localhost' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('localhost')
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

src = Path(r'D:\workspace\123\ccc\astrobiology\data\pdfs\isms.2018.TL03.pdf')
tmp_dir = Path(r'D:\workspace\123\ccc\astrobiology\backend\tmp_validation')
tmp_dir.mkdir(parents=True, exist_ok=True)
suffix = uuid.uuid4().hex[:8]
tmp_pdf = tmp_dir / f'codex_validation_{suffix}.pdf'

for stale in PDFDocument.objects.filter(filename__startswith='codex_validation_'):
    stale.delete()

doc = fitz.open(src)
meta = dict(doc.metadata or {})
meta['title'] = f'Codex Validation {suffix}'
doc.set_metadata(meta)
doc.save(tmp_pdf)
doc.close()

client = Client(HTTP_HOST='localhost')
with tmp_pdf.open('rb') as f:
    resp = client.post('/api/pdf/documents/upload/', {'file': f})
    upload_payload = json.loads(resp.content.decode('utf-8', errors='replace'))

document_id = upload_payload.get('document_id')
detail_status = None
detail_payload = None
for _ in range(60):
    detail = client.get(f'/api/pdf/documents/{document_id}/')
    detail_status = detail.status_code
    detail_payload = json.loads(detail.content.decode('utf-8', errors='replace'))
    if detail_status == 200 and detail_payload.get('processed') is True:
        break
    time.sleep(1)

db_state = PDFDocument.objects.filter(id=document_id).values('id', 'title', 'filename', 'processed', 'page_count').first()
print(json.dumps({
    'upload_status': resp.status_code,
    'upload_payload': upload_payload,
    'detail_status': detail_status,
    'document_detail': detail_payload,
    'db_state': db_state,
    'temp_pdf': str(tmp_pdf),
}, ensure_ascii=False, indent=2, default=str))

delete_resp = client.delete(f'/api/pdf/documents/{document_id}/')
print('DELETE_STATUS', delete_resp.status_code)
print(delete_resp.content.decode('utf-8', errors='replace'))
if tmp_pdf.exists():
    tmp_pdf.unlink()