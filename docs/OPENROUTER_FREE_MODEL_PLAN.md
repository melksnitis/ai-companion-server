# OpenRouter Free-Only Model Enforcement Plan

## Goals
1. Ensure the backend **never uses paid OpenRouter models** automatically.
2. Surface a **clear startup error** when the configured model is not free, guiding operators to a CLI workflow.
3. Ship a **“beautiful” TUI selector** that helps developers choose one of the currently free OpenRouter models and persists the selection (e.g., in `.env`).

## Current State
- `AgentService` hardcodes `deepseek/deepseek-v3.2` (@app/services/agent_service.py#67-75).
- Router config also pins the same model (@router/config.json#14-26).
- No automated pricing validation. Switching models requires manual `.env` or config edits.

## Proposed Components

### 1. `FreeModelPolicyService`
Location: `app/services/free_model_policy.py`

Responsibilities:
1. **Fetch user-filtered model metadata** from `GET https://openrouter.ai/api/v1/models/user` using `OPENROUTER_API_KEY`.
2. **Cache responses** in memory (e.g., 5 minutes) and expose helpers:
   - `fetch_models(force_refresh=False)`
   - `get_model(model_id)`
   - `is_free(model_id)` (price fields `prompt`, `completion`, and `request` must be `"0"`).
3. **Guard API**:
   - `ensure_model_is_free(model_id)` → raises `ValueError` if the model is missing or has any non-zero price component.
4. **Utility**: `list_free_models()` sorted by context window, then alphabetically.

Implementation Notes:
- Use `httpx.AsyncClient` (already in dependencies) for non-blocking fetches.
- Centralize auth header injection using `settings.openrouter_api_key`.
- Provide structured error messages when the API call or parsing fails.

### 2. Server-Side Enforcement

**Configuration**
- Add `OPENROUTER_MODEL_ID` to `Settings` and `.env.example`.
- Continue to allow router JSON overrides, but the guard should validate whichever model ID the server is about to use.

**Integration Points**
1. **Startup check** (FastAPI lifespan or `AgentService.__init__`):
   ```python
   guard.ensure_model_is_free(settings.openrouter_model_id)
   ```
2. **Exception behavior**:
   - Raise an `HTTPException` (503) containing:
     - Model ID
     - Pricing snapshot returned from API
     - Instruction to run `python scripts/select_openrouter_model.py`
3. **Router config sync**:
   - Provide helper to rewrite `router/config.json` defaults when `.env` model changes (optional but recommended).

### 3. Interactive TUI Selector (Beautiful CLI)

File: `scripts/select_openrouter_model.py` (invoked via `poetry run` or `python -m`).

**Tech choice**: [`textual`](https://github.com/Textualize/textual) – modern Python TUI aligning with “beautiful” requirement.
- Add dependency: `textual>=0.76` to `requirements.txt` (dev section).

**Workflow**
1. Fetch models via `FreeModelPolicyService`.
2. Filter to free models and present them in a Textual `DataTable` with columns:
   - Model ID
   - Provider
   - Context length
   - Modalities
3. Provide side panel with detailed description & pricing.
4. Keyboard actions:
   - `↑/↓`: navigate
   - `/`: fuzzy search
   - `Enter`: confirm selection
   - `Q`: quit without changes
5. On confirmation:
   - Update `.env` (and `.env.example` optionally) with `OPENROUTER_MODEL_ID=<selection>`.
   - Print summary + reminder to restart services.

**Implementation Helpers**
- `.env` manipulation: use `dotenv` from `python-dotenv` (already in requirements) or a small parser that preserves comments and ordering.
- Provide `--dry-run` option for CI or validation scripts.

### 4. Error → CLI Feedback Loop
When `FreeModelPolicyService.ensure_model_is_free` fails:
- Return JSON body:
  ```json
  {
    "detail": "Model deepseek/deepseek-v3.2 is not free.",
    "pricing": {"prompt": "0.00001", "completion": "0.00002"},
    "next_steps": "Run `python scripts/select_openrouter_model.py` and pick any free model."
  }
  ```
- Log a server-side warning with the same payload for observability.

### 5. Tests
1. **Unit tests** for `FreeModelPolicyService` (mock OpenRouter responses).
2. **Integration test** simulating:
   - Free model → no exception.
   - Paid model → raises with instructions.
3. **CLI smoke test**: run script with mocked API to ensure `.env` update occurs (use temp file).

### 6. Rollout Steps
1. Implement service + CLI + configs.
2. Update documentation:
   - README “Configure environment” section.
   - New doc snippet referencing CLI usage.
3. Add `make select-openrouter-model` shortcut.
4. Ship branch `feature/openrouter-free-model-enforcement`.

## Open Questions
1. Should router JSON auto-sync with `.env`, or remain manual to avoid overwriting custom configs?
2. How often should pricing metadata refresh? (Default 5 min; CLI can force fresh fetch.)
3. Do we need multi-select for fallback models? (Future enhancement.)

## Next Actions
1. Finalize dependency choice (`textual`) and add to requirements.
2. Implement `FreeModelPolicyService`.
3. Build TUI CLI and wiring for `.env` updates.
4. Wire enforcement check into server startup + error messaging.
