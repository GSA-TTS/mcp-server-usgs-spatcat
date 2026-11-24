"""Shared tool annotations and safe input checks."""

from fastmcp.exceptions import ToolError

READ_ONLY = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}


def unique_ids(values: list[str]) -> list[str]:
    if len(set(values)) != len(values):
        raise ToolError("invalid_input: IDs must be unique.")
    return values
