from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, eq=False)
class Var:
    index: int
    display_name: str

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Var):
            return NotImplemented
        return self.index == other.index

    def __hash__(self) -> int:
        return hash(("Var", self.index))


@dataclass(frozen=True, eq=False)
class Node:
    head: str
    args: list["Term"]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return NotImplemented
        return self.head == other.head and self.args == other.args

    def __hash__(self) -> int:
        return hash(("Node", self.head, tuple(self.args)))


@dataclass(frozen=True, eq=False)
class Pi:
    display_name: str
    domain: "Term"
    body: "Term"
    implicit: bool

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Pi):
            return NotImplemented
        return (
            self.domain == other.domain
            and self.body == other.body
            and self.implicit == other.implicit
        )

    def __hash__(self) -> int:
        return hash(("Pi", self.domain, self.body, self.implicit))


Term = Var | Node | Pi


@dataclass(frozen=True, eq=False)
class Binder:
    display_name: str
    type: Term
    implicit: bool

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Binder):
            return NotImplemented
        return self.type == other.type and self.implicit == other.implicit

    def __hash__(self) -> int:
        return hash(("Binder", self.type, self.implicit))

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Binder":
        return cls(
            display_name=d["display_name"],
            type=term_from_dict(d["type"]),
            implicit=d["implicit"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "display_name": self.display_name,
            "type": term_to_dict(self.type),
            "implicit": self.implicit,
        }


@dataclass(frozen=True, eq=False)
class Statement:
    binders: list[Binder]
    body: Term

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Statement):
            return NotImplemented
        return self.binders == other.binders and self.body == other.body

    def __hash__(self) -> int:
        return hash(("Statement", tuple(self.binders), self.body))

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Statement":
        return cls(
            binders=[Binder.from_dict(b) for b in d["binders"]],
            body=term_from_dict(d["body"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "binders": [b.to_dict() for b in self.binders],
            "body": term_to_dict(self.body),
        }


def term_from_dict(d: dict[str, Any]) -> Term:
    kind = d["kind"]
    if kind == "var":
        return Var(index=d["index"], display_name=d["display_name"])
    if kind == "node":
        return Node(head=d["head"], args=[term_from_dict(a) for a in d["args"]])
    if kind == "pi":
        return Pi(
            display_name=d["display_name"],
            domain=term_from_dict(d["domain"]),
            body=term_from_dict(d["body"]),
            implicit=d["implicit"],
        )
    raise ValueError(f"unknown term kind: {kind!r}")


def term_to_dict(t: Term) -> dict[str, Any]:
    if isinstance(t, Var):
        return {"kind": "var", "index": t.index, "display_name": t.display_name}
    if isinstance(t, Pi):
        return {
            "kind": "pi",
            "display_name": t.display_name,
            "domain": term_to_dict(t.domain),
            "body": term_to_dict(t.body),
            "implicit": t.implicit,
        }
    return {"kind": "node", "head": t.head, "args": [term_to_dict(a) for a in t.args]}
