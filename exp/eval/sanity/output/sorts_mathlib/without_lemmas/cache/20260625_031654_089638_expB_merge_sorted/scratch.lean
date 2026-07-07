import LeanSrc.Sorts_Mathlib

theorem expB_merge_sorted [Preorder T] [DecidableRel (LT.lt (α := T))] {xs ys : List T} (sxs : Sorted xs) (sys : Sorted ys) : Sorted (merge xs ys) := by
  induction sxs generalizing ys with
  | nil =>
      simpa [merge] using sys
  | singleton =>
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
                  by_cases h : x < y
                              ^
                  · simp [merge, h, Sorted.cons, h]
error: error(lean.unknownIdentifier): Unknown identifier `x`

location:
                  by_cases h : x < y
                  · simp [merge, h, Sorted.cons, h]
                 ^
                  · simp [merge, h, Sorted.cons, h, Sorted.singleton]
error: unsolved goals
case pos
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
xs : List T
x✝ y : T
sys : Sorted [y]
h : sorry < y
⊢ Sorted (if x✝ < y then [x✝, y] else [y, x✝])

location:
                  · simp [merge, h, Sorted.cons, h]
                  · simp [merge, h, Sorted.cons, h, Sorted.singleton]
                 ^
              | cons y₂ ys₂ =>
error: unsolved goals
case neg
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
xs : List T
x✝ y : T
sys : Sorted [y]
h : ¬sorry < y
⊢ Sorted (if x✝ < y then [x✝, y] else [y, x✝])

location:
                  | cons sys' hy =>
                      by_cases hxy : x < y
                                    ^
                      · simp [merge, hxy]
error: error(lean.unknownIdentifier): Unknown identifier `x`

location:
                          exact hy (lt_of_lt_of_le h (le_of_lt hxy)))
                      · by_cases hxy₂ : x < y₂
                                       ^
                        · simp [merge, hxy, hxy₂]
error: error(lean.unknownIdentifier): Unknown identifier `x`

location:
                        · simp [merge, hxy, hxy₂]
                          exact Sorted.cons sys' hy
                         ^
      | @cons a b bs hs hba ih =>
error: Type mismatch
  Sorted.cons sys' hy
has type
  Sorted (y :: y₂ :: ys₂)
but is expected to have type
  Sorted (if x✝ < y then x✝ :: y :: y₂ :: ys₂ else y :: if x✝ < y₂ then x✝ :: y₂ :: ys₂ else y₂ :: merge [x✝] ys₂)

location:
                      intro h
                      exact hba (lt_of_lt_of_le h (le_of_lt hac)))
                                                           ^
                  · simp [merge, hac]
error: Application type mismatch: The argument
  hac
has type
  a < c
but is expected to have type
  ?m.403 < a
in the application
  le_of_lt hac

location:
                        have htail : Sorted (merge (b :: bs) (c :: d :: ds)) := ih (Sorted.cons hs2 hdc)
                        refine Sorted.cons htail ?_
                                          ^
                        intro h
error: Application type mismatch: The argument
  htail
has type
  Sorted (merge (b :: bs) (c :: d :: ds))
but is expected to have type
  Sorted (?m.542 :: ?m.543)
in the application
  Sorted.cons htail

location:
                      · simp [merge, hac]
                        have htail : Sorted (merge (a :: b :: bs) (d :: ds)) := ih hs2
                                                                               ^
                        refine Sorted.cons htail ?_
error: Type mismatch
  ih hs2
has type
  Sorted (merge (b :: bs) (d :: ds))
but is expected to have type
  Sorted (merge (a :: b :: bs) (d :: ds))

location:
                        have htail : Sorted (merge (a :: b :: bs) (d :: ds)) := ih hs2
                        refine Sorted.cons htail ?_
                                          ^
                        intro h
error: Application type mismatch: The argument
  htail
has type
  Sorted (merge (a :: b :: bs) (d :: ds))
but is expected to have type
  Sorted (?m.560 :: ?m.561)
in the application
  Sorted.cons htail

location:
                  by_cases h : x < y
                  · simp [merge, h, Sorted.cons, h]
                                ^
                  · simp [merge, h, Sorted.cons, h, Sorted.singleton]
error: This simp argument is unused:
  h
Hint: Omit it from the simp argument list.
  simp [merge, h̵,̵ ̵Sorted.cons, h]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
                  by_cases h : x < y
                  · simp [merge, h, Sorted.cons, h]
                                   ^
                  · simp [merge, h, Sorted.cons, h, Sorted.singleton]
error: This simp argument is unused:
  Sorted.cons
Hint: Omit it from the simp argument list.
  simp [merge, h, S̵o̵r̵t̵e̵d̵.̵c̵o̵n̵s̵,̵ ̵h]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
                  by_cases h : x < y
                  · simp [merge, h, Sorted.cons, h]
                                                ^
                  · simp [merge, h, Sorted.cons, h, Sorted.singleton]
error: This simp argument is unused:
  h
Hint: Omit it from the simp argument list.
  simp [merge, h, Sorted.cons,̵ ̵h̵]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
                  · simp [merge, h, Sorted.cons, h]
                  · simp [merge, h, Sorted.cons, h, Sorted.singleton]
                                ^
              | cons y₂ ys₂ =>
error: This simp argument is unused:
  h
Hint: Omit it from the simp argument list.
  simp [merge, h̵,̵ ̵Sorted.cons, h, Sorted.singleton]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
                  · simp [merge, h, Sorted.cons, h]
                  · simp [merge, h, Sorted.cons, h, Sorted.singleton]
                                   ^
              | cons y₂ ys₂ =>
error: This simp argument is unused:
  Sorted.cons
Hint: Omit it from the simp argument list.
  simp [merge, h, S̵o̵r̵t̵e̵d̵.̵c̵o̵n̵s̵,̵ ̵h, Sorted.singleton]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
                  · simp [merge, h, Sorted.cons, h]
                  · simp [merge, h, Sorted.cons, h, Sorted.singleton]
                                                ^
              | cons y₂ ys₂ =>
error: This simp argument is unused:
  h
Hint: Omit it from the simp argument list.
  simp [merge, h, Sorted.cons, h̵,̵ ̵Sorted.singleton]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
                  · simp [merge, h, Sorted.cons, h]
                  · simp [merge, h, Sorted.cons, h, Sorted.singleton]
                                                   ^
              | cons y₂ ys₂ =>
error: This simp argument is unused:
  Sorted.singleton
Hint: Omit it from the simp argument list.
  simp [merge, h, Sorted.cons, h,̵ ̵S̵o̵r̵t̵e̵d̵.̵s̵i̵n̵g̵l̵e̵t̵o̵n̵]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
                      by_cases hxy : x < y
                      · simp [merge, hxy]
                                    ^
                        exact Sorted.cons (Sorted.cons sys' hy) (by
error: This simp argument is unused:
  hxy
Hint: Omit it from the simp argument list.
  simp [merge,̵ ̵h̵x̵y̵]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
                      · by_cases hxy₂ : x < y₂
                        · simp [merge, hxy, hxy₂]
                                      ^
                          exact Sorted.cons (Sorted.cons (Sorted.singleton) hxy) hxy
error: This simp argument is unused:
  hxy
... [truncated, 4987 bytes total]
-/
