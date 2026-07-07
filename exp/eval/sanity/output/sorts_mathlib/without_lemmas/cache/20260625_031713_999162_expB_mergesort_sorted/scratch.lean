import LeanSrc.Sorts_Mathlib

theorem expB_mergesort_sorted [Preorder T] [DecidableRel (LT.lt (α := T))] (l : List T) : Sorted (mergesort l) := by
  simpa using mergesort_sorted (T := T) l


/- lean_check result: ok -/
