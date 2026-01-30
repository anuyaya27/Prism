import json
import hashlib
from typing import Tuple

from app.models.schemas import EvaluateRequest


def canonicalize_request(request: EvaluateRequest) -> Tuple[dict, bytes, str]:
    """
    Produce a deterministic representation of an EvaluateRequest.
    - Strips prompt whitespace
    - Sorts model IDs for stability
    - Uses sorted keys and compact separators
    Returns tuple of (canonical_dict, canonical_bytes, sha256 hex hash).
    """
    models = request.models[:] if request.models else []
    models_sorted = sorted(models)
    canonical = {
        "prompt": request.prompt.strip(),
        "models": models_sorted,
        "params": {
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "timeout_s": request.timeout_s,
            "synthesis_method": request.synthesis_method,
        },
    }
    canonical_bytes = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    run_hash = hashlib.sha256(canonical_bytes).hexdigest()
    return canonical, canonical_bytes, run_hash
