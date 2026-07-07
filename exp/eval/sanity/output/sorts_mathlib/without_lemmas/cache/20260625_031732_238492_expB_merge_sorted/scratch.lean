import LeanSrc.Sorts_Mathlib

theorem expB_merge_sorted [Preorder T] [DecidableRel (LT.lt (α := T))] {xs ys : List T} (sxs : Sorted xs) (sys : Sorted ys) : Sorted (merge xs ys) := by
  induction sxs generalizing ys with
  | nil =>
      simpa [merge] using sys
  | singleton =>
      cases ys with
      | nil =>
          simp [merge]
      | cons y ys =>
          by_cases h : x < y
          · simp [merge, h, Sorted.singleton]
          · cases ys with
            | nil =>
                simp [merge, h, Sorted.singleton]
            | cons y₂ ys₂ =>
                cases sys with
                | cons hs hny =>
                    have htail : Sorted (merge [x] (y₂ :: ys₂)) := by
                      simpa using singleton hs
                    simpa [merge, h] using Sorted.cons htail hny
  | cons a b xs hs hba ih =>
      cases ys with
      | nil =>
          simpa [merge] using Sorted.cons hs hba
      | cons c ys =>
          by_cases h : a < c
          · simpa [merge, h] using Sorted.cons (ih sys) hba
          · cases ys with
            | nil =>
                simp [merge, h, Sorted.singleton]
            | cons d ds =>
                cases sys with
                | cons hs' hdc =>
                    have htail : Sorted (merge (a :: b :: xs) (d :: ds)) := ih hs'
                    simpa [merge, h] using Sorted.cons htail h


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
          | cons y ys =>
              by_cases h : x < y
                          ^
              · simp [merge, h, Sorted.singleton]
error: error(lean.unknownIdentifier): Unknown identifier `x`

location:
              by_cases h : x < y
              · simp [merge, h, Sorted.singleton]
             ^
              · cases ys with
error: unsolved goals
case pos
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
xs : List T
x✝ y : T
ys : List T
sys : Sorted (y :: ys)
h : sorry < y
⊢ Sorted (if x✝ < y then x✝ :: y :: ys else y :: merge [x✝] ys)

location:
              · cases ys with
                | nil =>
                     ^
                    simp [merge, h, Sorted.singleton]
error: unsolved goals
case neg.nil
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
xs : List T
x✝ y : T
h : ¬sorry < y
sys : Sorted [y]
⊢ Sorted (if x✝ < y then [x✝, y] else [y, x✝])

location:
                    | cons hs hny =>
                        have htail : Sorted (merge [x] (y₂ :: ys₂)) := by
                                                   ^
                          simpa using singleton hs
error: error(lean.unknownIdentifier): Unknown identifier `x`

location:
                        have htail : Sorted (merge [x] (y₂ :: ys₂)) := by
                          simpa using singleton hs
                                               ^
                        simpa [merge, h] using Sorted.cons htail hny
error: Application type mismatch: The argument
  hs
has type
  Sorted (y₂ :: ys₂)
of sort `Prop` but is expected to have type
  ?m.219
of sort `outParam (Type ?u.1593)` in the application
  {hs}

location:
                        simpa [merge, h] using Sorted.cons htail hny
      | cons a b xs hs hba ih =>
     ^
          cases ys with
error: Too many variable names provided at alternative `cons`: 6 provided, but 3 expected

location:
          | nil =>
              simpa [merge] using Sorted.cons hs hba
                                             ^
          | cons c ys =>
error: error(lean.unknownIdentifier): Unknown identifier `hs`

location:
          | nil =>
              simpa [merge] using Sorted.cons hs hba
                                                ^
          | cons c ys =>
error: error(lean.unknownIdentifier): Unknown identifier `hba`

location:
          | cons c ys =>
              by_cases h : a < c
                              ^
              · simpa [merge, h] using Sorted.cons (ih sys) hba
error: Type mismatch
  c
has type
  T
of sort `Type u_1` but is expected to have type
  Sorted (b✝ :: xs✝)
of sort `Prop`

