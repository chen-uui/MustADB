import ast
import json
import re
from typing import Any, Dict, Iterable, List, Optional


class ExtractionFieldPostprocessor:
    PLACEHOLDER_TEXTS = {
        "",
        "unknown",
        "not specified",
        "none",
        "null",
        "n/a",
        "na",
    }
    GENERIC_METEORITE_BLOCKLIST = {
        "meteorite",
        "meteorites",
        "sample",
        "samples",
        "paper",
        "academic paper",
    }
    TITLE_STOPWORDS = {
        "the",
        "of",
        "and",
        "for",
        "with",
        "from",
        "using",
        "based",
        "analysis",
        "study",
        "evidence",
        "determination",
        "algorithm",
        "model",
        "pre-training",
    }
    KNOWN_NAME_MAP = {
        "allende": "Allende",
        "murchison": "Murchison",
        "tissint": "Tissint",
        "nakhla": "Nakhla",
        "orgueil": "Orgueil",
        "orgueil": "Orgueil",
        "tagish lake": "Tagish Lake",
        "tagish": "Tagish Lake",
        "winchcombe": "Winchcombe",
        "sutters mill": "Sutters Mill",
        "chelyabinsk": "Chelyabinsk",
        "sikhote-alin": "Sikhote-Alin",
        "sikhote alin": "Sikhote-Alin",
        "gibeon": "Gibeon",
        "campo del cielo": "Campo del Cielo",
        "ryugu": "Ryugu",
        "bennu": "Bennu",
    }
    KNOWN_NAME_PATTERN = re.compile(
        r"\b("
        + "|".join(re.escape(name) for name in sorted(KNOWN_NAME_MAP.keys(), key=len, reverse=True))
        + r")\b",
        re.IGNORECASE,
    )

    NWA_PATTERN = re.compile(r"\bNWA\s*-?\s*(\d{3,6})\b", re.IGNORECASE)
    ALH_PATTERN = re.compile(r"\bALH\s*-?\s*(\d{3,6})\b", re.IGNORECASE)
    EETA_PATTERN = re.compile(r"\bEETA\s*-?\s*(\d{3,6})\b", re.IGNORECASE)

    PHRASE_SPLIT_PATTERN = re.compile(r"[;,\uFF0C\uFF1B\u3001]+")

    CONTROL_KEYWORDS = (
        "sterile",
        "blank",
        "control",
        "contamination",
        "dnase",
        "clean room",
        "freezer",
        "storage",
        "curation",
        "prevent",
        "minimize",
        "foil",
        "protocol",
    )
    GENERIC_CONTROL_ONLY = {"sterile handling", "clean room technology"}

    ORGANIC_CANONICAL_PATTERNS = (
        (re.compile(r"\biom\b|\binsoluble organic matter\b", re.IGNORECASE), "insoluble organic matter"),
        (re.compile(r"\bsom\b|\bsoluble organic matter\b", re.IGNORECASE), "soluble organic matter"),
        (
            re.compile(
                r"\bpolycyclic aromatic hydrocarbons?\b|\bpahs?\b",
                re.IGNORECASE,
            ),
            "PAHs",
        ),
        (re.compile(r"\bamino acids?\b", re.IGNORECASE), "amino acids"),
        (re.compile(r"\bnucleobases?\b", re.IGNORECASE), "nucleobases"),
        (
            re.compile(
                r"\baliphatic (?:organic )?(?:compounds?|hydrocarbons?)\b",
                re.IGNORECASE,
            ),
            "aliphatic compounds",
        ),
        (
            re.compile(
                r"\baromatic (?:organic )?(?:compounds?|hydrocarbons?)\b",
                re.IGNORECASE,
            ),
            "aromatic compounds",
        ),
        (re.compile(r"\baliphatic amines?\b", re.IGNORECASE), "aliphatic amines"),
        (
            re.compile(r"\bvolatile organic compounds?\b", re.IGNORECASE),
            "volatile organic compounds",
        ),
        (
            re.compile(r"\bdimethyl ?sulfides?\b", re.IGNORECASE),
            "dimethylsulfides",
        ),
        (
            re.compile(r"\bn[- ]heterocycles?\b", re.IGNORECASE),
            "n-heterocycles",
        ),
        (re.compile(r"\bhydrocarbons?\b", re.IGNORECASE), "hydrocarbons"),
    )
    ORGANIC_NOISE_HINTS = (
        "dominant",
        "displays",
        "evident",
        "identified",
        "tentative",
        "figure",
        "study",
        "along with",
        "can also",
    )

    @classmethod
    def postprocess_submission_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(data)

        raw_name = data.get("name") or data.get("meteorite_name") or ""
        normalized_name = cls.normalize_meteorite_name(raw_name)
        out["name"] = normalized_name

        raw_contam = data.get("contamination_exclusion_method") or data.get("contamination_exclusion") or ""
        out["contamination_exclusion_method"] = cls.normalize_contamination_controls_text(raw_contam)

        raw_organic = data.get("organic_compounds")
        out["organic_compounds"] = cls.normalize_organic_compounds_list(raw_organic)

        return out

    @classmethod
    def normalize_meteorite_name(cls, value: Any) -> str:
        text = cls._clean_text(value)
        if not text:
            return ""

        candidates: List[str] = []
        for code in cls._extract_code_candidates(text):
            cls._append_unique(candidates, code)
        for name in cls._extract_known_name_candidates(text):
            cls._append_unique(candidates, name)

        if candidates:
            return "; ".join(candidates[:3])

        if cls._looks_like_title_noise(text):
            return ""

        token = cls._clean_text(text)
        if not token:
            return ""
        lowered = token.lower()
        if lowered in cls.GENERIC_METEORITE_BLOCKLIST:
            return ""
        if len(token.split()) > 5 or len(token) > 48:
            return ""
        if not re.search(r"[A-Za-z0-9]", token):
            return ""
        return token

    @classmethod
    def normalize_contamination_controls_text(cls, value: Any) -> str:
        tokens = cls.normalize_contamination_controls_tokens(value)
        return "; ".join(tokens)

    @classmethod
    def normalize_contamination_controls_tokens(cls, value: Any) -> List[str]:
        out: List[str] = []
        raw_phrases = cls._to_phrase_candidates(value)
        for phrase in raw_phrases:
            for core in cls._canonicalize_contamination_phrase(phrase):
                cls._append_unique(out, core, case_insensitive=True)

        if len(out) == 1 and out[0].lower() in cls.GENERIC_CONTROL_ONLY:
            return []
        return out[:6]

    @classmethod
    def normalize_organic_compounds_text(cls, value: Any) -> str:
        tokens = cls.normalize_organic_compounds_tokens(value)
        return "; ".join(tokens)

    @classmethod
    def normalize_organic_compounds_list(cls, value: Any) -> List[str]:
        return cls.normalize_organic_compounds_tokens(value)

    @classmethod
    def normalize_organic_compounds_tokens(cls, value: Any) -> List[str]:
        out: List[str] = []
        raw_tokens = cls._to_phrase_candidates(value)
        for token in raw_tokens:
            canonical_matches = cls._extract_canonical_organic_matches(token)
            if canonical_matches:
                for normalized in canonical_matches:
                    cls._append_unique(out, normalized, case_insensitive=True)
                continue
            normalized = cls._canonicalize_organic_token(token)
            if not normalized:
                continue
            cls._append_unique(out, normalized, case_insensitive=True)
        return out[:12]

    @classmethod
    def _extract_code_candidates(cls, text: str) -> List[str]:
        codes: List[str] = []
        for match in cls.NWA_PATTERN.finditer(text):
            cls._append_unique(codes, f"NWA {match.group(1)}")
        for match in cls.ALH_PATTERN.finditer(text):
            cls._append_unique(codes, f"ALH{match.group(1)}")
        for match in cls.EETA_PATTERN.finditer(text):
            cls._append_unique(codes, f"EETA{match.group(1)}")
        return codes

    @classmethod
    def _extract_known_name_candidates(cls, text: str) -> List[str]:
        names: List[str] = []
        for match in cls.KNOWN_NAME_PATTERN.finditer(text):
            key = match.group(1).lower()
            value = cls.KNOWN_NAME_MAP.get(key)
            if value:
                cls._append_unique(names, value)
        return names

    @classmethod
    def _canonicalize_contamination_phrase(cls, phrase: str) -> List[str]:
        text = cls._clean_text(phrase)
        if not text:
            return []
        lower = text.lower()

        if not any(keyword in lower for keyword in cls.CONTROL_KEYWORDS):
            return []

        out: List[str] = []
        if "dnase" in lower:
            out.append("DNase treatment")
        if ("quality-control" in lower or "quality control" in lower) and "blank" in lower:
            if "di water" in lower:
                out.append("quality-control blank of DI water")
            else:
                out.append("quality-control blank")
        if "sterile" in lower and "handling" in lower:
            out.append("sterile handling")
        if "clean room" in lower:
            out.append("clean room technology")
        if ("aluminum foil" in lower or "foil" in lower) and "storage" in lower:
            out.append("aluminum foil storage")
        if "freezer" in lower:
            out.append("freezer storage")
        if "stringent curation" in lower:
            out.append("stringent curation conditions")
        if "minimize" in lower and "contamination" in lower:
            out.append("minimize terrestrial contamination")
        if "prevent" in lower and ("oxidation" in lower or "hydrolysis" in lower):
            out.append("prevent oxidation and hydrolysis")

        if out:
            return out

        words = text.split()
        if len(words) > 12:
            text = " ".join(words[:12])
        return [text]

    @classmethod
    def _canonicalize_organic_token(cls, token: str) -> str:
        text = cls._clean_text(token)
        if not text:
            return ""

        if cls._looks_like_organic_noise(text):
            return ""

        if "(" in text and len(text) > 40:
            text = text.split("(", 1)[0].strip()

        if len(text.split()) > 7 or len(text) > 56:
            return ""

        if not re.search(r"[A-Za-z]", text):
            return ""

        return text

    @classmethod
    def _extract_canonical_organic_matches(cls, token: str) -> List[str]:
        text = cls._clean_text(token)
        if not text:
            return []

        matches: List[str] = []
        for pattern, target in cls.ORGANIC_CANONICAL_PATTERNS:
            if pattern.search(text):
                cls._append_unique(matches, target, case_insensitive=True)

        if "PAHs" in matches:
            matches = [
                item for item in matches if item not in {"hydrocarbons", "aromatic compounds"}
            ]
        return matches

    @classmethod
    def _looks_like_title_noise(cls, text: str) -> bool:
        words = text.split()
        if len(words) > 12:
            return True
        lowered = text.lower()
        stopword_hits = sum(1 for w in words if w.lower().strip(".,:;()") in cls.TITLE_STOPWORDS)
        if len(words) >= 8 and stopword_hits >= 4:
            return True
        if any(mark in lowered for mark in (" by ", " et al", "doi", "http://", "https://")):
            return True
        return False

    @classmethod
    def _looks_like_organic_noise(cls, text: str) -> bool:
        lower = text.lower()
        if "." in text and len(text.split()) > 5:
            return True
        if any(hint in lower for hint in cls.ORGANIC_NOISE_HINTS):
            return True
        return False

    @classmethod
    def _to_phrase_candidates(cls, value: Any) -> List[str]:
        if value is None:
            return []

        if isinstance(value, dict):
            values: List[str] = []
            if "details" in value:
                values.extend(cls._to_phrase_candidates(value.get("details")))
            for item in value.values():
                values.extend(cls._to_phrase_candidates(item))
            return values

        if isinstance(value, (list, tuple, set)):
            values: List[str] = []
            for item in value:
                values.extend(cls._to_phrase_candidates(item))
            return values

        text = cls._clean_text(value)
        if not text:
            return []

        parsed = cls._try_literal_or_json(text)
        if isinstance(parsed, (list, tuple, set, dict)):
            return cls._to_phrase_candidates(parsed)

        return [part.strip() for part in cls.PHRASE_SPLIT_PATTERN.split(text) if part and part.strip()]

    @classmethod
    def _try_literal_or_json(cls, text: str) -> Optional[Any]:
        s = str(text or "").strip()
        if not s or s[0] not in "[{(":
            return None
        try:
            return ast.literal_eval(s)
        except (ValueError, SyntaxError):
            pass
        try:
            return json.loads(s)
        except (ValueError, TypeError, json.JSONDecodeError):
            return None

    @classmethod
    def _clean_text(cls, value: Any) -> str:
        if value is None:
            return ""
        text = re.sub(r"\s+", " ", str(value)).strip()
        if not text:
            return ""
        lowered = text.lower()
        if lowered in cls.PLACEHOLDER_TEXTS:
            return ""
        if text in {"{}", "[]"}:
            return ""
        return text

    @classmethod
    def _append_unique(
        cls, values: List[str], item: str, *, case_insensitive: bool = False
    ) -> None:
        cleaned = cls._clean_text(item)
        if not cleaned:
            return
        if case_insensitive:
            target = cleaned.lower()
            for existing in values:
                if existing.lower() == target:
                    return
        else:
            if cleaned in values:
                return
        values.append(cleaned)
