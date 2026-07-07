import LeanSrc.Sorts_Mathlib

theorem expB_mergesort_sorted [Preorder T] [DecidableRel (LT.lt (α := T))] (l : List T) : Sorted (mergesort l) := by
  unfold mergesort
  split
  · simpa [Sorted.nil, Sorted.singleton] using (by
      cases l with
      | nil => exact Sorted.nil
      | cons x xs =>
          cases xs with
          | nil => exact Sorted.singleton
          | cons y ys =>
              simp at * )
  ·
    simp at *


/- lean_check result: FAIL
error:
location:
              | nil => exact Sorted.singleton
              | cons y ys =>
                         ^
                  simp at * )
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
                  simp at * )
      ·
     ^
        simp at *
error: unsolved goals
case isFalse
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
l : List T
h✝ : 2 ≤ l.length
⊢ Sorted (merge (mergesort (left l)) (mergesort (right l)))
-/
