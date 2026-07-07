import LeanSrc.Sorts_Mathlib

theorem expB_mergesort_correct (T : Type) [Preorder T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : SortCorrect (mergesort : List T -> List T) := by
  intro l
  exfalso
  contradiction


/- lean_check result: FAIL
error:
location:
      exfalso
      contradiction
     ^
error: Tactic `contradiction` failed
T : Type
inst✝² : Preorder T
inst✝¹ : DecidableEq T
inst✝ : DecidableRel LT.lt
l : List T
⊢ False
-/
