import json
import shutil
import uuid
from pathlib import Path

from django.contrib.auth.models import User

from meteorite_search.review_models import ApprovedMeteorite, PendingMeteorite, RejectedMeteorite
from pdf_processor.models import PDFDocument


ROOT = Path(__file__).resolve().parents[1]
TMP_DIR = ROOT / "backend" / "tmp_smoke"
SEED_FILE = TMP_DIR / "seed.json"
SOURCE_PDF = ROOT / "data" / "pdfs" / "isms.2018.TL03.pdf"


def reset_tmp_dir() -> None:
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True, exist_ok=True)


def copy_pdf(prefix: str) -> Path:
    target = TMP_DIR / f"{prefix}-{uuid.uuid4().hex[:8]}.pdf"
    shutil.copy2(SOURCE_PDF, target)
    return target


def write_invalid_pdf(prefix: str) -> Path:
    target = TMP_DIR / f"{prefix}-{uuid.uuid4().hex[:8]}.pdf"
    target.write_text("this is not a real pdf file", encoding="utf-8")
    return target


def create_pdf_document(title: str, file_path: Path, uploaded_by: User) -> PDFDocument:
    return PDFDocument.objects.create(
        filename=file_path.name,
        title=title,
        file_path=str(file_path),
        file_size=file_path.stat().st_size,
        page_count=0,
        processed=False,
        category="smoke",
        uploaded_by=uploaded_by,
    )


def create_pending(name: str) -> PendingMeteorite:
    return PendingMeteorite.objects.create(
        name=name,
        classification="Chondrite",
        discovery_location="Smoke Lab",
        origin="Mars",
        organic_compounds=["glycine"],
        contamination_exclusion_method="Sterile handling",
        references=["Smoke reference"],
        confidence_score=0.82,
        extraction_source="manual",
        extraction_metadata={"source": "frontend-smoke"},
        review_notes="frontend smoke seed",
        priority=2,
    )


def cleanup_smoke_records() -> None:
    PDFDocument.objects.filter(filename__startswith="smoke-frontend-").delete()
    PDFDocument.objects.filter(title__startswith="Smoke Frontend ").delete()
    PendingMeteorite.objects.filter(name__startswith="Smoke Frontend ").delete()
    ApprovedMeteorite.objects.filter(name__startswith="Smoke Frontend ").delete()
    RejectedMeteorite.objects.filter(name__startswith="Smoke Frontend ").delete()


def main() -> None:
    if not SOURCE_PDF.exists():
        raise FileNotFoundError(f"Sample PDF not found: {SOURCE_PDF}")

    reset_tmp_dir()
    cleanup_smoke_records()

    admin_user, _ = User.objects.get_or_create(
        username="smoke_admin",
        defaults={"is_staff": True, "is_superuser": True, "email": "smoke@example.com"},
    )
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.is_active = True
    admin_user.set_password("SmokePass123!")
    admin_user.save()

    upload_valid = copy_pdf("smoke-frontend-upload-valid")
    upload_invalid = write_invalid_pdf("smoke-frontend-upload-invalid")
    single_success_pdf = copy_pdf("smoke-frontend-single-success")
    batch_success_pdf = copy_pdf("smoke-frontend-batch-success")
    single_failure_pdf = write_invalid_pdf("smoke-frontend-single-failure")

    single_success_doc = create_pdf_document("Smoke Frontend Single Success", single_success_pdf, admin_user)
    batch_success_doc = create_pdf_document("Smoke Frontend Batch Success", batch_success_pdf, admin_user)
    single_failure_doc = create_pdf_document("Smoke Frontend Single Failure", single_failure_pdf, admin_user)

    pending_records = {
        "approve_single": create_pending("Smoke Frontend Pending Approve Single"),
        "reject_single": create_pending("Smoke Frontend Pending Reject Single"),
        "batch_approve_a": create_pending("Smoke Frontend Pending Batch Approve A"),
        "batch_approve_b": create_pending("Smoke Frontend Pending Batch Approve B"),
        "batch_reject_a": create_pending("Smoke Frontend Pending Batch Reject A"),
        "batch_reject_b": create_pending("Smoke Frontend Pending Batch Reject B"),
        "approve_failure": create_pending("Smoke Frontend Pending Approve Failure"),
    }

    seed_payload = {
        "admin": {
            "username": "smoke_admin",
            "password": "SmokePass123!",
        },
        "files": {
            "upload_valid": str(upload_valid),
            "upload_invalid": str(upload_invalid),
        },
        "documents": {
            "single_success": {
                "id": str(single_success_doc.id),
                "title": single_success_doc.title,
            },
            "batch_success": {
                "id": str(batch_success_doc.id),
                "title": batch_success_doc.title,
            },
            "single_failure": {
                "id": str(single_failure_doc.id),
                "title": single_failure_doc.title,
            },
        },
        "pending": {key: {"id": value.id, "name": value.name} for key, value in pending_records.items()},
    }
    SEED_FILE.write_text(json.dumps(seed_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(seed_payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