location:
              by_cases h : a < c
              · simpa [merge, h] using Sorted.cons (ih sys) hba
                                                   ^
              · cases ys with
error: error(lean.unknownIdentifier): Unknown identifier `ih`

location:
              by_cases h : a < c
              · simpa [merge, h] using Sorted.cons (ih sys) hba
                                                           ^
              · cases ys with
error: error(lean.unknownIdentifier): Unknown identifier `hba`

location:
              · cases ys with
                | nil =>
                     ^
                    simp [merge, h, Sorted.singleton]
error: unsolved goals
case neg.nil
T : Type u_1
inst✝¹ : Preorder T
inst✝ : DecidableRel LT.lt
xs✝¹ : List T
a✝ b✝ : T
xs✝ : List T
a : Sorted (b✝ :: xs✝)
b : ¬b✝ < a✝
xs : ∀ {ys : List T}, Sorted ys → Sorted (merge (b✝ :: xs✝) ys)
c : T
h : ¬sorry
sys : Sorted [c]
⊢ Sorted (if a✝ < c then a✝ :: if b✝ < c then b✝ :: merge xs✝ [c] else c :: b✝ :: xs✝ else c :: a✝ :: b✝ :: xs✝)

location:
                    | cons hs' hdc =>
                        have htail : Sorted (merge (a :: b :: xs) (d :: ds)) := ih hs'
                                                             ^
                        simpa [merge, h] using Sorted.cons htail h
error: Application type mismatch: The argument
  xs
has type
  Sorted ?m.462 → Sorted (merge (b✝ :: xs✝) ?m.462)
of sort `Prop` but is expected to have type
  List ?m.460
of sort `Type ?u.4460` in the application
  [?m.461, ⋯]

location:
                    | cons hs' hdc =>
                        have htail : Sorted (merge (a :: b :: xs) (d :: ds)) := ih hs'
                                                                               ^
                        simpa [merge, h] using Sorted.cons htail h
error: error(lean.unknownIdentifier): Unknown identifier `ih`

location:
                    | cons hs' hdc =>
                        have htail : Sorted (merge (a :: b :: xs) (d :: ds)) := ih hs'
                                                        ^
                        simpa [merge, h] using Sorted.cons htail h
error: Application type mismatch: The argument
  b
has type
  ¬b✝ < a✝
of sort `Prop` but is expected to have type
  T
of sort `Type u_1` in the application
  List.cons b

location:
              by_cases h : x < y
              · simp [merge, h, Sorted.singleton]
                            ^
              · cases ys with
error: This simp argument is unused:
  h
Hint: Omit it from the simp argument list.
  simp [merge, h̵,̵ ̵Sorted.singleton]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
              by_cases h : x < y
              · simp [merge, h, Sorted.singleton]
                               ^
              · cases ys with
error: This simp argument is unused:
  Sorted.singleton
Hint: Omit it from the simp argument list.
  simp [merge, h,̵ ̵S̵o̵r̵t̵e̵d̵.̵s̵i̵n̵g̵l̵e̵t̵o̵n̵]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
                | nil =>
                    simp [merge, h, Sorted.singleton]
                                ^
                | cons y₂ ys₂ =>
error: This simp argument is unused:
  h
Hint: Omit it from the simp argument list.
  simp [merge, h̵,̵ ̵Sorted.singleton]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
                | nil =>
                    simp [merge, h, Sorted.singleton]
                                   ^
                | cons y₂ ys₂ =>
error: This simp argument is unused:
  Sorted.singleton
Hint: Omit it from the simp argument list.
  simp [merge, h,̵ ̵S̵o̵r̵t̵e̵d̵.̵s̵i̵n̵g̵l̵e̵t̵o̵n̵]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
                | nil =>
                    simp [merge, h, Sorted.singleton]
                                ^
                | cons d ds =>
error: This simp argument is unused:
  h
Hint: Omit it from the simp argument list.
  simp [merge, h̵,̵ ̵Sorted.singleton]
Note: This linter can be disabled with `s
... [truncated, 4414 bytes total]
-/
