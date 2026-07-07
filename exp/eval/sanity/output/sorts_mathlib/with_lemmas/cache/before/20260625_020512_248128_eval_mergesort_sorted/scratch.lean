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
  unfold mergesort
  split
  · simpa using (by
      cases l with
      | nil =>
        exact Sorted.nil
      | cons x xs =>
        cases xs with
        | nil =>
          exact Sorted.singleton
        | cons y ys =>
          exact Sorted.nil)
  · have hs₁ : Sorted (mergesort (left l)) := mergesort_sorted (l := left l)
    have hs₂ : Sorted (mergesort (right l)) := mergesort_sorted (l := right l)
    simpa using merge_sorted (l₁ := mergesort (left l)) (l₂ := mergesort (right l)) hs₁ hs₂


/- lean_check result: FAIL
error:
location:
            | cons y ys =>
              exact Sorted.nil)
                   ^
      · have hs₁ : Sorted (mergesort (left l)) := mergesort_sorted (l := left l)
error: typeclass instance problem is stuck
  LT ?m.107
Note: Lean will not try to resolve this typeclass instance problem because the type argument to `LT` is a metavariable. This argument must be fully determined before Lean will try to resolve the typeclass.
Hint: Adding type annotations and supplying implicit arguments to functions can give Lean more information for typeclass resolution. For example, if you have a variable `x` that you intend to be a `Nat`, but Lean reports it as having an unresolved type like `?m`, replacing `x` with `(x : Nat)` can get typeclass resolution un-stuck.

location:
        have hs₂ : Sorted (mergesort (right l)) := mergesort_sorted (l := right l)
        simpa using merge_sorted (l₁ := mergesort (left l)) (l₂ := mergesort (right l)) hs₁ hs₂
                                ^
error: Invalid argument name `l₁` for function `merge_sorted`
Hint: Perhaps you meant one of the following parameter names:
  • `T`: l̵₁̵T̲
  • `xs`: l̵₁̵x̲s̲
  • `ys`: l̵₁̵y̲s̲
  • `sxs`: l̵₁̵s̲x̲s̲
  • `sys`: l̵₁̵s̲y̲s̲
-/
