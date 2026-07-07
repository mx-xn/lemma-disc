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
theorem lemma_hint_10 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) (x : T) (xs : List T) (IH : Sorted xs → Sorted (insert_ t xs)) (s : Sorted (x :: xs)) (p : t < x) : Sorted (if t < x then t :: x :: xs else x :: insert_ t xs) := by admit
theorem lemma_hint_11 [Preorder T] [DecidableRel (LT.lt (α := T))] (x : T) (t : T) (p : ¬t < x) (h : T) (xs : List T) (s : Sorted (x :: h :: xs)) (h1 : Sorted (if t < h then t :: h :: xs else h :: insert_ t xs)) (pp : t < h) : Sorted (x :: if t < h then t :: h :: xs else h :: insert_ t xs) := by admit
theorem lemma_hint_12 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) (x : T) (h : T) (xs : List T) (p : ¬t < x) (IH : Sorted (h :: xs) → Sorted (insert_ t (h :: xs))) : Sorted (insert_ t (h :: xs)) := by admit
theorem lemma_hint_13 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) (x : T) (p : ¬t < x) (h : T) (xs : List T) (IH : Sorted (h :: xs) → Sorted (insert_ t (h :: xs))) (s : Sorted (x :: h :: xs)) : Sorted (insert_ t (h :: xs)) := by admit
theorem lemma_hint_14 [LT T] (x : T) (h : T) (xs : List T) (s : Sorted (x :: h :: xs)) : ¬h < x := by admit
theorem lemma_hint_15 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) (x : T) (h : T) (xs : List T) (p : ¬t < x) (IH : Sorted (h :: xs) → Sorted (insert_ t (h :: xs))) (s : Sorted (x :: h :: xs)) (p : ¬t < x) (a : ¬h < x) (h1 : Sorted (h :: xs)) : Sorted (insert_ t (h :: xs)) := by admit
theorem lemma_hint_16 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (t' : T) (h1 : count1 (e :: x :: xs) t' = count1 (e :: x :: xs) t') : Permut (e :: x :: xs) (e :: x :: xs) := by admit
theorem lemma_hint_17 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_18 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (t' : T) (h1 : count1 [] t' = count1 [] t') : Permut ([] : List T) [] := by admit
theorem lemma_hint_19 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) (h1 : ∀ (t : T), count1 (e :: x :: xs) t = count1 (e :: x :: xs) t) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_20 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) : Permut [e] [e] := by admit
theorem lemma_hint_21 [LT T] (a b : T) (l : List T) (s : Sorted (a :: b :: l)) : Not (b < a) := by admit
theorem lemma_hint_22 [DecidableEq T] {a b c : List T} (ab : Permut a b) (bc : Permut b c) : Permut a c := by admit
theorem lemma_hint_23 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) (t' : T) (h1 : count1 (e :: x :: xs) t' = count1 (e :: x :: xs) t') : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_24 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (p : ¬e < x) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_25 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : ¬e < x) (t : T) (h1 : count1 (x :: insert_ e xs) t = count1 (e :: x :: xs) t) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_26 [DecidableEq T] (a : List T) (c : List T) (t' : T) (h1 : count1 a t' = count1 c t') : Permut a c := by admit
theorem lemma_hint_27 [DecidableEq T] (c : List T) (a : List T) (b : List T) (t' : T) (h1 : count1 b t' = count1 c t') : Permut a c := by admit
theorem lemma_hint_28 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_29 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (p : ¬e < x) : Permut (x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_30 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (p : ¬e < x) (t : T) (h1 : (if x = t then 1 else 0) + (count1 xs t + if e = t then 1 else 0) = (if e = t then 1 else 0) + ((if x = t then 1 else 0) + count1 xs t)) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_31 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (p : ¬e < x) (t : T) (h1 : (if x = t then 1 else 0) + count1 (e :: xs) t = (if e = t then 1 else 0) + count1 (x :: xs) t) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_32 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (p : ¬e < x) (t : T) : count1 (x :: insert_ e xs) t = count1 (e :: x :: xs) t := by admit
theorem lemma_hint_33 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (t : T) (h1 : (if x = t then 1 else 0) + count1 (insertionsort xs) t = (if x = t then 1 else 0) + count1 xs t) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_34 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (p : ¬e < x) (t : T) (h1 : (if x = t then 1 else 0) + ((if e = t then 1 else 0) + count1 xs t) = (if e = t then 1 else 0) + ((if x = t then 1 else 0) + count1 xs t)) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_35 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (h1 : ∀ (t : T), count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_36 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (h1 : ∀ (t : T), count1 [e] t = count1 [e] t) : Permut (insert_ e []) [e] := by admit
theorem lemma_hint_37 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : ¬e < x) (t : T) (h1 : (if x = t then 1 else 0) + count1 (insert_ e xs) t = (if e = t then 1 else 0) + count1 (x :: xs) t) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_38 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (t : T) (h1 : count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_39 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : Permut (insertionsort ([] : List T)) [] := by admit

theorem eval_merge_sorted [Preorder T] [DecidableRel (LT.lt (α := T))] {xs ys : List T} (sxs : Sorted xs) (sys : Sorted ys) : Sorted (merge xs ys) := by
  induction xs with
  | nil =>
    simp [merge]
    exact sys
  | cons a xs ih =>
    cases ys with
    | nil =>
      simp [merge]
      exact sxs
    | cons y ys =>
      cases xs with
      | nil =>
        cases ys with
        | nil =>
          simp [merge]
          by_cases h : a < y
          · simp [merge, h]
            apply Sorted.cons
            · exact Sorted.singleton
            · intro hy
              exact lt_irrefl a (lt_trans h hy)
          · simp [merge, h]
            apply Sorted.cons
            · exact Sorted.singleton
            · exact h
        | cons z zs =>
          simp [merge]
          by_cases h : a < y
          · simp [merge, h]
            apply Sorted.cons
            · exact sys
            · intro hy
              exact lt_irrefl a (lt_trans h hy)
          · simp [merge, h]
            apply Sorted.cons
            · exact Sorted.singleton
            · exact h
      | cons b xs' =>
        simp [merge]
        by_cases h : a < y
        · simp [merge, h]
          apply Sorted.cons
          · apply ih
            · exact lemma_hint_5 a b xs' sxs
            · exact sys
          · intro hm
            by_cases hby : b < y
            · have hs : Sorted (b :: y :: ys) := by
                apply Sorted.cons
                · exact sys
                · exact hby
              exact lemma_hint_21 a b (merge xs' (y :: ys)) (Sorted.cons (ih (lemma_hint_5 a b xs' sxs) sys) hm)
            · exact lt_irrefl a (lt_trans h hm)
        · simp [merge, h]
          apply Sorted.cons
          · apply ih
            · exact sxs
            · exact lemma_hint_5 y z zs sys
          · intro hm
            by_cases haz : a < z
            · exact h hm
            · exact lemma_hint_21 y z (merge (a :: b :: xs') zs) (Sorted.cons (ih sxs (lemma_hint_5 y z zs sys)) hm)


/- lean_check result: FAIL
error:
location:
              · simp [merge, h]
                apply Sorted.cons
               ^
                · exact Sorted.singleton
error: Tactic `apply` failed: could not unify the conclusion of `@Sorted.cons`
  Sorted (?a :: ?b :: ?xs)
with the goal
  Sorted (y :: if a < z then a :: z :: zs else z :: merge [a] zs)
Note: The full type of `@Sorted.cons` is
  ∀ {T : Type ?u.14397} [inst : LT T] {a b : T} {xs : List T}, Sorted (b :: xs) → ¬b < a → Sorted (a :: b :: xs)
case neg
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
a y : T
sxs : Sorted [a]
z : T
zs : List T
sys : Sorted (y :: z :: zs)
ih : Sorted [] → Sorted (merge [] (y :: z :: zs))
h : ¬a < y
⊢ Sorted (y :: if a < z then a :: z :: zs else z :: merge [a] zs)

location:
            · simp [merge, h]
              apply Sorted.cons
             ^
              · apply ih
error: Tactic `apply` failed: could not unify the conclusion of `@Sorted.cons`
  Sorted (?a :: ?b :: ?xs)
with the goal
  Sorted (a :: if b < y then b :: merge xs' (y :: ys) else y :: merge (b :: xs') ys)
Note: The full type of `@Sorted.cons` is
  ∀ {T : Type ?u.14983} [inst : LT T] {a b : T} {xs : List T}, Sorted (b :: xs) → ¬b < a → Sorted (a :: b :: xs)
case pos
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
a y : T
ys : List T
sys : Sorted (y :: ys)
b : T
xs' : List T
sxs : Sorted (a :: b :: xs')
ih : Sorted (b :: xs') → Sorted (merge (b :: xs') (y :: ys))
h : a < y
⊢ Sorted (a :: if b < y then b :: merge xs' (y :: ys) else y :: merge (b :: xs') ys)

location:
            · simp [merge, h]
              apply Sorted.cons
             ^
              · apply ih
error: Tactic `apply` failed: could not unify the conclusion of `@Sorted.cons`
  Sorted (?a :: ?b :: ?xs)
with the goal
  Sorted (y :: merge (a :: b :: xs') ys)
Note: The full type of `@Sorted.cons` is
  ∀ {T : Type ?u.15109} [inst : LT T] {a b : T} {xs : List T}, Sorted (b :: xs) → ¬b < a → Sorted (a :: b :: xs)
case neg
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
a y : T
ys : List T
sys : Sorted (y :: ys)
b : T
xs' : List T
sxs : Sorted (a :: b :: xs')
ih : Sorted (b :: xs') → Sorted (merge (b :: xs') (y :: ys))
h : ¬a < y
⊢ Sorted (y :: merge (a :: b :: xs') ys)

location:
              by_cases h : a < y
              · simp [merge, h]
                     ^
                apply Sorted.cons
error: This simp argument is unused:
  merge
Hint: Omit it from the simp argument list.
  simp [m̵e̵r̵g̵e̵,̵ ̵h]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
                  exact lt_irrefl a (lt_trans h hy)
              · simp [merge, h]
                     ^
                apply Sorted.cons
error: This simp argument is unused:
  merge
Hint: Omit it from the simp argument list.
  simp [m̵e̵r̵g̵e̵,̵ ̵h]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
              by_cases h : a < y
              · simp [merge, h]
                     ^
                apply Sorted.cons
error: This simp argument is unused:
  merge
Hint: Omit it from the simp argument list.
  simp [m̵e̵r̵g̵e̵,̵ ̵h]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
                  exact lt_irrefl a (lt_trans h hy)
              · simp [merge, h]
                     ^
                apply Sorted.cons
error: This simp argument is unused:
  merge
Hint: Omit it from the simp argument list.
  simp [m̵e̵r̵g̵e̵,̵ ̵h]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
            by_cases h : a < y
            · simp [merge, h]
                   ^
              apply Sorted.cons
error: This simp argument is unused:
  merge
Hint: Omit it from the simp argument list.
  simp [m̵e̵r̵g̵e̵,̵ ̵h]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
                · exact lt_irrefl a (lt_trans h hm)
            · simp [merge, h]
                   ^
              apply Sorted.cons
error: This simp argument is unused:
  merge
Hint: Omit it from the simp argument list.
  simp [m̵e̵r̵g̵e̵,̵ ̵h]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`
-/
