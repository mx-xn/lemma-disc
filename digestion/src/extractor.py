from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from pathlib import Path

# Load .env before lean_dojo imports — they check GITHUB_ACCESS_TOKEN at import time.
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

import jsonschema
from lean_dojo_v2.lean_dojo.data_extraction.ast import IdentNode
from lean_dojo_v2.lean_dojo.data_extraction.traced_data import TracedRepo, TracedTactic

from digestion.models import (
    Declaration,
    Hypothesis,
    LeanProofTrace,
    Obligation,
    TacticNode,
    TacticSummary,
)
from digestion.tracer import trace_github_repo, trace_local_repo

_SCHEMA_PATH = Path(__file__).parent.parent.parent / "schemas" / "trace.schema.json"

# Tactics that implicitly consume every hypothesis in the local context.
_CONSUME_ALL_RE = re.compile(
    r"\bsimp_all\b"
    r"|\bassumption\b"
    r"|\btrivial\b"
    r"|\btauto\b"
    r"|\baesop\b"
    r"|\bomega\b"
    r"|simp\s*\[[^\]]*\*"  # simp [*, ...]
)

# Lean identifier continuation characters that Python's \w misses:
# subscript digits (₀–₉) and single-quote used in names like h₁ or h'.
_LEAN_ID_BOUNDARY = r"(?<![A-Za-z0-9_₀-₉'])"
_LEAN_ID_BOUNDARY_END = r"(?![A-Za-z0-9_₀-₉'])"

# Matches `T1 <;> T2` (non-greedy on T1 so `a <;> b <;> c` parses as T1=a, T2=`b <;> c`).
_SEMICOLON_RE = re.compile(r"^(.+?)\s+<;>\s+(.+)$", re.DOTALL)


# ---------------------------------------------------------------------------
# Proof-state parsing
# ---------------------------------------------------------------------------

# Lean's proof state prints let-bound hypotheses as `h : T := <value>` (and sometimes
# `h : T :=` when the value is elided). We only care about the type; the body is
# dropped. The leading whitespace requirement avoids over-eagerly stripping `:=`
# tokens that might appear glued inside notation (e.g. `{a:=5}`).
_LET_BODY_RE = re.compile(r"\s+:=.*$", re.DOTALL)


def _parse_obligations(state: str) -> list[Obligation]:
    if not state or state.strip() in ("", "no goals"):
        return []
    blocks = re.split(r"\n\n+", state.strip())
    result: list[Obligation] = []
    for block in blocks:
        hyps: list[Hypothesis] = []
        goal = ""
        for line in block.splitlines():
            s = line.strip()
            if s.startswith("⊢ "):  # ⊢
                goal = s[2:].strip()
            elif " : " in s and not s.startswith("⊢"):
                name, _, typ = s.partition(" : ")
                typ = _LET_BODY_RE.sub("", typ).strip()
                for n in name.split():
                    hyps.append(Hypothesis(name=n, type=typ))
        if goal:
            result.append(Obligation(hypotheses=hyps, goal=goal))
    return result


# ---------------------------------------------------------------------------
# Tactic summary (U and π)
# ---------------------------------------------------------------------------

def _compute_U(tt: TracedTactic, hyp_names: set[str]) -> list[str]:
    if not hyp_names:
        return []
    if _CONSUME_ALL_RE.search(tt.tactic):
        return sorted(hyp_names)

    used: set[str] = set()

    def _collect(node, _) -> None:
        if isinstance(node, IdentNode) and node.full_name is None and node.val in hyp_names:
            used.add(node.val)

    tt.ast.traverse_preorder(_collect, node_cls=None)

    # Regex fallback for references missed by AST (e.g. dot-notation h.subset).
    # Sort longest-first so that h₁ is checked before h; the Lean-aware boundary
    # guards against \b false-positives on subscript digits and primes.
    for name in sorted(hyp_names - used, key=len, reverse=True):
        pat = _LEAN_ID_BOUNDARY + re.escape(name) + _LEAN_ID_BOUNDARY_END
        if re.search(pat, tt.tactic):
            used.add(name)

    return sorted(used)


