import LeanSrc.Sorts_Mathlib

theorem expB_mergesort_permut [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (l : List T) : Permut (mergesort l) l := by
  intro t
  have h := mergesort_correct (T := T) l
  simpa [Permut] using (And.right h) t


/- lean_check result: FAIL
error:
location:
      intro t
      have h := mergesort_correct (T := T) l
                                       ^
      simpa [Permut] using (And.right h) t
error: Application type mismatch: The argument
  T
has type
  Type u_1
of sort `Type (u_1 + 1)` but is expected to have type
  Type
of sort `Type 1` in the application
  @mergesort_correct T
-/
