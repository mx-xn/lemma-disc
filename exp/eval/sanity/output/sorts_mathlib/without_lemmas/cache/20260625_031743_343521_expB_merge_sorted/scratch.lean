import LeanSrc.Sorts_Mathlib

theorem expB_merge_sorted [Preorder T] [DecidableRel (LT.lt (α := T))] {xs ys : List T} (sxs : Sorted xs) (sys : Sorted ys) : Sorted (merge xs ys) := by
  induction sxs generalizing ys with
  | nil =>
      simpa [merge] using sys
  | singleton x =>
      cases sys with
      | nil =>
          simpa [merge] using (Sorted.singleton : Sorted [x])
      | singleton y =>
          by_cases h : x < y
          · have hyx : ¬ y < x := by
              intro hyx
              have : x < x := lt_of_lt_of_le h (le_of_lt hyx)
              exact lt_irrefl _ this
            simpa [merge, h] using (Sorted.cons (Sorted.singleton : Sorted [y]) hyx)
          · simpa [merge, h] using (Sorted.cons (Sorted.singleton : Sorted [x]) h)
      | cons y z zs hs hzy =>
          by_cases h : x < y
          · have hyx : ¬ y < x := by
              intro hyx
              have : x < x := lt_of_lt_of_le h (le_of_lt hyx)
              exact lt_irrefl _ this
            simpa [merge, h] using (Sorted.cons (Sorted.cons hs hzy) hyx)
          · simpa [merge, h] using (Sorted.cons (Sorted.cons hs hzy) hzy)
  | cons a b xs hs hba ih =>
      cases sys with
      | nil =>
          simpa [merge] using (Sorted.cons hs hba)
      | singleton x =>
          by_cases h : a < x
          · have hxa : ¬ x < a := by
              intro hxa
              have : a < a := lt_of_lt_of_le h (le_of_lt hxa)
              exact lt_irrefl _ this
            simpa [merge, h] using (Sorted.cons (Sorted.cons hs hba) hxa)
          · simpa [merge, h] using (Sorted.cons (ih (Sorted.singleton : Sorted [x])) hba)
      | cons c d ys hs' hdc =>
          by_cases h : a < c
          · simpa [merge, h] using (Sorted.cons (ih (Sorted.cons hs' hdc)) hba)
          · simpa [merge, h] using (Sorted.cons (Sorted.cons (ih hs') hdc) hdc)


/- lean_check result: FAIL
error:
location:
          simpa [merge] using sys
      | singleton x =>
     ^
          cases sys with
error: Too many variable names provided at alternative `singleton`: 1 provided, but 0 expected

location:
          | nil =>
              simpa [merge] using (Sorted.singleton : Sorted [x])
                                                             ^
          | singleton y =>
error: error(lean.unknownIdentifier): Unknown identifier `x`

location:
              simpa [merge] using (Sorted.singleton : Sorted [x])
          | singleton y =>
         ^
              by_cases h : x < y
error: Too many variable names provided at alternative `singleton`: 1 provided, but 0 expected

location:
          | singleton y =>
              by_cases h : x < y
                          ^
              · have hyx : ¬ y < x := by
error: error(lean.unknownIdentifier): Unknown identifier `x`

location:
          | singleton y =>
              by_cases h : x < y
                              ^
              · have hyx : ¬ y < x := by
error: error(lean.unknownIdentifier): Unknown identifier `y`

location:
              · simpa [merge, h] using (Sorted.cons (Sorted.singleton : Sorted [x]) h)
          | cons y z zs hs hzy =>
         ^
              by_cases h : x < y
error: Too many variable names provided at alternative `cons`: 5 provided, but 2 expected

location:
          | cons y z zs hs hzy =>
              by_cases h : x < y
                          ^
              · have hyx : ¬ y < x := by
error: error(lean.unknownIdentifier): Unknown identifier `x`

location:
              · simpa [merge, h] using (Sorted.cons (Sorted.cons hs hzy) hzy)
      | cons a b xs hs hba ih =>
     ^
          cases sys with
error: Too many variable names provided at alternative `cons`: 6 provided, but 3 expected

location:
          | nil =>
              simpa [merge] using (Sorted.cons hs hba)
                                              ^
          | singleton x =>
error: error(lean.unknownIdentifier): Unknown identifier `hs`

location:
          | nil =>
              simpa [merge] using (Sorted.cons hs hba)
                                                 ^
          | singleton x =>
error: error(lean.unknownIdentifier): Unknown identifier `hba`

location:
              simpa [merge] using (Sorted.cons hs hba)
          | singleton x =>
         ^
              by_cases h : a < x
error: Too many variable names provided at alternative `singleton`: 1 provided, but 0 expected

location:
          | singleton x =>
              by_cases h : a < x
                              ^
              · have hxa : ¬ x < a := by
error: error(lean.unknownIdentifier): Unknown identifier `x`

location:
              · simpa [merge, h] using (Sorted.cons (ih (Sorted.singleton : Sorted [x])) hba)
          | cons c d ys hs' hdc =>
         ^
              by_cases h : a < c
error: Too many variable names provided at alternative `cons`: 5 provided, but 2 expected

location:
          | cons c d ys hs' hdc =>
              by_cases h : a < c
                              ^
              · simpa [merge, h] using (Sorted.cons (ih (Sorted.cons hs' hdc)) hba)
error: Type mismatch
  c
has type
  Sorted (b✝ :: xs✝)
but is expected to have type
  Sorted (b✝¹ :: xs✝¹)

location:
              by_cases h : a < c
              · simpa [merge, h] using (Sorted.cons (ih (Sorted.cons hs' hdc)) hba)
                                                    ^
              · simpa [merge, h] using (Sorted.cons (Sorted.cons (ih hs') hdc) hdc)
error: error(lean.unknownIdentifier): Unknown identifier `ih`

location:
              by_cases h : a < c
              · simpa [merge, h] using (Sorted.cons (ih (Sorted.cons hs' hdc)) hba)
                                                                              ^
              · simpa [merge, h] using (Sorted.cons (Sorted.cons (ih hs') hdc) hdc)
error: error(lean.unknownIdentifier): Unknown identifier `hba`

location:
              · simpa [merge, h] using (Sorted.cons (ih (Sorted.cons hs' hdc)) hba)
              · simpa [merge, h] using (Sorted.cons (Sorted.cons (ih hs') hdc) hdc)
                                                                 ^
error: error(lean.unknownIdentifier): Unknown identifier `ih`

location:
              · simpa [merge, h] using (Sorted.cons (ih (Sorted.cons hs' hdc)) hba)
              · simpa [merge, h] using (Sorted.cons (Sorted.cons (ih hs') hdc) hdc)
                                                                         ^
error: error(lean.unknownIdentifier): Unknown identifier `hdc`

location:
              · simpa [merge, h] using (Sorted.cons (ih (Sorted.cons hs' hdc)) hba)
              · simpa [merge, h] using (Sorted.cons (Sorted.cons (ih hs') hdc) hdc)
                                                                              ^
error: error(lean.unknownIdentifier): Unknown identifier `hdc`
-/
