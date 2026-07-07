import LeanSrc.Sorts_Mathlib

theorem expB_mergesort_sorted [Preorder T] [DecidableRel (LT.lt (α := T))] (l : List T) : Sorted (mergesort l) := by
  by_cases h : l.length < 2
  · simp [mergesort, h]
    cases l with
    | nil =>
        exact Sorted.nil
    | cons x xs =>
        cases xs with
        | nil =>
            exact Sorted.singleton
        | cons y ys =>
            linarith
  · simp [mergesort, h]


/- lean_check result: FAIL
error:
location:
            | cons y ys =>
                linarith
               ^
      · simp [mergesort, h]
error: linarith failed to find a contradiction
case pos.cons.cons
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
x y : T
ys : List T
h : (x :: y :: ys).length < 2
⊢ False
failed

location:
                linarith
      · simp [mergesort, h]
             ^
error: Possibly looping simp theorem: `mergesort.eq_1`
Note: Possibly caused by: `mergesort`
Hint: You can disable a simp theorem from the default simp set by passing `- theoremName` to `simp`.

location:
                linarith
      · simp [mergesort, h]
       ^
error: Tactic `simp` failed with a nested error:
maximum recursion depth has been reached
use `set_option maxRecDepth <num>` to increase limit
use `set_option diagnostics true` to get diagnostic information
-/
