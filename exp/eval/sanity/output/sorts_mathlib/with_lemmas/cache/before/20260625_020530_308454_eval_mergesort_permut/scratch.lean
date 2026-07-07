import LeanSrc.Sorts_Mathlib

theorem lemma_hint_0 [DecidableEq T] (l : List T) : Permut l l := by admit
theorem lemma_hint_1 [DecidableEq T] (l : List T) (t' : T) (h1 : count1 l t' = count1 l t') : Permut l l := by admit
theorem lemma_hint_2 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : Permut ([] : List T) [] := by admit
theorem lemma_hint_3 [DecidableEq T] (a : List T) (c : List T) (t' : T) (h1 : count1 a t' = count1 c t') : Permut a c := by admit
theorem lemma_hint_4 [DecidableEq T] (c : List T) (a : List T) (b : List T) (t' : T) (h1 : count1 b t' = count1 c t') : Permut a c := by admit
theorem lemma_hint_5 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) : Permut [e] [e] := by admit
theorem lemma_hint_6 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (t' : T) (h1 : count1 [] t' = count1 [] t') : Permut ([] : List T) [] := by admit
theorem lemma_hint_7 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) : Permut (e :: x :: xs) (e :: x :: xs) := by admit
theorem lemma_hint_8 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (t' : T) (h1 : count1 (e :: x :: xs) t' = count1 (e :: x :: xs) t') : Permut (e :: x :: xs) (e :: x :: xs) := by admit
theorem lemma_hint_9 [DecidableEq T] {a b c : List T} (ab : Permut a b) (bc : Permut b c) : Permut a c := by admit

theorem eval_mergesort_permut [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (l : List T) : Permut (mergesort l) l := by
  unfold Permut
  intro t
  unfold mergesort
  split_ifs <;> rfl


/- lean_check result: FAIL
error:
location:
      unfold mergesort
      split_ifs <;> rfl
                   ^
error: Tactic `rfl` failed: The left-hand side
  count1
    (have this := ⋯;
    have this := ⋯;
    merge (mergesort (left l)) (mergesort (right l)))
    t
is not definitionally equal to the right-hand side
  count1 l t
case neg
T : Type u_1
inst✝² : LT T
inst✝¹ : DecidableEq T
inst✝ : DecidableRel LT.lt
l : List T
t : T
h✝ : ¬l.length < 2
⊢ count1
      (have this := ⋯;
      have this := ⋯;
      merge (mergesort (left l)) (mergesort (right l)))
      t =
    count1 l t
-/
