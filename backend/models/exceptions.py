from backend.models.schemas import SemanticErrorReason

class SemanticException(Exception):
    def __init__(self, reason: SemanticErrorReason, message: str, details: dict = None):
        super().__init__(message)
        self.reason = reason
        self.message = message
        self.details = details or {}
