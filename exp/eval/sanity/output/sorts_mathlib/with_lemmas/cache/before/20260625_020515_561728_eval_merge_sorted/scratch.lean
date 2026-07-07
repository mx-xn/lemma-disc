import LeanSrc.Sorts_Mathlib

theorem lemma_hint_0 [DecidableEq T] (l : List T) : Permut l l := by admit
theorem lemma_hint_1 [Preorder T] [DecidableRel (LT.lt (α := T))] (x : T) (p : ¬t < x) (h : T) (xs : List T) (s : Sorted (x :: h :: xs)) : Sorted (h :: xs) := by admit
theorem lemma_hint_2 [LT T] (x : T) (xs : List T) (s : Sorted (x :: xs)) : Sorted xs := by admit
theorem lemma_hint_3 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) (x : T) (p : ¬t < x) : Sorted (x :: insert_ t []) := by admit
theorem lemma_hint_4 [DecidableEq T] (l : List T) (t' : T) (h1 : count1 l t' = count1 l t') : Permut l l := by admit
theorem lemma_hint_5 [Preorder T] [DecidableRel (LT.lt (α := T))] (x : T) (h : T) (xs : List T) (s : Sorted (x :: h :: xs)) : Sorted (h :: xs) := by admit
theorem lemma_hint_6 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : Permut ([] : List T) [] := by admit
theorem lemma_hint_7 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) : Sorted (insert_ t []) := by admit
theorem lemma_hint_8 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) (x : T) (h : T) (xs : List T) (s : Sorted (x :: h :: xs)) (h1 : Sorted (h :: insert_ t xs)) : Sorted (x :: h :: insert_ t xs) := by admit
theorem lemma_hint_9 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) : Permut (e :: x :: xs) (e :: x :: xs) := by admit

theorem eval_merge_sorted [Preorder T] [DecidableRel (LT.lt (α := T))] {xs ys : List T} (sxs : Sorted xs) (sys : Sorted ys) : Sorted (merge xs ys) := by
  induction xs generalizing ys with
  | nil =>
    simpa [merge] using sys
  | cons a xs ih =>
    cases xs with
    | nil =>
      cases ys with
      | nil =>
        simp [merge]
      | cons y ys' =>
        simp [merge]
        by_cases h : a < y
        · simp [h]
          exact Sorted.cons sys h
        · simp [h]
          cases sys with
          | singleton =>
            exact Sorted.singleton
          | cons sys' hy =>
            exact Sorted.cons sys' h
    | cons b xs' =>
      cases sxs with
      | cons sbxs hba =>
        cases ys with
        | nil =>
          simp [merge]
          exact Sorted.cons sbxs hba
        | cons y ys' =>
          by_cases hay : a < y
          · simp [merge, hay]
            apply Sorted.cons
            · exact ih sbxs sys
            · exact hba
          · simp [merge, hay]
            apply Sorted.cons
            · exact ih sxs (lemma_hint_2 y (y :: ys') sys)
            · exact hay


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
a : T
ih : ∀ {ys : List T}, Sorted [] → Sorted ys → Sorted (merge [] ys)
sxs : Sorted [a]
sys : Sorted []
⊢ Sorted [a]

location:
            · simp [h]
              exact Sorted.cons sys h
                                   ^
            · simp [h]
error: Application type mismatch: The argument
  h
has type
  a < y
but is expected to have type
  ¬y < a
in the application
  Sorted.cons sys h

location:
              | singleton =>
                exact Sorted.singleton
               ^
              | cons sys' hy =>
error: Type mismatch
  Sorted.singleton
has type
  Sorted [?m.173]
but is expected to have type
  Sorted (y :: merge [a] [])

location:
              | cons sys' hy =>
                exact Sorted.cons sys' h
                                      ^
        | cons b xs' =>
error: Application type mismatch: The argument
  h
has type
  ¬a < y
but is expected to have type
  ¬b✝ < ?m.221
in the application
  Sorted.cons sys' h

location:
              · simp [merge, hay]
                apply Sorted.cons
               ^
                · exact ih sbxs sys
error: Tactic `apply` failed: could not unify the conclusion of `@Sorted.cons`
  Sorted (?a :: ?b :: ?xs)
with the goal
  Sorted (a :: if b < y then b :: merge xs' (y :: ys') else y :: merge (b :: xs') ys')
Note: The full type of `@Sorted.cons` is
  ∀ {T : Type ?u.3844} [inst : LT T] {a b : T} {xs : List T}, Sorted (b :: xs) → ¬b < a → Sorted (a :: b :: xs)
case pos
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
a b : T
xs' : List T
ih : ∀ {ys : List T}, Sorted (b :: xs') → Sorted ys → Sorted (merge (b :: xs') ys)
hba : ¬b < a
sbxs : Sorted (b :: xs')
y : T
ys' : List T
sys : Sorted (y :: ys')
hay : a < y
⊢ Sorted (a :: if b < y then b :: merge xs' (y :: ys') else y :: merge (b :: xs') ys')

location:
              · simp [merge, hay]
                apply Sorted.cons
               ^
                · exact ih sxs (lemma_hint_2 y (y :: ys') sys)
error: Tactic `apply` failed: could not unify the conclusion of `@Sorted.cons`
  Sorted (?a :: ?b :: ?xs)
with the goal
  Sorted (y :: merge (a :: b :: xs') ys')
Note: The full type of `@Sorted.cons` is
  ∀ {T : Type ?u.3989} [inst : LT T] {a b : T} {xs : List T}, Sorted (b :: xs) → ¬b < a → Sorted (a :: b :: xs)
case neg
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
a b : T
xs' : List T
ih : ∀ {ys : List T}, Sorted (b :: xs') → Sorted ys → Sorted (merge (b :: xs') ys)
hba : ¬b < a
sbxs : Sorted (b :: xs')
y : T
ys' : List T
sys : Sorted (y :: ys')
hay : ¬a < y
⊢ Sorted (y :: merge (a :: b :: xs') ys')
-/
