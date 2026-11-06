# ShashGuru

A chess analyzer that takes a FEN or PGN and asks an LLM to analyse it.



##### Platforms

It should work with Unix and Windows.

Please open an issue if it doesn't. 

### Usage
Build and run from docker-compose-vllm.yml
I provide a shell script on linux for starting it: "refreshDockers.sh"



### Development

Backend (FastAPI, Python 3.12+):

```
cd backend
pip install -r requirements-dev.txt
pytest                                   # unit + API tests (engine tests need the binaries in backend/executables)
uvicorn app.main:app --port 5000         # interactive API docs at http://localhost:5000/docs
```

Configuration is read from environment variables: `AI_BASE_URL`, `LLM_MODEL`, `REDIS_HOST`, `REDIS_PORT`,
`ENGINE_POOL_SIZE`, `ENGINE_THREADS`, `ENGINE_HASH_MB`, `ANALYSIS_TIMEOUT`.

Frontend (Vue 3 + TypeScript + Pinia):

```
cd frontend
npm install
npm run dev          # proxies /backend/* to http://localhost:5000
npm run type-check && npm run lint && npm test
```

### REST API

In production nginx exposes the backend under `/backend/*`. Errors are `{"detail": ...}` with the usual status codes
(422 validation, 503 engine/LLM unavailable).

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/evaluations` | `{fen, depth, lines, engine}` -> engine lines (scores relative to the side to move) |
| POST | `/api/v1/games/analysis` | `{pgn}` or `{moves}` (UCI) -> evaluation of every position |
| GET | `/api/v1/styles` | available LLM analysis styles |
| POST | `/api/v1/analyses` | `{fen, depth, style}` -> LLM analysis, streamed as NDJSON |
| POST | `/api/v1/chat` | `{messages, style}` -> answer to a follow-up question, streamed as NDJSON |
| GET / DELETE | `/api/v1/admin/cache` | Redis cache statistics / clear |
| GET | `/api/v1/admin/engines` | engine pool statistics |
| GET | `/health`, `/metrics` | health check, Prometheus metrics |

Streams (`application/x-ndjson`) contain one JSON event per line:
`{"type":"context","prompt":...}` (analyses only), `{"type":"token","text":...}`*, then `{"type":"done"}` or `{"type":"error","message":...}`.

### Dependencies

ShashGuru integrates with external chess engines and tools:

[Alexander](https://github.com/amchess/Alexander) – licensed under the GNU General Public License v3 (GPLv3).

[ShashChess](https://github.com/amchess/ShashChess) – licensed under the GNU General Public License v3 (GPLv3).

These projects are bundled or invoked by ShashGuru under the terms of the GPLv3. Their source code is available at the links above.
