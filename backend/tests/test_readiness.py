from types import SimpleNamespace

import pytest
from fastapi import Response, status

import app.main as main_module
from app.config import _read_local_llm_base_url


def test_local_model_url_rejects_external_hosts(monkeypatch):
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "https://models.example.com/api/v1")

    with pytest.raises(ValueError, match="loopback"):
        _read_local_llm_base_url()


def test_readiness_returns_503_when_a_dependency_is_unavailable(monkeypatch):
    monkeypatch.setattr(
        main_module,
        "check_database_readiness",
        lambda: SimpleNamespace(ready=False, detail="Database stopped."),
    )
    monkeypatch.setattr(
        main_module,
        "get_local_llm_client",
        lambda: SimpleNamespace(
            check_readiness=lambda: SimpleNamespace(ready=True, detail="Model ready.")
        ),
    )
    response = Response()

    result = main_module.readiness_check(response)

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert result.status == "not_ready"
    assert result.database.ready is False
    assert result.local_model.ready is True


def test_readiness_reports_ready_when_both_dependencies_are_available(monkeypatch):
    monkeypatch.setattr(
        main_module,
        "check_database_readiness",
        lambda: SimpleNamespace(ready=True, detail="Database ready."),
    )
    monkeypatch.setattr(
        main_module,
        "get_local_llm_client",
        lambda: SimpleNamespace(
            check_readiness=lambda: SimpleNamespace(ready=True, detail="Model ready.")
        ),
    )
    response = Response()

    result = main_module.readiness_check(response)

    assert response.status_code == status.HTTP_200_OK
    assert result.status == "ready"
