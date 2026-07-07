import LeanSrc.Sorts_Mathlib

theorem lemma_hint_0 [DecidableEq T] (l : List T) (t' : T) (h1 : count1 l t' = count1 l t') : Permut l l := by admit
theorem lemma_hint_1 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_2 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_3 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : Permut ([] : List T) [] := by admit
theorem lemma_hint_4 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_5 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_6 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (IH : ∀ (t : T), count1 (insertionsort xs) t = count1 xs t) (t : T) : count1 (x :: insertionsort xs) t = count1 (x :: xs) t := by admit
theorem lemma_hint_7 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) (h1 : ∀ (t : T), count1 (e :: x :: xs) t = count1 (e :: x :: xs) t) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_8 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (h1 : Permut (insert_ x (insertionsort xs)) (x :: xs)) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_9 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : Permut (insertionsort ([] : List T)) [] := by admit

theorem eval_mergesort_correct (T : Type) [Preorder T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : SortCorrect (mergesort : List T -> List T) := by
  intro l
  cases l with
  | nil =>
    constructor
    · simp [SortCorrect, mergesort, Sorted.nil]
    · exact lemma_hint_3
  | cons a xs =>
    cases xs with
    | nil =>
      constructor
      · simp [mergesort, Sorted.singleton]
      · simpa [mergesort] using (lemma_hint_0 [a] a rfl)
    | cons b ys =>
      constructor
      · unfold mergesort
        simp
        have h : False := by simp
        exact False.elim h
      · unfold Permut
        intro t
        unfold mergesort
        simp
        have h : False := by simp
        exact False.elim h


/- lean_check result: FAIL
error:
location:
        · simp [SortCorrect, mergesort, Sorted.nil]
        · exact lemma_hint_3
               ^
      | cons a xs =>
error: typeclass instance problem is stuck
  DecidableRel LT.lt
Note: Lean will not try to resolve this typeclass instance problem because the first, second, and third type arguments to `DecidableRel` contain metavariables. These arguments must be fully determined before Lean will try to resolve the typeclass.
Hint: Adding type annotations and supplying implicit arguments to functions can give Lean more information for typeclass resolution. For example, if you have a variable `x` that you intend to be a `Nat`, but Lean reports it as having an unresolved type like `?m`, replacing `x` with `(x : Nat)` can get typeclass resolution un-stuck.

location:
            simp
            have h : False := by simp
                                ^
            exact False.elim h
error: `simp` made no progress

location:
            simp
            have h : False := by simp
                                ^
            exact False.elim h
error: `simp` made no progress

location:
        constructor
        · simp [SortCorrect, mergesort, Sorted.nil]
               ^
        · exact lemma_hint_3
error: This simp argument is unused:
  SortCorrect
Hint: Omit it from the simp argument list.
  simp [S̵o̵r̵t̵C̵o̵r̵r̵e̵c̵t̵,̵ ̵mergesort, Sorted.nil]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`
-/
