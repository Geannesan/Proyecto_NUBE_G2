from pathlib import Path
import json


def _json_safe(value):
    return json.loads(json.dumps(value, default=str))


def _manifest_summary(active) -> dict | None:
    if not isinstance(active, dict):
        return None
    summary = {
        key: active.get(key)
        for key in (
            "label", "title", "format", "instance_id",
            "claim_generator", "signature_info",
        )
        if active.get(key) is not None
    }
    summary["assertion_count"] = len(active.get("assertions", []) or [])
    summary["ingredient_count"] = len(active.get("ingredients", []) or [])
    return _json_safe(summary)


def inspect_content_credentials(path: str | Path) -> dict:
    """Valida C2PA cuando el SDK oficial está disponible.

    La ausencia de credenciales se reporta como desconocida, nunca como fraude.
    """
    try:
        from c2pa import Context, Reader
    except ImportError:
        return {
            "status": "sdk_unavailable",
            "provenance": "unknown",
            "has_manifest": False,
            "message": "Instale c2pa-python para validar Content Credentials.",
        }

    reader = None
    try:
        reader = Reader(str(Path(path)), context=Context())
        active = reader.get_active_manifest()
        state = str(reader.get_validation_state())
        results = reader.get_validation_results()
        return {
            "status": "validated" if active else "not_present",
            "provenance": "credential_present" if active else "unknown",
            "has_manifest": bool(active),
            "validation_state": state,
            "validation_results": _json_safe(results),
            "active_manifest": _manifest_summary(active),
            "message": (
                "Content Credentials encontradas y procesadas por el SDK oficial."
                if active else "El archivo no contiene Content Credentials verificables."
            ),
        }
    except Exception as error:
        return {
            "status": "not_present_or_invalid",
            "provenance": "unknown",
            "has_manifest": False,
            "message": f"No se obtuvo una credencial C2PA válida: {type(error).__name__}.",
        }
    finally:
        if reader is not None and hasattr(reader, "close"):
            reader.close()
