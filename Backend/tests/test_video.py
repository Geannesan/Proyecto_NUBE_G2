from fastapi.testclient import TestClient

from main import app


def test_video_rejects_text_file():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/video/analyze",
            data={
                "detector_type": "deepfake",
            },
            files={
                "file": (
                    "archivo.txt",
                    b"no es video",
                    "text/plain",
                ),
            },
        )

    assert response.status_code == 400
