import LeanSrc.Sorts_Mathlib

theorem expB_mergesort_sorted [Preorder T] [DecidableRel (LT.lt (α := T))] (l : List T) : Sorted (mergesort l) := by
  induction l using mergesort.induct with
  | case1 =>
      simp [mergesort, Sorted.nil]
  | case2 x =>
      simp [mergesort, Sorted.singleton]
  | case3 l h₁ h₂ ih₁ ih₂ =>
      simp [mergesort, h₁, ih₁, ih₂]


/- lean_check result: FAIL
error:
location:
          simp [mergesort, Sorted.singleton]
      | case3 l h₁ h₂ ih₁ ih₂ =>
     ^
          simp [mergesort, h₁, ih₁, ih₂]
error: Invalid alternative name `case3`: There are no unhandled alternatives

location:
      | case1 =>
          simp [mergesort, Sorted.nil]
               ^
      | case2 x =>
error: Possibly looping simp theorem: `mergesort.eq_1`
Note: Possibly caused by: `mergesort`
Hint: You can disable a simp theorem from the default simp set by passing `- theoremName` to `simp`.

location:
      | case1 =>
          simp [mergesort, Sorted.nil]
         ^
      | case2 x =>
error: Tactic `simp` failed with a nested error:
maximum recursion depth has been reached
use `set_option maxRecDepth <num>` to increase limit
use `set_option diagnostics true` to get diagnostic information

location:
      | case2 x =>
          simp [mergesort, Sorted.singleton]
               ^
      | case3 l h₁ h₂ ih₁ ih₂ =>
error: Possibly looping simp theorem: `mergesort.eq_1`
Note: Possibly caused by: `mergesort`
Hint: You can disable a simp theorem from the default simp set by passing `- theoremName` to `simp`.

location:
      | case2 x =>
          simp [mergesort, Sorted.singleton]
         ^
      | case3 l h₁ h₂ ih₁ ih₂ =>
error: Tactic `simp` failed with a nested error:
maximum recursion depth has been reached
use `set_option maxRecDepth <num>` to increase limit
use `set_option diagnostics true` to get diagnostic information
-/
