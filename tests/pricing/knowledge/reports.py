"""Typed views of the JSON-like reports the pricing code returns, for tests that index into them.

The pricing functions build plain dicts without annotations, so the checker infers each report as a union of
its literal's value types and rejects nested indexing. These views state what the tests rely on: a report is a
string-keyed record that is present, and its values are JSON-like. They return the same object, never a copy.
"""

from typing import Any


def present(value: dict[str, Any] | None) -> dict[str, Any]:
    """The report a test expects to be present."""
    assert value is not None
    return value


def reports(values: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """The list of reports a test expects to be present."""
    assert values is not None
    return values


def thawed(value: Any) -> dict[str, Any]:
    """A record returned through `thaw`, whose return type covers any JSON value; checks that it is a dict."""
    assert isinstance(value, dict)
    return value


def thawed_records(values: list[Any]) -> list[dict[str, Any]]:
    """Records returned through `thaw`; checks that each is a dict."""
    assert all(isinstance(value, dict) for value in values)
    return values
