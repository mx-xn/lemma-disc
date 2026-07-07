import LeanSrc.Sorts_Mathlib

theorem expB_insertionsort_correct (T : Type) [Preorder T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : SortCorrect (insertionsort : List T -> List T) := by
  let rec insert_sorted
      (t : T) :
      ∀ l, Sorted l → Sorted (insert_ t l) := by
        intro l hs
        cases hs with
        | nil =>
            simp [insert_]
            exact Sorted.singleton
        | singleton =>
            rename_i x
            by_cases htx : t < x
            · simp [insert_, htx]
              exact Sorted.cons Sorted.singleton (by
                intro hxt
                exact not_lt_of_ge (le_of_lt hxt) htx)
            · simp [insert_, htx]
              by_cases hxt : x < t
              · exact Sorted.cons Sorted.singleton hxt
              · exact Sorted.cons Sorted.singleton hxt
        | cons hs' hba =>
            rename_i a b xs
            by_cases hta : t < a
            · simp [insert_, hta]
              exact Sorted.cons (Sorted.cons hs' hba) (by
                intro hat
                exact not_lt_of_ge (le_of_lt hat) hta)
            · simp [insert_, hta]
              by_cases htb : t < b
              · simp [insert_, htb]
                exact Sorted.cons (Sorted.cons hs' (by
                  intro hbt
                  exact hta (lt_of_lt_of_le hbt (le_of_lt htb)))) hba
              · simp [insert_, htb]
                exact Sorted.cons (insert_sorted t (b :: xs) hs') hba
  let rec insert_permut
      (t : T) :
      ∀ l u, count1 (insert_ t l) u = count1 (t :: l) u := by
        intro l u
        cases l with
        | nil =>
            simp [insert_]
        | cons x xs =>
            simp [insert_]
            by_cases h : t < x
            · simp [h, count1]
            · simp [h, count1, insert_permut t xs u, Nat.add_left_comm, Nat.add_comm]
  intro l
  induction l with
  | nil =>
      constructor
      · simp [insertionsort]
        exact Sorted.nil
      · intro t
        simp [insertionsort, count1]
  | cons x xs ih =>
      rcases ih with ⟨hs, hp⟩
      constructor
      · simp [insertionsort]
        exact insert_sorted x (insertionsort xs) hs
      · intro t
        simp [insertionsort]
        rw [insert_permut x (insertionsort xs) t]
        simp [count1, hp t]


/- lean_check result: FAIL
error:
location:
                  by_cases hxt : x < t
                  · exact Sorted.cons Sorted.singleton hxt
                                                      ^
                  · exact Sorted.cons Sorted.singleton hxt
error: Application type mismatch: The argument
  hxt
has type
  x < t
but is expected to have type
  ¬t < x
in the application
  Sorted.cons Sorted.singleton hxt

location:
                  · exact Sorted.cons Sorted.singleton hxt
                  · exact Sorted.cons Sorted.singleton hxt
                                                      ^
            | cons hs' hba =>
error: Application type mismatch: The argument
  hxt
has type
  ¬x < t
but is expected to have type
  ¬t < x
in the application
  Sorted.cons Sorted.singleton hxt

location:
                      intro hbt
                      exact hta (lt_of_lt_of_le hbt (le_of_lt htb)))) hba
                                                                     ^
                  · simp [insert_, htb]
error: Application type mismatch: The argument
  hba
has type
  ¬b < a
but is expected to have type
  ¬t < a
in the application
  Sorted.cons (Sorted.cons hs' ?m.236) hba

location:
                      intro hbt
                      exact hta (lt_of_lt_of_le hbt (le_of_lt htb)))) hba
                                                             ^
                  · simp [insert_, htb]
error: Application type mismatch: The argument
  htb
has type
  t < b
but is expected to have type
  ?m.247 < a
in the application
  le_of_lt htb

location:
                  · simp [insert_, htb]
                    exact Sorted.cons (insert_sorted t (b :: xs) hs') hba
                                     ^
      let rec insert_permut
error: Application type mismatch: The argument
  insert_sorted t (b :: xs) hs'
has type
  Sorted (insert_ t (b :: xs))
but is expected to have type
  Sorted (b :: insert_ t xs)
in the application
  Sorted.cons (insert_sorted t (b :: xs) hs')

location:
                  by_cases htb : t < b
                  · simp [insert_, htb]
                         ^
                    exact Sorted.cons (Sorted.cons hs' (by
error: This simp argument is unused:
  insert_
Hint: Omit it from the simp argument list.
  simp [i̵n̵s̵e̵r̵t̵_̵,̵ ̵htb]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
                      exact hta (lt_of_lt_of_le hbt (le_of_lt htb)))) hba
                  · simp [insert_, htb]
                         ^
                    exact Sorted.cons (insert_sorted t (b :: xs) hs') hba
error: This simp argument is unused:
  insert_
Hint: Omit it from the simp argument list.
  simp [i̵n̵s̵e̵r̵t̵_̵,̵ ̵htb]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`
-/