def _compute_pi(
    input_hyps: list[Hypothesis],
    output_hyps: list[Hypothesis],
    U: list[str],
) -> dict[str, list[str]]:
    input_by_name = {h.name: h.type for h in input_hyps}
    input_names = set(input_by_name)
    result: dict[str, list[str]] = {}
    for h in output_hyps:
        if h.name in input_by_name and h.type == input_by_name[h.name]:
            result[h.name] = [h.name]  # pass-through
        else:
            # New hypothesis: infer parents from its type string.
            parents = [
                n for n in input_names
                if re.search(r"\b" + re.escape(n) + r"\b", h.type)
            ]
            result[h.name] = parents if parents else list(U)
    return result


# ---------------------------------------------------------------------------
# <;> combinator decomposition
# ---------------------------------------------------------------------------

def _split_connective(goal: str, op: str) -> tuple[str, str] | None:
    """Split goal at the first top-level occurrence of binary operator op.

    Returns (left, right) with whitespace stripped, or None if not found.
    Tracks parenthesis/bracket depth so connectives inside sub-expressions
    are not mistaken for the top-level one.
    """
    depth = 0
    span = len(op) + 2  # " op "
    for i, ch in enumerate(goal):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif depth == 0 and goal[i:i + span] == f" {op} ":
            left = goal[:i].strip()
            right = goal[i + span:].strip()
            if left and right:
                return left, right
    return None


def _infer_constructor_subgoals(in_obl: Obligation) -> list[Obligation] | None:
    """Infer the output obligations produced by `constructor` on in_obl.

    Handles:
      A ∧ B  → [⊢ A, ⊢ B]
      A ↔ B  → [⊢ A → B, ⊢ B → A]

    Returns None for goal shapes where inference is not supported.
    The hypotheses are identical in every subgoal (constructor doesn't
    introduce or consume hypotheses).
    """
    hyps = in_obl.hypotheses
    pair = _split_connective(in_obl.goal, "∧")
    if pair:
        a, b = pair
        return [Obligation(hypotheses=hyps, goal=a), Obligation(hypotheses=hyps, goal=b)]
    pair = _split_connective(in_obl.goal, "↔")
    if pair:
        a, b = pair
        return [
            Obligation(hypotheses=hyps, goal=f"{a} → {b}"),
            Obligation(hypotheses=hyps, goal=f"{b} → {a}"),
        ]
    return None


def _expand_semicolons(nodes: list[TacticNode]) -> list[TacticNode]:
    """Post-process the node list to expand `T1 <;> T2` leaf nodes.

    For each node whose tactic_text matches `T1 <;> T2` and whose subgoals
    can be inferred from T1 + the input obligation:
      - The node is rewritten as T1 with child_ids pointing to new T2 leaves.
      - One T2 leaf is created per inferred subgoal.

    New leaf IDs are assigned above the current maximum so DFS pre-order
    (root id < all descendant ids) is preserved.

    Falls back to the original single node for any pattern we cannot handle.
    """
    if not nodes:
        return nodes

    next_id = max(n.id for n in nodes) + 1
    rewritten: dict[int, TacticNode] = {n.id: n for n in nodes}
    new_nodes: list[TacticNode] = []

    for node in nodes:
        m = _SEMICOLON_RE.match(node.tactic_text)
        if not m:
            continue
        t1, t2 = m.group(1).strip(), m.group(2).strip()

        # Only expand when T1 is `constructor` and subgoals can be inferred.
        if t1 != "constructor":
            continue
        # Skip if _build_tree already attached children (shouldn't happen with
        # LeanDojo, but guard against it).
        if node.child_ids or node.output_obligations:
            continue

        subgoals = _infer_constructor_subgoals(node.input_obligation)
        if subgoals is None:
            continue

        # Build one T2 leaf per subgoal.
        child_ids: list[int] = []
        for sg in subgoals:
            cid = next_id
            next_id += 1
            # For `assumption`-family tactics: find the specific hypothesis
            # whose type matches the subgoal.  Fall back to all hyps if none.
            if _CONSUME_ALL_RE.search(t2):
                match = next(
                    (h.name for h in sg.hypotheses if h.type.strip() == sg.goal.strip()),
                    None,
                )
                u = [match] if match else sorted({h.name for h in sg.hypotheses})
            else:
                u = []
            new_nodes.append(TacticNode(
                id=cid,
                tactic_text=t2,
                input_obligation=sg,
                output_obligations=[],
                summary=TacticSummary(directly_used=u, dependency_maps=[]),
                parent_id=node.id,
                child_ids=[],
            ))
            child_ids.append(cid)

        # Rewrite the <;> node to represent T1 alone.
        # `constructor` operates purely on the goal; it doesn't reference hypotheses.
        dep_maps = [_compute_pi(node.input_obligation.hypotheses, sg.hypotheses, [])
                    for sg in subgoals]
        rewritten[node.id] = TacticNode(
            id=node.id,
            tactic_text=t1,
            input_obligation=node.input_obligation,
            output_obligations=subgoals,
            summary=TacticSummary(directly_used=[], dependency_maps=dep_maps),
            parent_id=node.parent_id,
            child_ids=child_ids,
        )

    return sorted(rewritten.values(), key=lambda n: n.id) + new_nodes


