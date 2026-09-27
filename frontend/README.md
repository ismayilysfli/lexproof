# LexProof frontend

A single evidence-first verification workflow built with Next.js 16, React 19,
TypeScript, and the existing Tailwind 4 setup. No paid API, hosted LLM, UI framework,
or runtime dependency was added. Geist is served locally from the font asset already
included in the pinned Next.js package; legal excerpts use Georgia.

## Run locally

From this directory:

```powershell
npm ci
# Optional: the default backend is already http://127.0.0.1:8000.
Copy-Item .env.example .env.local
npm run dev
```

Open <http://localhost:3000>. The backend must be running and have GDPR indexed.
From the repository root, in a separate terminal:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend
```

If the backend has no saved index, run this once from the repository root:

```powershell
curl.exe --fail-with-body -X POST http://127.0.0.1:8000/retrieval/index -F "file=@data/test-laws/gdpr.pdf;type=application/pdf"
```

The three example buttons populate the claim input; choose **Verify claim** to run
a real verification. Ctrl+Enter / Cmd+Enter also submits. The first backend request
can take longer while its local models load; subsequent requests reuse them.

## Backend integration

The browser sends `{ "claim": "..." }` to the same-origin `POST /api/verify` route.
That thin Next.js proxy calls the existing backend `POST /verify` with
`{ "claim": "...", "retrieval_k": 8 }`. Set the server-side `LEXPROOF_API_URL`
environment variable to change the backend address and restart Next.js.
The default is `http://127.0.0.1:8000`; for deployment it must be reachable from
the Next.js server. No backend endpoint, CORS policy, or verification logic changes
are required.

The proxy validates responses, checks the returned claim, removes internal ML fields,
and turns backend failures into safe error codes. Requests are not cached. A request
times out after two minutes; the UI preserves the claim and provides a retry.

The backend returns one final response, with no streaming progress events. The three
animated stages describe the work while the request is pending; they do not claim
individual stages have completed. Results render as soon as the response arrives.

Explanations are deterministic. The numeric comparison is deliberately limited to
the known GDPR Article 33 / 24-hour conflict, with an explicit backend conflict signal
and matching primary-law wording. Other claims fall back to textual evidence.
Official-source attribution is mapped to `gdpr.pdf`; unfamiliar documents do not
receive an invented official-source link. Pages come directly from the backend's PDF
citations. Long passages expand with native keyboard-accessible details controls.

## Checks

```powershell
npm run lint
npm run typecheck
npm run build
npx playwright install chromium
npm run test:e2e
```

Playwright starts the production server automatically (build first), or reuses an
existing server at `127.0.0.1:3000`. Tests cover the three verdicts, evidence expansion,
safe comparisons, confidence help, loading, retry, malformed data, network failure,
keyboard navigation, reduced motion, 320/390/768px layouts, and axe accessibility.
API contract tests run against isolated local HTTP servers. Test fixtures were captured
from this project's backend and are never used as application fallbacks.

To also run the live test against your running, GDPR-indexed backend:

```powershell
$env:LEXPROOF_LIVE_TESTS = "1"
npm run test:e2e
# Or only the live check:
npm run test:e2e:live
Remove-Item Env:LEXPROOF_LIVE_TESTS
```

Screenshots and failure traces are written to the ignored `test-results/` directory.
For a preinstalled Chromium executable, optionally set `PLAYWRIGHT_CHROMIUM_EXECUTABLE`.

## Structure

- `src/app/page.tsx`: header, editorial hero, how-it-works section, footer.
- `src/components/claim-verifier.tsx`: accessible claim entry, examples, request lifecycle, loading and errors.
- `src/components/verification-report.tsx`: verdict, confidence, comparison, source evidence and expansion.
- `src/components/icons.tsx`: small inline SVG interface marks.
- `src/lib/verification.ts`: explicit types, response validation, source metadata and conservative extraction.
- `src/app/api/verify/route.ts`: configurable same-origin backend proxy.
- `src/app/globals.css`: responsive visual system, focus treatments and reduced-motion behavior.
- `tests/`: browser, accessibility, API contract and optional live-backend checks.
