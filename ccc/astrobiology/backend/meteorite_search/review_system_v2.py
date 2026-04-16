from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from pdf_processor.extraction_postprocess import ExtractionFieldPostprocessor

from .review_models import (
    ApprovedMeteorite,
    MeteoriteReviewLogNew,
    PendingMeteorite,
    RejectedMeteorite,
)

logger = logging.getLogger(__name__)


class NewReviewSystem:
    """Review workflow service: pending -> approved/rejected -> restore/delete."""

    def __init__(self):
        self.quality_thresholds = {
            "high_confidence": 0.8,
            "medium_confidence": 0.6,
            "low_confidence": 0.4,
        }

    def _get_system_user(self) -> User:
        system_user, created = User.objects.get_or_create(
            username="system_user",
            defaults={"is_active": True},
        )
        if created or not system_user.has_usable_password():
            system_user.set_unusable_password()
            system_user.save(update_fields=["password"])
        return system_user

    def submit_for_review(
        self,
        data: Dict[str, Any],
        submitter: Optional[User] = None,
    ) -> Dict[str, Any]:
        try:
            normalized_data = ExtractionFieldPostprocessor.postprocess_submission_data(data)

            with transaction.atomic():
                pending_meteorite = PendingMeteorite(
                    name=normalized_data.get("name", "Unknown") or "Unknown",
                    classification=normalized_data.get("classification", "Unknown"),
                    discovery_location=normalized_data.get("discovery_location", "Unknown"),
                    origin=normalized_data.get("origin", "Unknown"),
                    organic_compounds=normalized_data.get("organic_compounds", []),
                    contamination_exclusion_method=(
                        normalized_data.get("contamination_exclusion_method", "Not specified")
                        or "Not specified"
                    ),
                    references=normalized_data.get("references", []),
                    confidence_score=float(normalized_data.get("confidence_score", 0.0)),
                    extraction_source=normalized_data.get("extraction_source", "manual"),
                    extraction_metadata=normalized_data.get("extraction_metadata", {}),
                    priority=self._calculate_priority(normalized_data),
                )
                pending_meteorite.full_clean()
                pending_meteorite.save()

                MeteoriteReviewLogNew.objects.create(
                    pending_meteorite=pending_meteorite,
                    reviewer=submitter or self._get_system_user(),
                    action="submitted",
                    previous_status="none",
                    new_status="pending",
                    notes=f"Submitted for review, confidence={pending_meteorite.confidence_score:.3f}",
                    review_details={"submission_data": normalized_data},
                )

                logger.info(
                    "submit_for_review success name=%s pending_id=%s",
                    pending_meteorite.name,
                    pending_meteorite.id,
                )
                return {
                    "success": True,
                    "pending_id": pending_meteorite.id,
                    "message": "Data submitted for review",
                }

        except Exception as exc:
            logger.exception("submit_for_review failed: %s", exc)
            return {"success": False, "error": str(exc)}

    def get_pending_reviews(
        self,
        reviewer: Optional[User] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        queryset = PendingMeteorite._default_manager.all()
        if status:
            queryset = queryset.filter(review_status=status)
        if reviewer:
            queryset = queryset.filter(assigned_reviewer=reviewer)

        out: List[Dict[str, Any]] = []
        for meteorite in queryset:
            out.append(
                {
                    "id": meteorite.id,
                    "name": meteorite.name,
                    "classification": meteorite.classification,
                    "discovery_location": meteorite.discovery_location,
                    "origin": meteorite.origin,
                    "confidence_score": meteorite.confidence_score,
                    "extraction_source": meteorite.extraction_source,
                    "created_at": meteorite.created_at,
                    "review_status": meteorite.review_status,
                    "priority": meteorite.priority,
                    "assigned_reviewer": (
                        meteorite.assigned_reviewer.username if meteorite.assigned_reviewer else None
                    ),
                    "organic_compounds_summary": meteorite.get_organic_compounds_summary(),
                    "references_count": meteorite.get_references_count(),
                }
            )
        return out

    def assign_reviewer(self, pending_id: int, reviewer: User, assigner: User) -> bool:
        try:
            with transaction.atomic():
                pending_meteorite = PendingMeteorite._default_manager.select_for_update().get(id=pending_id)
                previous_reviewer = pending_meteorite.assigned_reviewer
                pending_meteorite.assigned_reviewer = reviewer
                pending_meteorite.review_status = "under_review"
                pending_meteorite.save()

                MeteoriteReviewLogNew.objects.create(
                    pending_meteorite=pending_meteorite,
                    reviewer=assigner,
                    action="assigned",
                    previous_status="pending",
                    new_status="under_review",
                    notes=f"Assigned reviewer: {reviewer.username}",
                    review_details={
                        "previous_reviewer": previous_reviewer.username if previous_reviewer else None,
                        "new_reviewer": reviewer.username,
                    },
                )
                return True

        except PendingMeteorite._default_manager.model.DoesNotExist:
            raise ValidationError(f"Pending review record not found: ID={pending_id}")
        except Exception as exc:
            logger.exception("assign_reviewer failed pending_id=%s: %s", pending_id, exc)
            return False

    @transaction.atomic
    def approve_meteorite(self, pending_id: int, reviewer: User, notes: str = "") -> Dict[str, Any]:
        try:
            pending_meteorite = PendingMeteorite._default_manager.select_for_update().get(id=pending_id)

            approved_meteorite = ApprovedMeteorite(
                name=pending_meteorite.name,
                classification=pending_meteorite.classification,
                discovery_location=pending_meteorite.discovery_location,
                origin=pending_meteorite.origin,
                organic_compounds=pending_meteorite.organic_compounds,
                contamination_exclusion_method=pending_meteorite.contamination_exclusion_method,
                references=pending_meteorite.references,
                confidence_score=pending_meteorite.confidence_score,
                extraction_source=pending_meteorite.extraction_source,
                extraction_metadata=pending_meteorite.extraction_metadata,
                reviewer=reviewer,
                original_pending_id=pending_meteorite.id,
            )
            approved_meteorite.full_clean()
            approved_meteorite.save()

            MeteoriteReviewLogNew.objects.create(
                approved_meteorite=approved_meteorite,
                reviewer=reviewer,
                action="approved",
                previous_status=pending_meteorite.review_status,
                new_status="approved",
                notes=notes,
                review_details={
                    "original_pending_id": pending_meteorite.id,
                    "approval_timestamp": timezone.now().isoformat(),
                },
            )

            pending_meteorite.delete()
            return {
                "success": True,
                "approved_id": approved_meteorite.id,
                "message": "Data approved",
            }

        except PendingMeteorite._default_manager.model.DoesNotExist:
            raise ValidationError(f"Pending review record not found: ID={pending_id}")
        except Exception as exc:
            logger.exception("approve_meteorite failed pending_id=%s: %s", pending_id, exc)
            return {"success": False, "error": str(exc)}

    @transaction.atomic
    def reject_meteorite(
        self,
        pending_id: int,
        reviewer: User,
        reason: str,
        category: str = "data_quality",
        notes: str = "",
    ) -> Dict[str, Any]:
        try:
            pending_meteorite = PendingMeteorite._default_manager.select_for_update().get(id=pending_id)

            rejected_meteorite = RejectedMeteorite(
                name=pending_meteorite.name,
                classification=pending_meteorite.classification,
                discovery_location=pending_meteorite.discovery_location,
                origin=pending_meteorite.origin,
                organic_compounds=pending_meteorite.organic_compounds,
                contamination_exclusion_method=pending_meteorite.contamination_exclusion_method,
                references=pending_meteorite.references,
                confidence_score=pending_meteorite.confidence_score,
                extraction_source=pending_meteorite.extraction_source,
                extraction_metadata=pending_meteorite.extraction_metadata,
                reviewer=reviewer,
                rejection_reason=reason,
                rejection_category=category,
                original_pending_id=pending_meteorite.id,
                can_restore=True,
            )
            rejected_meteorite.full_clean()
            rejected_meteorite.save()

            MeteoriteReviewLogNew.objects.create(
                rejected_meteorite=rejected_meteorite,
                reviewer=reviewer,
                action="rejected",
                previous_status=pending_meteorite.review_status,
                new_status="rejected",
                notes=notes,
                review_details={
                    "original_pending_id": pending_meteorite.id,
                    "rejection_reason": reason,
                    "rejection_category": category,
                    "rejection_timestamp": timezone.now().isoformat(),
                },
            )

            pending_meteorite.delete()
            return {
                "success": True,
                "rejected_id": rejected_meteorite.id,
                "message": "Data rejected",
            }

        except PendingMeteorite._default_manager.model.DoesNotExist:
            raise ValidationError(f"Pending review record not found: ID={pending_id}")
        except Exception as exc:
            logger.exception("reject_meteorite failed pending_id=%s: %s", pending_id, exc)
            return {"success": False, "error": str(exc)}

    def request_revision(self, pending_id: int, reviewer: User, notes: str) -> bool:
        try:
            with transaction.atomic():
                pending_meteorite = PendingMeteorite._default_manager.select_for_update().get(id=pending_id)
                previous_status = pending_meteorite.review_status
                pending_meteorite.review_status = "needs_revision"
                pending_meteorite.review_notes = notes
                pending_meteorite.save()

                MeteoriteReviewLogNew.objects.create(
                    pending_meteorite=pending_meteorite,
                    reviewer=reviewer,
                    action="revision_requested",
                    previous_status=previous_status,
                    new_status="needs_revision",
                    notes=notes,
                    review_details={},
                )
                return True

        except PendingMeteorite._default_manager.model.DoesNotExist:
            raise ValidationError(f"Pending review record not found: ID={pending_id}")
        except Exception as exc:
            logger.exception("request_revision failed pending_id=%s: %s", pending_id, exc)
            return False

    def get_rejected_meteorites(self, reviewer: Optional[User] = None) -> List[Dict[str, Any]]:
        queryset = RejectedMeteorite._default_manager.all()
        if reviewer:
            queryset = queryset.filter(reviewer=reviewer)

        out: List[Dict[str, Any]] = []
        for meteorite in queryset:
            out.append(
                {
                    "id": meteorite.id,
                    "name": meteorite.name,
                    "classification": meteorite.classification,
                    "discovery_location": meteorite.discovery_location,
                    "origin": meteorite.origin,
                    "confidence_score": meteorite.confidence_score,
                    "rejected_at": meteorite.rejected_at,
                    "rejection_reason": meteorite.rejection_reason,
                    "rejection_category": meteorite.rejection_category,
                    "reviewer": meteorite.reviewer.username if meteorite.reviewer else None,
                    "can_restore": meteorite.can_restore,
                    "organic_compounds_summary": meteorite.get_organic_compounds_summary(),
                    "references_count": meteorite.get_references_count(),
                }
            )
        return out

    @transaction.atomic
    def restore_from_recycle_bin(
        self,
        rejected_id: int,
        restorer: User,
        notes: str = "",
    ) -> Dict[str, Any]:
        try:
            rejected_meteorite = RejectedMeteorite._default_manager.select_for_update().get(id=rejected_id)
            if not rejected_meteorite.can_restore:
                raise ValidationError("This record cannot be restored")

            pending_meteorite = PendingMeteorite(
                name=rejected_meteorite.name,
                classification=rejected_meteorite.classification,
                discovery_location=rejected_meteorite.discovery_location,
                origin=rejected_meteorite.origin,
                organic_compounds=rejected_meteorite.organic_compounds,
                contamination_exclusion_method=rejected_meteorite.contamination_exclusion_method,
                references=rejected_meteorite.references,
                confidence_score=rejected_meteorite.confidence_score,
                extraction_source=rejected_meteorite.extraction_source,
                extraction_metadata=rejected_meteorite.extraction_metadata,
                review_status="pending",
                priority=2,
            )
            pending_meteorite.full_clean()
            pending_meteorite.save()

            MeteoriteReviewLogNew.objects.create(
                pending_meteorite=pending_meteorite,
                reviewer=restorer,
                action="restored",
                previous_status="rejected",
                new_status="pending",
                notes=notes,
                review_details={
                    "original_rejected_id": rejected_meteorite.id,
                    "restore_timestamp": timezone.now().isoformat(),
                },
            )

            rejected_meteorite.delete()
            return {
                "success": True,
                "pending_id": pending_meteorite.id,
                "message": "Data restored to pending queue",
            }

        except RejectedMeteorite._default_manager.model.DoesNotExist:
            raise ValidationError(f"Rejected record not found: ID={rejected_id}")
        except Exception as exc:
            logger.exception("restore_from_recycle_bin failed rejected_id=%s: %s", rejected_id, exc)
            return {"success": False, "error": str(exc)}

    def permanently_delete(self, rejected_id: int, deleter: User, notes: str = "") -> bool:
        try:
            with transaction.atomic():
                rejected_meteorite = RejectedMeteorite._default_manager.select_for_update().get(id=rejected_id)
                MeteoriteReviewLogNew.objects.create(
                    reviewer=deleter,
                    action="permanently_deleted",
                    previous_status="rejected",
                    new_status="deleted",
                    notes=notes,
                    review_details={
                        "deleted_meteorite_name": rejected_meteorite.name,
                        "deleted_meteorite_id": rejected_meteorite.id,
                        "deletion_timestamp": timezone.now().isoformat(),
                    },
                )
                rejected_meteorite.delete()
                return True

        except RejectedMeteorite._default_manager.model.DoesNotExist:
            raise ValidationError(f"Rejected record not found: ID={rejected_id}")
        except Exception as exc:
            logger.exception("permanently_delete failed rejected_id=%s: %s", rejected_id, exc)
            return False

    def get_approved_meteorites(self, reviewer: Optional[User] = None) -> List[Dict[str, Any]]:
        queryset = ApprovedMeteorite._default_manager.filter(is_active=True)
        if reviewer:
            queryset = queryset.filter(reviewer=reviewer)

        out: List[Dict[str, Any]] = []
        for meteorite in queryset:
            out.append(
                {
                    "id": meteorite.id,
                    "name": meteorite.name,
                    "classification": meteorite.classification,
                    "discovery_location": meteorite.discovery_location,
                    "origin": meteorite.origin,
                    "confidence_score": meteorite.confidence_score,
                    "approved_at": meteorite.approved_at,
                    "reviewer": meteorite.reviewer.username if meteorite.reviewer else None,
                    "organic_compounds_summary": meteorite.get_organic_compounds_summary(),
                    "references_count": meteorite.get_references_count(),
                }
            )
        return out

    @transaction.atomic
    def move_approved_to_recycle_bin(
        self,
        approved_id: int,
        deleter: User,
        reason: str = "user_deleted",
        notes: str = "",
    ) -> Dict[str, Any]:
        try:
            approved_meteorite = ApprovedMeteorite._default_manager.select_for_update().get(
                id=approved_id,
                is_active=True,
            )

            rejected_meteorite = RejectedMeteorite(
                name=approved_meteorite.name,
                classification=approved_meteorite.classification,
                discovery_location=approved_meteorite.discovery_location,
                origin=approved_meteorite.origin,
                organic_compounds=approved_meteorite.organic_compounds,
                contamination_exclusion_method=approved_meteorite.contamination_exclusion_method,
                references=approved_meteorite.references,
                confidence_score=approved_meteorite.confidence_score,
                extraction_source=approved_meteorite.extraction_source,
                extraction_metadata=approved_meteorite.extraction_metadata,
                reviewer=deleter,
                rejection_reason=reason or "user_deleted",
                rejection_category="user_deleted",
                original_pending_id=approved_meteorite.original_pending_id,
                can_restore=True,
            )
            rejected_meteorite.full_clean()
            rejected_meteorite.save()

            MeteoriteReviewLogNew.objects.create(
                rejected_meteorite=rejected_meteorite,
                reviewer=deleter,
                action="rejected",
                previous_status="approved",
                new_status="rejected",
                notes=notes,
                review_details={
                    "original_approved_id": approved_meteorite.id,
                    "deletion_reason": reason,
                    "deletion_timestamp": timezone.now().isoformat(),
                    "can_restore": True,
                },
            )

            approved_meteorite.is_active = False
            approved_meteorite.save(update_fields=["is_active"])

            return {
                "success": True,
                "rejected_id": rejected_meteorite.id,
                "message": "Data moved to recycle bin",
            }

        except ApprovedMeteorite._default_manager.model.DoesNotExist:
            raise ValidationError(f"Approved record not found or inactive: ID={approved_id}")
        except Exception as exc:
            logger.exception("move_approved_to_recycle_bin failed approved_id=%s: %s", approved_id, exc)
            return {"success": False, "error": str(exc)}

    def move_to_recycle_bin(
        self,
        approved_id: int,
        deleter: User,
        reason: str = "user_deleted",
        notes: str = "",
    ) -> Dict[str, Any]:
        return self.move_approved_to_recycle_bin(
            approved_id=approved_id,
            deleter=deleter,
            reason=reason,
            notes=notes,
        )

    def _calculate_priority(self, data: Dict[str, Any]) -> int:
        confidence_score = float(data.get("confidence_score", 0.0))
        if confidence_score >= self.quality_thresholds["high_confidence"]:
            return 3
        if confidence_score >= self.quality_thresholds["medium_confidence"]:
            return 2
        return 1

    def get_review_statistics(self) -> Dict[str, Any]:
        pending_qs = PendingMeteorite._default_manager.all()
        approved_qs = ApprovedMeteorite._default_manager.filter(is_active=True)
        rejected_qs = RejectedMeteorite._default_manager.all()

        pending_total = pending_qs.count()
        approved_total = approved_qs.count()
        rejected_total = rejected_qs.count()
        total = pending_total + approved_total + rejected_total

        def pct(count: int) -> float:
            return (float(count) / float(total) * 100.0) if total > 0 else 0.0

        return {
            "pending_total": pending_total,
            "pending_by_status": {
                "pending": pending_qs.filter(review_status="pending").count(),
                "under_review": pending_qs.filter(review_status="under_review").count(),
                "needs_revision": pending_qs.filter(review_status="needs_revision").count(),
            },
            "approved_total": approved_total,
            "rejected_total": rejected_total,
            "approval_rate": round(pct(approved_total), 2),
            "rejection_rate": round(pct(rejected_total), 2),
            "pending_rate": round(pct(pending_total), 2),
            "avg_confidence": (
                round(
                    sum(item.confidence_score for item in pending_qs[:200]) / max(1, min(200, pending_total)),
                    4,
                )
                if pending_total > 0
                else 0.0
            ),
            "last_updated": timezone.now().isoformat(),
        }


new_review_system = NewReviewSystem()
