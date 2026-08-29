from __future__ import annotations

from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, PageBreak, Paragraph,
    Spacer, Table, TableStyle,
)
from reportlab.graphics.shapes import Drawing, Rect, String

from app.database.models import Analysis


PAGE_WIDTH, _ = A4
MARGIN = 20 * mm
BLACK = colors.black
LIGHT_GRAY = colors.HexColor("#E6E6E6")
VERY_LIGHT_GRAY = colors.HexColor("#F5F5F5")


def _safe(value: Any, fallback: str = "No disponible") -> str:
    return fallback if value is None or value == "" else str(value)


def _paragraph(value: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(_safe(value)).replace("\n", "<br/>"), style)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    common = {"textColor": BLACK}
    return {
        "title": ParagraphStyle(
            "ReportTitle", parent=base["Title"], fontName="Times-Bold",
            fontSize=16, leading=19, alignment=TA_CENTER, spaceAfter=8, **common,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle", parent=base["Normal"], fontName="Times-Roman",
            fontSize=11, leading=14, alignment=TA_CENTER, spaceAfter=12, **common,
        ),
        "h1": ParagraphStyle(
            "SectionHeading", parent=base["Heading1"], fontName="Times-Bold",
            fontSize=12, leading=15, spaceBefore=10, spaceAfter=6,
            keepWithNext=True, **common,
        ),
        "h2": ParagraphStyle(
            "SubsectionHeading", parent=base["Heading2"], fontName="Times-Bold",
            fontSize=11, leading=14, spaceBefore=7, spaceAfter=4,
            keepWithNext=True, **common,
        ),
        "body": ParagraphStyle(
            "ReportBody", parent=base["BodyText"], fontName="Times-Roman",
            fontSize=11, leading=15, alignment=TA_JUSTIFY, spaceAfter=6, **common,
        ),
        "small": ParagraphStyle(
            "ReportSmall", parent=base["BodyText"], fontName="Times-Roman",
            fontSize=9, leading=12, **common,
        ),
        "table": ParagraphStyle(
            "TableText", parent=base["BodyText"], fontName="Times-Roman",
            fontSize=9, leading=12, **common,
        ),
        "table_bold": ParagraphStyle(
            "TableTextBold", parent=base["BodyText"], fontName="Times-Bold",
            fontSize=9, leading=12, **common,
        ),
    }


def _page(canvas, document) -> None:
    canvas.saveState()
    canvas.setFillColor(BLACK)
    canvas.setStrokeColor(BLACK)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN, 15 * mm, PAGE_WIDTH - MARGIN, 15 * mm)
    canvas.setFont("Times-Roman", 9)
    canvas.drawString(MARGIN, 10 * mm, "DeepFakeShield | Informe técnico de análisis")
    canvas.drawRightString(PAGE_WIDTH - MARGIN, 10 * mm, f"Página {document.page}")
    canvas.restoreState()


def _table(
    rows: list[list[Any]], styles: dict[str, ParagraphStyle],
    widths: list[float] | None = None, *, header: bool = False,
) -> Table:
    normalized = []
    for row_index, row in enumerate(rows):
        normalized.append([
            _paragraph(
                cell,
                styles["table_bold"]
                if (header and row_index == 0) or column_index == 0
                else styles["table"],
            )
            for column_index, cell in enumerate(row)
        ])
    result = Table(normalized, colWidths=widths, repeatRows=1 if header else 0)
    commands = [
        ("TEXTCOLOR", (0, 0), (-1, -1), BLACK),
        ("GRID", (0, 0), (-1, -1), 0.45, BLACK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BACKGROUND", (0, 0), (0, -1), VERY_LIGHT_GRAY),
    ]
    if header:
        commands.extend([
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GRAY),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ])
    result.setStyle(TableStyle(commands))
    return result


def _metadata_coverage_chart(statistics: dict) -> Drawing:
    values = [
        ("EXIF", min(int(statistics.get("exif_fields", 0)) * 10, 100)),
        ("IPTC", min(int(statistics.get("iptc_fields", 0)) * 10, 100)),
        ("XMP", 100 if statistics.get("xmp_present") else 0),
        ("DQT", min(int(statistics.get("dqt_tables", 0)) * 50, 100)),
        ("APP", min(int(statistics.get("app_segments", 0)) * 20, 100)),
    ]
    drawing = Drawing(480, 105)
    for index, (label, value) in enumerate(values):
        y = 86 - index * 19
        drawing.add(String(0, y, label, fontName="Times-Roman", fontSize=9, fillColor=BLACK))
        drawing.add(Rect(48, y - 2, 360, 9, fillColor=VERY_LIGHT_GRAY, strokeColor=BLACK, strokeWidth=.25))
        drawing.add(Rect(48, y - 2, 3.6 * value, 9, fillColor=colors.HexColor("#777777"), strokeColor=None))
        drawing.add(String(416, y, f"{value}%", fontName="Times-Roman", fontSize=9, fillColor=BLACK))
    return drawing


