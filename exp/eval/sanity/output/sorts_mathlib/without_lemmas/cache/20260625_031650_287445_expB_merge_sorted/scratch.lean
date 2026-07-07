import LeanSrc.Sorts_Mathlib

theorem expB_merge_sorted [Preorder T] [DecidableRel (LT.lt (α := T))] {xs ys : List T} (sxs : Sorted xs) (sys : Sorted ys) : Sorted (merge xs ys) := by
  induction sxs generalizing ys with
  | nil =>
      intro sys
      simpa [merge] using sys
  | singleton =>
      intro ys sys
      cases ys with
      | nil =>
          simp [merge, Sorted.singleton]
      | cons y ys =>
          cases ys with
          | nil =>
              by_cases h : x < y
              · simp [merge, h, Sorted.cons, h]
              · simp [merge, h, Sorted.cons, h, Sorted.singleton]
          | cons y₂ ys₂ =>
              cases sys with
              | cons sys' hy =>
                  by_cases hxy : x < y
                  · simp [merge, hxy]
                    exact Sorted.cons (Sorted.cons sys' hy) (by
                      intro h
                      exact hy (lt_of_lt_of_le h (le_of_lt hxy)))
                  · by_cases hxy₂ : x < y₂
                    · simp [merge, hxy, hxy₂]
                      exact Sorted.cons (Sorted.cons (Sorted.singleton) hxy) hxy
                    · simp [merge, hxy, hxy₂]
                      exact Sorted.cons sys' hy
  | @cons a b bs hs hba ih =>
      intro ys sys
      cases ys with
      | nil =>
          simpa [merge] using Sorted.cons hs hba
      | cons c cs =>
          cases cs with
          | nil =>
              by_cases hac : a < c
              · simp [merge, hac]
                exact Sorted.cons (Sorted.singleton) (by
                  intro h
                  exact hba (lt_of_lt_of_le h (le_of_lt hac)))
              · simp [merge, hac]
                exact Sorted.cons (Sorted.cons hs hba) hac
          | cons d ds =>
              cases sys with
              | cons hs2 hdc =>
                  by_cases hac : a < c
                  · simp [merge, hac]
                    have htail : Sorted (merge (b :: bs) (c :: d :: ds)) := ih (Sorted.cons hs2 hdc)
                    refine Sorted.cons htail ?_
                    intro h
                    by_cases hbc : b < c
                    · have : merge (b :: bs) (c :: d :: ds) = b :: merge bs (c :: d :: ds) := by
                        simp [merge, hbc]
                      rw [this] at h
                      exact hba h
                    · have : merge (b :: bs) (c :: d :: ds) = c :: merge (b :: bs) (d :: ds) := by
                        simp [merge, hbc]
                      rw [this] at h
                      exact not_lt_of_ge (le_of_lt hac) h
                  · simp [merge, hac]
                    have htail : Sorted (merge (a :: b :: bs) (d :: ds)) := ih hs2
                    refine Sorted.cons htail ?_
                    intro h
                    by_cases had : a < d
                    · have : merge (a :: b :: bs) (d :: ds) = a :: merge (b :: bs) (d :: ds) := by
                        simp [merge, had]
                      rw [this] at h
                      exact hac h
                    · have : merge (a :: b :: bs) (d :: ds) = d :: merge (a :: b :: bs) ds := by
                        simp [merge, had]
                      rw [this] at h
                      exact hdc h


/- lean_check result: FAIL
error:
location:
      | nil =>
          intro sys
               ^
          simpa [merge] using sys
error: Tactic `introN` failed: There are no additional binders or `let` bindings in the goal to introduce
case nil
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
xs ys : List T
sys : Sorted ys
⊢ Sorted (merge [] ys)

location:
      | singleton =>
          intro ys sys
               ^
          cases ys with
error: Tactic `introN` failed: There are no additional binders or `let` bindings in the goal to introduce
case singleton
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
xs : List T
x✝ : T
ys : List T
sys : Sorted ys
⊢ Sorted (merge [x✝] ys)

location:
      | @cons a b bs hs hba ih =>
          intro ys sys
               ^
          cases ys with
error: Tactic `introN` failed: There are no additional binders or `let` bindings in the goal to introduce
case cons
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
xs : List T
a b : T
bs : List T
hs : Sorted (b :: bs)
hba : ¬b < a
ih : ∀ {ys : List T}, Sorted ys → Sorted (merge (b :: bs) ys)
ys : List T
sys : Sorted ys
⊢ Sorted (merge (a :: b :: bs) ys)
-/
