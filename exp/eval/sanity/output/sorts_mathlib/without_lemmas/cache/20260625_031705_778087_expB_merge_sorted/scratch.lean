import LeanSrc.Sorts_Mathlib

theorem expB_merge_sorted [Preorder T] [DecidableRel (LT.lt (α := T))] {xs ys : List T} (sxs : Sorted xs) (sys : Sorted ys) : Sorted (merge xs ys) := by
  induction xs generalizing ys with
  | nil =>
      simpa [merge] using sys
  | cons x xs ih =>
      cases xs with
      | nil =>
          cases ys with
          | nil =>
              simp [merge]
          | cons y ys =>
              by_cases h : x < y
              · have hyx : ¬ y < x := by
                  intro hyx
                  have hxy : x ≤ y := le_of_lt h
                  have hyx' : y ≤ x := le_of_lt hyx
                  have : x < x := lt_of_lt_of_le h hyx'
                  exact lt_irrefl _ this
                simpa [merge, h] using Sorted.cons sys hyx
              · cases ys with
                | nil =>
                    simpa [merge, h] using Sorted.cons Sorted.singleton h
                | cons y₂ ys₂ =>
                    cases sys with
                    | cons hs hny =>
                        have htail : Sorted (merge [x] (y₂ :: ys₂)) := by
                          exact ih Sorted.singleton hs
                        simpa [merge, h] using Sorted.cons htail hny
      | cons b xs' =>
          cases sxs with
          | cons hs hba =>
              cases ys with
              | nil =>
                  simpa [merge] using Sorted.cons hs hba
              | cons c ys =>
                  by_cases h : x < c
                  · simpa [merge, h] using Sorted.cons (ih hs sys) hba
                  · cases ys with
                    | nil =>
                        simpa [merge, h] using Sorted.cons (Sorted.cons hs hba) h
                    | cons d ds =>
                        cases sys with
                        | cons hs' hdc =>
                            have htail : Sorted (merge (x :: b :: xs') (d :: ds)) := ih (Sorted.cons hs hba) hs'
                            simpa [merge, h] using Sorted.cons htail hdc


/- lean_check result: FAIL
error:
location:
              cases ys with
              | nil =>
                   ^
                  simp [merge]
error: unsolved goals
case cons.nil.nil
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
x : T
ih : ∀ {ys : List T}, Sorted [] → Sorted ys → Sorted (merge [] ys)
sxs : Sorted [x]
sys : Sorted []
⊢ Sorted [x]

location:
                            have htail : Sorted (merge [x] (y₂ :: ys₂)) := by
                              exact ih Sorted.singleton hs
                                      ^
                            simpa [merge, h] using Sorted.cons htail hny
error: Application type mismatch: The argument
  Sorted.singleton
has type
  Sorted [?m.294]
but is expected to have type
  Sorted []
in the application
  ih Sorted.singleton

location:
                              exact ih Sorted.singleton hs
                            simpa [merge, h] using Sorted.cons htail hny
                                                              ^
          | cons b xs' =>
error: Application type mismatch: The argument
  htail
has type
  Sorted (merge [x] (y₂ :: ys₂))
but is expected to have type
  Sorted (?m.299 :: ?m.300)
in the application
  Sorted.cons htail

location:
                      by_cases h : x < c
                      · simpa [merge, h] using Sorted.cons (ih hs sys) hba
                                                          ^
                      · cases ys with
error: Application type mismatch: The argument
  ih hs sys
has type
  Sorted (merge (b :: xs') (c :: ys))
but is expected to have type
  Sorted (?m.486 :: ?m.487)
in the application
  Sorted.cons (ih hs sys)

location:
                            | cons hs' hdc =>
                                have htail : Sorted (merge (x :: b :: xs') (d :: ds)) := ih (Sorted.cons hs hba) hs'
                                                                                           ^
                                simpa [merge, h] using Sorted.cons htail hdc
error: Application type mismatch: The argument
  Sorted.cons hs hba
has type
  Sorted (x :: b :: xs')
but is expected to have type
  Sorted (b :: xs')
in the application
  ih (Sorted.cons hs hba)

location:
                                have htail : Sorted (merge (x :: b :: xs') (d :: ds)) := ih (Sorted.cons hs hba) hs'
                                simpa [merge, h] using Sorted.cons htail hdc
                                                                  ^
error: Application type mismatch: The argument
  htail
has type
  Sorted (merge (x :: b :: xs') (d :: ds))
but is expected to have type
  Sorted (?m.646 :: ?m.647)
in the application
  Sorted.cons htail
-/
