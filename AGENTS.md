# AGENTS.md

## Repository Map

The root repository atlas lives at [`codemap.md`](codemap.md). It provides:

- **Project responsibility** — what this codebase does at a high level
- **System entry points** — Docker compose, Nginx, FastAPI bootstrap, CI/CD
- **Architecture overview** — three-layer design diagram (frontend → Nginx → backend → core)
- **Runtime/data flow** — job pipeline lifecycle, authentication flow, tailoring pipeline
- **Directory map table** — every directory with its responsibility summary and link to its `codemap.md`
- **Root config/deployment file map** — purpose of every root config file
- **Key integration points** — cross-boundary contracts (frontend↔backend, SSE, AI providers, auth)
- **Operational notes** — Python version, DB, concurrency, timeouts, AI keys, deployment

Each directory in the project contains its own `codemap.md` with local responsibility, entry points, module inventory, data flow, and integration contracts. Start from the root map and follow links to drill into any area of the codebase.
