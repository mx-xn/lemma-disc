import LeanSrc.Definitions

theorem prop_77 (x: Nat) (xs: List Nat) :
  (sorted xs → sorted (insort x xs)) := by
  induction xs with
  | nil => simp [insort, sorted]
  | cons y ys ih =>
    intro h
    by_cases hle : x ≤ y
    · simp only [insort, if_pos hle, sorted, Bool.and_eq_true]
      exact ⟨by simp [hle], h⟩
    · have hyx : y ≤ x := Nat.le_of_lt (Nat.lt_of_not_le hle)
      simp only [insort, if_neg hle]
      simp only [sorted, Bool.and_eq_true] at h
      cases ys with
      | nil =>
        simp only [insort, if_pos hyx, sorted]
        simp [hyx]
      | cons z zs =>
        obtain ⟨hyz, hzs⟩ := h
        simp only [sorted, Bool.and_eq_true]
        constructor
        · by_cases hxz : x ≤ z
          · simp [insort, if_pos hxz, hyx]
          · simp [insort, if_neg hxz, hyz]
        · apply ih
          simp [sorted, Bool.and_eq_true, hyz, hzs]
