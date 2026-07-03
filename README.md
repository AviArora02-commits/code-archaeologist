# Code Archaeologist

[![Live Demo](https://img.shields.io/badge/demo-live-success)](https://frontend-six-alpha-67.vercel.app)
[![Cognee Cloud](https://img.shields.io/badge/memory-Cognee%20Cloud-blue)](https://github.com/topoteretes/cognee)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

**Personal project** — give legacy codebases permanent memory on Cognee Cloud.

Trace **why** code was written — not with semantic search guesses, but with sourced evidence chains:
**function → commit → PR → issue**.

Built after struggling to onboard onto legacy Java and C++ systems at Ericsson Global, where generic LLMs could not explain *why* decades-old code worked the way it did.

## Live demo

| Service | URL |
|---------|-----|
| **App** | https://frontend-six-alpha-67.vercel.app |
| **API** | https://backend-production-c1682.up.railway.app |
| **Health** | https://backend-production-c1682.up.railway.app/api/health |

## Features

- Connect any public GitHub repo and ingest code + git history + PR/issue context
- Ask **why** questions — get answers with evidence chains, not hallucinations
- **Expert knowledge** panel — capture tribal memory from senior engineers into Cognee
- **Knowledge graph** visualization — files, entities, commits, expert notes
- **Multi-repo fleet** — isolated Cognee datasets per repository
- **160+ languages** — Java, C++, Python, COBOL, RPG, Markdown runbooks, and more

## Quick start

### 1. Clone & configure

```bash
git clone https://github.com/AviArora02-commits/code-archaeologist
cd code-archaeologist
cp .env.example .env
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

### Environment variables

See [`.env.example`](./.env.example) for full list. Key variables:

| Variable | Purpose |
|----------|---------|
| `COGNEE_MODE` | `local` or `cloud` |
| `COGNEE_CLOUD_URL` / `COGNEE_API_KEY` | Cognee Cloud credentials |
| `GEMINI_API_KEY` | LLM for enrichment |
| `GITHUB_TOKEN` | Higher GitHub API rate limits |

## Architecture

```
┌─────────────┐     REST      ┌──────────────────┐
│  Next.js    │ ────────────► │  FastAPI         │
│  (Vercel)   │               │  (Railway)       │
└─────────────┘               └────────┬─────────┘
                                       │
                              ┌────────▼─────────┐
                              │  Cognee SDK      │
                              │  local | cloud   │
                              └────────┬─────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
               GitPython          GitHub API         SQLite
            (clone, blame)    (PRs, issues)      (job status)
```

## Cognee lifecycle

| Operation | How it's used |
|-----------|----------------|
| **`remember()`** | Ingest code entities + expert tribal knowledge per repo dataset |
| **`recall()`** | `GRAPH_COMPLETION` why-queries with evidence extraction |
| **`improve()`** | After expert knowledge submit + positive feedback |
| **`forget()`** | Per-repo delete — removes dataset without affecting other repos |

## Tests

```bash
cd backend && pytest tests/unit -v
cd frontend && npm test
```

## Known limitations

- Entity extraction uses regex heuristics (AST parsers planned)
- Shallow clones may miss ancient history
- GitHub rate limits without a personal access token
- Cognee ingest cost scales with chunk count — review dry-run estimate before confirming

## Roadmap

- VS Code extension with hover-to-trace
- Deeper Java/C++ AST parsing
- Private repo authentication
- Enterprise GitLab support

## Author

**Avi Arora** — built to solve real onboarding pain on legacy telecom systems.

## License

MIT — see [LICENSE](./LICENSE).

## AI disclosure

Built with AI assistance (Cursor Agent). Architecture and product direction by the author.