# ---------------------------------------------------------------------------
# Tree reconstruction
# ---------------------------------------------------------------------------

def _strip_arm_bodies(text: str) -> str:
    """Replace arm bodies in compound tactics with _*_, keeping arm headers."""
    lines = text.splitlines()
    result = []
    skip_until_indent: int | None = None

    for line in lines:
        if not line.strip():
            result.append(line)
            continue
        indent = len(line) - len(line.lstrip())
        if skip_until_indent is not None:
            if indent > skip_until_indent:
                continue
            skip_until_indent = None

        # Replace body of each '| arm => body' occurrence in the line.
        # Handles arms both at the start of a line and inline (e.g. after `cases … with`).
        new_line = re.sub(r'(\|[^|=>]*=>\s*)([^|]+)',
                          lambda m: m.group(1) + '_*_', line)
        if new_line != line:
            result.append(new_line)
        elif re.search(r'\|[^|=>]*=>\s*$', line.rstrip()):
            # Arm header with body on following indented lines.
            result.append(re.sub(r'(\|[^|=>]*=>\s*)$',
                                  lambda m: m.group(1).rstrip() + ' _*_', line.rstrip()))
            skip_until_indent = indent
        else:
            result.append(line)

    return '\n'.join(result)


def _is_cdot(tt: TracedTactic) -> bool:
    """Return True for Lean.cdot (·) focus tactics — structural, not semantic."""
    return tt.tactic.lstrip().startswith("·")


def _obligations_match(o1: Obligation, o2: Obligation) -> bool:
    if o1.goal != o2.goal or len(o1.hypotheses) != len(o2.hypotheses):
        return False
    return all(
        h1.name == h2.name and h1.type == h2.type
        for h1, h2 in zip(o1.hypotheses, o2.hypotheses)
    )


def _subtract_leftover(
    after: list[Obligation], leftover: list[Obligation]
) -> list[Obligation]:
    """Multiset difference: return after-obligations that aren't in leftover.

    Lean's `state_after` for a non-focusing tactic prints both the goals
    introduced by the tactic AND the unhandled goals already pending from
    earlier tactics ("leftover").  Each leftover removes one matching
    after-obligation; what remains is what the tactic genuinely produced.
    """
    consumed = [False] * len(leftover)
    result: list[Obligation] = []
    for obl in after:
        matched = False
        for k, lo in enumerate(leftover):
            if not consumed[k] and _obligations_match(obl, lo):
                consumed[k] = True
                matched = True
                break
        if not matched:
            result.append(obl)
    return result


def _contains(outer: TracedTactic, inner: TracedTactic) -> bool:
    os_, oe = outer.start, outer.end
    is_, ie = inner.start, inner.end
    if os_ is None or oe is None or is_ is None or ie is None:
        return False
    return os_ <= is_ and ie <= oe and (os_, oe) != (is_, ie)


