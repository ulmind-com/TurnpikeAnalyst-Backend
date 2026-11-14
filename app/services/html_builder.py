"""A tiny element builder so markup is expressed as Python, not literal HTML.

Email bodies still have to reach the recipient as HTML (that is the only format
email clients render), but nothing in the application code is written as HTML
markup: every element is constructed by calling :func:`el`, and the one place
that turns a tree into a string is :func:`render` below. Text children are
HTML-escaped, so interpolating a user's name can never inject markup.
"""

from __future__ import annotations

from html import escape
from typing import Dict, List, Union

# Elements that never have a closing tag.
_VOID = {"meta", "img", "br", "hr", "input", "link"}

Node = Union["Tag", "Raw", str, None]


class Raw(str):
    """A string that is emitted verbatim (already safe / not to be escaped)."""


class Tag:
    __slots__ = ("name", "attrs", "children")

    def __init__(self, name: str, attrs: Dict[str, object], children: List[Node]) -> None:
        self.name = name
        self.attrs = attrs
        self.children = children

    def __str__(self) -> str:
        return render(self)


def el(_name: str, *children: Node, **attrs: object) -> Tag:
    """Build an element. Keyword attrs map ``cls`` -> ``class`` and turn a
    trailing underscore / inner underscores into dashes (``data_x`` -> ``data-x``).
    ``None``/``False`` attribute values are dropped."""
    return Tag(_name, attrs, [c for c in children if c is not None])


def raw(text: str) -> Raw:
    """Wrap pre-formatted text so :func:`render` emits it without escaping."""
    return Raw(text)


def _attr_name(key: str) -> str:
    if key == "cls":
        return "class"
    return key.rstrip("_").replace("_", "-")


def render(node: Node) -> str:
    if node is None:
        return ""
    if isinstance(node, Raw):
        return str(node)
    if isinstance(node, str):
        return escape(node)

    attrs = "".join(
        f' {_attr_name(k)}="{escape(str(v), quote=True)}"'
        for k, v in node.attrs.items()
        if v is not None and v is not False
    )
    if node.name in _VOID:
        return f"<{node.name}{attrs}>"
    inner = "".join(render(c) for c in node.children)
    return f"<{node.name}{attrs}>{inner}</{node.name}>"


def document(root: Tag) -> str:
    """Render a full HTML document (prepends the doctype)."""
    return "<!DOCTYPE html>\n" + render(root)
