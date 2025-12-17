from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import httpx

@dataclass(frozen=True)
class OllamaConfig:
    base_url: str = "http://127.0.0.1:11434"
    timeout_s: float = 180.0

class OllamaError(RuntimeError):
    pass

class Ollama:
    def __init__(self, cfg: OllamaConfig = OllamaConfig()):
        self.cfg = cfg

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.cfg.base_url}{path}"
        try:
            with httpx.Client(timeout=self.cfg.timeout_s) as c:
                r = c.post(url, json=payload)
                r.raise_for_status()
                return r.json()
        except Exception as e:
            raise OllamaError(f"Ollama POST {url} failed: {e}") from e

    def embeddings(self, model: str, text: str) -> List[float]:
        data = self._post("/api/embeddings", {"model": model, "prompt": text})
        emb = data.get("embedding")
        if not isinstance(emb, list):
            raise OllamaError("Invalid embeddings response.")
        return emb  # type: ignore[return-value]

    def generate(self, model: str, prompt: str, *, system: Optional[str] = None) -> str:
        payload: Dict[str, Any] = {"model": model, "prompt": prompt, "stream": False}
        if system:
            payload["system"] = system
        data = self._post("/api/generate", payload)
        out = data.get("response")
        if not isinstance(out, str):
            raise OllamaError("Invalid generate response.")
        return out
