from collections import Counter
from typing import Sequence

from app.llms.base import LLMGeneration
from app.models.schemas import SynthesisPayload


class ResponseSynthesizer:
    def synthesize(self, prompt: str, generations: Sequence[LLMGeneration]) -> SynthesisPayload:  # noqa: D401
        """Combine model outputs into a single response."""
        raise NotImplementedError


class SimpleSynthesizer(ResponseSynthesizer):
    """
    Rule-based synthesizer:
    - Prefer majority/consensus if present.
    - Otherwise return the longest non-empty response as a proxy for coverage.
    """

    def synthesize(self, prompt: str, generations: Sequence[LLMGeneration]) -> SynthesisPayload:
        usable = [gen for gen in generations if gen.response and not gen.error]
        pool = usable if usable else [gen for gen in generations if gen.response]

        if not pool:
            return SynthesisPayload(
                ok=False,
                text=None,
                method="simple_majority",
                rationale="No responses were available to synthesize.",
            )

        normalized = [gen.response.strip() for gen in pool]
        counter = Counter(normalized)
        candidate, count = counter.most_common(1)[0]

        if count > 1:
            rationale = f"Selected majority response seen {count} time(s) among {len(pool)} usable outputs."
            return SynthesisPayload(ok=True, text=candidate, method="simple_majority", rationale=rationale)

        longest = max(pool, key=lambda g: len(g.response))
        rationale = "No overlaps found; selected longest non-empty response."
        return SynthesisPayload(ok=True, text=longest.response, method="longest_nonempty", rationale=rationale)
