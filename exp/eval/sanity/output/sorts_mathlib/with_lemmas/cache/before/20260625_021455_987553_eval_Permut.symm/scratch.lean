import LeanSrc.Sorts_Mathlib

theorem lemma_hint_0 [DecidableEq T] {a b c : List T} (ab : Permut a b) (bc : Permut b c) : Permut a c := by admit
theorem lemma_hint_1 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (t' : T) (h1 : count1 [e] t' = count1 [e] t') : Permut [e] [e] := by admit
theorem lemma_hint_2 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) : Permut [e] [e] := by admit
theorem lemma_hint_3 [DecidableEq T] (l : List T) : Permut l l := by admit
theorem lemma_hint_4 [DecidableEq T] (c : List T) (a : List T) (b : List T) (t' : T) (h1 : count1 b t' = count1 c t') : Permut a c := by admit
theorem lemma_hint_5 [DecidableEq T] (a : List T) (c : List T) (t' : T) (h1 : count1 a t' = count1 c t') : Permut a c := by admit
theorem lemma_hint_6 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) : Permut (e :: x :: xs) (e :: x :: xs) := by admit
theorem lemma_hint_7 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (t' : T) (h1 : count1 (e :: x :: xs) t' = count1 (e :: x :: xs) t') : Permut (e :: x :: xs) (e :: x :: xs) := by admit
theorem lemma_hint_8 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (h1 : ∀ (t : T), count1 [e] t = count1 [e] t) : Permut (insert_ e []) [e] := by admit
theorem lemma_hint_9 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (t' : T) (h1 : count1 [e] t' = count1 [e] t') : Permut (insert_ e []) [e] := by admit
theorem lemma_hint_10 [DecidableEq T] (l : List T) (t' : T) (h1 : count1 l t' = count1 l t') : Permut l l := by admit
theorem lemma_hint_11 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) : Permut (insert_ e []) [e] := by admit
theorem lemma_hint_12 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (t : T) (h1 : (if x = t then 1 else 0) + count1 (insert_ e xs) t = (if e = t then 1 else 0) + count1 (x :: xs) t) : Permut (x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_13 [DecidableEq T] (a : List T) (b : List T) (c : List T) (d : List T) (t : T) (h1 : count1 (a ++ b) t = count1 (c ++ d) t) : Permut (a ++ b) (c ++ d) := by admit
theorem lemma_hint_14 [DecidableEq T] (a : List T) (b : List T) (c : List T) (d : List T) (ac : Permut a c) (t : T) (hl : count1 (a ++ b) t = count1 a t + count1 b t) (hr : count1 (c ++ d) t = count1 c t + count1 d t) (h1 : count1 a t + count1 b t = count1 c t + count1 d t) : Permut (a ++ b) (c ++ d) := by admit
theorem lemma_hint_15 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (h1 : ∀ (t : T), count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_16 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (t : T) (h1 : (if x = t then 1 else 0) + ((if e = t then 1 else 0) + count1 xs t) = (if e = t then 1 else 0) + ((if x = t then 1 else 0) + count1 xs t)) : Permut (x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_17 [DecidableEq T] (c : List T) (d : List T) (a : List T) (b : List T) (ac : Permut a c) (t : T) (hl : count1 (a ++ b) t = count1 a t + count1 b t) (h1 : count1 (a ++ b) t = count1 (c ++ d) t) : Permut (a ++ b) (c ++ d) := by admit
theorem lemma_hint_18 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (t : T) (h1 : (if x = t then 1 else 0) + count1 (insertionsort xs) t = (if x = t then 1 else 0) + count1 xs t) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_19 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (t : T) (h1 : count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_20 [DecidableEq T] (a : List T) (b : List T) (c : List T) (d : List T) (ac : Permut a c) (t : T) (hl : count1 (a ++ b) t = count1 a t + count1 b t) (hr : count1 (c ++ d) t = count1 c t + count1 d t) (h1 : count1 (a ++ b) t = count1 (c ++ d) t) : Permut (a ++ b) (c ++ d) := by admit
theorem lemma_hint_21 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (t : T) (h1 : (if x = t then 1 else 0) + (count1 xs t + if e = t then 1 else 0) = (if e = t then 1 else 0) + ((if x = t then 1 else 0) + count1 xs t)) : Permut (x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_22 [DecidableEq T] (a : List T) (b : List T) (c : List T) (d : List T) (ac : Permut a c) (t : T) (hr : count1 (c ++ d) t = count1 c t + count1 d t) (h1 : count1 (a ++ b) t = count1 (c ++ d) t) : Permut (a ++ b) (c ++ d) := by admit
theorem lemma_hint_23 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (t : T) (h1 : (if x = t then 1 else 0) + count1 (e :: xs) t = (if e = t then 1 else 0) + count1 (x :: xs) t) : Permut (x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_24 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (p : ¬e < x) : Permut (x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_25 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (t : T) (h1 : count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_26 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_27 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (t' : T) (h1 : count1 [] t' = count1 [] t') : Permut ([] : List T) [] := by admit
theorem lemma_hint_28 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) (h1 : ∀ (t : T), count1 (e :: x :: xs) t = count1 (e :: x :: xs) t) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_29 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) : Permut (insert_ e (x :: xs)) (e :: x :: xs) := by admit
theorem lemma_hint_30 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (t : T) (h1 : count1 (x :: insertionsort xs) t = count1 (x :: xs) t) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_31 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (p : ¬e < x) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_32 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_33 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) (t' : T) (h1 : count1 (e :: x :: xs) t' = count1 (e :: x :: xs) t') : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_34 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (p : ¬e < x) (t : T) (h1 : (if x = t then 1 else 0) + ((if e = t then 1 else 0) + count1 xs t) = (if e = t then 1 else 0) + ((if x = t then 1 else 0) + count1 xs t)) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_35 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (p : ¬e < x) (t : T) (h1 : (if x = t then 1 else 0) + (count1 xs t + if e = t then 1 else 0) = (if e = t then 1 else 0) + ((if x = t then 1 else 0) + count1 xs t)) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_36 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : Permut ([] : List T) [] := by admit
theorem lemma_hint_37 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : ¬e < x) (t : T) (h1 : count1 (x :: insert_ e xs) t = count1 (e :: x :: xs) t) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_38 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (h1 : Permut (x :: insertionsort xs) (x :: xs)) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_39 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : ¬e < x) (t : T) (h1 : (if x = t then 1 else 0) + count1 (insert_ e xs) t = (if e = t then 1 else 0) + count1 (x :: xs) t) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit

theorem eval_Permut.symm [DecidableEq T] {l m : List T} (p : Permut l m) : Permut m l := by
  intro t
  symm
  exact p t


/- lean_check result: ok -/
