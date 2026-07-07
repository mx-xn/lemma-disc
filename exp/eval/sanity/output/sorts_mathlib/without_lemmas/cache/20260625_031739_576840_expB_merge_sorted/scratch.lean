import LeanSrc.Sorts_Mathlib

theorem expB_merge_sorted [Preorder T] [DecidableRel (LT.lt (α := T))] {xs ys : List T} (sxs : Sorted xs) (sys : Sorted ys) : Sorted (merge xs ys) := by
  induction sxs generalizing ys with
  | nil =>
      simpa [merge] using sys
  | singleton =>
      cases sys with
      | nil =>
          simp [merge]
      | singleton =>
          by_cases h : x < x_1
          · have hyx : ¬ x_1 < x := by
              intro hyx
              have : x < x := lt_of_lt_of_le h (le_of_lt hyx)
              exact lt_irrefl _ this
            simpa [merge, h] using Sorted.cons Sorted.singleton hyx
          · simpa [merge, h] using Sorted.cons Sorted.singleton h
      | cons hs hny =>
          by_cases h : x < a
          · have hax : ¬ a < x := by
              intro hax
              have : x < x := lt_of_lt_of_le h (le_of_lt hax)
              exact lt_irrefl _ this
            simpa [merge, h] using Sorted.cons (Sorted.cons hs hny) hax
          · simpa [merge, h] using Sorted.cons (Sorted.cons hs hny) hny
  | cons hs hba ih =>
      cases sys with
      | nil =>
          simpa [merge] using Sorted.cons hs hba
      | singleton =>
          by_cases h : a < x
          · have hxa : ¬ x < a := by
              intro hxa
              have : a < a := lt_of_lt_of_le h (le_of_lt hxa)
              exact lt_irrefl _ this
            simpa [merge, h] using Sorted.cons (Sorted.cons hs hba) hxa
          · simpa [merge, h] using Sorted.cons (ih Sorted.singleton) hba
      | cons hs' hdc =>
          by_cases h : a < c
          · simpa [merge, h] using Sorted.cons (ih (Sorted.cons hs' hdc)) hba
          · simpa [merge, h] using Sorted.cons (Sorted.cons (ih hs') hdc) hdc


/- lean_check result: FAIL
error:
location:
          cases sys with
          | nil =>
               ^
              simp [merge]
error: unsolved goals
case singleton.nil
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
xs : List T
x✝ : T
⊢ Sorted [x✝]

location:
          | singleton =>
              by_cases h : x < x_1
                          ^
              · have hyx : ¬ x_1 < x := by
error: error(lean.unknownIdentifier): Unknown identifier `x`

location:
          | singleton =>
              by_cases h : x < x_1
                              ^
              · have hyx : ¬ x_1 < x := by
error: error(lean.unknownIdentifier): Unknown identifier `x_1`

location:
          | cons hs hny =>
              by_cases h : x < a
                          ^
              · have hax : ¬ a < x := by
error: error(lean.unknownIdentifier): Unknown identifier `x`

location:
          | cons hs hny =>
              by_cases h : x < a
                              ^
              · have hax : ¬ a < x := by
error: error(lean.unknownIdentifier): Unknown identifier `a`

location:
          | singleton =>
              by_cases h : a < x
                          ^
              · have hxa : ¬ x < a := by
error: error(lean.unknownIdentifier): Unknown identifier `a`

location:
          | singleton =>
              by_cases h : a < x
                              ^
              · have hxa : ¬ x < a := by
error: error(lean.unknownIdentifier): Unknown identifier `x`

location:
          | cons hs' hdc =>
              by_cases h : a < c
                          ^
              · simpa [merge, h] using Sorted.cons (ih (Sorted.cons hs' hdc)) hba
error: error(lean.unknownIdentifier): Unknown identifier `a`

location:
          | cons hs' hdc =>
              by_cases h : a < c
                              ^
              · simpa [merge, h] using Sorted.cons (ih (Sorted.cons hs' hdc)) hba
error: error(lean.unknownIdentifier): Unknown identifier `c`
-/
