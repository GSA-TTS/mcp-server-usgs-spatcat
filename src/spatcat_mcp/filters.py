"""Small allowlisted attribute-filter grammar, not an arbitrary SQL executor."""

from __future__ import annotations

import re

from fastmcp.exceptions import ToolError

TOKEN = re.compile(
    r"\s*(?:('[^']*(?:''[^']*)*')|(-?\d+(?:\.\d+)?)|"
    r"([A-Za-z_][A-Za-z0-9_]*)|(<=|>=|<>|!=|=|<|>)|([(),]))"
)
KEYWORDS = {"AND", "OR", "IN", "LIKE", "IS", "NOT", "NULL"}


def validate_where(where: str) -> str:
    """Allow comparisons, IN, LIKE, IS NULL, AND/OR, and bounded grouping."""
    tokens: list[tuple[str, str]] = []
    offset = 0
    while offset < len(where.rstrip()):
        match = TOKEN.match(where, offset)
        if match is None:
            raise ToolError("invalid_filter: Use supported read-only attribute syntax.")
        index = next(i for i, group in enumerate(match.groups()) if group is not None)
        value = match.group(index + 1)
        kind = ("string", "number", "identifier", "operator", "punctuation")[index]
        if kind == "identifier" and value.upper() in KEYWORDS:
            kind, value = "keyword", value.upper()
        tokens.append((kind, value))
        offset = match.end()
    cursor = 0

    def take(value: str) -> bool:
        nonlocal cursor
        if cursor < len(tokens) and tokens[cursor][1] == value:
            cursor += 1
            return True
        return False

    def literal() -> bool:
        nonlocal cursor
        if cursor < len(tokens) and tokens[cursor][0] in {"string", "number"}:
            cursor += 1
            return True
        return False

    def clause(depth: int) -> bool:
        nonlocal cursor
        if depth > 20:
            return False
        if take("("):
            return expression(depth + 1) and take(")")
        if cursor >= len(tokens) or tokens[cursor][0] != "identifier":
            return False
        cursor += 1
        if take("IS"):
            take("NOT")
            return take("NULL")
        negated = take("NOT")
        if take("IN"):
            if not take("(") or not literal():
                return False
            while take(","):
                if not literal():
                    return False
            return take(")")
        if take("LIKE"):
            return literal()
        if negated or cursor >= len(tokens) or tokens[cursor][0] != "operator":
            return False
        cursor += 1
        return literal()

    def expression(depth: int) -> bool:
        if not clause(depth):
            return False
        while take("AND") or take("OR"):
            if not clause(depth):
                return False
        return True

    if not expression(0) or cursor != len(tokens):
        raise ToolError(
            "invalid_filter: Use field comparisons, IN, LIKE, IS NULL, AND/OR, "
            "and parentheses; functions and SQL statements are unsupported."
        )
    return where