def _support_level(record: Analysis) -> tuple[str, str]:
    prediction = str(record.prediction).upper()
    confidence = float(record.confidence or 0.0)
    if prediction == "INCONCLUSIVE":
        return "Indeterminado", "La evidencia no superó los criterios de decisión."
    if confidence >= 90:
        level = "Soporte alto del modelo"
    elif confidence >= 70:
        level = "Soporte moderado del modelo"
    else:
        level = "Soporte limitado del modelo"
    return level, (
        "Categoría descriptiva basada en un score sin calibrar. No es una razón "
        "de verosimilitud ni la probabilidad de que la hipótesis sea verdadera."
    )


def _axis_rows(metadata: dict[str, Any], record: Analysis) -> list[list[Any]]:
    axes = metadata.get("axes", {})
    if axes:
        rows = [["Eje", "Estado", "Resultado", "Score", "Modelo"]]
        labels = {
            "generation": "Generación sintética",
            "manipulation": "Manipulación / deepfake",
            "identity_impersonation": "Suplantación de identidad",
        }
        for name in ("generation", "manipulation", "identity_impersonation"):
            axis = axes.get(name)
            if not axis:
                continue
            score = axis.get("confidence")
            rows.append([
                labels[name], axis.get("status", "unknown"),
                axis.get("prediction", "No evaluado"),
                f"{float(score):.2f}%" if score is not None else "No aplica",
                axis.get("model", "No aplica"),
            ])
        return rows
    axis_name = (
        "Generación sintética" if record.detector_type == "ai"
        else "Manipulación / deepfake"
    )
    status = "inconclusive" if str(record.prediction).upper() == "INCONCLUSIVE" else "evaluado"
    return [
        ["Eje", "Estado", "Resultado", "Score", "Modelo"],
        [axis_name, status, record.prediction, f"{record.confidence:.2f}%", record.model_name],
        ["Suplantación de identidad", "not_assessed", "No evaluado", "No aplica",
         "Requiere referencia biométrica autorizada"],
    ]


def _credentials_rows(integrity: dict[str, Any]) -> list[list[Any]]:
    credentials = integrity.get("content_credentials", {})
    if not isinstance(credentials, dict):
        credentials = {"status": credentials}
    manifest = credentials.get("active_manifest") or {}
    signature = manifest.get("signature_info") or {}
    active_results = (credentials.get("validation_results") or {}).get("activeManifest") or {}
    failures = active_results.get("failure") or []
    return [
        ["SHA-256", integrity.get("sha256", "No disponible")],
        ["Estado C2PA", credentials.get("status", "unknown")],
        ["Manifestación presente", credentials.get("has_manifest", False)],
        ["Estado de validación", credentials.get("validation_state", "No disponible")],
        ["Emisor declarado", signature.get("issuer", "No disponible")],
        ["Fallos/advertencias de confianza", len(failures)],
        ["Interpretación", credentials.get("message", "Sin información adicional")],
    ]


def _probability_chart(probabilities: dict[str, Any]) -> Drawing:
    drawing = Drawing(470, max(70, 32 * len(probabilities) + 18))
    bar_x = 105
    bar_width = 300
    for index, (label, raw_value) in enumerate(probabilities.items()):
        value = max(0.0, min(100.0, float(raw_value)))
        y = drawing.height - 28 - index * 32
        drawing.add(String(0, y + 2, str(label), fontName="Times-Roman", fontSize=10, fillColor=BLACK))
        drawing.add(Rect(bar_x, y, bar_width, 12, fillColor=colors.HexColor("#E0E0E0"), strokeColor=BLACK, strokeWidth=0.4))
        drawing.add(Rect(bar_x, y, bar_width * value / 100.0, 12, fillColor=colors.HexColor("#666666"), strokeColor=None))
        drawing.add(String(bar_x + bar_width + 8, y + 2, f"{value:.2f}%", fontName="Times-Roman", fontSize=10, fillColor=BLACK))
    return drawing


