from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional

from app.llms.base import LLMClient


@dataclass
class RegisteredModel:
    model_id: str
    factory: Callable[[], LLMClient]
    enabled: bool = True
    description: str | None = None
    provider: str | None = None
    disabled_reason: Optional[str] = None


class ModelRegistry:
    """
    Registry mapping string IDs to LLM client factories.
    """

    def __init__(self) -> None:
        self._models: Dict[str, RegisteredModel] = {}

    def register(
        self,
        model_id: str,
        factory: Callable[[], LLMClient],
        *,
        provider: Optional[str] = None,
        enabled: bool = True,
        description: str | None = None,
        disabled_reason: str | None = None,
    ) -> None:
        reason = disabled_reason if not enabled else None
        self._models[model_id] = RegisteredModel(
            model_id=model_id,
            factory=factory,
            enabled=enabled,
            description=description,
            provider=provider,
            disabled_reason=reason,
        )

    def available_ids(self) -> List[str]:
        return [mid for mid, entry in self._models.items() if entry.enabled]

    def list_models(self) -> List[dict]:
        result = []
        for mid, entry in self._models.items():
            result.append(
                {
                    "id": mid,
                    "provider": entry.provider,
                    "enabled": entry.enabled,
                    "disabled_reason": entry.disabled_reason,
                    "description": entry.description,
                }
            )
        return result

    def resolve(self, model_ids: Iterable[str] | None = None) -> List[LLMClient]:
        """
        If model_ids is None, return enabled models. If provided, return requested models (even if disabled),
        raising ValueError for unknown IDs.
        """
        if model_ids is None:
            ids = self.available_ids()
        else:
            ids = list(model_ids)

        missing = [mid for mid in ids if mid not in self._models]
        if missing:
            available = ", ".join(self.available_ids())
            suffix = f" Available models: {available}" if available else " Call GET /models to inspect registry."
            raise ValueError(f"Unknown model(s): {', '.join(missing)}.{suffix}")

        return [self._models[mid].factory() for mid in ids]
