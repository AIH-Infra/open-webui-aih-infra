from typing import Any, Optional


def resolve_effective_hybrid(hybrid: Any, global_default: bool) -> bool:
    if isinstance(hybrid, bool):
        return hybrid

    if isinstance(hybrid, str):
        normalized = hybrid.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False

    return global_default


def normalize_reranking_preset_models(value: Any) -> list[str]:
    if not value:
        return []

    if isinstance(value, str):
        candidates = value.splitlines()
    elif isinstance(value, (list, tuple, set)):
        candidates = value
    else:
        return []

    normalized: list[str] = []
    seen = set()

    for item in candidates:
        if not isinstance(item, str):
            continue
        model = item.strip()
        if not model or model in seen:
            continue
        normalized.append(model)
        seen.add(model)

    return normalized[:50]


def resolve_effective_reranking_model(
    requested_model: Any,
    global_default: str,
    preset_models: list[str],
) -> Optional[str]:
    if not isinstance(global_default, str):
        global_default = ""

    requested = requested_model.strip() if isinstance(requested_model, str) else ""
    if not requested:
        return global_default or None

    if requested in preset_models:
        return requested

    return global_default or None


def normalize_rag_mode_value(rag_mode: Any) -> str:
    if rag_mode in (None, ""):
        return "traditional"

    if isinstance(rag_mode, str):
        normalized = rag_mode.strip().lower()
        if normalized in {"agent", "disabled", "traditional"}:
            return normalized

    return "traditional"


def normalize_rag_mode(metadata: Optional[dict]) -> str:
    params = (metadata or {}).get("params", {}) or {}
    return normalize_rag_mode_value(params.get("rag_mode"))
