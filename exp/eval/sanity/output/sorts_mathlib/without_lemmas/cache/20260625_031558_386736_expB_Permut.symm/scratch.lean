import LeanSrc.Sorts_Mathlib

theorem expB_Permut.symm [DecidableEq T] {l m : List T} (p : Permut l m) : Permut m l := by
  intro t
  symm
  exact p t


/- lean_check result: ok -/
