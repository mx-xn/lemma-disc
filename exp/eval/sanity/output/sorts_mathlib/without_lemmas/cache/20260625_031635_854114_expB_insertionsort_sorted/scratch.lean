import LeanSrc.Sorts_Mathlib

theorem expB_insertionsort_sorted [Preorder T] [DecidableRel (LT.lt (α := T))] {l : List T} : Sorted (insertionsort l) := by
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
          exact Sorted.cons Sorted.singleton h
        · simp [h]
          exact Sorted.cons Sorted.singleton h
    | cons hs_tail hba =>
        rename_i a b xs
        simp [insert_]
        by_cases hta : t < a
        · simp [hta]
          exact Sorted.cons (Sorted.cons hs_tail hba) hta
        · simp [hta]
          by_cases htb : t < b
          · simp [htb]
            exact Sorted.cons (Sorted.cons hs_tail htb) hba
          · simp [htb]
            exact Sorted.cons (sorted_insert t hs_tail) htb
  induction l with
  | nil =>
      simp [insertionsort]
      exact Sorted.nil
  | cons x xs ih =>
      simp [insertionsort]
      exact sorted_insert x ih


/- lean_check result: FAIL
error:
location:
            · simp [h]
              exact Sorted.cons Sorted.singleton h
                                                ^
            · simp [h]
error: Application type mismatch: The argument
  h
has type
  t < x
but is expected to have type
  ¬x < t
in the application
  Sorted.cons Sorted.singleton h

location:
            · simp [hta]
              exact Sorted.cons (Sorted.cons hs_tail hba) hta
                                                         ^
            · simp [hta]
error: Application type mismatch: The argument
  hta
has type
  t < a
but is expected to have type
  ¬a < t
in the application
  Sorted.cons (Sorted.cons hs_tail hba) hta

location:
              · simp [htb]
                exact Sorted.cons (Sorted.cons hs_tail htb) hba
                                                      ^
              · simp [htb]
error: Application type mismatch: The argument
  htb
has type
  t < b
but is expected to have type
  ¬b < t
in the application
  Sorted.cons hs_tail htb

location:
              · simp [htb]
                exact Sorted.cons (sorted_insert t hs_tail) htb
                                 ^
      induction l with
error: Application type mismatch: The argument
  sorted_insert t hs_tail
has type
  Sorted (insert_ t (b :: xs))
but is expected to have type
  Sorted (b :: insert_ t xs)
in the application
  Sorted.cons (sorted_insert t hs_tail)
-/
