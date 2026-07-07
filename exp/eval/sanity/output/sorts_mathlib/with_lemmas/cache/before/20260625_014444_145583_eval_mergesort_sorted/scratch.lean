import LeanSrc.Sorts_Mathlib

theorem lemma_hint_0 [DecidableEq T] (l : List T) (t' : T) (h1 : count1 l t' = count1 l t') : Permut l l := by admit
theorem lemma_hint_1 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : Permut ([] : List T) [] := by admit
theorem lemma_hint_2 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : Permut (insertionsort ([] : List T)) [] := by admit
theorem lemma_hint_3 [DecidableEq T] (a : List T) (c : List T) (t' : T) (h1 : count1 a t' = count1 c t') : Permut a c := by admit
theorem lemma_hint_4 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) (h1 : ∀ (t : T), count1 (e :: x :: xs) t = count1 (e :: x :: xs) t) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_5 [DecidableEq T] (c : List T) (a : List T) (b : List T) (t' : T) (h1 : count1 b t' = count1 c t') : Permut a c := by admit
theorem lemma_hint_6 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_7 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) : Permut (e :: x :: xs) (e :: x :: xs) := by admit
theorem lemma_hint_8 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (t' : T) (h1 : count1 [] t' = count1 [] t') : Permut ([] : List T) [] := by admit
theorem lemma_hint_9 [Preorder T] [DecidableRel (LT.lt (α := T))] (x : T) (p : ¬t < x) (h : T) (xs : List T) (s : Sorted (x :: h :: xs)) : Sorted (h :: xs) := by admit

theorem eval_mergesort_sorted [Preorder T] [DecidableRel (LT.lt (α := T))] (l : List T) : Sorted (mergesort l) := by
  unfold mergesort
  split
  · simpa [Sorted.nil, Sorted.singleton] using (by
      cases l with
      | nil =>
        exact Sorted.nil
      | cons x xs =>
        cases xs with
        | nil =>
          exact Sorted.singleton
        | cons y ys =>
          simp at *
    )
  · have hL : Sorted (mergesort (left l)) := mergesort_sorted (l := left l)
    have hR : Sorted (mergesort (right l)) := mergesort_sorted (l := right l)
    exact merge_sorted (l₁ := mergesort (left l)) (l₂ := mergesort (right l)) hL hR


/- lean_check result: FAIL
error:
location:
              exact Sorted.singleton
            | cons y ys =>
                       ^
              simp at *
error: unsolved goals
case cons.cons
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
x y : T
ys : List T
h✝ : ys.length + 1 + 1 < 2
⊢ Sorted (x :: y :: ys)

location:
        have hR : Sorted (mergesort (right l)) := mergesort_sorted (l := right l)
        exact merge_sorted (l₁ := mergesort (left l)) (l₂ := mergesort (right l)) hL hR
                          ^
error: Invalid argument name `l₁` for function `merge_sorted`
Hint: Perhaps you meant one of the following parameter names:
  • `T`: l̵₁̵T̲
  • `xs`: l̵₁̵x̲s̲
  • `ys`: l̵₁̵y̲s̲
  • `sxs`: l̵₁̵s̲x̲s̲
  • `sys`: l̵₁̵s̲y̲s̲
-/
