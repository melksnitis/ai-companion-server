import argparse
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.free_model_policy import (  # noqa: E402
    FreeModelPolicyService,
    ModelNotFreeError,
    ModelNotFoundError,
    MissingOpenRouterAPIKeyError,
    OpenRouterModel,
)
from scripts import select_openrouter_model  # noqa: E402


def make_model(
    model_id: str,
    *,
    prompt_price: str,
    completion_price: str,
    request_price: str = "0",
) -> OpenRouterModel:
    return OpenRouterModel(
        id=model_id,
        name=model_id,
        pricing={
            "prompt": prompt_price,
            "completion": completion_price,
            "request": request_price,
        },
        provider="unit-test",
        context_length=128000,
        description="unit test model",
        raw={"id": model_id},
    )


@pytest.mark.asyncio
async def test_ensure_model_is_free(monkeypatch):
    service = FreeModelPolicyService(api_key="test-key", cache_ttl_seconds=0)
    models = [
        make_model("free/model", prompt_price="0", completion_price="0"),
        make_model("paid/model", prompt_price="0.000001", completion_price="0"),
    ]

    async def fake_fetch(_self):
        return models

    monkeypatch.setattr(FreeModelPolicyService, "_fetch_from_api", fake_fetch)

    model = await service.ensure_model_is_free("free/model")
    assert model.id == "free/model"

    with pytest.raises(ModelNotFreeError):
        await service.ensure_model_is_free("paid/model")

    with pytest.raises(ModelNotFoundError):
        await service.ensure_model_is_free("unknown/model")


@pytest.mark.asyncio
async def test_fetch_models_requires_api_key():
    service = FreeModelPolicyService(api_key="placeholder", cache_ttl_seconds=0)
    service.api_key = ""
    with pytest.raises(MissingOpenRouterAPIKeyError):
        await service.fetch_models(force_refresh=True)


def test_cli_updates_env(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    args = argparse.Namespace(env_file=str(env_file), update_example=False, dry_run=False)
    selected_model = make_model("free/model", prompt_price="0", completion_price="0")

    async def fake_list_free_models(*_, **__):
        return [selected_model]

    monkeypatch.setattr(
        select_openrouter_model.free_model_policy_service,
        "list_free_models",
        fake_list_free_models,
    )
    monkeypatch.setattr(
        select_openrouter_model.ModelSelectorApp,
        "run",
        lambda self: selected_model,
    )

    exit_code = select_openrouter_model.run_cli(args)
    assert exit_code == 0
    assert env_file.exists()
    env_contents = env_file.read_text()
    assert "OPENROUTER_MODEL_ID=" in env_contents
    assert "free/model" in env_contents


def test_cli_dry_run_does_not_touch_env(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    args = argparse.Namespace(env_file=str(env_file), update_example=False, dry_run=True)
    selected_model = make_model("free/model", prompt_price="0", completion_price="0")

    async def fake_list_free_models(*_, **__):
        return [selected_model]

    monkeypatch.setattr(
        select_openrouter_model.free_model_policy_service,
        "list_free_models",
        fake_list_free_models,
    )
    monkeypatch.setattr(
        select_openrouter_model.ModelSelectorApp,
        "run",
        lambda self: selected_model,
    )

    exit_code = select_openrouter_model.run_cli(args)
    assert exit_code == 0
    assert not env_file.exists()
