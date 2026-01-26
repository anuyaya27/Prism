import re

STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "of",
    "to",
    "for",
    "in",
    "on",
    "with",
    "by",
    "at",
    "from",
    "that",
    "this",
    "these",
    "those",
    "is",
    "are",
    "was",
    "were",
    "be",
    "as",
    "it",
    "its",
    "their",
    "they",
    "you",
    "your",
}


def extract_keywords(text: str) -> set[str]:
    tokens = [t for t in re.findall(r"\b\w+\b", text.lower()) if len(t) > 2 and t not in STOPWORDS]
    return set(tokens)
