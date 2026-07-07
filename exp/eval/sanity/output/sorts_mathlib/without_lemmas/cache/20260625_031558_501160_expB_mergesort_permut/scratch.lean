import LeanSrc.Sorts_Mathlib

theorem expB_mergesort_permut [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (l : List T) : Permut (mergesort l) l := by
  intro t
  simpa [Permut] using mergesort.permut (l := l) t


/- lean_check result: FAIL
error:
location:
      intro t
      simpa [Permut] using mergesort.permut (l := l) t
                          ^
error: error(lean.unknownIdentifier): Unknown constant `mergesort.permut`
-/
