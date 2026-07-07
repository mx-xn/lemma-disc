import LeanSrc.Sorts_Mathlib

theorem lemma_hint_0 [DecidableEq T] (l : List T) (t' : T) (h1 : count1 l t' = count1 l t') : Permut l l := by admit
theorem lemma_hint_1 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_2 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_3 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : Permut ([] : List T) [] := by admit
theorem lemma_hint_4 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_5 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_6 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (IH : ∀ (t : T), count1 (insertionsort xs) t = count1 xs t) (t : T) : count1 (x :: insertionsort xs) t = count1 (x :: xs) t := by admit
theorem lemma_hint_7 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) (h1 : ∀ (t : T), count1 (e :: x :: xs) t = count1 (e :: x :: xs) t) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_8 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (h1 : Permut (insert_ x (insertionsort xs)) (x :: xs)) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_9 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : Permut (insertionsort ([] : List T)) [] := by admit
theorem lemma_hint_10 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (t : T) (h1 : count1 (x :: insertionsort xs) t = count1 (x :: xs) t) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_11 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h1 : ∀ (t : T), count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_12 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (t : T) (h1 : count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_13 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_14 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (t : T) (h1 : count1 (x :: insertionsort xs) t = count1 (x :: xs) t) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_15 [DecidableEq T] (l : List T) : ∀ (t : T), count1 l t = count1 l t := by admit
theorem lemma_hint_16 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) : Permut (e :: x :: xs) (e :: x :: xs) := by admit
theorem lemma_hint_17 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (h1 : ∀ (t : T), count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_18 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) (x : T) (h : T) (xs : List T) (p : ¬t < x) (IH : Sorted (h :: xs) → Sorted (insert_ t (h :: xs))) : Sorted (insert_ t (h :: xs)) := by admit
theorem lemma_hint_19 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) (x : T) (h : T) (xs : List T) (s : Sorted (x :: h :: xs)) (h1 : Sorted (h :: insert_ t xs)) : Sorted (x :: h :: insert_ t xs) := by admit
theorem lemma_hint_20 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) (x : T) (xs : List T) (IH : Sorted xs → Sorted (insert_ t xs)) (s : Sorted (x :: xs)) (p : t < x) : Sorted (if t < x then t :: x :: xs else x :: insert_ t xs) := by admit
theorem lemma_hint_21 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) (x : T) (p : ¬t < x) (h : T) (xs : List T) (IH : Sorted (h :: xs) → Sorted (insert_ t (h :: xs))) (s : Sorted (x :: h :: xs)) : Sorted (insert_ t (h :: xs)) := by admit
theorem lemma_hint_22 [Preorder T] [DecidableRel (LT.lt (α := T))] (x : T) (h : T) (xs : List T) (s : Sorted (x :: h :: xs)) : Sorted (h :: xs) := by admit
theorem lemma_hint_23 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (IH : ∀ (t : T), count1 (insertionsort xs) t = count1 xs t) (h : ∀ (t : T), count1 (insert_ x (insertionsort xs)) t = count1 (x :: insertionsort xs) t) : ∀ (t : T), count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t := by admit
theorem lemma_hint_24 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) (x : T) (h : T) (xs : List T) (p : ¬t < x) (IH : Sorted (h :: xs) → Sorted (insert_ t (h :: xs))) (s : Sorted (x :: h :: xs)) (p : ¬t < x) (a : ¬h < x) (h1 : Sorted (h :: xs)) : Sorted (insert_ t (h :: xs)) := by admit
theorem lemma_hint_25 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) : ∀ (t : T), count1 (e :: x :: xs) t = count1 (e :: x :: xs) t := by admit
theorem lemma_hint_26 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) (t' : T) (h1 : count1 (e :: x :: xs) t' = count1 (e :: x :: xs) t') : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_27 [DecidableEq T] (a : List T) (c : List T) (t' : T) (h1 : count1 a t' = count1 c t') : Permut a c := by admit
theorem lemma_hint_28 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (t : T) (h1 : count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_29 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (t : T) (h1 : (if x = t then 1 else 0) + count1 (insertionsort xs) t = (if x = t then 1 else 0) + count1 xs t) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_30 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (h1 : Permut (x :: insertionsort xs) (x :: xs)) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_31 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (t' : T) (h1 : count1 (e :: x :: xs) t' = count1 (e :: x :: xs) t') : Permut (e :: x :: xs) (e :: x :: xs) := by admit
theorem lemma_hint_32 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (t' : T) (h1 : count1 [] t' = count1 [] t') : Permut (insertionsort ([] : List T)) [] := by admit
theorem lemma_hint_33 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (t' : T) (h1 : count1 [] t' = count1 [] t') : Permut ([] : List T) [] := by admit
theorem lemma_hint_34 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : ¬e < x) (t : T) (h1 : count1 (x :: insert_ e xs) t = count1 (e :: x :: xs) t) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_35 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (p : ¬e < x) (t : T) : count1 (x :: insert_ e xs) t = count1 (e :: x :: xs) t := by admit
theorem lemma_hint_36 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (h1 : ∀ (t : T), count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_37 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (t : T) (h1 : count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_38 [Preorder T] [DecidableRel (LT.lt (α := T))] (x : T) (p : ¬t < x) (h : T) (xs : List T) (s : Sorted (x :: h :: xs)) : Sorted (h :: xs) := by admit
theorem lemma_hint_39 [DecidableEq T] (c : List T) (a : List T) (b : List T) (t' : T) (h1 : count1 b t' = count1 c t') : Permut a c := by admit

theorem eval_mergesort_correct (T : Type) [Preorder T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : SortCorrect (mergesort : List T -> List T) := by
  intro l
  by_cases h : l.length < 2
  · have hm : mergesort l = l := by
      unfold mergesort
      simp [h]
    constructor
    · rw [hm]
      cases l with
      | nil =>
        exact Sorted.nil
      | cons x xs =>
        cases xs with
        | nil =>
          exact Sorted.singleton
        | cons y ys =>
          simp at h
          linarith
    · rw [hm]
      intro t
      rfl
  · have hm : mergesort l = merge (mergesort (left l)) (mergesort (right l)) := by
      unfold mergesort
      simp [h]
    constructor
    · rw [hm]
      cases h1 : mergesort (left l) <;> cases h2 : mergesort (right l) <;> simp [merge]
        · exact Sorted.nil
        · assumption
        · assumption
        · by_cases hxy : head! (t :: ts) < head! (t_1 :: ts_1) <;> simp [hxy]
          · cases ts with
            | nil =>
              exact Sorted.singleton
            | cons a as =>
              exact Sorted.cons (by assumption) (by intro hlt; exact hxy hlt)
          · cases ts_1 with
            | nil =>
              exact Sorted.singleton
            | cons a as =>
              exact Sorted.cons (by assumption) (by intro hlt; exact hxy hlt)
    · intro t
      rfl


/- lean_check result: FAIL
error:
location:
          rfl
      · have hm : mergesort l = merge (mergesort (left l)) (mergesort (right l)) := by
                                                                                   ^
          unfold mergesort
error: unsolved goals
T : Type
inst✝² : Preorder T
inst✝¹ : DecidableEq T
inst✝ : DecidableRel LT.lt
l : List T
h : ¬l.length < 2
⊢ merge (mergesort (left l)) (mergesort (right l)) =
    merge (if (left l).length < 2 then left l else merge (mergesort (left (left l))) (mergesort (right (left l))))
      (if (right l).length < 2 then right l else merge (mergesort (left (right l))) (mergesort (right (right l))))

location:
        constructor
        · rw [hm]
       ^
          cases h1 : mergesort (left l) <;> cases h2 : mergesort (right l) <;> simp [merge]
error: unsolved goals
case neg.left.nil.nil
T : Type
inst✝² : Preorder T
inst✝¹ : DecidableEq T
inst✝ : DecidableRel LT.lt
l : List T
h : ¬l.length < 2
hm : mergesort l = merge (mergesort (left l)) (mergesort (right l))
h1 : mergesort (left l) = []
h2 : mergesort (right l) = []
⊢ Sorted []
case neg.left.nil.cons
T : Type
inst✝² : Preorder T
inst✝¹ : DecidableEq T
inst✝ : DecidableRel LT.lt
l : List T
h : ¬l.length < 2
hm : mergesort l = merge (mergesort (left l)) (mergesort (right l))
h1 : mergesort (left l) = []
head✝ : T
tail✝ : List T
h2 : mergesort (right l) = head✝ :: tail✝
⊢ Sorted (head✝ :: tail✝)
case neg.left.cons.nil
T : Type
inst✝² : Preorder T
inst✝¹ : DecidableEq T
inst✝ : DecidableRel LT.lt
l : List T
h : ¬l.length < 2
hm : mergesort l = merge (mergesort (left l)) (mergesort (right l))
head✝ : T
tail✝ : List T
h1 : mergesort (left l) = head✝ :: tail✝
h2 : mergesort (right l) = []
⊢ Sorted (head✝ :: tail✝)
case neg.left.cons.cons
T : Type
inst✝² : Preorder T
inst✝¹ : DecidableEq T
inst✝ : DecidableRel LT.lt
l : List T
h : ¬l.length < 2
hm : mergesort l = merge (mergesort (left l)) (mergesort (right l))
head✝¹ : T
tail✝¹ : List T
h1 : mergesort (left l) = head✝¹ :: tail✝¹
head✝ : T
tail✝ : List T
h2 : mergesort (right l) = head✝ :: tail✝
⊢ Sorted (if head✝¹ < head✝ then head✝¹ :: merge tail✝¹ (head✝ :: tail✝) else head✝ :: merge (head✝¹ :: tail✝¹) tail✝)

location:
          rfl
      · have hm : mergesort l = merge (mergesort (left l)) (mergesort (right l)) := by
     ^
          unfold mergesort
error: unsolved goals
case neg.right
T : Type
inst✝² : Preorder T
inst✝¹ : DecidableEq T
inst✝ : DecidableRel LT.lt
l : List T
h : ¬l.length < 2
hm : mergesort l = merge (mergesort (left l)) (mergesort (right l))
⊢ Permut (mergesort l) l

location:
          cases h1 : mergesort (left l) <;> cases h2 : mergesort (right l) <;> simp [merge]
            · exact Sorted.nil
           ^
            · assumption
error: unexpected token '·'; expected command
-/
