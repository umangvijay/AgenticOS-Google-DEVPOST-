import pytest
from backend.instrumentation.telemetry import TelemetrySanitizer

def test_telemetry_sanitizer():
    # Test basic dictionary redaction
    raw_data = {
        "api_key": "123456",
        "username": "alice",
        "email_address": "alice@example.com",
        "normal_field": "hello world"
    }
    
    sanitized = TelemetrySanitizer.sanitize(raw_data)
    
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["email_address"] == "[REDACTED]"
    assert sanitized["username"] == "alice"
    assert sanitized["normal_field"] == "hello world"

def test_telemetry_sanitizer_nested():
    # Test nested redaction
    raw_data = {
        "user": {
            "token": "abcdef",
            "age": 30
        },
        "items": [
            {"name": "apple", "secret_recipe": "xyz"},
            {"name": "banana"}
        ]
    }
    
    sanitized = TelemetrySanitizer.sanitize(raw_data)
    
    assert sanitized["user"]["token"] == "[REDACTED]"
    assert sanitized["user"]["age"] == 30
    assert sanitized["items"][0]["secret_recipe"] == "[REDACTED]"
    assert sanitized["items"][1]["name"] == "banana"

def test_telemetry_sanitizer_truncation():
    # Test string truncation
    long_string = "A" * 3000
    sanitized = TelemetrySanitizer.sanitize(long_string)
    
    assert len(sanitized) < 3000
    assert sanitized.endswith("[TRUNCATED]")
    assert len(sanitized) == 1015 # 1000 + length of "... [TRUNCATED]"
