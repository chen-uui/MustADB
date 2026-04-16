import json
import re
from typing import Any, Dict, List

from .extraction_postprocess import ExtractionFieldPostprocessor

EXTRACTION_OUTPUT_TEMPLATE: Dict[str, Any] = {
    "name": "",
    "classification": "",
    "discovery_location": "",
    "origin": "",
    "organic_compounds": [],
    "contamination_exclusion_method": "",
    "references": [],
}

ORGANIC_COMPOUND_CANONICAL_EXAMPLES = [
    "insoluble organic matter",
    "soluble organic matter",
    "PAHs",
    "amino acids",
    "nucleobases",
    "aliphatic compounds",
    "aromatic compounds",
]

ORGANIC_COMPOUNDS_PROMPT_GUIDANCE = (
    '"organic_compounds" must be a JSON array of short compound names or compound classes, '
    "not an object and not a sentence. Prefer canonical labels when supported by the text: "
    + ", ".join(f'"{item}"' for item in ORGANIC_COMPOUND_CANONICAL_EXAMPLES)
    + ". Use [] when the fragment does not mention any organic compounds."
)

STRICT_ORGANIC_COMPOUNDS_PROMPT_GUIDANCE = (
    '"organic_compounds" must be a JSON array of short compound names or explicit compound classes '
    "that are directly stated in the current text fragment. Do not infer, expand, or guess from "
    'generic phrases such as "organic matter", "organics", "prebiotic compounds", '
    '"indigenous organics", "soluble organics", or "organic inventory". '
    "Only use a canonical label when that exact class or a clear synonym is explicitly present in the fragment. "
    'Do not map "organic matter" to "insoluble organic matter" or "soluble organic matter" unless '
    '"insoluble organic matter", "soluble organic matter", "IOM", or "SOM" is explicitly present. '
    "If the evidence is generic or ambiguous, return []."
)

CONTAMINATION_EXCLUSION_PROMPT_GUIDANCE = (
    '"contamination_exclusion_method" should contain only explicit anti-contamination or QA/QC procedures '
    'directly mentioned in the fragment, such as blank controls, sterile handling, DNase treatment, '
    'cold curation, aluminum foil storage, or similar methods. Do not infer methods from a general '
    'discussion of contamination risk.'
)

EXTRACTION_OUTPUT_SCHEMA_JSON = json.dumps(EXTRACTION_OUTPUT_TEMPLATE, ensure_ascii=False)


def get_organic_compounds_prompt_guidance(strict: bool = False) -> str:
    if strict:
        return STRICT_ORGANIC_COMPOUNDS_PROMPT_GUIDANCE
    return ORGANIC_COMPOUNDS_PROMPT_GUIDANCE


def normalize_extraction_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return dict(EXTRACTION_OUTPUT_TEMPLATE)

    normalized = dict(EXTRACTION_OUTPUT_TEMPLATE)
    normalized["name"] = ExtractionFieldPostprocessor.normalize_meteorite_name(
        payload.get("name") or payload.get("meteorite_name") or ""
    )
    normalized["classification"] = _normalize_text(payload.get("classification"))
    normalized["discovery_location"] = _normalize_text(payload.get("discovery_location"))
    normalized["origin"] = _normalize_text(payload.get("origin"))
    normalized["organic_compounds"] = ExtractionFieldPostprocessor.normalize_organic_compounds_list(
        payload.get("organic_compounds")
    )
    normalized["contamination_exclusion_method"] = (
        ExtractionFieldPostprocessor.normalize_contamination_controls_text(
            payload.get("contamination_exclusion_method")
            or payload.get("contamination_exclusion")
            or ""
        )
    )
    normalized["references"] = _normalize_references(payload.get("references"))
    return normalized


def _normalize_text(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    if text.lower() in ExtractionFieldPostprocessor.PLACEHOLDER_TEXTS:
        return ""
    if text in {"{}", "[]"}:
        return ""
    return text


def _normalize_references(value: Any) -> List[Dict[str, str]]:
    if not isinstance(value, list):
        return []

    normalized: List[Dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        cleaned = {
            str(key): _normalize_text(raw_value)
            for key, raw_value in item.items()
            if _normalize_text(raw_value)
        }
        if cleaned:
            normalized.append(cleaned)
        if len(normalized) >= 10:
            break
    return normalized
