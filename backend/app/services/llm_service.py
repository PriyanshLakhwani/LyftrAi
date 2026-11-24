import json
import time
from typing import List, Dict, Any, Optional
import litellm
from ..config import settings

# Helper to parse the X‑Simulate‑Failure header
def parse_failure_header(header_value: str) -> Dict[str, int]:
    """Parse header like "key_1=429,key_2=500" into a dict.
    Returns an empty dict if header is None or malformed.
    """
    result: Dict[str, int] = {}
    if not header_value:
        return result
    for part in header_value.split(','):
        part = part.strip()
        if not part or '=' not in part:
            continue
        key, code = part.split('=', 1)
        try:
            result[key.strip()] = int(code.strip())
        except ValueError:
            continue
    return result

class LLMService:
    """Thin wrapper around LiteLLM that provides:
    * In‑memory cache keyed by model+system_prompt+full_message_list
    * Automatic fallback across multiple API keys
    * Optional failure simulation via X‑Simulate‑Failure header
    """

    # a process‑wide cache so that different FastAPI request instances share it
    _global_cache: Dict[str, Dict[str, Any]] = {}

    def __init__(self) -> None:
        # Build a list of dicts: {"key_id": "key_1", "api_key": "<key>"}
        self.keys = [
            {"key_id": f"key_{i+1}", "api_key": k}
            for i, k in enumerate(settings.api_keys_list)
        ]
        self.cache = LLMService._global_cache

    # ---------------------------------------------------------------------
    # Cache helpers
    # ---------------------------------------------------------------------
    def _cache_key(self, model: str, system_prompt: Optional[str], messages: List[Dict[str, str]]) -> str:
        """Create a deterministic hashable cache key.
        The order of messages matters – we serialize the whole payload.
        """
        payload = {
            "model": model,
            "system_prompt": system_prompt,
            "messages": messages,
        }
        # json.dumps with sorted keys gives a stable string representation
        return json.dumps(payload, sort_keys=True)

    # ---------------------------------------------------------------------
    # Provider call (single key)
    # ---------------------------------------------------------------------
    def _call_provider(self, model: str, messages: List[Dict[str, str]], api_key: str) -> Dict[str, Any]:
        start = time.time()
        # litellm will raise LiteLLMException on HTTP errors
        response = litellm.completion(model=model, messages=messages, api_key=api_key)
        latency = int((time.time() - start) * 1000)
        usage = response.get("usage", {})
        return {
            "reply": response["choices"][0]["message"]["content"],
            "model": model,
            "latency_ms": latency,
            "input_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
        }

    # ---------------------------------------------------------------------
    # Public method used by the FastAPI route
    # ---------------------------------------------------------------------
    def get_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        simulate_header: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return a dict containing the assistant reply and all required metadata.
        Handles caching, key fallback, and simulated failures.
        """
        # Build the full message list for the LLM call (system prompt first)
        full_messages: List[Dict[str, str]] = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        # -----------------------------------------------------------------
        # 1️⃣  Cache lookup
        # -----------------------------------------------------------------
        cache_key = self._cache_key(settings.DEFAULT_MODEL, system_prompt, full_messages)
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            return {
                **cached,
                "resolution_source": "LLM_CACHE",
                "key_id": None,
                "fallback_attempts": 0,
                "from_cache": True,
            }

        # -----------------------------------------------------------------
        # 2️⃣  Simulated failures (if enabled)
        # -----------------------------------------------------------------
        simulate_map = parse_failure_header(simulate_header) if simulate_header else {}

        # -----------------------------------------------------------------
        # 3️⃣  Iterate over the key pool, applying fallback logic
        # -----------------------------------------------------------------
        for idx, entry in enumerate(self.keys):
            key_id = entry["key_id"]
            api_key = entry["api_key"]

            # Skip this key if the simulation header says it should fail
            if settings.ENABLE_FAILURE_SIMULATION:
                if key_id in simulate_map or "*" in simulate_map:
                    continue

            try:
                result = self._call_provider(settings.DEFAULT_MODEL, full_messages, api_key)
                # Successful call – store in cache for future identical requests
                self.cache[cache_key] = result
                result.update(
                    {
                        "resolution_source": "LIVE_INFERENCE",
                        "key_id": key_id,
                        "fallback_attempts": idx,
                        "from_cache": False,
                    }
                )
                return result
            except litellm.exceptions.LiteLLMException as exc:
                status = getattr(exc, "status_code", None)

                print(
                    f"Provider failed | key_id={key_id} | "
                    f"status={status} | error={str(exc)}"
                )

                if status in (429, 500, 502, 503):
                    continue

                raise

        # -----------------------------------------------------------------
        # 4️⃣  All keys exhausted – raise a 503‑type exception that FastAPI will
        #     convert to the required JSON payload.
        # -----------------------------------------------------------------
        raise litellm.exceptions.LiteLLMException(message="All providers unavailable",status_code=503)
