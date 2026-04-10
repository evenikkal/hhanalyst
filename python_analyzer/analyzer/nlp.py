"""NLP pipeline using Natasha (MIPT) for Russian text processing.

Based on: https://habr.com/ru/companies/mipt/articles/472890/
Uses Natasha's NER, morphological analysis, and segmentation.

Natasha internally uses pymorphy2 which requires pkg_resources (removed
in Python 3.14). We patch it to use pymorphy3 instead.
"""

import re
import sys
from dataclasses import dataclass, field
from typing import List

# Patch: redirect pymorphy2 → pymorphy3 for Python 3.14+ compatibility
import pymorphy3
sys.modules["pymorphy2"] = pymorphy3
sys.modules["pymorphy2.analyzer"] = pymorphy3.analyzer

from natasha import (
    Segmenter,
    MorphVocab,
    NewsEmbedding,
    NewsMorphTagger,
    NewsNERTagger,
    Doc,
)

# Initialize pipeline components once (heavy objects, reuse across calls)
segmenter = Segmenter()
morph_vocab = MorphVocab()
emb = NewsEmbedding()
morph_tagger = NewsMorphTagger(emb)
ner_tagger = NewsNERTagger(emb)


@dataclass
class NLPResult:
    """Result of NLP analysis on a single vacancy."""
    lemmatized_text: str = ""
    entities: List[dict] = field(default_factory=list)
    tokens: List[str] = field(default_factory=list)
    lemmas: List[str] = field(default_factory=list)


def _strip_html(text: str) -> str:
    """Remove HTML tags from hh.ru descriptions."""
    return re.sub(r"<[^>]+>", " ", text)


def analyze_text(text: str) -> NLPResult:
    """Run full NLP pipeline on text: segmentation, morphology, NER."""
    if not text:
        return NLPResult()

    text = _strip_html(text)
    doc = Doc(text)

    # Sentence and token segmentation
    doc.segment(segmenter)

    # Morphological tagging + lemmatization
    doc.tag_morph(morph_tagger)
    for token in doc.tokens:
        token.lemmatize(morph_vocab)

    # Named Entity Recognition
    doc.tag_ner(ner_tagger)
    for span in doc.spans:
        span.normalize(morph_vocab)

    tokens = [t.text for t in doc.tokens]
    lemmas = [t.lemma for t in doc.tokens if t.lemma]
    lemmatized_text = " ".join(lemmas)

    entities = []
    for span in doc.spans:
        entities.append({
            "text": span.text,
            "normal": span.normal,
            "type": span.type,  # PER, ORG, LOC
            "start": span.start,
            "stop": span.stop,
        })

    return NLPResult(
        lemmatized_text=lemmatized_text,
        entities=entities,
        tokens=tokens,
        lemmas=lemmas,
    )


def lemmatize(text: str) -> str:
    """Lemmatize text for improved keyword matching.

    E.g. 'опытом разработки на Python' → 'опыт разработка на python'
    """
    if not text:
        return ""
    text = _strip_html(text)
    doc = Doc(text)
    doc.segment(segmenter)
    doc.tag_morph(morph_tagger)
    for token in doc.tokens:
        token.lemmatize(morph_vocab)
    return " ".join(t.lemma for t in doc.tokens if t.lemma)


def extract_entities(text: str) -> List[dict]:
    """Extract named entities (PER, ORG, LOC) from text."""
    result = analyze_text(text)
    return result.entities


def extract_entities_batch(vacancies: list) -> dict:
    """Extract and aggregate entities across all vacancies.

    Returns {type: {normalized_name: count}}.
    """
    from collections import Counter

    agg = {"ORG": Counter(), "LOC": Counter(), "PER": Counter()}
    for v in vacancies:
        text = " ".join([
            v.get("name", ""),
            v.get("snippet", {}).get("requirement", "") or "",
            v.get("snippet", {}).get("responsibility", "") or "",
            v.get("description", "") or "",
        ])
        for ent in extract_entities(text):
            etype = ent["type"]
            name = ent["normal"] or ent["text"]
            if etype in agg:
                agg[etype][name] += 1

    return {k: dict(v.most_common(20)) for k, v in agg.items()}
