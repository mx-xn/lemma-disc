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
    · exact Sorted.nil
    · exact (lemma_hint_3 (T := T))
  | cons a xs =>
    cases xs with
    | nil =>
      constructor
      · exact Sorted.singleton
      · simpa [mergesort] using (lemma_hint_0 (T := T) [a] a rfl)
    | cons b ys =>
      constructor
      · simp [mergesort]
      · unfold Permut
        intro t
        simp [mergesort]


/- lean_check result: FAIL
error:
location:
        constructor
        · exact Sorted.nil
               ^
        · exact (lemma_hint_3 (T := T))
error: typeclass instance problem is stuck
  LT ?m.37
Note: Lean will not try to resolve this typeclass instance problem because the type argument to `LT` is a metavariable. This argument must be fully determined before Lean will try to resolve the typeclass.
Hint: Adding type annotations and supplying implicit arguments to functions can give Lean more information for typeclass resolution. For example, if you have a variable `x` that you intend to be a `Nat`, but Lean reports it as having an unresolved type like `?m`, replacing `x` with `(x : Nat)` can get typeclass resolution un-stuck.

location:
        · exact Sorted.nil
        · exact (lemma_hint_3 (T := T))
         ^
      | cons a xs =>
error: Type mismatch
  lemma_hint_3
has type
  Permut [] []
but is expected to have type
  Permut (mergesort []) []

location:
          constructor
          · exact Sorted.singleton
           ^
          · simpa [mergesort] using (lemma_hint_0 (T := T) [a] a rfl)
error: Type mismatch
  Sorted.singleton
has type
  Sorted [?m.77]
but is expected to have type
  Sorted (mergesort [a])

location:
          constructor
          · simp [mergesort]
                 ^
          · unfold Permut
error: Possibly looping simp theorem: `mergesort.eq_1`
Note: Possibly caused by: `mergesort`
Hint: You can disable a simp theorem from the default simp set by passing `- theoremName` to `simp`.

location:
          constructor
          · simp [mergesort]
           ^
          · unfold Permut
error: Tactic `simp` failed with a nested error:
maximum recursion depth has been reached
use `set_option maxRecDepth <num>` to increase limit
use `set_option diagnostics true` to get diagnostic information

location:
            intro t
            simp [mergesort]
                 ^
error: Possibly looping simp theorem: `mergesort.eq_1`
Note: Possibly caused by: `mergesort`
Hint: You can disable a simp theorem from the default simp set by passing `- theoremName` to `simp`.

location:
            intro t
            simp [mergesort]
           ^
error: Tactic `simp` failed with a nested error:
maximum recursion depth has been reached
use `set_option maxRecDepth <num>` to increase limit
use `set_option diagnostics true` to get diagnostic information
-/
