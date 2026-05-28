"""Service-safe error contracts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


def _to_json_value(value: Any) -> JsonValue:
    """Normalize values into JSON-safe scalar/list/dict shapes."""
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Mapping):
        return {str(key): _to_json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [_to_json_value(item) for item in value]
    return str(value)


class EngramServiceError(Exception):
    """Base service error with stable machine-readable metadata."""

    code: str
    message: str
    details: dict[str, JsonValue]
    fix: str | None

    def __init__(
        self,
        *,
        code: str,
        message: str,
        details: Mapping[str, Any] | None = None,
        fix: str | None = None,
    ) -> None:
        self.code = str(code)
        self.message = str(message)
        self.details = (
            {str(key): _to_json_value(item) for key, item in details.items()} if details else {}
        )
        self.fix = fix
        super().__init__(self.message)

    def to_dict(self) -> dict[str, object]:
        """Serialize this error into a JSON-safe dictionary."""
        res = {
            "code": self.code,
            "message": self.message,
            "details": dict(self.details),
        }
        if self.fix is not None:
            res["fix"] = self.fix
        return res


class ValidationError(EngramServiceError):
    """Raised when service inputs or parameters fail validation rules."""
