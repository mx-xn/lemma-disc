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
    cases ih with
    | nil =>
      exact lemma_hint_0 x
    | singleton =>
      by_cases h : x < x_1
      · simp [insert_, h]
        exact Sorted.cons Sorted.singleton h
      · simp [insert_, h]
        exact lemma_hint_1 x x_1 h
    | cons hs hnot =>
      by_cases h : x < a
      · simp [insert_, h]
        exact Sorted.cons (Sorted.cons hs hnot) h
      · simp [insert_, h]
        exact Sorted.cons ih h


/- lean_check result: FAIL
error:
location:
        cases ih with
        | nil =>
       ^
          exact lemma_hint_0 x
error: Dependent elimination failed: Failed to solve equation
  insertionsort xs = []
-/
