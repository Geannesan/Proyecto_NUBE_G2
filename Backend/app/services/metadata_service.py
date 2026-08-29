import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

from PIL import ExifTags, Image, IptcImagePlugin


def _safe_text(value, limit: int = 240) -> str:
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    return str(value).replace("\x00", " ").strip()[:limit]


def _jpeg_segments(data: bytes) -> dict:
    result = {"app_markers": {}, "app_segments_total": 0, "dqt_tables": [], "comments": [], "jfif_present": False, "adobe_marker_present": False, "photoshop_resource_present": False, "jumbf_c2pa_marker_present": False}
    if not data.startswith(b"\xff\xd8"):
        return result
    cursor = 2
    while cursor + 4 <= len(data):
        if data[cursor] != 0xFF:
            cursor += 1
            continue
        while cursor < len(data) and data[cursor] == 0xFF:
            cursor += 1
        if cursor >= len(data): break
        marker = data[cursor]; cursor += 1
        if marker in (0xD9, 0xDA): break
        if marker in range(0xD0, 0xD8) or marker == 0x01: continue
        if cursor + 2 > len(data): break
        length = int.from_bytes(data[cursor:cursor + 2], "big")
        if length < 2 or cursor + length > len(data): break
        payload = data[cursor + 2:cursor + length]; cursor += length
        if 0xE0 <= marker <= 0xEF:
            name = f"APP{marker - 0xE0}"
            result["app_markers"][name] = result["app_markers"].get(name, 0) + 1
            result["app_segments_total"] += 1
            result["jfif_present"] |= name == "APP0" and payload.startswith(b"JFIF")
            result["adobe_marker_present"] |= name == "APP14" and payload.startswith(b"Adobe")
            result["photoshop_resource_present"] |= b"Photoshop 3.0" in payload
            result["jumbf_c2pa_marker_present"] |= any(token in payload.lower() for token in (b"jumb", b"c2pa"))
        elif marker == 0xFE:
            result["comments"].append(_safe_text(payload))
        elif marker == 0xDB:
            offset = 0
            while offset < len(payload):
                descriptor = payload[offset]; offset += 1
                precision, table_id = descriptor >> 4, descriptor & 0x0F
                coefficient_bytes = 128 if precision else 64
                values = payload[offset:offset + coefficient_bytes]
                if len(values) != coefficient_bytes: break
                offset += coefficient_bytes
                result["dqt_tables"].append({"table_id": table_id, "precision_bits": 16 if precision else 8, "coefficient_count": 64, "sha256": hashlib.sha256(values).hexdigest(), "first_coefficients": list(values[:8])})
    result["duplicate_app1"] = result["app_markers"].get("APP1", 0) > 1
    result["duplicate_app2"] = result["app_markers"].get("APP2", 0) > 1
    return result


def _parse_exif_date(value):
    try:
        return datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S") if value else None
    except (TypeError, ValueError):
        return None


