# ReefCommand backend

Python 3.12+, managed with [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run uvicorn reefcommand.api.app:app --reload
uv run pytest
uv run ruff check .
```

## Package map

Each stage of the pipeline is one package.
The boundary between deterministic and autonomous components is the important structural line in this codebase, so it is also the package line.

| Package | Autonomous? | Responsibility |
| --- | --- | --- |
| `domain` | no | Pydantic models shared by every stage. The contract between packages. |
| `ingestion` | no | External adapters plus cache. Every value carries its provenance. |
| `evidence` | thermal and fusion are deterministic; disease, runoff, physical use an LLM | Four independent support scores, then one reconciled summary. |
| `policy` | no | Source-grounded intervention knowledge base. Decides what actions are eligible. |
| `coordinator` | yes, and only this | Act now, or get more data. Schema-constrained output only. |
| `optimizer` | no | OR-Tools constrained allocation of boats, teams, gear, time, budget. |
| `orchestration` | no | Wires the stages, handles events, owns re-planning. |
| `api` | no | FastAPI surface for the dashboard. |
| `llm` | no | Model client, structured-output plumbing, retries. |

## Rules that this package layout enforces

The LLM does not decide what treatments exist.
`policy` is the only place candidate actions are defined, and every action carries requirements, contraindications, resource cost, and provenance.

The LLM does not assign boats or teams.
`optimizer` is the only place allocation happens.

The Coordinator's output never reaches `optimizer` without passing `coordinator/validation.py`.
That is a hard import-direction rule, not a convention.

## Testing with DeepSeek

The LLM client supports `anthropic` and `deepseek` providers through the same structured Pydantic contract.

From `backend/`, copy the root example environment file and set these values in `.env`:

```powershell
Copy-Item ..\.env.example .env
```

```dotenv
REEFCOMMAND_LLM_PROVIDER=deepseek
REEFCOMMAND_LLM_MODEL=deepseek-v4-flash
REEFCOMMAND_DEEPSEEK_API_KEY=your-key-here
REEFCOMMAND_DEEPSEEK_BASE_URL=https://api.deepseek.com/beta
REEFCOMMAND_OFFLINE_DEMO=false
```

First make one provider-only request:

```powershell
uv run python ../scripts/test_deepseek.py
```

Then run the existing API or pipeline after the smoke test succeeds:

```bash
uv run uvicorn reefcommand.api.app:app --reload
```

The DeepSeek adapter uses the official Beta endpoint required for strict function calls and validates arguments against the same Pydantic model used by Anthropic.
It explicitly selects non-thinking mode because DeepSeek V4 thinking mode does not accept forced `tool_choice`.
The `deepseek-v4-flash` example is an official DeepSeek API model identifier, not a local alias.
Transient transport errors, HTTP 429 responses, and server errors retry with bounded backoff.
Do not commit `.env` or paste the API key into chat, issues, logs, or pull requests.

## Inspecting agent execution

Every completed plan retains a structured execution trace in process.
The trace includes tool inputs and provenance, investigator support and confidence, concise rationales, fusion and policy outputs, the complete Coordinator decision, validation checks, timing, provider, model, retry count, and provider-reported token usage when available.
It never includes API keys, authorization headers, raw prompts, or private token-by-token model reasoning.

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/plan/PLAN_ID/trace" |
    ConvertTo-Json -Depth 30

Invoke-RestMethod "http://127.0.0.1:8000/plan/PLAN_ID/trace/cheeca_rocks" |
    ConvertTo-Json -Depth 30
```

Trace retention is currently in memory and follows the same prototype lifecycle as the current plan store.
