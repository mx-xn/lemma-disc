import LeanSrc.Sorts_Mathlib

theorem expB_mergesort_correct (T : Type) [Preorder T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : SortCorrect (mergesort : List T -> List T) := by
  simpa [SortCorrect]


/- lean_check result: FAIL
error:
location:
    theorem expB_mergesort_correct (T : Type) [Preorder T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : SortCorrect (mergesort : List T -> List T) := by
      simpa [SortCorrect]
     ^
error: Tactic `assumption` failed
T : Type
inst✝² : Preorder T
inst✝¹ : DecidableEq T
inst✝ : DecidableRel LT.lt
⊢ ∀ (l : List T), Sorted (mergesort l) ∧ Permut (mergesort l) l
-/
