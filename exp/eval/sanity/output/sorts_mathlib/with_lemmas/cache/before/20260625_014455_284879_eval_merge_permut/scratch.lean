import LeanSrc.Sorts_Mathlib

theorem lemma_hint_0 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_1 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) : Permut (e :: x :: xs) (e :: x :: xs) := by admit
theorem lemma_hint_2 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) (h1 : ∀ (t : T), count1 (e :: x :: xs) t = count1 (e :: x :: xs) t) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_3 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_4 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (p : ¬e < x) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_5 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) : Permut (insert_ e (x :: xs)) (e :: x :: xs) := by admit
theorem lemma_hint_6 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (h1 : ∀ (t : T), count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_7 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) (t' : T) (h1 : count1 (e :: x :: xs) t' = count1 (e :: x :: xs) t') : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_8 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (t : T) (h1 : (if x = t then 1 else 0) + count1 (e :: xs) t = (if e = t then 1 else 0) + count1 (x :: xs) t) : Permut (x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_9 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (p : ¬e < x) : Permut (x :: insert_ e xs) (e :: x :: xs) := by admit

theorem eval_merge_permut [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (xs ys : List T) : Permut (merge xs ys) (xs ++ ys) := by
  intro t
  induction xs with
  | nil =>
    simp [merge, Permut, count1]
  | cons x xs ih =>
    induction ys with
    | nil =>
      simp [merge, count1]
    | cons y ys ihy =>
      by_cases h : x < y
      · simp [merge, h, count1]
        exact ih (y :: ys) t
      · simp [merge, h, count1]
        exact ihy t


/- lean_check result: FAIL
error:
location:
          · simp [merge, h, count1]
            exact ih (y :: ys) t
                 ^
          · simp [merge, h, count1]
error: Function expected at
  ih
but this term has type
  count1 (merge xs (y :: ys)) t = count1 (xs ++ y :: ys) t
Note: Expected a function because this term is being applied to the argument
  (y :: ys)

location:
          · simp [merge, h, count1]
            exact ihy t
                     ^
error: Application type mismatch: The argument
  t
has type
  T
of sort `Type u_1` but is expected to have type
  count1 (merge xs ys) t = count1 (xs ++ ys) t
of sort `Prop` in the application
  ihy t

location:
      | nil =>
        simp [merge, Permut, count1]
                    ^
      | cons x xs ih =>
error: This simp argument is unused:
  Permut
Hint: Omit it from the simp argument list.
  simp [merge, P̵e̵r̵m̵u̵t̵,̵ ̵count1]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
      | nil =>
        simp [merge, Permut, count1]
                            ^
      | cons x xs ih =>
error: This simp argument is unused:
  count1
Hint: Omit it from the simp argument list.
  simp [merge, Permut,̵ ̵c̵o̵u̵n̵t̵1̵]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`
-/
