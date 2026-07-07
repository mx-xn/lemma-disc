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
    intro ys sxs sys
    simpa [merge] using sys
  | cons a xs ih =>
    intro ys sxs sys
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
            · exact ih (y :: ys') sbxs sys
            · exact hba
          · simp [merge, hay]
            apply Sorted.cons
            · exact ih ys' sxs (lemma_hint_2 y (y :: ys') sys)
            · exact hay


/- lean_check result: FAIL
error:
location:
      | nil =>
        intro ys sxs sys
             ^
        simpa [merge] using sys
error: Tactic `introN` failed: There are no additional binders or `let` bindings in the goal to introduce
case nil
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
ys : List T
sxs : Sorted []
sys : Sorted ys
⊢ Sorted (merge [] ys)

location:
      | cons a xs ih =>
        intro ys sxs sys
             ^
        cases xs with
error: Tactic `introN` failed: There are no additional binders or `let` bindings in the goal to introduce
case cons
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
a : T
xs : List T
ih : ∀ {ys : List T}, Sorted xs → Sorted ys → Sorted (merge xs ys)
ys : List T
sxs : Sorted (a :: xs)
sys : Sorted ys
⊢ Sorted (merge (a :: xs) ys)
-/
