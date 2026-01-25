import asyncio
import random
import time
from datetime import datetime

from app.llms.base import LLMClient, LLMGeneration


class MockEchoClient(LLMClient):
    """
    Deterministic echo client that mirrors the prompt with a model tag.
    """

    name = "mock-echo"

    async def generate(self, prompt: str) -> LLMGeneration:
        await asyncio.sleep(0.05)
        content = f"[echo:{self.name}] {prompt.strip()}"
        return LLMGeneration(model=self.name, response=content, latency_ms=50.0, created_at=datetime.utcnow())


class MockReasonerClient(LLMClient):
    """
    Pseudo-reasoning client that returns a templated analysis using seeded randomness.
    """

    name = "mock-reasoner"

    async def generate(self, prompt: str) -> LLMGeneration:
        await asyncio.sleep(0.1)
        seed = abs(hash(prompt)) % (2**32)
        rng = random.Random(seed)
        stance = rng.choice(["concise", "cautious", "optimistic", "skeptical"])
        steps = rng.randint(2, 4)
        bullet_points = [f"step {i+1}: {self._fabricate_step(rng)}" for i in range(steps)]
        response = "analysis:\n" + "\n".join(f"- {bp}" for bp in bullet_points)
        return LLMGeneration(
            model=self.name,
            response=response,
            latency_ms=100.0,
            created_at=datetime.utcnow(),
            meta={"stance": stance},
        )

    def _fabricate_step(self, rng: random.Random) -> str:
        verbs = ["consider", "estimate", "compare", "project", "outline", "contrast"]
        nouns = ["impact", "tradeoff", "risk", "opportunity", "path", "constraint"]
        return f"{rng.choice(verbs)} {rng.choice(nouns)}"
