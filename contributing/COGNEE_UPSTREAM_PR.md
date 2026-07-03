# Contribute to Cognee upstream (PR track — $100 × top 20)

This is a **copy-paste ready** integration example for the Cognee open-source repo.  
PR it to: https://github.com/topoteretes/cognee

---

## Steps

1. Fork https://github.com/topoteretes/cognee
2. Find or open an issue: *"Add Code Archaeologist integration example"* (or use an existing `good-first-issue`)
3. Comment: *"I'd like to work on this"* and tag maintainers
4. Wait for assignment
5. Add the file below at `examples/integrations/code-archaeologist/README.md`
6. Open PR (max 5 PRs per person for hackathon)

---

## File to add: `examples/integrations/code-archaeologist/README.md`

```markdown
# Code Archaeologist + Open-Source Cognee

[Code Archaeologist](https://github.com/AviArora02-commits/code-archaeologist) is a reference app for legacy code understanding using the full Cognee memory lifecycle.

## Problem

Enterprise teams maintain decades-old Java/C++ codebases. Stateless LLMs cannot explain *why* code exists. Cognee provides persistent graph-vector memory.

## Cognee lifecycle used

| API | Usage |
|-----|--------|
| `remember()` | Ingest code entities + git blame + GitHub PR/issue context |
| `recall()` | `GRAPH_COMPLETION` why-queries with evidence chains |
| `improve()` | Expert knowledge + user feedback |
| `forget()` | Per-repo dataset deletion |

## Quick start (self-hosted open-source Cognee)

\`\`\`bash
git clone https://github.com/AviArora02-commits/code-archaeologist
cd code-archaeologist
cp .env.open-source.example .env
# Set GEMINI_API_KEY or LLM_API_KEY
docker compose up --build
# Open http://localhost:3000
\`\`\`

## SDK mode

\`\`\`python
import cognee

await cognee.remember(document, dataset_name="owner_repo")
results = await cognee.recall(query_text="Why does X exist?", datasets=["owner_repo"])
await cognee.improve()
await cognee.forget(dataset="owner_repo")
\`\`\`

## Links

- Live demo (Cognee Cloud): https://frontend-six-alpha-67.vercel.app
- Source: https://github.com/AviArora02-commits/code-archaeologist
```

---

## PR title

`docs: add Code Archaeologist integration example for legacy code memory`

## PR description

```
Adds an integration example showing how to use open-source Cognee for legacy code understanding with the full remember/recall/improve/forget lifecycle.

Includes Docker quick-start for self-hosted evaluation.
```

---

## Other PR ideas (if maintainers prefer code)

1. **Document `GRAPH_COMPLETION` + dataset isolation** pattern for multi-repo apps
2. **Fix or document** `run_in_background` behavior differences local vs cloud
3. **Add Java/C++** to supported loader docs if missing

Always: comment on issue → get assigned → one focused PR.
