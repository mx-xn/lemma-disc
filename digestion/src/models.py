from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Hypothesis:
    name: str
    type: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "type": self.type}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Hypothesis:
        return cls(name=d["name"], type=d["type"])


@dataclass
class Obligation:
    hypotheses: list[Hypothesis]
    goal: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "goal": self.goal,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Obligation:
        return cls(
            hypotheses=[Hypothesis.from_dict(h) for h in d["hypotheses"]],
            goal=d["goal"],
        )


@dataclass
class TacticSummary:
    directly_used: list[str]
    # One dict per output branch: maps each h ∈ Γᵢ to its parents in Γ.
    dependency_maps: list[dict[str, list[str]]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "directly_used": self.directly_used,
            "dependency_maps": self.dependency_maps,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TacticSummary:
        return cls(
            directly_used=d["directly_used"],
            dependency_maps=d["dependency_maps"],
        )


@dataclass
class TacticNode:
    id: int
    tactic_text: str
    input_obligation: Obligation
    output_obligations: list[Obligation]
    summary: TacticSummary
    parent_id: int | None
    child_ids: list[int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tactic_text": self.tactic_text,
            "input_obligation": self.input_obligation.to_dict(),
            "output_obligations": [o.to_dict() for o in self.output_obligations],
            "summary": self.summary.to_dict(),
            "parent_id": self.parent_id,
            "child_ids": self.child_ids,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TacticNode:
        return cls(
            id=d["id"],
            tactic_text=d["tactic_text"],
            input_obligation=Obligation.from_dict(d["input_obligation"]),
            output_obligations=[Obligation.from_dict(o) for o in d["output_obligations"]],
            summary=TacticSummary.from_dict(d["summary"]),
            parent_id=d["parent_id"],
            child_ids=d["child_ids"],
        )


@dataclass
class Declaration:
    name: str
    statement: str
    root_tactic_id: int
    tactic_nodes: list[TacticNode]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "statement": self.statement,
            "root_tactic_id": self.root_tactic_id,
            "tactic_nodes": [n.to_dict() for n in self.tactic_nodes],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Declaration:
        return cls(
            name=d["name"],
            statement=d["statement"],
            root_tactic_id=d["root_tactic_id"],
            tactic_nodes=[TacticNode.from_dict(n) for n in d["tactic_nodes"]],
        )


@dataclass
class LeanProofTrace:
    source_file: str
    declarations: list[Declaration]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_file": self.source_file,
            "declarations": [d.to_dict() for d in self.declarations],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> LeanProofTrace:
        return cls(
            source_file=d["source_file"],
            declarations=[Declaration.from_dict(decl) for decl in d["declarations"]],
        )
