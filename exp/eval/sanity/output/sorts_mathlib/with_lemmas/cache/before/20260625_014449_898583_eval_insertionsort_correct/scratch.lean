import LeanSrc.Sorts_Mathlib

theorem lemma_hint_0 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_1 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_2 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (h1 : Permut (insert_ x (insertionsort xs)) (x :: xs)) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_3 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_4 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_5 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (t : T) (h1 : count1 (x :: insertionsort xs) t = count1 (x :: xs) t) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_6 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h1 : ∀ (t : T), count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_7 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (h1 : ∀ (t : T), count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_8 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (t : T) (h1 : count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_9 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (t : T) (h1 : (if x = t then 1 else 0) + count1 (insertionsort xs) t = (if x = t then 1 else 0) + count1 xs t) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit

theorem eval_insertionsort_correct (T : Type) [Preorder T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : SortCorrect (insertionsort : List T -> List T) := by
  intro l
  induction l with
  | nil =>
    exact And.intro Sorted.nil (by intro t; rfl)
  | cons x xs ih =>
    exact And.intro
      (by
        simp [insertionsort]
        cases h : insertionsort xs with
        | nil =>
          simp [insert_]
          exact Sorted.singleton
        | cons y ys =>
          by_cases hxy : x < y
          · simp [insert_, h, hxy]
            exact Sorted.cons (by simpa [h] using ih.left) (by simpa using hxy)
          · simp [insert_, h, hxy]
            have hs : Sorted (y :: ys) := by simpa [h] using ih.left
            cases hs with
            | singleton =>
              exact Sorted.cons Sorted.singleton (by simpa using hxy)
            | cons hs' hnot =>
              exact Sorted.cons (Sorted.cons hs' hnot) (by simpa using hxy))
      (by
        exact lemma_hint_3 x xs)


/- lean_check result: FAIL
error:
location:
              · simp [insert_, h, hxy]
                exact Sorted.cons (by simpa [h] using ih.left) (by simpa using hxy)
                                                                  ^
              · simp [insert_, h, hxy]
error: Type mismatch: After simplification, term
  hxy
 has type
  x < y
but is expected to have type
  ¬y < x

location:
                | cons hs' hnot =>
                  exact Sorted.cons (Sorted.cons hs' hnot) (by simpa using hxy))
                                                              ^
          (by
error: Type mismatch: After simplification, term
  hxy
 has type
  ¬x < y
but is expected to have type
  ¬y < ?m.254

location:
              by_cases hxy : x < y
              · simp [insert_, h, hxy]
                              ^
                exact Sorted.cons (by simpa [h] using ih.left) (by simpa using hxy)
error: This simp argument is unused:
  h
Hint: Omit it from the simp argument list.
  simp [insert_, h,̵ ̵h̵xy]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
                exact Sorted.cons (by simpa [h] using ih.left) (by simpa using hxy)
              · simp [insert_, h, hxy]
                              ^
                have hs : Sorted (y :: ys) := by simpa [h] using ih.left
error: This simp argument is unused:
  h
Hint: Omit it from the simp argument list.
  simp [insert_, h,̵ ̵h̵xy]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`
-/
