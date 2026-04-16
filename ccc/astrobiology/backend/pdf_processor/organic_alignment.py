import re
from typing import List, Sequence, Tuple


GENERIC_ORGANIC_PHRASES = (
    "organic matter",
    "organics",
    "prebiotic compounds",
    "prebiotic compound",
    "indigenous organics",
    "soluble organics",
    "organic inventory",
    "organic-rich",
    "organic rich",
    "carbonaceous material",
)

INORGANIC_KEYWORDS = (
    "perchlorate",
    "chlorate",
    "nitrate",
    "nitrite",
    "sulfate",
    "sulfite",
    "phosphate",
    "chloride",
    "carbonate",
    "silicate",
    "oxide",
    "hydroxide",
    "olivine",
    "pyroxene",
    "iodide",
    "water",
    "ice",
)

ORGANIC_MARKERS = (
    "organic",
    "hydrocarbon",
    "amino",
    "amine",
    "nucleobase",
    "carbox",
    "aldehyde",
    "ketone",
    "pah",
    "benz",
    "naphthal",
    "anthrac",
    "phenanthr",
    "fluoranth",
    "pyrene",
    "fluorene",
    "methyl",
    "ethyl",
    "formaldehyde",
    "organosulfide",
    "dimethylsulfide",
)

FORMULA_WHITELIST = {
    "aib",
    "gly",
    "ala",
}

FORMULA_WITHOUT_C_PATTERN = re.compile(r"^(?!.*c)(?=.*\d)[a-z][a-z0-9+\-]{1,8}$", re.IGNORECASE)

GOLD_LEVEL_CLASS_RULES = (
    (
        re.compile(r"\b(pahs?|polycyclic aromatic hydrocarbons?)\b", re.IGNORECASE),
        "PAHs",
    ),
    (
        re.compile(r"\b(dimethylsulfides?|dimethyl sulfides?)\b", re.IGNORECASE),
        "dimethylsulfides",
    ),
    (
        re.compile(r"\b(aliphatic amines?)\b", re.IGNORECASE),
        "aliphatic amines",
    ),
    (
        re.compile(r"\b(amino acids?)\b", re.IGNORECASE),
        "amino acids",
    ),
    (
        re.compile(r"\b(carboxylic acids?)\b", re.IGNORECASE),
        "carboxylic acids",
    ),
    (
        re.compile(r"\b(hydrocarbons?)\b", re.IGNORECASE),
        "hydrocarbons",
    ),
    (
        re.compile(r"\b(volatile organic compounds?)\b", re.IGNORECASE),
        "volatile organic compounds",
    ),
    (
        re.compile(r"\b(primordial organic matter)\b", re.IGNORECASE),
        "primordial organic matter",
    ),
)

PROJECTION_RULES = (
    (
        re.compile(
            r"\b(gly|glycine|ala|alanine|serine|valine|isovaline|"
            r"[abgβαγ\- ]*alanine|[aα\- ]*aminoisobutyric acid|aib|amino acids?)\b",
            re.IGNORECASE,
        ),
        "amino acids",
        "specific amino-acid items -> amino acids",
    ),
    (
        re.compile(
            r"\b(aliphatic amines?|monoamines?|amines?)\b",
            re.IGNORECASE,
        ),
        "aliphatic amines",
        "amine-family items -> aliphatic amines",
    ),
    (
        re.compile(
            r"\b(nucleobases?|adenine|guanine|uracil|cytosine|thymine|xanthine|hypoxanthine)\b",
            re.IGNORECASE,
        ),
        "nucleobases",
        "specific nucleobases -> nucleobases",
    ),
    (
        re.compile(
            r"\b(dicarboxylic acids?|monocarboxylic acids?|pyridine carboxylic acids?|carboxylic acids?)\b",
            re.IGNORECASE,
        ),
        "carboxylic acids",
        "carboxylic-acid subclasses -> carboxylic acids",
    ),
    (
        re.compile(
            r"\b(pahs?|polycyclic aromatic hydrocarbons?|naphthalenes?|"
            r"phenanthrenes?|anthracenes?|fluoranthenes?|pyrenes?|chrysenes?|"
            r"benzanthracenes?|tetracenes?|fluorenes?)\b",
            re.IGNORECASE,
        ),
        "PAHs",
        "specific PAH species -> PAHs",
    ),
    (
        re.compile(
            r"\b(dimethylsulfides?|dimethyl sulfides?)\b",
            re.IGNORECASE,
        ),
        "dimethylsulfides",
        "dimethyl sulfide variants -> dimethylsulfides",
    ),
)


