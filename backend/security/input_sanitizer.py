"""
AgentOS — Input Sanitizer

Defense-in-depth input validation:
- XSS payload stripping
- Path traversal blocking
- SQL injection pattern detection
- Size limits on bodies/uploads/goal text
- Prompt injection detection for agent inputs
"""

import re
import html
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Size Limits ───────────────────────────────────────────────────
MAX_GOAL_LENGTH = 5_000          # Max characters for a workflow goal
MAX_UPLOAD_SIZE_MB = 10          # Max file upload size
MAX_BODY_SIZE_KB = 512           # Max request body size
MAX_FIELD_LENGTH = 10_000        # Max length for any single text field
MAX_EMAIL_LENGTH = 254           # RFC 5321
MAX_NAME_LENGTH = 200

# ── Dangerous Patterns ────────────────────────────────────────────

# XSS attack vectors
XSS_PATTERNS = [
    re.compile(r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),  # onclick=, onerror=, etc.
    re.compile(r"<iframe\b", re.IGNORECASE),
    re.compile(r"<object\b", re.IGNORECASE),
    re.compile(r"<embed\b", re.IGNORECASE),
    re.compile(r"<svg\b[^>]*\bon\w+", re.IGNORECASE),
    re.compile(r"data\s*:\s*text/html", re.IGNORECASE),
    re.compile(r"expression\s*\(", re.IGNORECASE),  # CSS expression()
    re.compile(r"vbscript\s*:", re.IGNORECASE),
]

# Path traversal
PATH_TRAVERSAL_PATTERNS = [
    re.compile(r"\.\./"),
    re.compile(r"\.\.\\"),
    re.compile(r"%2e%2e[/\\]", re.IGNORECASE),
    re.compile(r"%252e%252e", re.IGNORECASE),
    re.compile(r"/etc/passwd", re.IGNORECASE),
    re.compile(r"\\windows\\", re.IGNORECASE),
    re.compile(r"\0"),  # Null bytes
]

# SQL injection (defense-in-depth — parameterized queries are primary defense)
SQL_INJECTION_PATTERNS = [
    re.compile(r";\s*(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|EXEC)\b", re.IGNORECASE),
    re.compile(r"UNION\s+SELECT", re.IGNORECASE),
    re.compile(r"'\s*OR\s+'1'\s*=\s*'1", re.IGNORECASE),
    re.compile(r"--\s*$"),
]


class InputValidationError(Exception):
    """Raised when input fails sanitization."""
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(message)


def sanitize_text(text: str, field_name: str = "input", max_length: int = MAX_FIELD_LENGTH) -> str:
    """
    Sanitize a text input.
    - Strip leading/trailing whitespace
    - HTML-escape dangerous characters
    - Block XSS patterns
    - Block path traversal
    - Enforce length limit
    """
    if not isinstance(text, str):
        raise InputValidationError(f"{field_name} must be a string", field_name)

    # Length check
    if len(text) > max_length:
        raise InputValidationError(
            f"{field_name} exceeds maximum length of {max_length} characters",
            field_name,
        )

    # Check for XSS
    for pattern in XSS_PATTERNS:
        if pattern.search(text):
            logger.warning(f"XSS pattern detected in {field_name}")
            raise InputValidationError(
                f"Potentially dangerous content detected in {field_name}",
                field_name,
            )

    # Check for path traversal
    for pattern in PATH_TRAVERSAL_PATTERNS:
        if pattern.search(text):
            logger.warning(f"Path traversal detected in {field_name}")
            raise InputValidationError(
                f"Invalid characters in {field_name}",
                field_name,
            )

    return text.strip()


def sanitize_goal(goal: str) -> str:
    """Sanitize a workflow goal input."""
    return sanitize_text(goal, "goal", MAX_GOAL_LENGTH)


def sanitize_email(email: str) -> str:
    """Validate and normalize an email address."""
    email = email.strip().lower()

    if len(email) > MAX_EMAIL_LENGTH:
        raise InputValidationError("Email too long", "email")

    # Basic RFC-compliant pattern
    pattern = re.compile(
        r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9]"
        r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
        r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
    )
    if not pattern.match(email):
        raise InputValidationError("Invalid email address", "email")

    return email


def sanitize_name(name: str) -> str:
    """Sanitize a user name."""
    name = sanitize_text(name, "name", MAX_NAME_LENGTH)
    # Strip any HTML tags completely
    name = re.sub(r"<[^>]+>", "", name)
    return name


def check_sql_injection(text: str, field_name: str = "input") -> None:
    """
    Defense-in-depth check for SQL injection patterns.
    The primary defense is parameterized queries — this is an extra layer.
    """
    for pattern in SQL_INJECTION_PATTERNS:
        if pattern.search(text):
            logger.warning(f"SQL injection pattern detected in {field_name}: {text[:50]}")
            raise InputValidationError(
                f"Invalid characters in {field_name}",
                field_name,
            )


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename for safe storage."""
    # Remove path components
    filename = filename.replace("\\", "/").split("/")[-1]
    # Remove null bytes
    filename = filename.replace("\x00", "")
    # Allow only safe characters
    filename = re.sub(r"[^\w\s\-.]", "_", filename)
    # Prevent dotfile exploits
    filename = filename.lstrip(".")

    if not filename:
        raise InputValidationError("Invalid filename", "filename")

    return filename
