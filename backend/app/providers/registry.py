from dataclasses import dataclass
from typing import Dict, Iterable, List

from app.providers.base import Provider, ProviderFactory, ProviderModel


@dataclass
class RegisteredProvider:
    name: str
    factory: ProviderFactory


class ProviderRegistry:
    """
    Registry to manage provider instances and model lookup.
    """

    def __init__(self) -> None:
        self._providers: Dict[str, RegisteredProvider] = {}

    def register(self, name: str, factory: ProviderFactory) -> None:
        self._providers[name] = RegisteredProvider(name=name, factory=factory)

    def providers(self) -> List[Provider]:
        return [entry.factory() for entry in self._providers.values()]

    def list_models(self) -> List[ProviderModel]:
        models: List[ProviderModel] = []
        for provider in self.providers():
            models.extend(provider.list_models())
        return models

    def resolve_models(self, requested: Iterable[str] | None = None) -> List[ProviderModel]:
        """
        If requested is None, return all available models.
        Otherwise, return only requested (even if unavailable).
        """
        available = {m.id: m for m in self.list_models()}
        if requested is None:
            return [m for m in available.values() if m.available]

        missing = [mid for mid in requested if mid not in available]
        if missing:
            raise ValueError(f"Unknown model(s): {', '.join(missing)}. Call GET /models to inspect registry.")
        return [available[mid] for mid in requested]