def align_organic_compounds_for_evaluation(
    tokens: Sequence[str],
    *,
    use_filter: bool,
    use_projection: bool,
) -> Tuple[List[str], List[str], List[str], List[str]]:
    raw_tokens = _dedupe(tokens)
    filtered_tokens = list(raw_tokens)
    removed_tokens: List[str] = []

    if use_filter:
        filtered_tokens, removed_tokens = filter_obvious_non_organics(raw_tokens)

    projected_tokens = list(filtered_tokens)
    projection_notes: List[str] = []
    if use_projection:
        projected_tokens, projection_notes = project_tokens_to_gold_classes(filtered_tokens)

    return raw_tokens, filtered_tokens, projected_tokens, projection_notes + [
        f"filtered: {token}" for token in removed_tokens
    ]


def filter_obvious_non_organics(tokens: Sequence[str]) -> Tuple[List[str], List[str]]:
    kept: List[str] = []
    removed: List[str] = []
    for token in _dedupe(tokens):
        lower = token.lower()
        if _gold_level_class_target(token):
            kept.append(token)
            continue
        if _is_generic_organic_phrase(lower):
            removed.append(token)
            continue
        if _is_non_organic_formula(lower):
            removed.append(token)
            continue
        if _has_inorganic_keyword(lower) and not _has_organic_marker(lower):
            removed.append(token)
            continue
        kept.append(token)
    return kept, removed


def project_tokens_to_gold_classes(tokens: Sequence[str]) -> Tuple[List[str], List[str]]:
    deduped = _dedupe(tokens)
    projected: List[str] = []
    notes: List[str] = []
    seen = set()

    for token in deduped:
        canonical_class = _gold_level_class_target(token)
        if not canonical_class:
            continue
        canonical_lower = canonical_class.lower()
        if canonical_lower not in seen:
            projected.append(canonical_class)
            seen.add(canonical_lower)
        if re.sub(r"\s+", " ", token).strip().lower() != canonical_lower:
            notes.append(f"{token} -> {canonical_class} (gold-level class preserved)")

    for token in deduped:
        canonical_class = _gold_level_class_target(token)
        if canonical_class:
            continue
        mapped = False
        for pattern, target, note in PROJECTION_RULES:
            if pattern.search(token):
                target_lower = target.lower()
                if target_lower not in seen:
                    projected.append(target)
                    seen.add(target_lower)
                notes.append(f"{token} -> {target} ({note})")
                mapped = True
                break
        if not mapped:
            token_lower = token.lower()
            if token_lower not in seen:
                projected.append(token)
                seen.add(token_lower)
    return projected, _dedupe(notes)


def _is_generic_organic_phrase(lower: str) -> bool:
    return any(phrase in lower for phrase in GENERIC_ORGANIC_PHRASES)


def _has_inorganic_keyword(lower: str) -> bool:
    return any(keyword in lower for keyword in INORGANIC_KEYWORDS)


def _has_organic_marker(lower: str) -> bool:
    return any(marker in lower for marker in ORGANIC_MARKERS)


def _is_non_organic_formula(lower: str) -> bool:
    compact = lower.replace(" ", "")
    if compact in FORMULA_WHITELIST:
        return False
    if compact in {"clo4", "clo3", "no3", "no2", "so4", "po4"}:
        return True
    return bool(FORMULA_WITHOUT_C_PATTERN.fullmatch(compact))


def _gold_level_class_target(token: str) -> str:
    text = re.sub(r"\s+", " ", str(token or "")).strip()
    if not text:
        return ""
    for pattern, target in GOLD_LEVEL_CLASS_RULES:
        if pattern.search(text):
            return target
    return ""


def _dedupe(values: Sequence[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        out.append(text)
    return out
