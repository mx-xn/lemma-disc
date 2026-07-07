import LeanSrc.Sorts_Mathlib

theorem expB_insertionsort_sorted [Preorder T] [DecidableRel (LT.lt (α := T))] {l : List T} : Sorted (insertionsort l) := by
  have not_lt_of_lt : ∀ {a b : T}, a < b → ¬ b < a := by
    intro a b hab hba
    have haa : a < a := lt_trans hab hba
    exact lt_irrefl a haa
  let rec sorted_insert (t : T) : ∀ {l : List T}, Sorted l → Sorted (insert_ t l) := by
    intro l hs
    cases hs with
    | nil =>
        simp [insert_]
        exact Sorted.singleton
    | singleton =>
        rename_i x
        simp [insert_]
        by_cases h : t < x
        · simp [h]
          exact Sorted.cons Sorted.singleton (not_lt_of_lt h)
        · simp [h]
          exact Sorted.cons Sorted.singleton h
    | cons hs_tail hba =>
        rename_i a b xs
        simp [insert_]
        by_cases hta : t < a
        · simp [hta]
          exact Sorted.cons (Sorted.cons hs_tail hba) (not_lt_of_lt hta)
        · simp [hta]
          by_cases htb : t < b
          · simp [htb]
            exact Sorted.cons (Sorted.cons hs_tail (not_lt_of_lt htb)) hta
          · simp [htb]
            have hs' : Sorted (b :: insert_ t xs) := by
              simpa [insert_, htb] using (sorted_insert t hs_tail)
            exact Sorted.cons hs' hba
  induction l with
  | nil =>
      simp [insertionsort]
      exact Sorted.nil
  | cons x xs ih =>
      simp [insertionsort]
      exact sorted_insert x ih


/- lean_check result: ok -/
