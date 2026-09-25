# LexProof

LexProof verifies AI-generated legal claims against authoritative legal sources.

## Architecture

- Frontend: Next.js + TypeScript + Tailwind
- Backend: FastAPI + Python
- Legal document parsing: PyMuPDF
- Legal article chunking with page citations
- Retrieval: local `intfloat/multilingual-e5-small` embeddings
- Verification: local `MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli`
- No hosted LLM or paid API is required.

## Backend setup (PowerShell)

Run from the project root. The current dependency pins were tested with Python 3.14.
Create the venv only if it does not already exist:

```powershell
Set-Location C:\Users\user\HackathonProjects\lexproof
py -3.14 -m venv backend/.venv
.\backend\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements-dev.txt
```

`requirements-dev.txt` includes the existing backend dependencies plus pytest.
For runtime dependencies only, use `python -m pip install -r backend/requirements.txt`.
If PowerShell blocks activation, allow scripts for the current shell with
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate again.
Alternatively, use `.\backend\.venv\Scripts\python.exe` directly in place of `python`.

Start the backend from the project root:

```powershell
python -m uvicorn app.main:app --app-dir backend --reload
```

API docs: <http://127.0.0.1:8000/docs>. Health: <http://127.0.0.1:8000/health>.
The existing endpoints remain `POST /documents/upload`, `POST /retrieval/index`,
`POST /retrieval/search`, and `POST /verify`.

## Index GDPR

With the backend running, open another PowerShell window at the project root:

```powershell
curl.exe --fail-with-body -X POST "http://127.0.0.1:8000/retrieval/index" -F "file=@data/test-laws/gdpr.pdf;type=application/pdf"
```

Indexing saves the current document's passages, metadata, and embeddings to
`data/indexes/retrieval.npz`. FastAPI restores that index on startup without
re-embedding the PDF or loading models until they are needed. Calling the same
endpoint again rebuilds and replaces the index; indexing another document replaces
GDPR, as with the original single-document in-memory index.

Missing, incompatible, or corrupt caches leave the API available but unindexed;
run the indexing command again. Cache read/write problems are logged. If saving
fails, the newly built in-memory index still works for the current server process.
To use a different cache, set `$env:LEXPROOF_INDEX_PATH` to an absolute file path
before starting the server. The default path is independent of the working directory.
Changes to a source PDF do not automatically rebuild its cache.

## Regression tests and benchmark

No running server or Swagger interaction is needed. Tests call the real FastAPI
app through its test client and reuse `data/test-laws/gdpr.pdf` (88 pages, 99 articles).
From the project root with the venv activated:

```powershell
# Full suite: parser/chunker, API checks, retrieval, verification, index persistence.
python -m pytest -q

# Seven exact retrieval/verdict benchmark cases, with a concise PASS/FAIL summary.
.\scripts\benchmark.ps1

# Equivalent Python command (also works outside PowerShell).
python -m pytest -q -m benchmark
```

The benchmark script uses the project's venv directly, so activation is optional.
If scripts are disabled, run it with a process-only policy override:
`powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\benchmark.ps1 -Offline`
(omit `-Offline` if the models have not been downloaded yet).
It returns a nonzero exit code on test/setup failure. Both commands print the
retrieval and verification summary. Supported and contradicted cases must also
cite Article 33 as primary evidence; retrieval must find Articles 15, 33, 21, and
32 in the respective top-three results. Assertion failures include actual results.

Each test session builds a fresh GDPR index once and reuses both loaded models.
Tests use an isolated temporary index and never replace the development server's
cache. Cache tests also exercise rebuilding with a small synthetic PDF.
The full suite and a separate benchmark invocation are separate processes, so
each loads its own model instances.

The first model use may download the free model weights from Hugging Face.
Subsequent runs reuse Hugging Face's disk cache (normally
`$env:USERPROFILE\.cache\huggingface\hub`); no inference API is called.
Once both models are cached, avoid network checks entirely with:

```powershell
.\scripts\benchmark.ps1 -Offline

# Offline full suite (this also affects a server started from the same shell).
$env:HF_HUB_OFFLINE = "1"
python -m pytest -q
Remove-Item Env:HF_HUB_OFFLINE
```

Offline runs fail visibly if model files are missing; benchmark cases are not
silently skipped. Generated indexes and caches are ignored by Git. Keep the GDPR
PDF available at the fixture path above.

## Frontend development

```powershell
Set-Location frontend
npm run dev
```
