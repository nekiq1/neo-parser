import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import ai, config


def test_gemini_uses_current_default_model_and_header_key():
    response = Mock()
    response.ok = True
    response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "OK"}]}}]
    }
    with patch.object(ai.requests, "post", return_value=response) as post:
        result = ai.ask(
            {"ai_provider": "Gemini", "gemini_api_key": "unit-test-key"},
            "Reply OK",
        )
    assert result == "OK"
    args, kwargs = post.call_args
    assert args[0].endswith("/models/gemini-3.8-flash:generateContent")
    assert kwargs["headers"]["x-goog-api-key"] == "unit-test-key"
    assert "key=" not in args[0]
    assert kwargs["json"]["contents"][0]["role"] == "user"


def test_gemini_migrates_legacy_default_model():
    assert config.DEFAULTS["gemini_model"] == "gemini-3.8-flash"


def test_gemini_model_prefix_is_normalized():
    response = Mock()
    response.ok = True
    response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "OK"}]}}]
    }
    with patch.object(ai.requests, "post", return_value=response) as post:
        ai.ask(
            {"ai_provider": "Gemini", "gemini_api_key": "unit-test-key",
             "gemini_model": "models/gemini-3.8-flash"},
            "Reply OK",
        )
    assert post.call_args.args[0].endswith("/models/gemini-3.8-flash:generateContent")


def test_gemini_http_error_is_reported_without_key():
    response = Mock()
    response.ok = False
    response.status_code = 404
    response.json.return_value = {
        "error": {"message": "Model is not available", "status": "NOT_FOUND"}
    }
    with patch.object(ai.requests, "post", return_value=response):
        try:
            ai.ask(
                {"ai_provider": "Gemini", "gemini_api_key": "do-not-print-this"},
                "Reply OK",
            )
        except RuntimeError as exc:
            assert "404" in str(exc) and "NOT_FOUND" in str(exc)
            assert "do-not-print-this" not in str(exc)
        else:
            raise AssertionError("Expected Gemini HTTP error")
