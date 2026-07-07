import LeanSrc.Sorts_Mathlib

theorem lemma_hint_0 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) : Sorted (insert_ t []) := by admit
theorem lemma_hint_1 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) (x : T) (p : ¬t < x) : Sorted (x :: insert_ t []) := by admit
theorem lemma_hint_2 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (t : T) (h1 : count1 (x :: insertionsort xs) t = count1 (x :: xs) t) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_3 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h1 : ∀ (t : T), count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_4 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (t : T) (h1 : count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_5 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (t : T) (h1 : (if x = t then 1 else 0) + count1 (insertionsort xs) t = (if x = t then 1 else 0) + count1 xs t) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_6 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (t : T) (h1 : (if x = t then 1 else 0) + count1 (insertionsort xs) t = (if x = t then 1 else 0) + count1 xs t) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_7 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (h1 : ∀ (t : T), count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_8 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_9 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit

theorem eval_insertionsort_sorted [Preorder T] [DecidableRel (LT.lt (α := T))] {l : List T} : Sorted (insertionsort l) := by
  induction l with
  | nil =>
    exact Sorted.nil
  | cons x xs ih =>
    simp [insertionsort]
    generalize hsort : insertionsort xs = ys
    have hs : Sorted ys := by simpa [hsort] using ih
    revert hsort
    cases hs with
    | nil =>
      intro hsort
      exact lemma_hint_0 x
    | singleton (y := y) =>
      intro hsort
      by_cases h : x < y
      · simp [insert_, h]
        exact Sorted.cons Sorted.singleton h
      · simp [insert_, h]
        exact lemma_hint_1 x y h
    | cons (a := a) (b := b) (xs := zs) hs' hnot =>
      intro hsort
      by_cases h : x < a
      · simp [insert_, h]
        exact Sorted.cons (Sorted.cons hs' hnot) h
      · simp [insert_, h]
        exact Sorted.cons (Sorted.cons hs' hnot) h


/- lean_check result: FAIL
error:
location:
        revert hsort
        cases hs with
       ^
        | nil =>
error: Alternative `cons` has not been provided

location:
        exact Sorted.nil
      | cons x xs ih =>
                    ^
        simp [insertionsort]
error: unsolved goals
case cons.singleton
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
x : T
xs : List T
ih : Sorted (insertionsort xs)
x✝ : T
⊢ insertionsort xs = [x✝] → Sorted (insert_ x [x✝])

location:
          exact lemma_hint_0 x
        | singleton (y := y) =>
                   ^
          intro hsort
error: unexpected token '('; expected command
-/
