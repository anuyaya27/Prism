from collections import Counter
from typing import Sequence

from app.llms.base import LLMGeneration
from app.models.schemas import SynthesizedResponse


class ResponseSynthesizer:
    def synthesize(self, prompt: str, generations: Sequence[LLMGeneration]) -> SynthesizedResponse:  # noqa: D401
        """Combine model outputs into a single response."""
        raise NotImplementedError


class SimpleSynthesizer(ResponseSynthesizer):
    """
    Rule-based synthesizer:
    - If there is a consensus string, return it.
    - Otherwise return the longest response as a proxy for coverage.
    """

    def synthesize(self, prompt: str, generations: Sequence[LLMGeneration]) -> SynthesizedResponse:
        if not generations:
            return SynthesizedResponse(
                strategy="first",
                response="",
                rationale="no generations available",
                explain="No generations were available; synthesis returned empty.",
            )

        normalized = [gen.response.strip() for gen in generations]
        counter = Counter(normalized)
        (candidate, count) = counter.most_common(1)[0]

        if count > 1:
            primary = next(gen for gen in generations if gen.response.strip() == candidate)
            rationale = f"Selected majority response seen {count} times."
            explain = (
                f"Primary model: {primary.model} (provider={primary.provider}); "
                f"reason: majority consensus ({count}/{len(generations)}). "
                "Merged content: none (responses identical)."
            )
            return SynthesizedResponse(strategy="consensus", response=candidate, rationale=rationale, explain=explain)

        longest = max(generations, key=lambda g: len(g.response))
        rationale = "No overlap found; selected longest response as closest to full reasoning."
        explain = (
            f"Primary model: {longest.model} (provider={longest.provider}); "
            "reason: longest response heuristic for coverage; merged content: none."
        )
        return SynthesizedResponse(strategy="longest", response=longest.response, rationale=rationale, explain=explain)
