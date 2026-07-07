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
  · rw [mergesort, h]
    cases l with
    | nil =>
      exact Sorted.nil
    | cons x xs =>
      cases xs with
      | nil =>
        exact Sorted.singleton
      | cons y ys =>
        exfalso
        omega
  · rw [mergesort, h]
    have hs₁ : Sorted (mergesort (left l)) := mergesort_sorted (l := left l)
    have hs₂ : Sorted (mergesort (right l)) := mergesort_sorted (l := right l)
    exact merge_sorted (xs := mergesort (left l)) (ys := mergesort (right l)) hs₁ hs₂


/- lean_check result: FAIL
error:
location:
      by_cases h : l.length < 2
      · rw [mergesort, h]
                      ^
        cases l with
error: Invalid rewrite argument: Expected an equality or iff proof or definition name, but `h` is a proof of
  l.length < 2

location:
            omega
      · rw [mergesort, h]
                      ^
        have hs₁ : Sorted (mergesort (left l)) := mergesort_sorted (l := left l)
error: Invalid rewrite argument: Expected an equality or iff proof or definition name, but `h ?a✝` is a proof of
  False
-/