def _technology_rows(record: Analysis, metadata: dict[str, Any]) -> list[dict[str, Any]]:
    registered = metadata.get("technology_evidence") or []
    if registered:
        return registered
    technical = metadata.get("technical_metadata") or {}
    integrity = metadata.get("integrity") or {}
    credentials = integrity.get("content_credentials") or {}
    if not isinstance(credentials, dict):
        credentials = {"status": credentials}
    derived = [{
        "technology": "Clasificador de IA",
        "status": "executed",
        "purpose": "Estimar la clase solicitada.",
        "observation": f"Modelo: {record.model_name}; resultado: {record.prediction}; score: {record.confidence:.2f}%.",
    }]
    if integrity.get("sha256"):
        derived.append({
            "technology": "SHA-256", "status": "executed",
            "purpose": "Fijar la identidad binaria del archivo.",
            "observation": "Hash registrado en la base de datos.",
        })
    if credentials:
        derived.append({
            "technology": "C2PA / Content Credentials",
            "status": "unavailable" if credentials.get("status") == "sdk_unavailable" else "executed",
            "purpose": "Examinar procedencia e integridad declaradas.",
            "observation": credentials.get("message", f"Estado: {credentials.get('status', 'unknown')}"),
        })
    if technical:
        derived.append({
            "technology": "Metadatos técnicos / EXIF" if record.media_type == "image" else "FFprobe",
            "status": "executed",
            "purpose": "Caracterizar técnicamente el archivo.",
            "observation": f"Formato: {technical.get('format') or technical.get('format_name') or 'desconocido'}; EXIF: {technical.get('exif_present', 'no aplica')}.",
        })
    if record.media_type == "video" and metadata.get("sampled_frames") is not None:
        derived.append({
            "technology": "Muestreo y agregación temporal", "status": "executed",
            "purpose": "Contrastar varios instantes y combinar sus scores.",
            "observation": f"{metadata.get('sampled_frames')} muestreados; {metadata.get('valid_frames', 'N/D')} evaluables.",
        })
    if record.media_type == "audio" and metadata.get("chunk_count") is not None:
        derived.append({
            "technology": "Segmentación acústica", "status": "executed",
            "purpose": "Contrastar varios tramos de la señal.",
            "observation": f"{metadata.get('chunk_count')} segmentos analizados.",
        })
    return derived


