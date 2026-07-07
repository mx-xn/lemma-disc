import LeanSrc.Sorts_Mathlib

theorem lemma_hint_0 [DecidableEq T] (l : List T) : Permut l l := by admit
theorem lemma_hint_1 [DecidableEq T] (l : List T) (t' : T) (h1 : count1 l t' = count1 l t') : Permut l l := by admit
theorem lemma_hint_2 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : Permut ([] : List T) [] := by admit
theorem lemma_hint_3 [LT T] (x : T) (xs : List T) (s : Sorted (x :: xs)) : Sorted xs := by admit
theorem lemma_hint_4 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : Permut (insertionsort ([] : List T)) [] := by admit
theorem lemma_hint_5 [DecidableEq T] (a : List T) (c : List T) (t' : T) (h1 : count1 a t' = count1 c t') : Permut a c := by admit
theorem lemma_hint_6 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) (h1 : ∀ (t : T), count1 (e :: x :: xs) t = count1 (e :: x :: xs) t) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_7 [DecidableEq T] (c : List T) (a : List T) (b : List T) (t' : T) (h1 : count1 b t' = count1 c t') : Permut a c := by admit
theorem lemma_hint_8 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_9 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) : Permut (e :: x :: xs) (e :: x :: xs) := by admit

theorem eval_mergesort_sorted [Preorder T] [DecidableRel (LT.lt (α := T))] (l : List T) : Sorted (mergesort l) := by
  by_cases h : l.length < 2
  · simp [mergesort, h]
    cases l with
    | nil =>
      exact Sorted.nil
    | cons x xs =>
      cases xs with
      | nil =>
        exact Sorted.singleton
      | cons y ys =>
        exfalso
        simpa using h
  · simp [mergesort, h]
    have hs₁ : Sorted (mergesort (left l)) := mergesort_sorted (l := left l)
    have hs₂ : Sorted (mergesort (right l)) := mergesort_sorted (l := right l)
    exact merge_sorted (xs := mergesort (left l)) (ys := mergesort (right l)) hs₁ hs₂


/- lean_check result: FAIL
error:
location:
            exfalso
            simpa using h
           ^
      · simp [mergesort, h]
error: Type mismatch: After simplification, term
  h
 has type
  ys.length + 1 + 1 < 2
but is expected to have type
  False

location:
            simpa using h
      · simp [mergesort, h]
             ^
        have hs₁ : Sorted (mergesort (left l)) := mergesort_sorted (l := left l)
error: Possibly looping simp theorem: `mergesort.eq_1`
Note: Possibly caused by: `mergesort`
Hint: You can disable a simp theorem from the default simp set by passing `- theoremName` to `simp`.

location:
            simpa using h
      · simp [mergesort, h]
       ^
        have hs₁ : Sorted (mergesort (left l)) := mergesort_sorted (l := left l)
error: Tactic `simp` failed with a nested error:
maximum recursion depth has been reached
use `set_option maxRecDepth <num>` to increase limit
use `set_option diagnostics true` to get diagnostic information
-/
