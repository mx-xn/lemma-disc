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
  induction sxs with
  | nil =>
    simpa [merge] using sys
  | singleton =>
    cases ys with
    | nil =>
      simp [merge]
    | cons y ys' =>
      simp [merge]
      by_cases hxy : x < y
      · simp [hxy]
        exact Sorted.cons sys hxy
      · simp [hxy]
        cases sys with
        | singleton =>
          exact Sorted.singleton
        | cons sys' hyx =>
          apply Sorted.cons
          · exact sys'
          · intro h
            exact hxy ((Preorder.le_iff_not_gt.mp (Preorder.le_of_not_gt h)) )
  | @cons a b xs sbxs hba ih =>
    cases ys with
    | nil =>
      simp [merge]
      exact Sorted.cons sbxs hba
    | cons y ys' =>
      simp [merge]
      by_cases hay : a < y
      · simp [hay]
        have hs : Sorted (merge (b :: xs) (y :: ys')) := ih sys
        apply Sorted.cons
        · exact hs
        · intro h
          dsimp [merge] at hs
          by_cases hby : b < y
          · have : merge (b :: xs) (y :: ys') = b :: merge xs (y :: ys') := by simp [merge, hby]
            rw [this] at h
            exact hba h
          · have : merge (b :: xs) (y :: ys') = y :: merge (b :: xs) ys' := by simp [merge, hby]
            rw [this] at h
            exact (Preorder.lt_irrefl y) ((Preorder.lt_of_lt_of_le hay) (Preorder.le_of_not_gt h))
      · simp [hay]
        have hya : ¬ a < y := by
          intro h
          exact hay ((Preorder.le_iff_not_gt.mp (Preorder.le_of_not_gt h)))
        cases sbxs with
        | singleton =>
          apply Sorted.cons
          · exact sys
          · exact hya
        | cons srest hbb =>
          apply Sorted.cons
          · exact ih sys
          · exact hya


/- lean_check result: FAIL
error:
location:
        cases ys with
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
sys : Sorted []
⊢ Sorted [x✝]

location:
          simp [merge]
          by_cases hxy : x < y
                        ^
          · simp [hxy]
error: error(lean.unknownIdentifier): Unknown identifier `x`

location:
          by_cases hxy : x < y
          · simp [hxy]
           ^
            exact Sorted.cons sys hxy
error: `simp` made no progress

location:
            exact Sorted.cons sys hxy
          · simp [hxy]
           ^
            cases sys with
error: `simp` made no progress

location:
          · simp [hay]
            have hs : Sorted (merge (b :: xs) (y :: ys')) := ih sys
                                                            ^
            apply Sorted.cons
error: Function expected at
  ih
but this term has type
  Sorted (merge (b :: xs) (y :: ys'))
Note: Expected a function because this term is being applied to the argument
  sys

location:
            have hs : Sorted (merge (b :: xs) (y :: ys')) := ih sys
            apply Sorted.cons
           ^
            · exact hs
error: Tactic `apply` failed: could not unify the conclusion of `@Sorted.cons`
  Sorted (?a :: ?b :: ?xs)
with the goal
  Sorted (a :: if b < y then b :: merge xs (y :: ys') else y :: merge (b :: xs) ys')
Note: The full type of `@Sorted.cons` is
  ∀ {T : Type ?u.3463} [inst : LT T] {a b : T} {xs : List T}, Sorted (b :: xs) → ¬b < a → Sorted (a :: b :: xs)
case pos
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
xs✝ : List T
a b : T
xs : List T
sbxs : Sorted (b :: xs)
hba : ¬b < a
y : T
ys' : List T
sys : Sorted (y :: ys')
ih : Sorted (merge (b :: xs) (y :: ys'))
hay : a < y
hs : Sorted (merge (b :: xs) (y :: ys'))
⊢ Sorted (a :: if b < y then b :: merge xs (y :: ys') else y :: merge (b :: xs) ys')

location:
              intro h
              exact hay ((Preorder.le_iff_not_gt.mp (Preorder.le_of_not_gt h)))
                         ^
            cases sbxs with
error: error(lean.unknownIdentifier): Unknown constant `Preorder.le_iff_not_gt.mp`

location:
            | singleton =>
              apply Sorted.cons
             ^
              · exact sys
error: Tactic `apply` failed: could not unify the conclusion of `@Sorted.cons`
  Sorted (?a :: ?b :: ?xs)
with the goal
  Sorted (y :: merge [a, b] ys')
Note: The full type of `@Sorted.cons` is
  ∀ {T : Type ?u.3681} [inst : LT T] {a b : T} {xs : List T}, Sorted (b :: xs) → ¬b < a → Sorted (a :: b :: xs)
case neg.singleton
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
xs : List T
a b : T
hba : ¬b < a
y : T
ys' : List T
sys : Sorted (y :: ys')
hay hya : ¬a < y
ih : Sorted (merge [b] (y :: ys'))
⊢ Sorted (y :: merge [a, b] ys')

location:
            | cons srest hbb =>
              apply Sorted.cons
             ^
              · exact ih sys
error: Tactic `apply` failed: could not unify the conclusion of `@Sorted.cons`
  Sorted (?a :: ?b :: ?xs)
with the goal
  Sorted (y :: merge (a :: b :: b✝ :: xs✝) ys')
Note: The full type of `@Sorted.cons` is
  ∀ {T : Type ?u.3790} [inst : LT T] {a b : T} {xs : List T}, Sorted (b :: xs) → ¬b < a → Sorted (a :: b :: xs)
case neg.cons
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
xs : List T
a b : T
hba : ¬b < a
y : T
ys' : List T
sys : Sorted (y :: ys')
hay hya : ¬a < y
b✝ : T
xs✝ : List T
srest : Sorted (b✝ :: xs✝)
hbb : ¬b✝ < b
ih : Sorted (merge (b :: b✝ :: xs✝) (y :: ys'))
⊢ Sorted (y :: merge (a :: b :: b✝ :: xs✝) ys')
-/
