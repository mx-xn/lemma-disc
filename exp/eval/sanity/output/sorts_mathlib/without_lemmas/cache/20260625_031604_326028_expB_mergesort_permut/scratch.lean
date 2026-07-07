import LeanSrc.Sorts_Mathlib

theorem expB_mergesort_permut [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (l : List T) : Permut (mergesort l) l := by
  intro t
  simpa [Permut] using (And.right (mergesort_correct l)) t


/- lean_check result: FAIL
error:
location:
      intro t
      simpa [Permut] using (And.right (mergesort_correct l)) t
                                                        ^
error: Application type mismatch: The argument
  l
has type
  List T
of sort `Type u_1` but is expected to have type
  Type
of sort `Type 1` in the application
  @mergesort_correct l
-/
