import re
from typing import Iterable, List, Sequence, Set, Tuple

HEDGE_TERMS = {
    "maybe",
    "perhaps",
    "possibly",
    "might",
    "uncertain",
    "unclear",
    "likely",
    "unlikely",
    "could",
    "should",
    "may",
    "appears",
    "suggests",
}

NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def tokenize(text: str) -> List[str]:
    return [t for t in re.findall(r"\b\w+\b", text.lower()) if t]


def lcs_length(a: Sequence[str], b: Sequence[str]) -> int:
    if not a or not b:
        return 0
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[-1][-1]


def rouge_l(reference: str, candidate: str) -> float:
    ref_tokens = tokenize(reference)
    cand_tokens = tokenize(candidate)
    if not ref_tokens and not cand_tokens:
        return 1.0
    lcs = lcs_length(ref_tokens, cand_tokens)
    denom = max(len(ref_tokens), len(cand_tokens), 1)
    return lcs / denom


def bullet_request_count(prompt: str) -> int | None:
    match = re.search(r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:bullet|bullets|points|items)", prompt, re.IGNORECASE)
    if not match:
        return None
    token = match.group(1).lower()
    if token.isdigit():
        return int(token)
    return NUMBER_WORDS.get(token)


def count_bullets(text: str) -> int:
    bullet_lines = [line for line in text.splitlines() if re.match(r"^\s*[-*]\s+", line) or re.match(r"^\s*\d+\.\s+", line)]
    return len(bullet_lines)


def format_compliance(prompt: str, text: str) -> float:
    expected = bullet_request_count(prompt)
    if expected is None:
        return 1.0
    actual = count_bullets(text)
    if actual == 0 and expected > 0:
        return 0.0
    diff = abs(actual - expected)
    return max(0.0, 1.0 - (diff / max(expected, 1)))


def hedge_count(text: str) -> int:
    tokens = tokenize(text)
    return sum(1 for t in tokens if t in HEDGE_TERMS)


def keyword_coverage(prompt_keywords: Set[str], tokens_a: Set[str], tokens_b: Set[str]) -> float:
    if not prompt_keywords:
        return 0.0
    combined = tokens_a | tokens_b
    return len(combined & prompt_keywords) / len(prompt_keywords)


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def length_ratio(a_tokens: Sequence[str], b_tokens: Sequence[str]) -> float:
    if not a_tokens or not b_tokens:
        return 0.0
    shorter, longer = sorted([len(a_tokens), len(b_tokens)])
    return shorter / longer if longer else 0.0


def distance_summary(pairs: Iterable[Tuple[str, str, float, float]]) -> dict:
    """
    pairs: iterable of (a_id, b_id, rouge_l_score, jaccard_score).
    Returns max distance info.
    """
    worst = None
    for a, b, rouge, jacc in pairs:
        distance = (1 - rouge) + (1 - jacc)
        if worst is None or distance > worst[0]:
            worst = (distance, a, b, rouge, jacc)
    if worst is None:
        return {"max_distance": 0.0, "pair": None, "reason": "Not enough pairs."}
    distance_value, a, b, rouge, jacc = worst
    reason = f"Low overlap: rouge_l={rouge:.2f}, jaccard={jacc:.2f}"
    return {"max_distance": round(distance_value, 4), "pair": {"a": a, "b": b}, "reason": reason}
