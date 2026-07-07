import LeanSrc.Sorts_Mathlib

theorem expB_merge_sorted [Preorder T] [DecidableRel (LT.lt (α := T))] {xs ys : List T} (sxs : Sorted xs) (sys : Sorted ys) : Sorted (merge xs ys) := by
  induction xs generalizing ys with
  | nil =>
      intro sxs sys
      simpa [merge] using sys
  | cons a xs ih =>
      intro sxs sys
      cases ys with
      | nil =>
          simpa [merge] using sxs
      | cons b ys =>
          cases xs with
          | nil =>
              cases sys with
              | nil =>
                  simp [merge]
              | singleton =>
                  by_cases h : a < b
                  · have hba : ¬ b < a := by
                      intro hba
                      exact lt_irrefl _ (lt_trans h hba)
                    simpa [merge, h] using (Sorted.cons (Sorted.singleton : Sorted [b]) hba)
                  · simpa [merge, h] using (Sorted.cons (Sorted.singleton : Sorted [a]) h)
              | cons hs hcb =>
                  by_cases h : a < b
                  · have hba : ¬ b < a := by
                      intro hba
                      exact lt_irrefl _ (lt_trans h hba)
                    simpa [merge, h] using (Sorted.cons (Sorted.cons hs hcb) hba)
                  · simpa [merge, h] using (Sorted.cons (Sorted.cons hs hcb) h)
          | cons c xs' =>
              cases sxs with
              | cons hs hac =>
                  cases sys with
                  | nil =>
                      simp at *
                  | singleton =>
                      by_cases h : a < b
                      · have hba : ¬ b < a := by
                          intro hba
                          exact lt_irrefl _ (lt_trans h hba)
                        simpa [merge, h] using (Sorted.cons (Sorted.cons hs hac) hba)
                      · simpa [merge, h] using (Sorted.cons (ih hs (Sorted.singleton : Sorted [b])) hac)
                  | cons hs' hbd =>
                      by_cases h : a < b
                      · simpa [merge, h] using (Sorted.cons (ih hs (Sorted.cons hs' hbd)) hac)
                      · simpa [merge, h] using (Sorted.cons (Sorted.cons (ih (Sorted.cons hs hac) hs') hbd) h)


/- lean_check result: FAIL
error:
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
      | cons a xs ih =>
          intro sxs sys
               ^
          cases ys with
error: Tactic `introN` failed: There are no additional binders or `let` bindings in the goal to introduce
case cons
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
a : T
xs : List T
ih : ∀ {ys : List T}, Sorted xs → Sorted ys → Sorted (merge xs ys)
ys : List T
sxs : Sorted (a :: xs)
sys : Sorted ys
⊢ Sorted (merge (a :: xs) ys)
-/
