import LeanSrc.Sorts_Mathlib

theorem expB_insertionsort_correct (T : Type) [Preorder T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : SortCorrect (insertionsort : List T -> List T) := by
  let rec insert_sorted
      (t : T) :
      ∀ l, Sorted l → Sorted (insert_ t l) := by
        intro l hs
        cases hs with
        | nil =>
            simp [insert_]
        | singleton =>
            rename_i x
            simp [insert_]
            by_cases h : t < x
            · simp [h]
              exact Sorted.cons Sorted.singleton h
            · simp [h]
              exact Sorted.cons Sorted.singleton h
        | cons hs' hba =>
            rename_i a b xs
            simp [insert_]
            by_cases hta : t < a
            · simp [hta]
              exact Sorted.cons (Sorted.cons hs' hba) hta
            · simp [hta]
              by_cases htb : t < b
              · simp [htb]
                exact Sorted.cons (Sorted.cons hs' htb) hta
              · simp [htb]
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
            · simp [h, count1, insert_permut t xs u, Nat.add_assoc, Nat.add_left_comm, Nat.add_comm]
  intro l
  induction l with
  | nil =>
      constructor
      · simp [insertionsort, Sorted.nil]
      · intro t
        simp [insertionsort, Permut, count1]
  | cons x xs ih =>
      rcases ih with ⟨hs, hp⟩
      constructor
      · simp [insertionsort]
        exact insert_sorted x (insertionsort xs) hs
      · intro t
        simp [insertionsort]
        rw [insert_permut x (insertionsort xs) t, hp t]


/- lean_check result: FAIL
error:
location:
            cases hs with
            | nil =>
                 ^
                simp [insert_]
error: unsolved goals
case nil
T : Type
inst✝² : Preorder T
inst✝¹ : DecidableEq T
inst✝ : DecidableRel LT.lt
t : T
⊢ Sorted [t]

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
                  exact Sorted.cons (Sorted.cons hs' hba) hta
                                                         ^
                · simp [hta]
error: Application type mismatch: The argument
  hta
has type
  t < a
but is expected to have type
  ¬a < t
in the application
  Sorted.cons (Sorted.cons hs' hba) hta

location:
                  · simp [htb]
                    exact Sorted.cons (Sorted.cons hs' htb) hta
                                                      ^
                  · simp [htb]
error: Application type mismatch: The argument
  htb
has type
  t < b
but is expected to have type
  ¬b < t
in the application
  Sorted.cons hs' htb

location:
                  · simp [htb]
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
            simp [insertionsort]
            rw [insert_permut x (insertionsort xs) t, hp t]
                                                     ^
error: Tactic `rewrite` failed: Did not find an occurrence of the pattern
  count1 (insertionsort xs) t
in the target expression
  count1 (x :: insertionsort xs) t = count1 (x :: xs) t
case cons.right
T : Type
inst✝² : Preorder T
inst✝¹ : DecidableEq T
inst✝ : DecidableRel LT.lt
x : T
xs : List T
hs : Sorted (insertionsort xs)
hp : Permut (insertionsort xs) xs
t : T
⊢ count1 (x :: insertionsort xs) t = count1 (x :: xs) t

location:
                · simp [h, count1]
                · simp [h, count1, insert_permut t xs u, Nat.add_assoc, Nat.add_left_comm, Nat.add_comm]
                                                        ^
      intro l
error: This simp argument is unused:
  Nat.add_assoc
Hint: Omit it from the simp argument list.
  simp [h, count1, insert_permut t xs u, Nat.add_a̵s̵s̵o̵c̵,̵ ̵N̵a̵t̵.̵a̵d̵d̵_̵left_comm, Nat.add_comm]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
          · intro t
            simp [insertionsort, Permut, count1]
                                ^
      | cons x xs ih =>
error: This simp argument is unused:
  Permut
Hint: Omit it from the simp argument list.
  simp [insertionsort, P̵e̵r̵m̵u̵t̵,̵ ̵count1]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`
-/
