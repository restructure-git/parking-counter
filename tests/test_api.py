from __future__ import annotations

import cv2
import pytest
from fastapi.testclient import TestClient

import app.database as database_module
from app.config import settings
from app.main import app
from app.services import detection_service, reference_manager, space_store
from scripts.create_sample_data import make_flat_image, make_invalid_image_bytes


def encode_jpeg(image) -> bytes:
    ok, buf = cv2.imencode(".jpg", image)
    assert ok
    return buf.tobytes()


def make_full_image(width: int = 200, height: int = 200, occupied_region: tuple | None = None):
    image = make_flat_image(width, height)
    if occupied_region:
        x, y, w, h = occupied_region
        cv2.rectangle(
            image,
            (x + w // 10, y + h // 10),
            (x + w - w // 10, y + h - h // 10),
            (30, 30, 200),
            thickness=-1,
        )
    return image


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(space_store, "PARKING_SPACES_PATH", tmp_path / "parking_spaces.json")
    monkeypatch.setattr(reference_manager, "REFERENCE_DIR", tmp_path / "reference")
    monkeypatch.setattr(database_module, "DB_PATH", tmp_path / "parking.db")
    monkeypatch.setattr(detection_service, "TMP_DIR", tmp_path / "tmp")
    monkeypatch.setattr(detection_service, "ANNOTATED_IMAGE_PATH", tmp_path / "tmp" / "latest.jpg")
    detection_service.state_manager.reset()
    with TestClient(app) as test_client:
        yield test_client
    detection_service.state_manager.reset()


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_status_shape_with_no_data(client: TestClient) -> None:
    response = client.get("/api/status")
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "updated_at": None,
        "total": 0,
        "empty": 0,
        "occupied": 0,
        "unknown": 0,
        "spaces": [],
    }


def test_detect_rejects_invalid_content_type(client: TestClient) -> None:
    response = client.post(
        "/api/detect",
        files={"file": ("note.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400


def test_detect_rejects_oversized_file(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "max_upload_size_mb", 0)
    image_bytes = encode_jpeg(make_flat_image())
    response = client.post(
        "/api/detect",
        files={"file": ("photo.jpg", image_bytes, "image/jpeg")},
    )
    assert response.status_code == 413


def test_detect_rejects_corrupt_image(client: TestClient) -> None:
    response = client.post(
        "/api/detect",
        files={"file": ("photo.jpg", make_invalid_image_bytes(), "image/jpeg")},
    )
    assert response.status_code == 400


def test_detect_with_no_spaces_returns_empty_result(client: TestClient) -> None:
    image_bytes = encode_jpeg(make_flat_image())
    response = client.post(
        "/api/detect",
        files={"file": ("photo.jpg", image_bytes, "image/jpeg")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["spaces"] == []


def test_full_pipeline_register_and_confirm_occupied(client: TestClient) -> None:
    space_region = (20, 20, 100, 100)

    create_response = client.post(
        "/admin/spaces/api",
        json={"name": "A-01", "x": 20, "y": 20, "width": 100, "height": 100},
    )
    assert create_response.status_code == 200
    space_id = create_response.json()["id"]

    reference_bytes = encode_jpeg(make_full_image())
    ref_response = client.post(
        "/api/reference",
        files={"file": ("reference.jpg", reference_bytes, "image/jpeg")},
    )
    assert ref_response.status_code == 200
    assert space_id in ref_response.json()["registered"]

    occupied_bytes = encode_jpeg(make_full_image(occupied_region=space_region))

    for _ in range(3):
        detect_response = client.post(
            "/api/detect",
            files={"file": ("current.jpg", occupied_bytes, "image/jpeg")},
        )
        assert detect_response.status_code == 200

    final_body = detect_response.json()
    space_status = next(s for s in final_body["spaces"] if s["id"] == space_id)
    assert space_status["status"] == "occupied"

    status_response = client.get("/api/status")
    assert status_response.status_code == 200
    assert status_response.json()["occupied"] == 1


def test_admin_update_and_delete_space(client: TestClient) -> None:
    create_response = client.post(
        "/admin/spaces/api",
        json={"name": "B-01", "x": 0, "y": 0, "width": 10, "height": 10},
    )
    space_id = create_response.json()["id"]

    update_response = client.put(
        f"/admin/spaces/api/{space_id}",
        json={"name": "B-02", "x": 5, "y": 5, "width": 20, "height": 20},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "B-02"

    delete_response = client.delete(f"/admin/spaces/api/{space_id}")
    assert delete_response.status_code == 200

    missing_update = client.put(
        f"/admin/spaces/api/{space_id}",
        json={"name": "B-03", "x": 0, "y": 0, "width": 10, "height": 10},
    )
    assert missing_update.status_code == 404
