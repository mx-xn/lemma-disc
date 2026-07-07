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
  induction sxs generalizing ys with
  | nil =>
    cases ys with
    | nil =>
      simpa [merge] using Sorted.nil
    | cons y ys =>
      simpa [merge] using sys
  | singleton =>
    rename_i x
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
          exact sys
      | cons hy tys =>
        by_cases hxy : x < y
        · simp [merge, hxy]
          exact Sorted.cons sys hxy
        · simp [merge, hxy]
          exact sys
  | cons srest hba ih =>
    rename_i a b xs
    cases ys with
    | nil =>
      simpa [merge] using Sorted.cons srest hba
    | cons y ys =>
      cases ys with
      | nil =>
        by_cases hay : a < y
        · simp [merge, hay]
          exact Sorted.cons (Sorted.singleton) hba
        · simp [merge, hay]
          exact Sorted.cons srest hba
      | cons hy tys =>
        have sysTail : Sorted (hy :: tys) := lemma_hint_3 y hy tys sys
        by_cases hay : a < y
        · simp [merge, hay]
          exact Sorted.cons (ih (y :: hy :: tys) sys) hba
        · simp [merge, hay]
          exact Sorted.cons (Sorted.cons (ih (hy :: tys) sysTail) hay) (by
            have hy_not : ¬ hy < y := by
              cases sys with
              | cons _ h => exact h
            exact hy_not)


/- lean_check result: FAIL
error:
location:
            · simp [merge, hxy]
              exact Sorted.singleton
                   ^
            · simp [merge, hxy]
error: typeclass instance problem is stuck
  LT ?m.160
Note: Lean will not try to resolve this typeclass instance problem because the type argument to `LT` is a metavariable. This argument must be fully determined before Lean will try to resolve the typeclass.
Hint: Adding type annotations and supplying implicit arguments to functions can give Lean more information for typeclass resolution. For example, if you have a variable `x` that you intend to be a `Nat`, but Lean reports it as having an unresolved type like `?m`, replacing `x` with `(x : Nat)` can get typeclass resolution un-stuck.

location:
            · simp [merge, hxy]
              exact sys
             ^
          | cons hy tys =>
error: Type mismatch
  sys
has type
  Sorted [y]
but is expected to have type
  Sorted [y, x]

location:
            · simp [merge, hxy]
              exact Sorted.cons sys hxy
                                   ^
            · simp [merge, hxy]
error: Application type mismatch: The argument
  hxy
has type
  x < y
but is expected to have type
  ¬y < x
in the application
  Sorted.cons sys hxy

location:
            · simp [merge, hxy]
              exact sys
             ^
      | cons srest hba ih =>
error: Type mismatch
  sys
has type
  Sorted (y :: hy :: tys)
but is expected to have type
  Sorted (y :: if x < hy then x :: hy :: tys else hy :: merge [x] tys)

location:
            · simp [merge, hay]
              exact Sorted.cons (Sorted.singleton) hba
             ^
            · simp [merge, hay]
error: Type mismatch
  Sorted.cons Sorted.singleton hba
has type
  Sorted [a, b]
but is expected to have type
  Sorted (a :: if b < y then b :: merge xs [y] else y :: b :: xs)

location:
            · simp [merge, hay]
              exact Sorted.cons srest hba
                               ^
          | cons hy tys =>
error: Application type mismatch: The argument
  srest
has type
  Sorted (b :: xs)
but is expected to have type
  Sorted (a :: b :: xs)
in the application
  Sorted.cons srest

location:
            · simp [merge, hay]
              exact Sorted.cons (ih (y :: hy :: tys) sys) hba
                                   ^
            · simp [merge, hay]
error: Application type mismatch: The argument
  y :: hy :: tys
has type
  List T
of sort `Type u_1` but is expected to have type
  Sorted ?m.328
of sort `Prop` in the application
  ih (y :: hy :: tys)

location:
            · simp [merge, hay]
              exact Sorted.cons (Sorted.cons (ih (hy :: tys) sysTail) hay) (by
                                                ^
                have hy_not : ¬ hy < y := by
error: Application type mismatch: The argument
  hy :: tys
has type
  List T
of sort `Type u_1` but is expected to have type
  Sorted ?m.343
of sort `Prop` in the application
  ih (hy :: tys)

location:
                  | cons _ h => exact h
                exact hy_not)
               ^
error: Type mismatch
  hy_not
has type
  ¬hy < y
but is expected to have type
  ¬y < ?m.335
-/
