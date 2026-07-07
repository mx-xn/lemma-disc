import LeanSrc.Sorts_Mathlib

theorem expB_mergesort_sorted [Preorder T] [DecidableRel (LT.lt (α := T))] (l : List T) : Sorted (mergesort l) := by
  by_cases h : l.length < 2
  · cases l with
    | nil =>
        exact Sorted.nil
    | cons x xs =>
        cases xs with
        | nil =>
            exact Sorted.singleton
        | cons y ys =>
            simp at h
  · simpa [mergesort, h]


/- lean_check result: FAIL
error:
location:
        | nil =>
            exact Sorted.nil
                 ^
        | cons x xs =>
error: typeclass instance problem is stuck
  LT ?m.46
Note: Lean will not try to resolve this typeclass instance problem because the type argument to `LT` is a metavariable. This argument must be fully determined before Lean will try to resolve the typeclass.
Hint: Adding type annotations and supplying implicit arguments to functions can give Lean more information for typeclass resolution. For example, if you have a variable `x` that you intend to be a `Nat`, but Lean reports it as having an unresolved type like `?m`, replacing `x` with `(x : Nat)` can get typeclass resolution un-stuck.

location:
            | nil =>
                exact Sorted.singleton
               ^
            | cons y ys =>
error: Type mismatch
  Sorted.singleton
has type
  Sorted [?m.83]
but is expected to have type
  Sorted (mergesort [x])

location:
                exact Sorted.singleton
            | cons y ys =>
                       ^
                simp at h
error: unsolved goals
case pos.cons.cons
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
x y : T
ys : List T
h : ys.length + 1 + 1 < 2
⊢ Sorted (mergesort (x :: y :: ys))

location:
                simp at h
      · simpa [mergesort, h]
       ^
error: Tactic `simp` failed with a nested error:
maximum recursion depth has been reached
use `set_option maxRecDepth <num>` to increase limit
use `set_option diagnostics true` to get diagnostic information
-/
