from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.database as database_module
from app.main import app
from app.services import detection_service, reference_manager, space_store


@pytest.fixture()
def configured_client(tmp_path, monkeypatch):
    monkeypatch.setattr(space_store, "PARKING_SPACES_PATH", tmp_path / "parking_spaces.json")
    monkeypatch.setattr(reference_manager, "REFERENCE_DIR", tmp_path / "reference")
    monkeypatch.setattr(database_module, "DB_PATH", tmp_path / "parking.db")
    monkeypatch.setattr(detection_service, "TMP_DIR", tmp_path / "tmp")
    monkeypatch.setattr(detection_service, "ANNOTATED_IMAGE_PATH", tmp_path / "tmp" / "latest.jpg")
    monkeypatch.setenv("PARKING_ADMIN_USERNAME", "testadmin")
    monkeypatch.setenv("PARKING_ADMIN_PASSWORD", "testpass")
    detection_service.state_manager.reset()
    with TestClient(app) as test_client:
        yield test_client
    detection_service.state_manager.reset()


def test_health_does_not_require_auth(configured_client: TestClient) -> None:
    response = configured_client.get("/health")
    assert response.status_code == 200


def test_dashboard_requires_auth_when_configured(configured_client: TestClient) -> None:
    response = configured_client.get("/")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Basic"


def test_dashboard_rejects_wrong_credentials(configured_client: TestClient) -> None:
    response = configured_client.get("/", auth=("testadmin", "wrong-password"))
    assert response.status_code == 401


def test_dashboard_accepts_correct_credentials(configured_client: TestClient) -> None:
    response = configured_client.get("/", auth=("testadmin", "testpass"))
    assert response.status_code == 200


def test_api_status_requires_auth_when_configured(configured_client: TestClient) -> None:
    response = configured_client.get("/api/status")
    assert response.status_code == 401


def test_no_auth_required_when_unconfigured(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("PARKING_ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("PARKING_ADMIN_PASSWORD", raising=False)
    monkeypatch.setattr(space_store, "PARKING_SPACES_PATH", tmp_path / "parking_spaces.json")
    monkeypatch.setattr(reference_manager, "REFERENCE_DIR", tmp_path / "reference")
    monkeypatch.setattr(database_module, "DB_PATH", tmp_path / "parking.db")
    monkeypatch.setattr(detection_service, "TMP_DIR", tmp_path / "tmp")
    monkeypatch.setattr(detection_service, "ANNOTATED_IMAGE_PATH", tmp_path / "tmp" / "latest.jpg")
    detection_service.state_manager.reset()
    with TestClient(app) as test_client:
        response = test_client.get("/")
    assert response.status_code == 200
