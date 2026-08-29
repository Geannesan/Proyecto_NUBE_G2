from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.report_service import create_pdf_report


def test_report_is_generated_in_memory():
    record = SimpleNamespace(
        id="memory-test",
        created_at=datetime.now(timezone.utc),
        original_filename="sample.png",
        media_type="image",
        detector_type="comprehensive",
        prediction="REAL_HUMAN",
        confidence=91.2,
        model_name="test-model",
        processing_time_ms=10,
        probabilities={"AI": 8.8, "DEEPFAKE": 4.2},
        evidence=["Reporte generado sin archivo persistente."],
        analysis_metadata={"quality": {"score": 100}},
    )
    report = create_pdf_report(record)  # type: ignore[arg-type]
    assert isinstance(report, bytes)
    assert report.startswith(b"%PDF")
    assert len(report) > 1000