def _image_metadata(path: Path) -> dict:
    raw = path.read_bytes()
    with Image.open(path) as image:
        exif = {ExifTags.TAGS.get(key, str(key)): _safe_text(value) for key, value in image.getexif().items()}
        try:
            iptc = {str(key): _safe_text(value) for key, value in (IptcImagePlugin.getiptcinfo(image) or {}).items()}
        except Exception:
            iptc = {}
        xmp_value = image.info.get("xmp") or image.info.get("XML:com.adobe.xmp")
        xmp_present = bool(xmp_value) or b"<x:xmpmeta" in raw or b"<?xpacket" in raw
        binary = _jpeg_segments(raw) if image.format == "JPEG" else {"app_markers": {}, "app_segments_total": 0, "dqt_tables": [], "comments": [], "not_applicable": "DQT y APP corresponden a JPEG."}
        width, height = image.size
        ratio = width / height if height else 0
        ratios = {"1:1": 1, "4:3": 4 / 3, "3:2": 3 / 2, "16:9": 16 / 9, "5:4": 5 / 4, "9:16": 9 / 16}
        nearest_name, nearest_value = min(ratios.items(), key=lambda item: abs(ratio - item[1]))
        deviation = abs(ratio - nearest_value) / nearest_value * 100
        dates = {"original": exif.get("DateTimeOriginal"), "digitized": exif.get("DateTimeDigitized"), "modified_declared": exif.get("DateTime")}
        comparable = [value for value in (_parse_exif_date(value) for value in dates.values()) if value]
        temporal_status = "not_assessable" if len(comparable) < 2 else ("consistent" if comparable == sorted(comparable) else "attention")
        thumbnail = bool(exif.get("JPEGInterchangeFormat") and exif.get("JPEGInterchangeFormatLength"))
        expected = {"JPEG": {".jpg", ".jpeg", ".jpe"}, "PNG": {".png"}, "WEBP": {".webp"}, "TIFF": {".tif", ".tiff"}}
        extension_consistent = path.suffix.lower() in expected.get(image.format, {path.suffix.lower()})
        findings = [
            {"category": "Descriptivo", "check": "EXIF", "status": "observed" if exif else "not_available", "observation": f"{len(exif)} campos encontrados.", "interpretation": "La ausencia reduce información de procedencia, pero no demuestra generación por IA."},
            {"category": "Descriptivo", "check": "IPTC / XMP", "status": "observed" if iptc or xmp_present else "not_available", "observation": f"IPTC: {len(iptc)} campos; XMP: {'presente' if xmp_present else 'ausente'}.", "interpretation": "Registra declaraciones editoriales o de autoría cuando existen."},
            {"category": "Binario", "check": "Tablas JPEG DQT", "status": "observed" if binary.get("dqt_tables") else ("not_applicable" if image.format != "JPEG" else "not_available"), "observation": f"{len(binary.get('dqt_tables', []))} tablas extraídas.", "interpretation": "Sus hashes permiten comparación con un catálogo validado; solos no atribuyen editor o cámara."},
            {"category": "Binario", "check": "Miniatura incrustada", "status": "observed" if thumbnail else "not_available", "observation": "Declarada en EXIF." if thumbnail else "No declarada en EXIF accesible.", "interpretation": "Solo puede compararse cuando existe una miniatura recuperable."},
            {"category": "Consistencia", "check": "Formato y extensión", "status": "consistent" if extension_consistent else "attention", "observation": f"Contenido {image.format}; extensión {path.suffix.lower()}.", "interpretation": "Una discordancia puede indicar renombrado o conversión."},
            {"category": "Consistencia", "check": "Relación de aspecto", "status": "consistent" if deviation <= 2 else "observed", "observation": f"{ratio:.4f}; cercana a {nearest_name}; desviación {deviation:.2f}%.", "interpretation": "Una relación no estándar puede deberse a recorte, exportación o generación; no determina origen."},
            {"category": "Consistencia", "check": "Coherencia temporal declarada", "status": temporal_status, "observation": f"Original: {dates['original'] or 'N/D'}; digitalizada: {dates['digitized'] or 'N/D'}; modificada: {dates['modified_declared'] or 'N/D'}.", "interpretation": "Compara fechas declaradas; no las autentica."},
        ]
        observed = sum(item["status"] in {"observed", "consistent", "attention"} for item in findings)
        forensic = {
            "schema_version": "1.0",
            "statistics": {"exif_fields": len(exif), "iptc_fields": len(iptc), "xmp_present": xmp_present, "dqt_tables": len(binary.get("dqt_tables", [])), "app_segments": binary.get("app_segments_total", 0), "binary_comments": len(binary.get("comments", [])), "thumbnail_declared": thumbnail, "checks_executed": len(findings), "checks_with_observation": observed, "metadata_coverage_percent": round(observed / len(findings) * 100, 1)},
            "descriptive": {"exif": exif, "iptc": iptc, "xmp_present": xmp_present, "capture": {key: exif.get(key) for key in ("Make", "Model", "LensModel", "ExposureTime", "FNumber", "ISOSpeedRatings", "PhotographicSensitivity", "FocalLength") if exif.get(key)}, "dates": dates},
            "binary": binary,
            "consistency": {"aspect_ratio": round(ratio, 4), "nearest_standard_ratio": nearest_name, "ratio_deviation_percent": round(deviation, 2), "extension_consistent": extension_consistent, "temporal_status": temporal_status},
            "findings": findings,
            "interpretive_caveat": "Los metadatos apoyan la trazabilidad. Ningún campo aislado confirma que el contenido sea real, generado o manipulado.",
        }
        return {
            "status": "available",
            "format": image.format,
            "width": width,
            "height": height,
            "mode": image.mode,
            "color_space": image.mode,
            "exif_present": bool(exif),
            "exif": exif,
            "software": exif.get("Software"),
            "capture_datetime": exif.get("DateTimeOriginal", exif.get("DateTime")),
            "forensic_metadata": forensic,
        }


def _ffprobe_metadata(path: Path) -> dict:
    command = [
        "ffprobe", "-v", "error", "-show_format", "-show_streams",
        "-of", "json", str(path),
    ]
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=30, check=False
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        return {"status": "unavailable", "reason": type(error).__name__}
    if completed.returncode != 0:
        return {"status": "unreadable", "reason": completed.stderr[-300:]}
    payload = json.loads(completed.stdout)
    streams = []
    for stream in payload.get("streams", []):
        streams.append({
            key: stream.get(key)
            for key in (
                "index", "codec_type", "codec_name", "profile", "width", "height",
                "sample_rate", "channels", "duration", "bit_rate", "avg_frame_rate",
            )
            if stream.get(key) is not None
        })
    media_format = payload.get("format", {})
    return {
        "status": "available",
        "format_name": media_format.get("format_name"),
        "duration": media_format.get("duration"),
        "size": media_format.get("size"),
        "bit_rate": media_format.get("bit_rate"),
        "tags": media_format.get("tags", {}),
        "streams": streams,
    }


def inspect_technical_metadata(path: str | Path, media_type: str) -> dict:
    media_path = Path(path)
    try:
        return _image_metadata(media_path) if media_type == "image" else _ffprobe_metadata(media_path)
    except Exception as error:
        return {"status": "unreadable", "reason": type(error).__name__}
