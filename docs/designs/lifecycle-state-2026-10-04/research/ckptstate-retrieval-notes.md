# ckptstate-retrieval-notes — locators, dates, versions (supporting evidence for checkpoint-state.md)

Access date for everything below: 2026-10-04 (machine clock of the research host).
Retrieval was read-only HTTPS (curl / web_fetch). No login, no install, no repo writes.

## A. LangGraph documentation (docs.langchain.com, markdown source)

The public docs site is JS-rendered; the same pages are served as raw MDX-derived markdown by
appending `.md`. Fetched with `curl -sSL`:

| Page | URL fetched | HTTP | bytes |
|---|---|---|---|
| Persistence | https://docs.langchain.com/oss/python/langgraph/persistence.md | 200 | 5265 |
| Checkpointers | https://docs.langchain.com/oss/python/langgraph/checkpointers.md | 200 | 46197 |
| Fault tolerance | https://docs.langchain.com/oss/python/langgraph/fault-tolerance.md | 200 | 27573 |
| Interrupts | https://docs.langchain.com/oss/python/langgraph/interrupts.md | 200 | 47311 |
| Time travel | https://docs.langchain.com/oss/python/langgraph/use-time-travel.md | 200 | 13078 |
| Graph API | https://docs.langchain.com/oss/python/langgraph/graph-api.md | 200 | (graph-api) |
| Backward compatibility | https://docs.langchain.com/oss/python/langgraph/backward-compatibility.md | 200 | |
| Add memory | https://docs.langchain.com/oss/python/langgraph/add-memory.md | 200 | 74398 |
| Subgraphs | https://docs.langchain.com/oss/python/langgraph/use-subgraphs.md | 200 | 37103 |

The older `langchain-ai.github.io/langgraph/...` paths returned HTTP 200 but only a
"Redirecting..." stub (JS redirect), so they were not usable as text evidence.

Doc pages embed an "Edit this page on GitHub" link to `github.com/langchain-ai/docs/edit/main/src/oss/langgraph/<page>.mdx`;
that is the canonical source-of-truth path for the doc text, not a version pin. The docs carry no
dated release/version marker at fetch time; the *code* pins below are the material versions.

## B. LangGraph source (code pins)

Repo: https://github.com/langchain-ai/langgraph
Sparse shallow clone (`--depth 1 --filter=blob:none`), checked out at:

- Commit `9a0394d88b2211f299dcd69df92db3480c69ee61`, committed 2026-10-03T08:55:59-04:00,
  subject: "fix(langgraph): don't replay an abandoned branch into a DeltaChannel fork (#8548)".

Package versions at that commit (from each `libs/*/pyproject.toml`):
- `libs/checkpoint` → `langgraph-checkpoint` **4.2.0**
- `libs/checkpoint-sqlite` → `langgraph-checkpoint-sqlite` **3.1.1**
- `libs/checkpoint-postgres` → `langgraph-checkpoint-postgres` **3.1.2**

PyPI cross-check (https://pypi.org/pypi/langgraph-checkpoint/json, 2026-10-04): latest release
`langgraph-checkpoint` **4.2.0**, project URL declares source at
`https://github.com/langchain-ai/langgraph/tree/main/libs/checkpoint`. Matches the clone.

GitHub releases API (`/repos/langchain-ai/langgraph/releases/latest`) returned a `langgraph-cli`
pre-release tag (`cli==0.4.32.dev0`, 2026-09-23) because the repo publishes per-package tags
(`v0.0.x`, `sdk==0.4.x`); the code commit above is therefore the reliable pin, not a release tag.

Files read (paths inside the repo at that commit):
- `libs/checkpoint/langgraph/checkpoint/base/__init__.py` (BaseCheckpointSaver, Checkpoint TypedDict)
- `libs/checkpoint/langgraph/checkpoint/memory/__init__.py`
- `libs/checkpoint-sqlite/langgraph/checkpoint/sqlite/__init__.py`
- `libs/checkpoint-postgres/langgraph/checkpoint/postgres/base.py` (MIGRATIONS list, UPSERT SQL)
- `libs/langgraph/langgraph/pregel/_checkpoint.py` (create_checkpoint, versions_seen, bumps)
- `libs/checkpoint-sqlite/tests/test_delta_channel_migration.py`
- `libs/checkpoint-sqlite/tests/test_ttl.py`

## C. Primary papers (arXiv)

Source: arXiv API (`https://export.arxiv.org/api/query`) then HTML (`https://arxiv.org/html/<id>`);
HTML converted to text locally. PDFs were also fetched but no `pdftotext` was available on the host,
so HTML was the readable form.

1. **Mnemosyne: Agentic Transaction Processing for Validating and Repairing AI-generated Workflows**
   - arXiv:2607.00269v3, first submitted 2026-06-30, last updated 2026-08-31 (per API).
   - HTML: https://arxiv.org/html/2607.00269v3 (HTTP 200, 847457 bytes)
   - PDF: https://arxiv.org/pdf/2607.00269v3 (HTTP 200, 576180 bytes)
   - Abstract: https://export.arxiv.org/api/query?id_list=2607.00269v3
2. **ACRFence: Preventing Semantic Rollback Attacks in Agent Checkpoint-Restore**
   - arXiv:2603.20625v1, 2026-03-21.
   - HTML: https://arxiv.org/html/2603.20625v1 (HTTP 200, 88834 bytes)
   - PDF: https://arxiv.org/pdf/2603.20625v1 (HTTP 200, 463072 bytes)
3. **Stored Is Not Supported: Typed Provenance and Assertion Guardrails for Persistent AI Agents**
   - arXiv:2609.02127v1, 2026-09-02.
   - HTML: https://arxiv.org/html/2609.02127v1 (HTTP 200, 539287 bytes)
   - Used only as a cross-check for "authorized state projections / staleness flags"; not a load-bearing
     source for this report.

Note on provenance: search-engine access was unavailable in this run (the web-search tool returned
`no API key`). All sources above were reached by direct URL, not by a search result. The candidate
papers were found via the arXiv API query endpoint, which is itself a public primary index.