def _build_tree(tactics: list[TracedTactic]) -> list[TacticNode]:
    if not tactics:
        return []

    # Filter out Lean.cdot (·) tactics — they are structural focus combinators,
    # not semantic proof steps.  Keeping them breaks parent/child assignment
    # because constructor's span covers only its own keyword, not the · branches,
    # so the span-based stack would orphan the inner branch tactics.
    tactics = [tt for tt in tactics if not _is_cdot(tt)]
    if not tactics:
        return []

    n = len(tactics)
    parent_ids: list[int | None] = [None] * n
    children: list[list[int]] = [[] for _ in range(n)]

    # Stack of indices of open ancestors in DFS pre-order.
    stack: list[int] = []
    for i, tt in enumerate(tactics):
        while stack and not _contains(tactics[stack[-1]], tt):
            stack.pop()
        if stack:
            parent_ids[i] = stack[-1]
            children[stack[-1]].append(i)
        stack.append(i)

    root_indices = [i for i in range(n) if parent_ids[i] is None]

    # Pass 1 — multi-branch matching.
    # A tactic with N > 1 output obligations (e.g. constructor, apply And.intro)
    # opens N parallel branches.  After cdot-filtering those branches show up as
    # orphan roots whose state_before matches one of the N output obligations.
    # Find them by proof-state matching and make them direct children.
    already_matched: set[int] = set()
    for idx, ri in enumerate(root_indices):
        out_obls = _parse_obligations(tactics[ri].state_after)
        if len(out_obls) <= 1:
            continue
        matched: list[int | None] = [None] * len(out_obls)
        for k, obl in enumerate(out_obls):
            for rj in root_indices[idx + 1:]:
                if rj in already_matched or parent_ids[rj] is not None:
                    continue
                in_obls = _parse_obligations(tactics[rj].state_before)
                if in_obls and _obligations_match(in_obls[0], obl):
                    matched[k] = rj
                    already_matched.add(rj)
                    break
        for rj in matched:
            if rj is not None:
                parent_ids[rj] = ri
                children[ri].append(rj)

    # Pass 2 — sequential chaining.
    # Remaining roots with a single pending obligation chain to the next root,
    # unless that root was already attached in pass 1.
    for j in range(len(root_indices) - 1):
        ri, ri_next = root_indices[j], root_indices[j + 1]
        if parent_ids[ri_next] is not None:
            continue
        if _parse_obligations(tactics[ri].state_after):
            parent_ids[ri_next] = ri
            children[ri].append(ri_next)

    # Pass 3 — goal-stack re-parenting within each parent's children group.
    # Compound tactics like `cases … with | arm => tac1; tac2; tac3; tac4`
    # produce arm-local sequential tactics as flat siblings under the compound
    # parent.  When `tac1` opens N>1 goals (e.g. via `constructor`), `tac2`
    # focuses on goal 0, `tac3` on whatever follows, and `tac4` may close a
    # later goal that originated several tactics back — not from `tac3`'s
    # output.  Naive sequential chaining fails because Lean prints all pending
    # goals in `state_after`, including leftovers, so a closed-goal tactic
    # appears to "produce" the next pending goal.
    #
    # Algorithm: simulate Lean's goal stack across the group.
    #   open_goals[0] is the focused goal; entries are (producer_idx, obligation).
    #   For each tactic ci:
    #     1. Match ci.state_before[0] against open_goals; the matching producer
    #        becomes ci's parent.  (Forward search prefers the focused goal.)
    #     2. Replace the matched obligation with ci's NEW outputs
    #        (state_after minus state_before[1:] leftover) at the same position.
    #   Tactics whose match falls back to parent_idx stay direct children of it;
    #   tactics matching a sibling are re-parented to that sibling.
    def _apply_chain_tips(parent_idx: int) -> None:
        grp = children[parent_idx]
        if len(grp) <= 1:
            return

        open_goals: list[tuple[int, Obligation]] = []
        new_grp: list[int] = []

        for ci in grp:
            in_obls = _parse_obligations(tactics[ci].state_before)
            if not in_obls:
                new_grp.append(ci)
                continue
            focused = in_obls[0]
            leftover = in_obls[1:]

            match_idx: int | None = None
            for k in range(len(open_goals)):
                if _obligations_match(focused, open_goals[k][1]):
                    match_idx = k
                    break

            all_after = _parse_obligations(tactics[ci].state_after)
            new_outputs = _subtract_leftover(all_after, leftover)

            if match_idx is None:
                # No tracked producer for this focused goal — it's a parent
                # obligation handled directly.  Seed any leftover not already
                # in open_goals as parent obligations so later siblings can
                # match against them.
                for obl in leftover:
                    if not any(_obligations_match(obl, o) for _, o in open_goals):
                        open_goals.append((parent_idx, obl))
                new_grp.append(ci)
                insert_at = 0
            else:
                producer = open_goals[match_idx][0]
                if producer == parent_idx:
                    new_grp.append(ci)
                else:
                    parent_ids[ci] = producer
                    children[producer].append(ci)
                open_goals.pop(match_idx)
                insert_at = match_idx

            for j, obl in enumerate(new_outputs):
                open_goals.insert(insert_at + j, (ci, obl))

        children[parent_idx][:] = new_grp

    for i in range(n):
        _apply_chain_tips(i)

    nodes: list[TacticNode] = []
    for i, tt in enumerate(tactics):
        in_obls = _parse_obligations(tt.state_before)
        in_obl = in_obls[0] if in_obls else Obligation(hypotheses=[], goal="")
        # Filter out leftover goals: state_after typically lists all pending
        # goals (focused-then-others), but this tactic only "owns" the goals
        # it actually introduced — i.e. state_after \ state_before[1:].
        all_after = _parse_obligations(tt.state_after)
        out_obls = _subtract_leftover(all_after, in_obls[1:])

        direct_children = children[i]
        # Compound tactics (induction, cases, …) report "no goals" in state_after
        # because the full block closes the goal.  Recover per-branch obligations
        # from the direct children's state_before instead.
        is_compound = not out_obls and bool(direct_children)
        if is_compound:
            out_obls = [
                next(iter(_parse_obligations(tactics[c].state_before)),
                     Obligation(hypotheses=[], goal=""))
                for c in direct_children
            ]

        hyp_names = {h.name for h in in_obl.hypotheses}
        U = _compute_U(tt, hyp_names)
        dep_maps = [_compute_pi(in_obl.hypotheses, o.hypotheses, U) for o in out_obls]

        tactic_text = _strip_arm_bodies(tt.tactic) if is_compound else tt.tactic
        child_ids = direct_children[: len(out_obls)]

        nodes.append(TacticNode(
            id=i,
            tactic_text=tactic_text,
            input_obligation=in_obl,
            output_obligations=out_obls,
            summary=TacticSummary(directly_used=U, dependency_maps=dep_maps),
            parent_id=parent_ids[i],
            child_ids=child_ids,
        ))

    return _expand_semicolons(nodes)


