"""
Evidence enrichment for Semantic Graph Linking.
Deterministic, compact, and CI-safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import re
from typing import Any, Dict, List, Optional

# Import legal NER for enhanced entity extraction
try:
    from mahoun.pipelines.ingestion.legal_ner import LegalNEREngine
    HAS_LEGAL_NER = True
except ImportError:
    HAS_LEGAL_NER = False


_SYNONYMS = (
    ("رأی", "رای"),
    ("آيين", "آیین"),
    ("آیین‌نامه", "آیین نامه"),
    ("آيين‌نامه", "آیین نامه"),
    ("قانونی", "قانون"),
    ("رأی وحدت رویه", "رای وحدت رویه"),
)

_DIGIT_MAP = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
_ARABIC_DIGIT_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

_ARTICLE_RE = re.compile(r"(?:ماده|article)\s*([0-9۰-۹]+)", re.IGNORECASE)
_CLAUSE_RE = re.compile(r"(?:بند|clause)\s*([0-9۰-۹]+)", re.IGNORECASE)
_UNIFICATION_RE = re.compile(
    r"(?:رای وحدت رویه|رأی وحدت رویه|وحدت رویه)\s*([0-9۰-۹]+)",
    re.IGNORECASE,
)
_CIRCULAR_RE = re.compile(r"(?:بخشنامه|circular)\s*([0-9۰-۹]+)", re.IGNORECASE)
_JUDGMENT_RE = re.compile(
    r"(?:رأی|رای)(?:\s+(?:صادره|دادگاه|داوری|تجدیدنظر|استیناف|دادسرای|دادستان|شورای|هیئت|مرجع))+(?:\s+(?:تهران|اصفهان|تبریز|مشهد|شیراز|کرج|قم|اهواز))?(?:\s+(?:سال|در سال))?\s*([0-9۰-۹]{4})",
    re.IGNORECASE,
)
_DATE_RE = re.compile(r"([0-9۰-۹]{4}[/-][0-9۰-۹]{1,2}[/-][0-9۰-۹]{1,2})")
_YEAR_RE = re.compile(r"(?:سال\s*)?([0-9۰-۹]{4})")


@dataclass(frozen=True)
class Entity:
    entity_type: str
    text: str
    start: int
    end: int
    identity: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class EnrichedEvidence:
    doc_id: str
    chunk_hash: str
    locator: str
    text: str
    normalized_text: str
    entities: List[Entity]
    evidence_type: str
    authority_score: float
    relevance_score: float
    semantic_score: float
    recency_score: float
    conflict_risk: float
    overall_weight: float
    metadata: Dict[str, Any] = field(default_factory=dict)


def _normalize_digits(text: str) -> str:
    return text.translate(_DIGIT_MAP).translate(_ARABIC_DIGIT_MAP)


def normalize_text(text: str) -> str:
    normalized = _normalize_digits(text).lower()
    for src, dst in _SYNONYMS:
        normalized = normalized.replace(src, dst)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _entity_from_match(entity_type: str, match: re.Match, key: str) -> Entity:
    value = _normalize_digits(match.group(1))
    return Entity(
        entity_type=entity_type,
        text=match.group(0),
        start=match.start(),
        end=match.end(),
        identity={key: value},
    )


def _extract_entities(text: str) -> List[Entity]:
    entities: List[Entity] = []

    # Use enhanced legal NER if available
    if HAS_LEGAL_NER:
        try:
            ner_engine = LegalNEREngine()
            ner_results = ner_engine.extract(text)

            # Convert NER results to Entity objects
            for entity_type, entity_list in ner_results.items():
                for item in entity_list:
                    if isinstance(item, dict) and "text" in item:
                        # Map NER entity types to evidence enrichment types
                        mapped_type = _map_ner_type_to_evidence_type(entity_type)
                        if mapped_type:
                            entities.append(Entity(
                                entity_type=mapped_type,
                                text=item["text"],
                                start=item.get("start", 0),
                                end=item.get("end", len(item["text"])),
                                identity=item.get("metadata", {})
                            ))
        except Exception as e:
            # Fallback to basic regex extraction if NER fails
            import logging
            logging.getLogger(__name__).warning(f"LegalNER extraction failed, falling back to regex: {e}")

    # Always do basic regex extraction as fallback/supplement
    for match in _ARTICLE_RE.finditer(text):
        entities.append(_entity_from_match("ARTICLE", match, "article_no"))
    for match in _CLAUSE_RE.finditer(text):
        entities.append(_entity_from_match("CLAUSE", match, "clause_no"))
    for match in _UNIFICATION_RE.finditer(text):
        entities.append(_entity_from_match("UNIFICATION_RULING", match, "ruling_no"))
    for match in _CIRCULAR_RE.finditer(text):
        entities.append(_entity_from_match("CIRCULAR", match, "circular_no"))
    for match in _JUDGMENT_RE.finditer(text):
        year = _normalize_digits(match.group(1))
        if _is_year_valid(year):
            entities.append(
                Entity(
                    entity_type="JUDGMENT",
                    text=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    identity={"year": year},
                )
            )
    for match in _DATE_RE.finditer(text):
        date_value = _normalize_digits(match.group(1))
        year_value = date_value.split("-")[0].split("/")[0]
        entities.append(
            Entity(
                entity_type="DATE",
                text=match.group(1),
                start=match.start(),
                end=match.end(),
                identity={"date": date_value, "year": year_value},
            )
        )
    for match in _YEAR_RE.finditer(text):
        year = _normalize_digits(match.group(1))
        if _is_year_valid(year):
            entities.append(
                Entity(
                    entity_type="DATE",
                    text=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    identity={"year": year},
                )
            )
    return entities


def _map_ner_type_to_evidence_type(ner_type: str) -> Optional[str]:
    """Map NER entity types to evidence enrichment types"""
    mapping = {
        "persons": "PERSON",
        "organizations": "ORGANIZATION",
        "courts": "COURT",
        "laws": "LAW",
        "topics": "TOPIC"
    }
    return mapping.get(ner_type.lower())


def _is_year_valid(year: str) -> bool:
    if not year.isdigit() or len(year) != 4:
        return False
    value = int(year)
    return 1300 <= value <= 1500 or 1900 <= value <= 2100


def _normalize_year(year: int) -> int:
    if 1300 <= year <= 1500:
        return year + 621
    return year


def _compute_recency(entities: List[Entity]) -> float:
    years: List[int] = []
    for ent in entities:
        if ent.entity_type != "DATE":
            continue
        year = ent.identity.get("year")
        if not year and "date" in ent.identity:
            year = ent.identity["date"].split("-")[0].split("/")[0]
        if year and year.isdigit():
            years.append(_normalize_year(int(year)))
    if not years:
        return 0.0
    most_recent = max(years)
    reference_year = 2024
    delta = max(0, reference_year - most_recent)
    return max(0.0, 1.0 - min(delta, 20) / 20.0)


def _infer_evidence_type(normalized_text: str) -> str:
    if "وحدت رویه" in normalized_text or "unification" in normalized_text:
        return "unification_ruling"
    if "بخشنامه" in normalized_text or "circular" in normalized_text:
        return "circular"
    if "قرارداد" in normalized_text or "پیمان" in normalized_text:
        return "contract"
    if "دادنامه" in normalized_text or "رای دادگاه" in normalized_text or "حکم" in normalized_text:
        return "judgment"
    if "داوری" in normalized_text:
        return "arbitration"
    if "قانون" in normalized_text or "ماده" in normalized_text or "آیین نامه" in normalized_text:
        return "law"
    return "other"


def _authority_score(evidence_type: str) -> float:
    return {
        "law": 0.95,
        "unification_ruling": 0.9,
        "circular": 0.75,
        "judgment": 0.7,
        "arbitration": 0.6,
        "contract": 0.65,
        "other": 0.5,
    }.get(evidence_type, 0.5)


def _detect_conflict(normalized_text: str) -> float:
    if re.search(r"(اسقاط|سلب حق|waiver)", normalized_text):
        return 1.0
    return 0.0


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def enrich_evidence(
    text: str,
    doc_id: str,
    relevance_score: float,
    semantic_score: float,
    metadata: Optional[Dict[str, Any]] = None,
) -> EnrichedEvidence:
    normalized = normalize_text(text)
    entities = _extract_entities(text)
    evidence_type = _infer_evidence_type(normalized)
    authority = _authority_score(evidence_type)
    recency = _compute_recency(entities)
    conflict_risk = _detect_conflict(normalized)

    relevance = _clamp(relevance_score)
    semantic = _clamp(semantic_score)
    overall_weight = (
        0.55 * max(relevance, semantic)
        + 0.35 * authority
        + 0.10 * recency
    )

    chunk_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    locator = f"{doc_id}:{chunk_hash}"

    return EnrichedEvidence(
        doc_id=doc_id,
        chunk_hash=chunk_hash,
        locator=locator,
        text=text,
        normalized_text=normalized,
        entities=entities,
        evidence_type=evidence_type,
        authority_score=authority,
        relevance_score=relevance,
        semantic_score=semantic,
        recency_score=recency,
        conflict_risk=conflict_risk,
        overall_weight=overall_weight,
        metadata=metadata or {},
    )
