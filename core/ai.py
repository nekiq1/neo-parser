"""AI assistant: DeepSeek (OpenAI-compatible) and Google Gemini REST API."""
import requests


GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"


def _gemini_error(response):
    """Extract a safe, useful provider error without ever echoing credentials."""
    try:
        payload = response.json()
        detail = payload.get("error", {}).get("message")
        status = payload.get("error", {}).get("status")
        if detail:
            suffix = f" ({status})" if status else ""
            return f"Gemini API HTTP {response.status_code}{suffix}: {detail}"
    except (ValueError, AttributeError):
        pass
    return f"Gemini API вернул HTTP {response.status_code}."


def _gemini_text(payload):
    candidates = payload.get("candidates") or []
    if not candidates:
        feedback = payload.get("promptFeedback") or {}
        reason = feedback.get("blockReason")
        if reason:
            raise RuntimeError(f"Gemini не обработал запрос: {reason}.")
        raise RuntimeError("Gemini вернул пустой ответ (нет candidates).")

    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    result = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
    if not result.strip():
        finish = candidates[0].get("finishReason")
        if finish:
            raise RuntimeError(f"Gemini не вернул текст. Причина завершения: {finish}.")
        raise RuntimeError("Gemini вернул ответ без текстовых частей.")
    return result.strip()


def _ask_gemini(settings: dict, prompt: str) -> str:
    key = (settings.get("gemini_api_key") or "").strip()
    model = (settings.get("gemini_model") or DEFAULT_GEMINI_MODEL).strip()
    if not key:
        raise ValueError("Не задан ключ Gemini (Настройки → AI).")
    # Accept both 'gemini-x' and 'models/gemini-x' in settings.
    model = model.removeprefix("models/").strip("/")
    if not model:
        model = DEFAULT_GEMINI_MODEL

    url = f"{GEMINI_API_BASE}/models/{model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": key,
    }
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 2048},
    }

    try:
        response = requests.post(url, headers=headers, json=body, timeout=60)
    except requests.RequestException as exc:
        raise RuntimeError(f"Не удалось связаться с Gemini API: {exc.__class__.__name__}.") from None

    if not response.ok:
        raise RuntimeError(_gemini_error(response))
    try:
        payload = response.json()
    except ValueError:
        raise RuntimeError("Gemini вернул некорректный JSON.") from None
    return _gemini_text(payload)


def ask(settings: dict, prompt: str) -> str:
    prov = settings.get("ai_provider", "DeepSeek")
    if prov == "Gemini":
        return _ask_gemini(settings, prompt)

    key, model = settings.get("deepseek_api_key"), settings.get("deepseek_model", "deepseek-chat")
    if not key:
        raise ValueError("Не задан ключ DeepSeek (Настройки → AI).")
    r = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}]},
        timeout=60,
    )
    r.raise_for_status()
    try:
        return r.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError):
        raise RuntimeError("DeepSeek вернул ответ в неожиданном формате.") from None
