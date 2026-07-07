import LeanSrc.Sorts_Mathlib

theorem expB_mergesort_permut [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (l : List T) : Permut (mergesort l) l := by
  intro t
  have h := mergesort_correct l
  simpa [Permut] using (And.right h) t


/- lean_check result: FAIL
error:
location:
      intro t
      have h := mergesort_correct l
                                 ^
      simpa [Permut] using (And.right h) t
error: Application type mismatch: The argument
  l
has type
  List T
of sort `Type u_1` but is expected to have type
  Type
of sort `Type 1` in the application
  @mergesort_correct l

location:
    
    theorem expB_mergesort_permut [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (l : List T) : Permut (mergesort l) l := by
                                                                                                                                 ^
      intro t
error: unsolved goals
case refine_1
T : Type u_1
inst✝² : LT T
inst✝¹ : DecidableEq T
inst✝ : DecidableRel LT.lt
l : List T
t : T
⊢ Preorder sorry
case refine_2
T : Type u_1
inst✝² : LT T
inst✝¹ : DecidableEq T
inst✝ : DecidableRel LT.lt
l : List T
t : T
⊢ DecidableEq sorry
case refine_3
T : Type u_1
inst✝² : LT T
inst✝¹ : DecidableEq T
inst✝ : DecidableRel LT.lt
l : List T
t : T
⊢ DecidableRel LT.lt
-/
