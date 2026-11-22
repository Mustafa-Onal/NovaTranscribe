import os
import json
import urllib.request
import urllib.error


DEFAULT_BASE_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "nova:latest")


def _post_json(url: str, payload: dict, timeout: int = 120) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama sunucusuna bağlanılamadı ({url}): {exc.reason}") from exc


def generate_reply(
    transcript: str,
    language: str = "tr",
    model: str | None = None,
    system_prompt: str | None = None,
    base_url: str = DEFAULT_BASE_URL,
) -> str:
    cleaned = transcript.strip()
    if not cleaned:
        raise ValueError("İşlenecek transkript metni boş.")

    target_model = (model or DEFAULT_MODEL).strip()
    prompt_system = system_prompt or (
        f"Sen yardımcı bir asistansın. Kullanıcının ses kaydından çıkarılan metni analiz et "
        f"ve net, öz ve doğrudan yanıt ver. Yanıt dili kodu: {language}."
    )

    chat_payload = {
        "model": target_model,
        "stream": False,
        "messages": [
            {"role": "system", "content": prompt_system},
            {"role": "user", "content": cleaned},
        ],
    }

    try:
        result = _post_json(f"{base_url}/api/chat", chat_payload)
        content = (result.get("message") or {}).get("content", "").strip()
    except RuntimeError as exc:
        if "HTTP 404" not in str(exc):
            raise
        gen_payload = {
            "model": target_model,
            "stream": False,
            "system": prompt_system,
            "prompt": cleaned,
        }
        result = _post_json(f"{base_url}/api/generate", gen_payload)
        content = (result.get("response") or "").strip()

    if not content:
        raise RuntimeError("Ollama boş yanıt döndürdü.")
    return content