def create_pdf_report(record: Analysis) -> bytes:
    output = BytesIO()
    styles = _styles()
    document = BaseDocTemplate(
        output, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=18 * mm, bottomMargin=22 * mm,
        title=f"DeepFakeShield - {record.id}", author="DeepFakeShield",
        subject="Informe técnico de análisis de contenido sintético y deepfake",
    )
    frame = Frame(
        document.leftMargin, document.bottomMargin,
        document.width, document.height, id="report",
    )
    document.addPageTemplates(PageTemplate(id="main", frames=[frame], onPage=_page))

    metadata = record.analysis_metadata or {}
    validation = metadata.get("validation", {})
    quality = metadata.get("quality", {})
    support_level, support_note = _support_level(record)
    methodology_rows = [["Modelo/checkpoint registrado", record.model_name]]
    methodology_rows.append([
        "Estrategia",
        metadata.get("inference_strategy", "Clasificación definida por el detector"),
    ])
    if record.media_type == "video":
        methodology_rows.extend([
            ["Fotogramas muestreados", metadata.get("sampled_frames", "No registrado")],
            ["Fotogramas evaluables", metadata.get("valid_frames", "No registrado")],
            ["Desacuerdo entre modelos", f"{metadata.get('model_disagreement_points')} puntos" if metadata.get("model_disagreement_points") is not None else "No calculado"],
        ])
    elif record.media_type == "audio":
        methodology_rows.append(["Segmentos acústicos", metadata.get("chunk_count", "No registrado")])
    elif record.media_type == "image":
        methodology_rows.extend([
            ["Dimensiones analizadas", f"{metadata.get('image_width', 'N/D')} × {metadata.get('image_height', 'N/D')} px"],
            ["Rostros/candidatos detectados", metadata.get("faces_detected", "No aplica al detector de generación")],
        ])
    story: list[Any] = [
        Paragraph("INFORME TÉCNICO DE ANÁLISIS FORENSE DIGITAL", styles["title"]),
        Paragraph(
            "Detección orientativa de contenido generado por IA, manipulación deepfake y trazabilidad",
            styles["subtitle"],
        ),
        _table([
            ["Identificador del análisis", record.id],
            ["Fecha y hora", record.created_at.isoformat()],
            ["Archivo examinado", record.original_filename],
            ["Tipo de medio", str(record.media_type).upper()],
            ["Detector solicitado", record.detector_type],
            ["Tiempo de procesamiento", f"{record.processing_time_ms} ms"],
        ], styles, [48 * mm, 122 * mm]),
        Paragraph("1. Conclusión ejecutiva", styles["h1"]),
        _table([
            ["Resultado del sistema", record.prediction],
            ["Score/confianza del modelo", f"{record.confidence:.2f}%"],
            ["Nivel de soporte descriptivo", support_level],
            ["Calidad de evidencia", f"{float(quality.get('score', 0.0)):.2f}%" if quality else "No calculada"],
            ["Calibración externa", "Disponible" if validation.get("calibrated") else "Pendiente"],
            ["Razón de verosimilitud (LR)", metadata.get("likelihood_ratio", "No calculada")],
        ], styles, [58 * mm, 112 * mm]),
        Spacer(1, 4),
        Paragraph(
            f"El sistema clasificó el archivo como <b>{escape(str(record.prediction))}</b>. "
            f"{escape(support_note)} La decisión debe interpretarse junto con la calidad del "
            "archivo, la procedencia, el alcance del detector y una revisión humana competente.",
            styles["body"],
        ),
        Paragraph("2. Alcance y conclusiones por eje", styles["h1"]),
        _table(_axis_rows(metadata, record), styles,
               [37 * mm, 25 * mm, 27 * mm, 20 * mm, 61 * mm], header=True),
        Paragraph(
            "Generación sintética y manipulación deepfake son hipótesis diferentes. Detectar "
            "manipulación no demuestra por sí solo la suplantación de una persona concreta; esa "
            "conclusión requiere referencia biométrica autorizada y comparación independiente.",
            styles["body"],
        ),
        Paragraph("3. Modelos y metodología ejecutada", styles["h1"]),
        _table(methodology_rows, styles, [55 * mm, 115 * mm]),
        Paragraph("Probabilidades informadas", styles["h2"]),
        _table([["Clase", "Score del modelo"]] + [
            [label, f"{float(value):.2f}%"]
            for label, value in (record.probabilities or {}).items()
        ], styles, [85 * mm, 85 * mm], header=True),
        _probability_chart(record.probabilities or {}),
        Paragraph("Indicadores observados", styles["h2"]),
    ]

    for index, item in enumerate(record.evidence or ["Sin indicadores narrativos."], 1):
        story.append(Paragraph(f"{index}. {escape(str(item))}", styles["body"]))

    technology_evidence = _technology_rows(record, metadata)
    story.extend([
        Paragraph("Matriz de evidencia tecnológica", styles["h2"]),
        _table(
            [["Tecnología", "Estado", "Finalidad", "Dato observado"]]
            + [
                [
                    item.get("technology"), item.get("status"),
                    item.get("purpose"), item.get("observation"),
                ]
                for item in technology_evidence
            ]
            if technology_evidence
            else [["Tecnología", "Estado", "Finalidad", "Dato observado"],
                  ["Registro tecnológico", "No disponible en análisis antiguo", "Trazabilidad", "Vuelva a ejecutar el archivo con la versión actual"]],
            styles,
            [34 * mm, 24 * mm, 50 * mm, 62 * mm],
            header=True,
        ),
        Paragraph(
            "La matriz enumera únicamente procesos registrados por el backend. Un estado "
            "unavailable, not_executed o inconclusive no se presenta como evidencia positiva.",
            styles["body"],
        ),
    ])

    integrity = metadata.get("integrity", {})
    technical = metadata.get("technical_metadata", {})
    technical_rows = [
        ["Formato", technical.get("format") or technical.get("format_name")],
        ["Resolución", f"{technical.get('width')} × {technical.get('height')}" if technical.get("width") and technical.get("height") else None],
        ["Duración", technical.get("duration")],
        ["Bitrate", technical.get("bit_rate")],
        ["EXIF presente", technical.get("exif_present")],
        ["Software/encoder declarado", technical.get("software") or (technical.get("tags") or {}).get("encoder")],
        ["Número de pistas", len(technical.get("streams", [])) if technical.get("streams") else None],
    ]
    technical_rows = [row for row in technical_rows if row[1] is not None]
    if not technical_rows:
        technical_rows = [["Estado", "No se registraron metadatos técnicos"]]

    forensic = technical.get("forensic_metadata", {})
    forensic_stats = forensic.get("statistics", {})
    descriptive = forensic.get("descriptive", {})
    binary = forensic.get("binary", {})
    consistency = forensic.get("consistency", {})

    story.extend([
        Paragraph("4. Integridad, procedencia y cadena técnica", styles["h1"]),
        _table(_credentials_rows(integrity), styles, [55 * mm, 115 * mm]),
        Paragraph(
            "Content Credentials informa procedencia e integridad declaradas. No sustituye la "
            "detección y debe revisarse junto con la confianza del certificado. La ausencia de "
            "C2PA tampoco demuestra que un archivo sea falso.", styles["body"],
        ),
        Paragraph("5. Metadatos técnicos", styles["h1"]),
        _table(technical_rows, styles, [55 * mm, 115 * mm]),
    ])
    if forensic:
        capture = descriptive.get("capture", {})
        story.extend([
            Paragraph("5.1 Campos EXIF, IPTC y XMP", styles["h2"]),
            _table([
                ["Medición", "Dato observado"],
                ["Campos EXIF", forensic_stats.get("exif_fields", 0)],
                ["Campos IPTC", forensic_stats.get("iptc_fields", 0)],
                ["Paquete XMP", "Presente" if forensic_stats.get("xmp_present") else "No presente"],
                ["Cámara / dispositivo", f"{capture.get('Make', 'N/D')} {capture.get('Model', '')}".strip()],
                ["Óptica y captura", "; ".join(f"{key}: {value}" for key, value in capture.items() if key not in {"Make", "Model"}) or "No declarada"],
            ], styles, [55 * mm, 115 * mm], header=True),
            Paragraph("5.2 Estructura binaria e historial embebido", styles["h2"]),
            _table([
                ["Prueba", "Dato calculado"],
                ["Tablas DQT", forensic_stats.get("dqt_tables", 0)],
                ["Hashes DQT", "; ".join(item.get("sha256", "")[:16] for item in binary.get("dqt_tables", [])) or "No disponibles"],
                ["Marcadores APP", f"{forensic_stats.get('app_segments', 0)}: {binary.get('app_markers', {})}"],
                ["APP1 / APP2 duplicados", f"{binary.get('duplicate_app1', False)} / {binary.get('duplicate_app2', False)}"],
                ["Comentarios COM", "; ".join(binary.get("comments", [])) or "No presentes"],
                ["Miniatura declarada", forensic_stats.get("thumbnail_declared", False)],
                ["Recursos Photoshop / Adobe", f"Photoshop: {binary.get('photoshop_resource_present', False)}; Adobe: {binary.get('adobe_marker_present', False)}"],
            ], styles, [55 * mm, 115 * mm], header=True),
            Paragraph("5.3 Consistencia y cruce forense", styles["h2"]),
            _table([
                ["Cruce", "Resultado"],
                ["Formato frente a extensión", "Coherente" if consistency.get("extension_consistent") else "Requiere atención"],
                ["Relación de aspecto", f"{consistency.get('aspect_ratio', 'N/D')} · cercana a {consistency.get('nearest_standard_ratio', 'N/D')} · desviación {consistency.get('ratio_deviation_percent', 'N/D')}%"],
                ["Secuencia temporal declarada", consistency.get("temporal_status", "No evaluable")],
                ["Cobertura descriptiva/binaria", f"{forensic_stats.get('checks_with_observation', 0)} de {forensic_stats.get('checks_executed', 0)} comprobaciones con observación"],
            ], styles, [55 * mm, 115 * mm], header=True),
            Paragraph("Gráfico de disponibilidad de rastros", styles["h2"]),
            _metadata_coverage_chart(forensic_stats),
            Paragraph("Matriz de hallazgos de metadatos", styles["h2"]),
            _table([["Capa", "Prueba", "Estado", "Dato e interpretación"]] + [[item.get("category"), item.get("check"), item.get("status"), f"{item.get('observation')} {item.get('interpretation')}"] for item in forensic.get("findings", [])], styles, [28 * mm, 35 * mm, 27 * mm, 80 * mm], header=True),
            Paragraph(forensic.get("interpretive_caveat"), styles["body"]),
        ])

    story.extend([
        PageBreak(),
        Paragraph("6. Recomendaciones de fortalecimiento y verificación certificada", styles["h1"]),
        Paragraph(
            "El score es una salida del modelo. No equivale a accuracy, tasa de error, "
            "probabilidad posterior ni fuerza probatoria calibrada. Para elevar el nivel de certeza, "
            "se recomienda complementar el análisis con proveedores o laboratorios cuyo alcance "
            "acreditado o conformidad publicada cubra expresamente la prueba requerida.", styles["body"],
        ),
        _table([
            ["Servicio recomendado", "Referencia verificable", "Aporte esperado"],
            ["Laboratorio de ensayo forense", "Acreditación ISO/IEC 17025 con alcance aplicable", "Método documentado, competencia técnica y trazabilidad del ensayo"],
            ["Validador de procedencia", "Producto conforme C2PA y lista de confianza oficial", "Validación interoperable de manifiestos, firma y cadena de procedencia"],
            ["Evaluación TEVV independiente", "Protocolo NIST AI RMF con dataset etiquetado y separado", "Accuracy, sensibilidad, especificidad, ROC/AUC, calibración y error por dominio"],
            ["Comparación biométrica", "Sistema evaluado bajo ISO/IEC 19795 y consentimiento aplicable", "Métricas de desempeño para una comparación de identidad autorizada"],
            ["Pruebas de robustez", "Servicio con protocolo versionado de compresión y perturbaciones", "Desempeño de peor caso ante transcodificación y contramedidas"],
        ], styles, [47 * mm, 58 * mm, 65 * mm], header=True),
        Paragraph("7. Dictamen técnico", styles["h1"]),
        Paragraph(
            f"Con la evidencia automatizada disponible, el resultado operativo es "
            f"<b>{escape(str(record.prediction))}</b>, con score de "
            f"<b>{record.confidence:.2f}%</b> y nivel <b>{escape(support_level.lower())}</b>. "
            "Sirve para priorización y apoyo analítico; no debe utilizarse aisladamente como "
            "identificación biométrica, atribución de autoría o prueba pericial concluyente.",
            styles["body"],
        ),
        Paragraph("8. Referencias metodológicas", styles["h1"]),
    ])

    references = [
        "Tabassi, E. (2023). Artificial Intelligence Risk Management Framework (AI RMF 1.0). NIST AI 100-1. DOI: 10.6028/NIST.AI.100-1.",
        "NIST (2024). Reducing Risks Posed by Synthetic Content: An Overview of Technical Approaches to Digital Content Transparency. NIST AI 100-4.",
        "Guo, T., Li, J. y Tang, Y. (2026). A score-based likelihood ratio framework for deepfake image identification in forensic science. Scientific Reports, 16, 12149. DOI: 10.1038/s41598-026-42176-w.",
        "Le, B. M., Kim, J., Woo, S. S., Moore, K., Abuadbba, A. y Tariq, S. (2025). SoK: Systematization and Benchmarking of Deepfake Detectors in a Unified Framework. arXiv:2401.04364v4.",
        "Qureshi, S. M., Saeed, A., Almotiri, S. H., Ahmad, F. y Al Ghamdi, M. A. (2024). Deepfake forensics: a survey of digital forensic methods for multimodal deepfake identification on social media. PeerJ Computer Science, 10:e2037. DOI: 10.7717/peerj-cs.2037.",
        "Aribe, S. Jr. (2025). A Hybrid Deep Learning and Forensic Approach for Robust Deepfake Detection. International Journal of Advanced Computer Science and Applications, 16(10).",
        "Fatima, N., Khan, H. F. y Behzad, M. (2025). Attack-Aware Deepfake Detection under Counter-Forensic Manipulations. arXiv:2512.22303v1.",
        "ISO/IEC 17025:2017. General requirements for the competence of testing and calibration laboratories.",
        "ISO/IEC 19795-1:2021. Information technology — Biometric performance testing and reporting — Part 1: Principles and framework.",
        "Coalition for Content Provenance and Authenticity (C2PA). Conformance Program and official Trust List.",
    ]
    for index, reference in enumerate(references, 1):
        story.extend([
            Paragraph(f"[{index}] {escape(reference)}", styles["small"]),
            Spacer(1, 3),
        ])
    story.extend([
        Spacer(1, 8),
        Paragraph(
            "Nota final: documento generado automáticamente. Conserve el original, verifique "
            "el hash y someta los hallazgos a revisión pericial cuando existan consecuencias "
            "legales, disciplinarias, financieras o reputacionales.", styles["body"],
        ),
    ])

    document.build(story)
    return output.getvalue()
