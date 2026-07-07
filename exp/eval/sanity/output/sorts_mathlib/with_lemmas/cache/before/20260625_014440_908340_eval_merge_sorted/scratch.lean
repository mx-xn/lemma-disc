import LeanSrc.Sorts_Mathlib

theorem lemma_hint_0 [Preorder T] [DecidableRel (LT.lt (α := T))] (x : T) (p : ¬t < x) (h : T) (xs : List T) (s : Sorted (x :: h :: xs)) : Sorted (h :: xs) := by admit
theorem lemma_hint_1 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) (x : T) (p : ¬t < x) : Sorted (x :: insert_ t []) := by admit
theorem lemma_hint_2 [DecidableEq T] (l : List T) (t' : T) (h1 : count1 l t' = count1 l t') : Permut l l := by admit
theorem lemma_hint_3 [Preorder T] [DecidableRel (LT.lt (α := T))] (x : T) (h : T) (xs : List T) (s : Sorted (x :: h :: xs)) : Sorted (h :: xs) := by admit
theorem lemma_hint_4 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : Permut ([] : List T) [] := by admit
theorem lemma_hint_5 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) : Sorted (insert_ t []) := by admit
theorem lemma_hint_6 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) (x : T) (h : T) (xs : List T) (s : Sorted (x :: h :: xs)) (h1 : Sorted (h :: insert_ t xs)) : Sorted (x :: h :: insert_ t xs) := by admit
theorem lemma_hint_7 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) : Permut (e :: x :: xs) (e :: x :: xs) := by admit
theorem lemma_hint_8 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) (x : T) (xs : List T) (IH : Sorted xs → Sorted (insert_ t xs)) (s : Sorted (x :: xs)) (p : t < x) : Sorted (if t < x then t :: x :: xs else x :: insert_ t xs) := by admit
theorem lemma_hint_9 [Preorder T] [DecidableRel (LT.lt (α := T))] (x : T) (t : T) (p : ¬t < x) (h : T) (xs : List T) (s : Sorted (x :: h :: xs)) (h1 : Sorted (if t < h then t :: h :: xs else h :: insert_ t xs)) (pp : t < h) : Sorted (x :: if t < h then t :: h :: xs else h :: insert_ t xs) := by admit

theorem eval_merge_sorted [Preorder T] [DecidableRel (LT.lt (α := T))] {xs ys : List T} (sxs : Sorted xs) (sys : Sorted ys) : Sorted (merge xs ys) := by
  revert ys
  induction xs with
  | nil =>
    intro ys sxs sys
    simpa [merge] using sys
  | cons x xs ih =>
    intro ys sxs sys
    cases xs with
    | nil =>
      cases ys with
      | nil =>
        simpa [merge] using Sorted.singleton
      | cons y ys =>
        cases ys with
        | nil =>
          by_cases hxy : x < y
          · simp [merge, hxy]
            exact Sorted.singleton
          · simp [merge, hxy]
            exact Sorted.cons Sorted.singleton hxy
        | cons y2 ys =>
          have sysTail : Sorted (y2 :: ys) := lemma_hint_3 y y2 ys sys
          by_cases hxy : x < y
          · simp [merge, hxy]
            exact Sorted.cons sys hxy
          · simp [merge, hxy]
            exact Sorted.cons (ih sysTail Sorted.singleton) hxy
    | cons x2 xs =>
      cases sxs with
      | cons srest hx2x =>
        cases ys with
        | nil =>
          simpa [merge] using Sorted.cons srest hx2x
        | cons y ys =>
          cases ys with
          | nil =>
            by_cases hxy : x < y
            · simp [merge, hxy]
              by_cases hx2y : x2 < y
              · simp [merge, hx2y]
                exact Sorted.cons (Sorted.cons Sorted.singleton hx2x) (by
                  intro hyx
                  exact hx2x (lt_of_lt_of_le hyx (le_of_not_gt hxy)))
              · simp [merge, hx2y]
                exact Sorted.cons (Sorted.cons Sorted.singleton hx2y) hxy
            · simp [merge, hxy]
              exact Sorted.cons (Sorted.cons srest hx2x) hxy
          | cons y2 ys =>
            have sysTail : Sorted (y2 :: ys) := lemma_hint_3 y y2 ys sys
            by_cases hxy : x < y
            · simp [merge, hxy]
              have hmerge : Sorted (merge (x2 :: xs) (y :: y2 :: ys)) := ih sys (Sorted.cons srest hx2x)
              apply Sorted.cons hmerge
              by_cases hx2y : x2 < y
              · intro hyx
                exact hx2x (lt_of_lt_of_le hyx (le_of_not_gt hx2y))
              · intro hyx
                exact hxy (lt_of_lt_of_le hyx (le_of_not_gt hxy))
            · simp [merge, hxy]
              have hmerge : Sorted (merge (x :: x2 :: xs) (y2 :: ys)) := ih sysTail (Sorted.cons srest hx2x)
              apply Sorted.cons hmerge
              by_cases hxy2 : x < y2
              · intro hy2y
                exact hxy (lt_of_lt_of_le hy2y (le_of_not_gt hxy2))
              · intro hy2y
                have hy2x : ¬ y2 < x := hxy2
                exact hy2x (lt_of_lt_of_le hy2y (le_of_not_gt hxy))


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
sxs✝ : Sorted []
ys : List T
sxs : Sorted ys
⊢ Sorted (merge [] ys)

location:
      | cons x xs ih =>
        intro ys sxs sys
                    ^
        cases xs with
error: Tactic `introN` failed: There are no additional binders or `let` bindings in the goal to introduce
case cons
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
x : T
xs : List T
ih : Sorted xs → ∀ {ys : List T}, Sorted ys → Sorted (merge xs ys)
sxs✝ : Sorted (x :: xs)
ys : List T
sxs : Sorted ys
⊢ Sorted (merge (x :: xs) ys)
-/
