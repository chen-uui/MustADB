"""Persist confirmed extraction results through the review workflow."""

import logging
from typing import Any, Dict, Optional

from django.contrib.auth.models import User

from meteorite_search.review_system_v2 import new_review_system

logger = logging.getLogger(__name__)


class MeteoriteStorageService:
    def initialize_rag_service(self) -> None:
        logger.info("MeteoriteStorageService: initialize_rag_service (noop)")

    def _store_to_database(
        self,
        meteorite_data: Dict[str, Any],
        *,
        submitter: Optional[User] = None,
        extraction_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Persist confirmed data into the pending-review queue."""
        try:
            metadata = dict(extraction_metadata or {})
            confidence = (
                meteorite_data.get("confidence_score")
                or meteorite_data.get("confidence")
                or metadata.get("confidence")
                or 0.0
            )

            submission_data = {
                "name": meteorite_data.get("name") or meteorite_data.get("meteorite_name") or "Unknown",
                "classification": meteorite_data.get("classification") or meteorite_data.get("type") or "Unknown",
                "discovery_location": (
                    meteorite_data.get("discovery_location")
                    or meteorite_data.get("location")
                    or "Unknown"
                ),
                "origin": meteorite_data.get("origin") or meteorite_data.get("source") or "Unknown",
                "organic_compounds": meteorite_data.get("organic_compounds") or [],
                "contamination_exclusion_method": (
                    meteorite_data.get("contamination_exclusion_method")
                    or meteorite_data.get("contamination_exclusion")
                    or "Not specified"
                ),
                "references": meteorite_data.get("references") or [],
                "confidence_score": float(confidence),
                "extraction_source": metadata.get("extraction_source", "pdf"),
                "extraction_metadata": metadata,
            }

            result = new_review_system.submit_for_review(submission_data, submitter=submitter)
            if result.get("success"):
                logger.info(
                    "MeteoriteStorageService: stored %s as pending_id=%s",
                    submission_data["name"],
                    result.get("pending_id"),
                )
            else:
                logger.warning(
                    "MeteoriteStorageService: review submission failed for %s: %s",
                    submission_data["name"],
                    result.get("error"),
                )
            return result
        except Exception as exc:
            logger.exception("Store to database failed: %s", exc)
            return {"success": False, "errors": [str(exc)]}
