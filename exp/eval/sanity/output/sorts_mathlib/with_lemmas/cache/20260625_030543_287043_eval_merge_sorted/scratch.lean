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
theorem lemma_hint_10 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) (x : T) (h : T) (xs : List T) (p : ¬t < x) (IH : Sorted (h :: xs) → Sorted (insert_ t (h :: xs))) : Sorted (insert_ t (h :: xs)) := by admit
theorem lemma_hint_11 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) (x : T) (p : ¬t < x) (h : T) (xs : List T) (IH : Sorted (h :: xs) → Sorted (insert_ t (h :: xs))) (s : Sorted (x :: h :: xs)) : Sorted (insert_ t (h :: xs)) := by admit
theorem lemma_hint_12 [LT T] (x : T) (h : T) (xs : List T) (s : Sorted (x :: h :: xs)) : ¬h < x := by admit
theorem lemma_hint_13 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) (x : T) (h : T) (xs : List T) (p : ¬t < x) (IH : Sorted (h :: xs) → Sorted (insert_ t (h :: xs))) (s : Sorted (x :: h :: xs)) (p : ¬t < x) (a : ¬h < x) (h1 : Sorted (h :: xs)) : Sorted (insert_ t (h :: xs)) := by admit
theorem lemma_hint_14 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (t' : T) (h1 : count1 (e :: x :: xs) t' = count1 (e :: x :: xs) t') : Permut (e :: x :: xs) (e :: x :: xs) := by admit
theorem lemma_hint_15 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_16 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (t' : T) (h1 : count1 [] t' = count1 [] t') : Permut ([] : List T) [] := by admit
theorem lemma_hint_17 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) (h1 : ∀ (t : T), count1 (e :: x :: xs) t = count1 (e :: x :: xs) t) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_18 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) : Permut [e] [e] := by admit
theorem lemma_hint_19 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) (t' : T) (h1 : count1 (e :: x :: xs) t' = count1 (e :: x :: xs) t') : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_20 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (p : ¬e < x) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_21 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : ¬e < x) (t : T) (h1 : count1 (x :: insert_ e xs) t = count1 (e :: x :: xs) t) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_22 [DecidableEq T] (a : List T) (c : List T) (t' : T) (h1 : count1 a t' = count1 c t') : Permut a c := by admit
theorem lemma_hint_23 [DecidableEq T] (c : List T) (a : List T) (b : List T) (t' : T) (h1 : count1 b t' = count1 c t') : Permut a c := by admit
theorem lemma_hint_24 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_25 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (p : ¬e < x) : Permut (x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_26 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (p : ¬e < x) (t : T) (h1 : (if x = t then 1 else 0) + (count1 xs t + if e = t then 1 else 0) = (if e = t then 1 else 0) + ((if x = t then 1 else 0) + count1 xs t)) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_27 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (p : ¬e < x) (t : T) (h1 : (if x = t then 1 else 0) + count1 (e :: xs) t = (if e = t then 1 else 0) + count1 (x :: xs) t) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_28 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (p : ¬e < x) (t : T) : count1 (x :: insert_ e xs) t = count1 (e :: x :: xs) t := by admit
theorem lemma_hint_29 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (t : T) (h1 : (if x = t then 1 else 0) + count1 (insertionsort xs) t = (if x = t then 1 else 0) + count1 xs t) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_30 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (p : ¬e < x) (t : T) (h1 : (if x = t then 1 else 0) + ((if e = t then 1 else 0) + count1 xs t) = (if e = t then 1 else 0) + ((if x = t then 1 else 0) + count1 xs t)) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_31 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (h1 : ∀ (t : T), count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_32 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (h1 : ∀ (t : T), count1 [e] t = count1 [e] t) : Permut (insert_ e []) [e] := by admit
theorem lemma_hint_33 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : ¬e < x) (t : T) (h1 : (if x = t then 1 else 0) + count1 (insert_ e xs) t = (if e = t then 1 else 0) + count1 (x :: xs) t) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_34 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (t : T) (h1 : count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_35 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : Permut (insertionsort ([] : List T)) [] := by admit
theorem lemma_hint_36 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (t : T) (h1 : count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_37 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (t' : T) (h1 : count1 [e] t' = count1 [e] t') : Permut [e] [e] := by admit
theorem lemma_hint_38 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (t : T) (h1 : (if x = t then 1 else 0) + (count1 xs t + if e = t then 1 else 0) = (if e = t then 1 else 0) + ((if x = t then 1 else 0) + count1 xs t)) : Permut (x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_39 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) : Permut (insert_ e (x :: xs)) (e :: x :: xs) := by admit

theorem eval_merge_sorted [Preorder T] [DecidableRel (LT.lt (α := T))] {xs ys : List T} (sxs : Sorted xs) (sys : Sorted ys) : Sorted (merge xs ys) := by
  induction sxs generalizing ys with
  | nil =>
    simp [merge]
    intro sys
    exact sys
  | singleton =>
    intro ys sys
    cases ys with
    | nil =>
      simp [merge]
      exact Sorted.singleton
    | cons y ys' =>
      cases ys' with
      | nil =>
        by_cases hxy : x < y
        · simp [merge, hxy]
          exact Sorted.cons Sorted.singleton (by
            intro hyx
            exact (Preorder.not_lt_of_ge (Preorder.le_of_not_gt hxy)) hyx)
        · simp [merge, hxy]
          exact Sorted.cons sys hxy
      | cons z zs =>
        by_cases hxy : x < y
        · simp [merge, hxy]
          exact Sorted.cons (Sorted.cons sys (by
            intro hyx
            exact (Preorder.not_lt_of_ge (Preorder.le_of_not_gt hxy)) hyx)) (by
              intro h
              cases sys with
              | cons _ _ _ _ _ hy =>
                exact hy h
              | _ => cases hxy)
        · simp [merge, hxy]
          exact Sorted.cons (merge_sorted Sorted.singleton (lemma_hint_3 y z zs sys)) (by
            intro h
            exact hxy h)
  | @cons a b xs sb hba IH =>
    intro ys sys
    cases ys with
    | nil =>
      simp [merge]
      exact Sorted.cons sb hba
    | cons y ys' =>
      cases ys' with
      | nil =>
        by_cases hay : a < y
        · simp [merge, hay]
          exact Sorted.cons (Sorted.cons sb (by
            intro hyb
            have hya : y ≤ a := Preorder.le_of_not_gt (by
              intro hay'
              exact (Preorder.not_lt_of_ge (show a ≤ y from Preorder.le_of_lt hay)) hay')
            have hba' : b ≤ y := le_trans (show b ≤ a from Preorder.le_of_not_gt hba) hya
            exact (Preorder.not_lt_of_ge hba') hyb)) hba
        · simp [merge, hay]
          exact Sorted.cons (Sorted.cons sb hba) hay
      | cons z zs =>
        by_cases hay : a < y
        · simp [merge, hay]
          have hm : Sorted (merge (b :: xs) (y :: z :: zs)) := IH (Sorted.cons sys (by
            cases sys with
            | cons _ _ _ _ _ hy => exact hy
            | _ => intro h; cases h))
          apply Sorted.cons hm
          intro h
          by_cases hby : b < y
          · simp [merge, hby] at h
            exact hba h
          · simp [merge, hby] at h
            exact (Preorder.not_lt_of_ge (show y ≤ a from Preorder.le_of_not_gt hay)) h
        · simp [merge, hay]
          have sys' : Sorted (z :: zs) := lemma_hint_3 y z zs sys
          have hm : Sorted (merge (a :: b :: xs) (z :: zs)) := merge_sorted (Sorted.cons sb hba) sys'
          apply Sorted.cons hm
          intro h
          by_cases haz : a < z
          · simp [merge, haz] at h
            exact hay h
          · simp [merge, haz] at h
            cases sys with
            | cons _ _ _ _ _ hy =>
              exact hy h
            | _ =>
              cases h


/- lean_check result: FAIL
error:
location:
        simp [merge]
        intro sys
             ^
        exact sys
error: Tactic `introN` failed: There are no additional binders or `let` bindings in the goal to introduce
case nil
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
xs ys : List T
sys : Sorted ys
⊢ Sorted ys

location:
      | singleton =>
        intro ys sys
             ^
        cases ys with
error: Tactic `introN` failed: There are no additional binders or `let` bindings in the goal to introduce
case singleton
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
xs : List T
x✝ : T
ys : List T
sys : Sorted ys
⊢ Sorted (merge [x✝] ys)

location:
      | @cons a b xs sb hba IH =>
        intro ys sys
             ^
        cases ys with
error: Tactic `introN` failed: There are no additional binders or `let` bindings in the goal to introduce
case cons
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
xs✝ : List T
a b : T
xs : List T
sb : Sorted (b :: xs)
hba : ¬b < a
IH : ∀ {ys : List T}, Sorted ys → Sorted (merge (b :: xs) ys)
ys : List T
sys : Sorted ys
⊢ Sorted (merge (a :: b :: xs) ys)
-/
