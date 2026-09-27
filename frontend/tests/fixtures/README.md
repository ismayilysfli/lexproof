# Verification fixtures

These JSON responses were captured from the project's unmodified FastAPI `POST /verify`
endpoint on 2026-09-25 using `data/test-laws/gdpr.pdf`, the exact three demo claims,
and `retrieval_k: 8`. They are used only by tests, never by the running application.

The full upstream fields are retained to test that the frontend proxy removes internal
model information. The insufficient-evidence response selects a primary passage outside
the five ranked candidates; its expanded report therefore contains six distinct passages.

The optional `@live` test verifies all three examples against an actual indexed backend,
without these fixtures or request interception.
