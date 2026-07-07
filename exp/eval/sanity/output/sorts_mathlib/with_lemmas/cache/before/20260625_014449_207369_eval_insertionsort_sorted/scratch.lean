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
    | singleton =>
      intro hsort
      by_cases h : x < x_1
      · simp [insert_, h]
        exact Sorted.cons Sorted.singleton h
      · simp [insert_, h]
        exact lemma_hint_1 x x_1 h
    | cons hs' hnot =>
      intro hsort
      by_cases h : x < a
      · simp [insert_, h]
        exact Sorted.cons (Sorted.cons hs' hnot) h
      · simp [insert_, h]
        exact Sorted.cons (Sorted.cons hs' hnot) h


/- lean_check result: FAIL
error:
location:
          intro hsort
          by_cases h : x < x_1
                          ^
          · simp [insert_, h]
error: error(lean.unknownIdentifier): Unknown identifier `x_1`

location:
          · simp [insert_, h]
            exact lemma_hint_1 x x_1 h
                                ^
        | cons hs' hnot =>
error: error(lean.unknownIdentifier): Unknown identifier `x_1`

location:
          intro hsort
          by_cases h : x < a
                          ^
          · simp [insert_, h]
error: error(lean.unknownIdentifier): Unknown identifier `a`

location:
          by_cases h : x < x_1
          · simp [insert_, h]
                          ^
            exact Sorted.cons Sorted.singleton h
error: This simp argument is unused:
  h
Hint: Omit it from the simp argument list.
  simp [insert_,̵ ̵h̵]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
            exact Sorted.cons Sorted.singleton h
          · simp [insert_, h]
                          ^
            exact lemma_hint_1 x x_1 h
error: This simp argument is unused:
  h
Hint: Omit it from the simp argument list.
  simp [insert_,̵ ̵h̵]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
          by_cases h : x < a
          · simp [insert_, h]
                          ^
            exact Sorted.cons (Sorted.cons hs' hnot) h
error: This simp argument is unused:
  h
Hint: Omit it from the simp argument list.
  simp [insert_,̵ ̵h̵]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
            exact Sorted.cons (Sorted.cons hs' hnot) h
          · simp [insert_, h]
                          ^
            exact Sorted.cons (Sorted.cons hs' hnot) h
error: This simp argument is unused:
  h
Hint: Omit it from the simp argument list.
  simp [insert_,̵ ̵h̵]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`
-/
