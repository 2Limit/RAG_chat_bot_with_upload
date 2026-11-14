# Local hardening verification

Base: `2Limit/RAG_chat_bot_with_upload` commit `bbb71827a8cd523884d2652e4ddd7c592e32572d`.
Changes are isolated locally. No deployment, push, PR, real documents or model API calls.

## Passed

- `python -m pytest -q`: **20 passed**. Includes original four chunking tests plus authentication, two-user same-filename/document isolation, same-session-ID conversation isolation, deletion clears only owner's history, path rejection, upload/request limits, invalid/empty text, partial ingestion cleanup and deletion failure retries, legacy schema refusal, vector owner/document filter contract, UI response headers, deletion-versus-in-flight-model transaction regression (409/no persisted messages), exclusive-file-create collision preserving pre-existing content even on later DELETE, monotonic document IDs and UI history-purge disclosure.
- `python -m tests.smoke_local`: actual loopback TCP server serves UI; unauthenticated list rejected; authenticated synthetic upload -> retrieval/chat -> deletion succeeded; server stopped and temporary synthetic storage removed.
- `python -m compileall -q app main.py scripts tests`: passed.
- Extracted inline frontend script `node --check`: passed.
- `git diff --check`: passed.

Test environment: Python 3.12, requirements-test.txt, Linux. Tests use actual FastAPI routes, SQLite and text ingestion; fake embeddings, LLM and vector storage. Real vector repository filter construction separately checked via fake collection. 36 deprecation warnings remain from UTC datetime defaults and Starlette/AnyIO, not test failures.

## Not verified / not a production certification

Actual Chroma operations, sentence-transformer model loading, Upstage responses, model quality, PDF adversarial fuzzing, real browser visual/interactivity, Windows execution, large/concurrent/multiworker workloads, production TLS and dependency vulnerability audit were not run. Existing dependency versions were retained. See SECURITY.md for onboarding, old-data migration, cleanup recovery, provider transmission and deployment constraints.
