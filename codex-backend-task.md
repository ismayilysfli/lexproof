You are working on the LexProof hackathon project.

Project root:
C:\Users\user\HackathonProjects\lexproof

IMPORTANT:
- Do not redesign or replace the existing architecture.
- Preserve the currently working FastAPI endpoints.
- Do not use any paid APIs.
- Do not add OpenAI, Anthropic, Gemini, or other hosted LLM APIs.
- Local Hugging Face models are allowed.
- Do not break the current legal parser, semantic retriever, or verifier.
- Work incrementally and run tests after changes.
- Explain every meaningful change in the final summary.
- Do not commit or push unless explicitly instructed.

Current backend:
- FastAPI
- PyMuPDF legal PDF parser
- legal article chunking
- intfloat/multilingual-e5-small embeddings
- multilingual semantic retrieval
- MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli verifier
- POST /documents/upload
- POST /retrieval/index
- POST /retrieval/search
- POST /verify

The verifier supports:
- SUPPORTED
- CONTRADICTED
- INSUFFICIENT_EVIDENCE

Known successful verification cases:

1.
Claim:
"A controller must notify the supervisory authority of certain personal data breaches within 72 hours where feasible."
Expected:
SUPPORTED
Expected primary article:
Article 33

2.
Claim:
"A controller must report a personal data breach within 24 hours."
Expected:
CONTRADICTED
Expected primary article:
Article 33

3.
Claim:
"Every company must give customers a free laptop after a personal data breach."
Expected:
INSUFFICIENT_EVIDENCE

Retrieval benchmark cases:

1.
"I have the right to get a copy of the personal data a company holds about me."
Expected relevant article in top 3:
Article 15

2.
"A company must report certain personal data breaches within 72 hours."
Expected relevant article in top 3:
Article 33

3.
"I can object to my personal data being used for direct marketing."
Expected relevant article in top 3:
Article 21

4.
"Companies must use appropriate security measures to protect personal data."
Expected relevant article in top 3:
Article 32

TASK:

1. Inspect the existing repository before changing anything.
2. Create an automated pytest regression suite for the backend.
3. Eliminate the need for manually copy-pasting these claims into Swagger.
4. Add tests for parser/chunker sanity, retrieval top-3 behavior, and all three verifier verdicts.
5. Reuse:
   C:\Users\user\HackathonProjects\lexproof\data\test-laws\gdpr.pdf
6. Avoid repeatedly loading/downloading models unnecessarily during one test run.
7. Add a PowerShell-friendly benchmark command/script.
8. Print a concise PASS/FAIL summary.
9. If safe, persist the retrieval index locally so server restarts do not require manual re-indexing.
10. Update .gitignore for generated caches if needed.
11. Update README with exact install/start/test commands.
12. Inspect available Codex skills and use only ones that materially help.

Do NOT:
- optimize embedding rankings beyond the benchmark
- build the frontend yet
- replace existing local models
- introduce unnecessary abstractions
- change working verdict logic unless tests demonstrate a problem

At the end:
- run the full test suite
- run the benchmark
- report which tests passed
- list files changed
- explain remaining problems
- do not commit
- do not push