# ---------------------------------------------------------------------------
# Top-level extraction
# ---------------------------------------------------------------------------

def extract(
    traced_repo: TracedRepo,
    files: list[str] | None = None,
) -> list[LeanProofTrace]:
    schema = json.loads(_SCHEMA_PATH.read_text())
    by_file: dict[str, list[Declaration]] = defaultdict(list)
    file_filter: set[str] | None = set(files) if files else None

    for thm in traced_repo.get_traced_theorems():
        if file_filter is not None and str(thm.theorem.file_path) not in file_filter:
            continue
        if not thm.has_tactic_proof():
            continue
        tactics = thm.get_traced_tactics(atomic_only=False)
        if not tactics:
            continue

        nodes = _build_tree(tactics)
        decl = Declaration(
            name=thm.theorem.full_name,
            statement=thm.get_theorem_statement(),
            root_tactic_id=nodes[0].id,
            tactic_nodes=nodes,
        )
        by_file[str(thm.theorem.file_path)].append(decl)

    traces: list[LeanProofTrace] = []
    for source_file, decls in by_file.items():
        trace = LeanProofTrace(source_file=source_file, declarations=decls)
        jsonschema.validate(trace.to_dict(), schema)
        traces.append(trace)

    return traces


def write_traces(traces: list[LeanProofTrace], repo_name: str, out_dir: Path) -> None:
    dest = out_dir / repo_name
    dest.mkdir(parents=True, exist_ok=True)
    for trace in traces:
        stem = Path(trace.source_file).stem
        out_path = dest / f"{stem}.json"
        out_path.write_text(json.dumps(trace.to_dict(), indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Extract proof traces from a Lean 4 repo.")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--local", metavar="PATH", help="Path to a local git repo.")
    src.add_argument("--github", nargs=2, metavar=("URL", "COMMIT"),
                     help="GitHub repo URL and commit hash.")
    parser.add_argument(
        "--out-dir",
        metavar="DIR",
        default=str(Path(__file__).parent.parent.parent / "data" / "traces"),
        help="Output directory for trace JSON files (default: data/traces/).",
    )
    parser.add_argument(
        "--files",
        metavar="FILE",
        nargs="+",
        help="Only extract traces for these source files (paths relative to repo root).",
    )
    args = parser.parse_args()

    if args.local:
        traced_repo = trace_local_repo(args.local)
    else:
        url, commit = args.github
        traced_repo = trace_github_repo(url, commit)

    traces = extract(traced_repo, files=args.files)
    write_traces(traces, traced_repo.name, Path(args.out_dir))
    print(f"Wrote {len(traces)} trace file(s) to {args.out_dir}/{traced_repo.name}/")


if __name__ == "__main__":
    main()
