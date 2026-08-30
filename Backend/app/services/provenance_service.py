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


def _provenance_declarations(reader, active: dict | None) -> dict:
    """Collect signed AI declarations from the active manifest chain."""
    pending = [active] if isinstance(active, dict) else []
    visited: set[str] = set()
    actions: list[dict] = []

    while pending:
        manifest = pending.pop()
        label = str(manifest.get("label", ""))
        if label and label in visited:
            continue
        if label:
            visited.add(label)

        for assertion in manifest.get("assertions", []) or []:
            if not str(assertion.get("label", "")).startswith("c2pa.actions"):
                continue
            for action in assertion.get("data", {}).get("actions", []) or []:
                actions.append(
                    {
                        key: action.get(key)
                        for key in (
                            "action",
                            "digitalSourceType",
                            "description",
                        )
                        if action.get(key) is not None
                    }
                )

        for ingredient in manifest.get("ingredients", []) or []:
            ingredient_label = ingredient.get("active_manifest")
            if not ingredient_label or ingredient_label in visited:
                continue
            try:
                ingredient_manifest = reader.get_manifest(ingredient_label)
            except Exception:
                ingredient_manifest = None
            if isinstance(ingredient_manifest, dict):
                pending.append(ingredient_manifest)

    trained_actions = [
        action
        for action in actions
        if str(action.get("digitalSourceType", "")).endswith(
            "/trainedAlgorithmicMedia"
        )
    ]
    created = any(
        action.get("action") == "c2pa.created"
        for action in trained_actions
    )
    edited = any(
        action.get("action") == "c2pa.edited"
        for action in trained_actions
    )

    return {
        "ai_created_declared": created,
        "ai_edited_declared": edited,
        "ai_provenance_declared": created or edited,
        "manifest_chain_depth": len(visited),
        "declared_actions": _json_safe(actions),
    }


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
        declarations = _provenance_declarations(reader, active)
        return {
            "status": "validated" if active else "not_present",
            "provenance": "credential_present" if active else "unknown",
            "has_manifest": bool(active),
            "validation_state": state,
            "validation_results": _json_safe(results),
            "active_manifest": _manifest_summary(active),
            "declarations": declarations,
            "message": (
                "Content Credentials declaran contenido creado o editado "
                "mediante IA."
                if declarations["ai_provenance_declared"]
                else "Content Credentials encontradas y procesadas por el SDK oficial."
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
