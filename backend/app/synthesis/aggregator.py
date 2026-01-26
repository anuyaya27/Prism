import re
from collections import Counter
from typing import Sequence

from app.providers.base import GenerationResult
from app.synthesis.keywords import extract_keywords
from app.models.schemas import SynthesisPayload


class ResponseSynthesizer:
    def synthesize(self, prompt: str, generations: Sequence[GenerationResult], method: str) -> SynthesisPayload:  # noqa: D401
        """Combine model outputs into a single response."""
        raise NotImplementedError


class MultiStrategySynthesizer(ResponseSynthesizer):
    def synthesize(self, prompt: str, generations: Sequence[GenerationResult], method: str) -> SynthesisPayload:
        usable = [gen for gen in generations if gen.text]
        if not usable:
            return SynthesisPayload(
                ok=False,
                method="longest_nonempty",
                text=None,
                rationale="No responses were available to synthesize.",
            )

        if method == "consensus_overlap":
            return self._consensus_overlap(usable)
        if method == "best_of_n":
            return self._best_of_n(prompt, usable)
        return self._longest_nonempty(usable)

    def _consensus_overlap(self, generations: Sequence[GenerationResult]) -> SynthesisPayload:
        sentence_counter: Counter[str] = Counter()
        sentence_source: dict[str, set[str]] = {}
        for gen in generations:
            sentences = self._split_sentences(gen.text or "")
            unique_sentences = set(sentences)
            for sentence in unique_sentences:
                sentence_counter[sentence] += 1
                sentence_source.setdefault(sentence, set()).add(gen.model_id)

        overlapping = [s for s, count in sentence_counter.items() if count > 1]
        if not overlapping:
            return self._longest_nonempty(generations, rationale="No overlapping sentences; fell back to longest.")

        overlapping_sorted = sorted(overlapping, key=lambda s: (-sentence_counter[s], -len(s)))
        text = "\n".join(overlapping_sorted)
        rationale = f"Selected {len(overlapping_sorted)} overlapping sentence(s) appearing in multiple outputs."
        return SynthesisPayload(ok=True, method="consensus_overlap", text=text, rationale=rationale)

    def _best_of_n(self, prompt: str, generations: Sequence[GenerationResult]) -> SynthesisPayload:
        prompt_keywords = extract_keywords(prompt)
        best = None
        best_score = float("-inf")
        for gen in generations:
            text = gen.text or ""
            tokens = self._tokens(text)
            if not tokens:
                continue
            keyword_coverage = self._coverage(tokens, prompt_keywords)
            redundancy = 1 - (len(set(tokens)) / len(tokens))
            conciseness_penalty = 1 / (1 + len(tokens) / 200)
            score = keyword_coverage + (1 - redundancy) + conciseness_penalty
            if score > best_score:
                best_score = score
                best = (gen, score, keyword_coverage, redundancy, conciseness_penalty)

        if best is None:
            return self._longest_nonempty(generations, rationale="Unable to score responses; fell back to longest.")

        gen, score, coverage, redundancy, conciseness = best
        rationale = (
            f"Selected {gen.model_id} via best_of_n scoring: "
            f"coverage={coverage:.2f}, redundancy={redundancy:.2f}, conciseness={conciseness:.2f}, score={score:.2f}."
        )
        return SynthesisPayload(ok=True, method="best_of_n", text=gen.text, rationale=rationale)

    def _longest_nonempty(self, generations: Sequence[GenerationResult], rationale: str | None = None) -> SynthesisPayload:
        target = max(generations, key=lambda g: len(g.text or ""))
        return SynthesisPayload(
            ok=True,
            method="longest_nonempty",
            text=target.text,
            rationale=rationale or f"Selected longest response from {target.model_id}.",
        )

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return [t for t in re.findall(r"\b\w+\b", text.lower()) if t]

    def _split_sentences(self, text: str) -> list[str]:
        parts = re.split(r"[.!?]\s+|\n", text)
        return [p.strip() for p in parts if p.strip()]

    def _coverage(self, tokens: list[str], keywords: set[str]) -> float:
        if not keywords:
            return 0.0
        token_set = set(tokens)
        return len(token_set & keywords) / len(keywords)
