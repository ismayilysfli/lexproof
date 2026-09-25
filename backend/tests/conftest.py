from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def gdpr_pdf():
    path = Path(__file__).resolve().parents[2] / "data/test-laws/gdpr.pdf"
    assert path.is_file(), f"Missing regression fixture: {path}"
    return path.read_bytes()


@pytest.fixture(scope="session")
def index_cache_path(tmp_path_factory):
    # Tests must never overwrite the index used by the development server.
    path = tmp_path_factory.mktemp("retrieval") / "index.npz"
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("LEXPROOF_INDEX_PATH", str(path))
        yield path


@pytest.fixture(scope="session")
def client(index_cache_path):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def indexed_client(client, gdpr_pdf):
    # Build from the real PDF once, even if a previous run left a disk cache.
    response = client.post(
        "/retrieval/index",
        files={"file": ("gdpr.pdf", gdpr_pdf, "application/pdf")},
    )
    assert response.status_code == 200, response.text
    assert response.json()["article_count"] == 99
    assert response.json()["passage_count"] >= 99
    return client


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    marker = item.get_closest_marker("benchmark")
    if marker:
        report.user_properties.append(("benchmark_case", marker.args))


def pytest_terminal_summary(terminalreporter):
    cases = {}
    for reports in terminalreporter.stats.values():
        for report in reports:
            for name, value in getattr(report, "user_properties", []):
                if name != "benchmark_case":
                    continue
                key = tuple(value)
                if report.failed:
                    cases[key] = "FAIL"
                elif report.skipped and cases.get(key) != "FAIL":
                    cases[key] = "SKIP"
                elif report.when == "call" and key not in cases:
                    cases[key] = "PASS"
    for group in ("Retrieval", "Verification"):
        results = [(label, status) for (section, label), status in cases.items() if section == group]
        if results:
            terminalreporter.write_line(f"\n{group}:")
            for label, status in results:
                terminalreporter.write_line(f"{label}: {status}")
