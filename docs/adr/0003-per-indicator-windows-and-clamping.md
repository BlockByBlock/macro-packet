# Per-indicator windows plus default clamping against COVID distortion

Every percentile/z-score window in the plan contains 2020, which silently distorts all standardizations. Each indicator spec therefore carries an explicit `window_years` (shorter or exclusion-capable per indicator), and transforms clamp/winsorize extreme observations by default rather than letting single observations dominate. Decided up front because it poisons every number the engine emits if ignored.
