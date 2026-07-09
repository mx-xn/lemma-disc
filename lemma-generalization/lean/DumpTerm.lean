import Lean

open Lean Meta

namespace DumpTerm

/-- Mirrors `schemas/term_tree.schema.json`'s `Term` (`Var | Node | Pi`). -/
inductive Term where
  | var  (index : Nat) (displayName : String)
  | node (head : String) (args : List Term)
  | pi   (displayName : String) (domain : Term) (body : Term) (implicit : Bool)

/-- Mirrors the schema's `Binder`. -/
structure Binder where
  displayName : String
  type : Term
  implicit : Bool

/-- Mirrors the schema's `Statement`. -/
structure Statement where
  binders : List Binder
  body : Term

-- Hand-written (not `deriving`) so field names/kind discriminators match the
-- schema exactly: {"kind": "var"|"node"|"pi", ...}.
partial def Term.toJson : Term → Json
  | .var index displayName =>
    Json.mkObj [("kind", "var"), ("index", Lean.toJson index), ("display_name", displayName)]
  | .node head args =>
    Json.mkObj [("kind", "node"), ("head", head), ("args", Json.arr (args.map Term.toJson).toArray)]
  | .pi displayName domain body implicit =>
    Json.mkObj [
      ("kind", "pi"),
      ("display_name", displayName),
      ("domain", Term.toJson domain),
      ("body", Term.toJson body),
      ("implicit", Lean.toJson implicit),
    ]
instance : ToJson Term := ⟨Term.toJson⟩

def Binder.toJson (b : Binder) : Json :=
  Json.mkObj [
    ("display_name", b.displayName),
    ("type", Term.toJson b.type),
    ("implicit", Lean.toJson b.implicit),
  ]
instance : ToJson Binder := ⟨Binder.toJson⟩

def Statement.toJson (s : Statement) : Json :=
  Json.mkObj [
    ("binders", Json.arr (s.binders.map Binder.toJson).toArray),
    ("body", Term.toJson s.body),
  ]
instance : ToJson Statement := ⟨Statement.toJson⟩

-- Walks `headType` (the applied head's own declared Pi-chain) in lockstep with the
-- full, implicit-inclusive argument list, keeping only the explicit ones. Each step
-- instantiates the Pi-chain's next binder with the argument actually supplied, since
-- later binders' types can depend on earlier explicit/implicit arguments alike.
private partial def keepExplicitArgs (headType : Expr) : List Expr → MetaM (List Expr)
  | [] => pure []
  | a :: rest => do
    let .forallE _ _ body binderInfo := headType
      | throwError "unsupported Expr shape: more arguments than head's Pi-chain provides"
    let restKept ← keepExplicitArgs (body.instantiate1 a) rest
    pure (if binderInfo.isExplicit then a :: restKept else restKept)

/--
Resolves an application spine's head to a fully-qualified constant name and its
*explicit-only* argument list, by peeling the head's own declared Pi-chain in
lockstep with the full (implicit-inclusive) argument list to read off each
position's `BinderInfo`. `throwError`s if the head isn't `Expr.const` (e.g. a bound
variable applied directly) -- out of scope, see CLAUDE.md's out-of-scope carve-outs.
-/
def resolveHeadAndExplicitArgs (e : Expr) : MetaM (Name × List Expr) := do
  let .const name _ := e.getAppFn
    | throwError "unsupported Expr shape: application head is not a global constant: {e.getAppFn}"
  let headType ← inferType e.getAppFn
  let args ← keepExplicitArgs headType e.getAppArgs.toList
  pure (name, args)

/--
The recursive Expr walker. `binderNames` is a stack of display names, innermost
(most-recently-bound) first, so `binderNames[idx]!` names a `bvar idx`. Strips
`Expr.mdata`. `Expr.forallE` here (i.e. NOT at the top of `exprToStatement`'s own
chain) becomes a nested `Term.pi`, not a `Statement.binders` entry -- this is how
a premise like `ih : ∀ (n : Nat), P n` gets represented. `throwError`s on
`Expr.fvar/.sort/.letE/.proj/.mvar/.lam` -- out of scope, see CLAUDE.md.
-/
partial def exprToTerm (binderNames : List String) (e : Expr) : MetaM Term := do
  match e with
  | .mdata _ e' => exprToTerm binderNames e'
  | .bvar idx =>
    let some name := binderNames[idx]?
      | throwError "unsupported Expr shape: bvar index {idx} out of range of binder stack {binderNames}"
    pure (.var idx name)
  | .forallE name domain body binderInfo =>
    let domainTerm ← exprToTerm binderNames domain
    let bodyTerm ← exprToTerm (name.toString :: binderNames) body
    pure (.pi name.toString domainTerm bodyTerm !binderInfo.isExplicit)
  | .app _ _ =>
    let (head, args) ← resolveHeadAndExplicitArgs e
    let argTerms ← args.mapM (exprToTerm binderNames)
    pure (.node head.toString argTerms)
  | .const name _ => pure (.node name.toString [])
  | .lit (.natVal n) => pure (.node (toString n) [])
  | .lit (.strVal s) => pure (.node s [])
  | _ => throwError "unsupported Expr shape: {e}"

/--
Top-level-only peel of `e`'s leading `∀`-chain into `Statement.binders`, converting
each binder's own type via `exprToTerm` (so a nested Pi inside a binder's type is
captured there, not further peeled here); the remaining non-forallE expression
becomes `Statement.body` via `exprToTerm`.
-/
private partial def statementBindersAndBody
    (binderNames : List String) (binders : List Binder) (e : Expr) : MetaM Statement := do
  match e with
  | .forallE name domain body binderInfo =>
    let domainTerm ← exprToTerm binderNames domain
    let binder : Binder :=
      { displayName := name.toString, type := domainTerm, implicit := !binderInfo.isExplicit }
    statementBindersAndBody (name.toString :: binderNames) (binders ++ [binder]) body
  | _ =>
    let bodyTerm ← exprToTerm binderNames e
    pure { binders := binders, body := bodyTerm }

def exprToStatement (e : Expr) : MetaM Statement :=
  statementBindersAndBody [] [] e

/-- Looks up `name`'s declared type in the environment and peels it. -/
def declToStatement (name : Name) : MetaM Statement := do
  let some info := (← getEnv).find? name
    | throwError "no such declaration: {name}"
  exprToStatement info.type

/--
For every constant in the environment whose name starts with `prefix`, sorted for
determinism: prints one JSON line, either `{"decl_name", "statement"}` on success
or `{"decl_name", "error"}` if `declToStatement` throws (message text only, no
category -- see the design discussion: distinguishing "expected out-of-scope shape"
from "DumpTerm bug" is left to a human reading the message, not encoded).
-/
def dumpMatching (namePrefix : String) : MetaM Unit := do
  let env ← getEnv
  let matching := env.constants.toList.filterMap fun (n, _) =>
    if namePrefix.isPrefixOf n.toString then some n else none
  let sorted := matching.toArray.qsort (fun a b => a.toString < b.toString)
  for name in sorted do
    let line ← try
      let stmt ← declToStatement name
      pure (Json.mkObj [("decl_name", name.toString), ("statement", Statement.toJson stmt)])
    catch ex =>
      let msg ← ex.toMessageData.toString
      pure (Json.mkObj [("decl_name", name.toString), ("error", msg)])
    IO.println line.compress

end DumpTerm
