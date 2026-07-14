from fastapi.testclient import TestClient

from main import app


def test_image_rejects_text_file():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/image/analyze",
            data={
                "detector_type": "ai",
            },
            files={
                "file": (
                    "archivo.txt",
                    b"no es una imagen",
                    "text/plain",
                ),
            },
        )

    assert response.status_code == 400
