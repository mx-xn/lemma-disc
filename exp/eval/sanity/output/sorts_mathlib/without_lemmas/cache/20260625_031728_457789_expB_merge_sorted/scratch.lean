import LeanSrc.Sorts_Mathlib

theorem expB_merge_sorted [Preorder T] [DecidableRel (LT.lt (α := T))] {xs ys : List T} (sxs : Sorted xs) (sys : Sorted ys) : Sorted (merge xs ys) := by
  induction xs generalizing ys with
  | nil =>
      intro sxs sys
      simpa [merge] using sys
  | cons x xs ih =>
      intro sxs sys
      cases ys with
      | nil =>
          simpa [merge] using sxs
      | cons y ys =>
          by_cases hxy : x < y
          · cases xs with
            | nil =>
                simp [merge, hxy]
            | cons x₂ xs₂ =>
                cases sxs with
                | cons hs hnx =>
                    have htail : Sorted (merge (x₂ :: xs₂) (y :: ys)) := ih hs sys
                    have hnot : ¬ (head := y) (merge (x₂ :: xs₂) (y :: ys)).head! < x := by
                      intro h
                      by_cases hx₂y : x₂ < y
                      · have hm : merge (x₂ :: xs₂) (y :: ys) = x₂ :: merge xs₂ (y :: ys) := by
                          simp [merge, hx₂y]
                        rw [hm] at h
                        exact hnx h
                      · have hm : merge (x₂ :: xs₂) (y :: ys) = y :: merge (x₂ :: xs₂) ys := by
                          simp [merge, hx₂y]
                        rw [hm] at h
                        exact not_lt_of_ge (le_of_lt hxy) h
                    simpa [merge, hxy] using Sorted.cons htail hnot
          · cases ys with
            | nil =>
                simp [merge, hxy]
            | cons y₂ ys₂ =>
                cases sys with
                | cons hs hny =>
                    have htail : Sorted (merge (x :: xs) (y₂ :: ys₂)) := ih sxs hs
                    have hnot : ¬ (head := y₂) (merge (x :: xs) (y₂ :: ys₂)).head! < y := by
                      intro h
                      by_cases hxy₂ : x < y₂
                      · have hm : merge (x :: xs) (y₂ :: ys₂) = x :: merge xs (y₂ :: ys₂) := by
                          simp [merge, hxy₂]
                        rw [hm] at h
                        exact hxy h
                      · have hm : merge (x :: xs) (y₂ :: ys₂) = y₂ :: merge (x :: xs) ys₂ := by
                          simp [merge, hxy₂]
                        rw [hm] at h
                        exact hny h
                    simpa [merge, hxy] using Sorted.cons htail hnot


/- lean_check result: FAIL
error:
location:
                        have htail : Sorted (merge (x₂ :: xs₂) (y :: ys)) := ih hs sys
                        have hnot : ¬ (head := y) (merge (x₂ :: xs₂) (y :: ys)).head! < x := by
                                          ^
                          intro h
error: unexpected token ':='; expected ')', ',' or ':'

location:
      | nil =>
          intro sxs sys
               ^
          simpa [merge] using sys
error: Tactic `introN` failed: There are no additional binders or `let` bindings in the goal to introduce
case nil
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
ys : List T
sxs : Sorted []
sys : Sorted ys
⊢ Sorted (merge [] ys)

location:
      | cons x xs ih =>
          intro sxs sys
               ^
          cases ys with
error: Tactic `introN` failed: There are no additional binders or `let` bindings in the goal to introduce
case cons
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
x : T
xs : List T
ih : ∀ {ys : List T}, Sorted xs → Sorted ys → Sorted (merge xs ys)
ys : List T
sxs : Sorted (x :: xs)
sys : Sorted ys
⊢ Sorted (merge (x :: xs) ys)
-/
