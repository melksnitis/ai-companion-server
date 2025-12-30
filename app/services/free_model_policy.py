from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional, Sequence

import httpx

from app.config import settings

OPENROUTER_MODELS_ENDPOINT = "https://openrouter.ai/api/v1/models/user"
DEFAULT_CACHE_TTL_SECONDS = 300


class OpenRouterAPIError(RuntimeError):
    """Base class for OpenRouter pricing/metadata errors."""

    pass


class MissingOpenRouterAPIKeyError(OpenRouterAPIError):
    """Raised when the OpenRouter API key is not configured."""

    def __init__(self) -> None:
        super().__init__(
            "OPENROUTER_API_KEY is not set. Please add it to your .env before using OpenRouter."
        )


class ModelNotFoundError(OpenRouterAPIError):
    """Raised when the requested model ID is not present in the user-specific catalog."""

    def __init__(self, model_id: str) -> None:
        super().__init__(f"Model '{model_id}' was not found in the OpenRouter catalog.")
        self.model_id = model_id


class ModelNotFreeError(OpenRouterAPIError):
    """Raised when a model has any non-zero pricing component."""

    def __init__(self, model_id: str, pricing: Dict[str, Any]) -> None:
        price_snapshot = ", ".join(f"{k}={v}" for k, v in pricing.items() if v is not None)
        super().__init__(
            f"Model '{model_id}' is not free. Pricing snapshot: {price_snapshot}."
        )
        self.model_id = model_id
        self.pricing = pricing


@dataclass(frozen=True)
class OpenRouterModel:
    """Subset of OpenRouter model metadata relevant for pricing decisions."""

    id: str
    name: Optional[str]
    pricing: Dict[str, Any]
    provider: Optional[str]
    context_length: Optional[int]
    description: Optional[str]
    raw: Dict[str, Any]

    def is_free(self) -> bool:
        """Return True if all known pricing entries are zero-equivalent."""
        return all(_price_is_zero(self.pricing.get(key)) for key in ("prompt", "completion", "request"))


def _price_is_zero(value: Any) -> bool:
    if value in (None, "", 0, "0", "0.0"):
        return True
    try:
        return Decimal(str(value)) == Decimal("0")
    except (InvalidOperation, TypeError):
        return False


class FreeModelPolicyService:
    """Service responsible for fetching OpenRouter model metadata and validating pricing."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
        endpoint: str = OPENROUTER_MODELS_ENDPOINT,
    ) -> None:
        self.api_key = api_key or settings.openrouter_api_key
        self.cache_ttl_seconds = cache_ttl_seconds
        self.endpoint = endpoint
        self._cache: Optional[List[OpenRouterModel]] = None
        self._cache_expiry: Optional[datetime] = None
        self._lock = asyncio.Lock()

    async def fetch_models(self, *, force_refresh: bool = False) -> List[OpenRouterModel]:
        """Fetch the OpenRouter models visible to the user, respecting cache TTL."""
        async with self._lock:
            if not force_refresh and self._cache and self._cache_expiry:
                if datetime.now(timezone.utc) < self._cache_expiry:
                    return self._cache

            models = await self._fetch_from_api()
            self._cache = models
            self._cache_expiry = datetime.now(timezone.utc) + timedelta(seconds=self.cache_ttl_seconds)
            return models

    async def list_free_models(self, *, force_refresh: bool = False) -> List[OpenRouterModel]:
        """Return all models whose pricing is effectively zero."""
        models = await self.fetch_models(force_refresh=force_refresh)
        free_models = [model for model in models if model.is_free()]
        return sorted(
            free_models,
            key=lambda model: (-(model.context_length or 0), model.id),
        )

    async def get_model(self, model_id: str) -> OpenRouterModel:
        """Return metadata for a given model ID."""
        models = await self.fetch_models()
        for model in models:
            if model.id == model_id or model.raw.get("canonical_slug") == model_id:
                return model
        raise ModelNotFoundError(model_id)

    async def ensure_model_is_free(self, model_id: str) -> OpenRouterModel:
        """Validate that the model is present and has zero pricing."""
        model = await self.get_model(model_id)
        if not model.is_free():
            raise ModelNotFreeError(model.id, model.pricing)
        return model

    async def refresh(self) -> List[OpenRouterModel]:
        """Force-refresh cache."""
        return await self.fetch_models(force_refresh=True)

    async def _fetch_from_api(self) -> List[OpenRouterModel]:
        if not self.api_key:
            raise MissingOpenRouterAPIKeyError()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(self.endpoint, headers=headers)

        if response.status_code >= 400:
            raise OpenRouterAPIError(
                f"Failed to fetch OpenRouter models (HTTP {response.status_code}): {response.text}"
            )

        payload = response.json()
        data = payload.get("data")
        if not isinstance(data, Sequence):
            raise OpenRouterAPIError("Malformed OpenRouter response: missing 'data' array")

        models: List[OpenRouterModel] = []
        for entry in data:
            if not isinstance(entry, Dict):
                continue
            pricing = entry.get("pricing") or {}
            top_provider = entry.get("top_provider") or {}
            model = OpenRouterModel(
                id=entry.get("id") or entry.get("canonical_slug"),
                name=entry.get("name"),
                pricing=pricing,
                provider=top_provider.get("name"),
                context_length=entry.get("context_length") or top_provider.get("context_length"),
                description=entry.get("description"),
                raw=entry,
            )
            if model.id:
                models.append(model)

        if not models:
            raise OpenRouterAPIError("OpenRouter response did not include any models.")

        return models


# Convenience singleton used across the app
free_model_policy_service = FreeModelPolicyService()
