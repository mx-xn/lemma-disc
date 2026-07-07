import LeanSrc.Sorts_Mathlib

theorem lemma_hint_0 [DecidableEq T] {a b c : List T} (ab : Permut a b) (bc : Permut b c) : Permut a c := by admit
theorem lemma_hint_1 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (t' : T) (h1 : count1 [e] t' = count1 [e] t') : Permut [e] [e] := by admit
theorem lemma_hint_2 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) : Permut [e] [e] := by admit
theorem lemma_hint_3 [DecidableEq T] (l : List T) : Permut l l := by admit
theorem lemma_hint_4 [DecidableEq T] (c : List T) (a : List T) (b : List T) (t' : T) (h1 : count1 b t' = count1 c t') : Permut a c := by admit
theorem lemma_hint_5 [DecidableEq T] (a : List T) (c : List T) (t' : T) (h1 : count1 a t' = count1 c t') : Permut a c := by admit
theorem lemma_hint_6 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) : Permut (e :: x :: xs) (e :: x :: xs) := by admit
theorem lemma_hint_7 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (t' : T) (h1 : count1 (e :: x :: xs) t' = count1 (e :: x :: xs) t') : Permut (e :: x :: xs) (e :: x :: xs) := by admit
theorem lemma_hint_8 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (h1 : ∀ (t : T), count1 [e] t = count1 [e] t) : Permut (insert_ e []) [e] := by admit
theorem lemma_hint_9 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (t' : T) (h1 : count1 [e] t' = count1 [e] t') : Permut (insert_ e []) [e] := by admit

theorem eval_Permut.symm [DecidableEq T] {l m : List T} (p : Permut l m) : Permut m l := by
  intro t
  symm
  exact p t


/- lean_check result: ok -/
