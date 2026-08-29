import os
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.database.models import Analysis


REPORTS_DIR = Path(
    os.getenv("REPORTS_DIR", "reports")
).resolve()


def _write_wrapped_text(
    pdf: canvas.Canvas,
    text: str,
    *,
    x: float,
    y: float,
    max_chars: int = 88,
    line_height: float = 15,
) -> float:
    words = text.split()
    lines: list[str] = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip()

        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    for line in lines:
        pdf.drawString(x, y, line)
        y -= line_height

    return y


def create_pdf_report(
    record: Analysis,
) -> Path:
    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        REPORTS_DIR
        / f"analysis_{record.id}.pdf"
    )

    pdf = canvas.Canvas(
        str(output_path),
        pagesize=A4,
    )

    _, height = A4
    x = 55
    y = height - 60

    pdf.setTitle(
        f"DeepFakeShield - {record.id}"
    )

    pdf.setFont(
        "Helvetica-Bold",
        18,
    )
    pdf.drawString(
        x,
        y,
        "DeepFakeShield - Reporte de análisis",
    )

    y -= 32
    pdf.setFont("Helvetica", 10)

    fields = [
        ("ID", record.id),
        ("Fecha", record.created_at.isoformat()),
        ("Archivo", record.original_filename),
        ("Tipo", record.media_type),
        ("Detector", record.detector_type),
        ("Resultado", record.prediction),
        ("Confianza", f"{record.confidence:.2f}%"),
        ("Modelo", record.model_name),
        ("Tiempo", f"{record.processing_time_ms} ms"),
    ]

    for label, value in fields:
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(x, y, f"{label}:")

        pdf.setFont("Helvetica", 10)
        y = _write_wrapped_text(
            pdf,
            str(value),
            x=x + 90,
            y=y,
            max_chars=72,
        )

        y -= 5

    y -= 10
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(x, y, "Probabilidades")

    y -= 20
    pdf.setFont("Helvetica", 10)

    for label, value in (
        record.probabilities or {}
    ).items():
        pdf.drawString(
            x + 15,
            y,
            f"- {label}: {float(value):.2f}%",
        )
        y -= 15

    y -= 10
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(x, y, "Evidencias")

    y -= 20
    pdf.setFont("Helvetica", 10)

    for evidence in record.evidence or []:
        y = _write_wrapped_text(
            pdf,
            f"- {evidence}",
            x=x + 15,
            y=y,
            max_chars=82,
        )
        y -= 4

        if y < 80:
            pdf.showPage()
            y = height - 60
            pdf.setFont("Helvetica", 10)

    metadata = record.analysis_metadata or {}
    axes = metadata.get("axes", {})
    if axes:
        y -= 12
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(x, y, "Ejes independientes")
        y -= 20
        for axis_name in ("generation", "manipulation", "identity_impersonation"):
            axis = axes.get(axis_name, {})
            if not axis:
                continue
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(x + 15, y, axis_name.replace("_", " ").title())
            y -= 14
            pdf.setFont("Helvetica", 9)
            axis_text = (
                f"Estado: {axis.get('status', 'unknown')}; "
                f"resultado: {axis.get('prediction', 'no evaluado')}; "
                f"confianza del modelo: {axis.get('confidence', 'N/A')}"
            )
            y = _write_wrapped_text(pdf, axis_text, x=x + 25, y=y, max_chars=85)
            y -= 6

    integrity = metadata.get("integrity", {})
    if integrity:
        y -= 8
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(x, y, "Integridad y trazabilidad")
        y -= 18
        pdf.setFont("Helvetica", 8)
        y = _write_wrapped_text(
            pdf,
            f"SHA-256: {integrity.get('sha256', 'no disponible')}",
            x=x + 15,
            y=y,
            max_chars=100,
            line_height=12,
        )
        y -= 5
        credentials = integrity.get("content_credentials", {})
        credentials_status = (
            credentials.get("status", "unknown")
            if isinstance(credentials, dict)
            else credentials
        )
        pdf.drawString(
            x + 15,
            y,
            f"Procedencia: {integrity.get('provenance', 'unknown')}; "
            f"Content Credentials: {credentials_status}",
        )

    y -= 18
    pdf.setFont("Helvetica-Oblique", 8)

    disclaimer = (
        "Este reporte separa generación, manipulación e identidad. Representa salidas probabilísticas de "
        "modelos de inteligencia artificial y no constituye por "
        "sí solo una prueba forense concluyente ni una medición de accuracy."
    )

    _write_wrapped_text(
        pdf,
        disclaimer,
        x=x,
        y=y,
        max_chars=105,
        line_height=12,
    )

    pdf.save()

    return output_path
