// Feature Parade BAD01 — @end bad_ending fixture
// 路由入口: ep01 gate 的 T29a/T29b/T29c 任一命中 → 本集

@episode main/bad/001:01 "Bad Ending — Regret" {

  @bg set bedroom
  &music night

  NARRATOR: [T37] The door closed. You never opened it again.
  YOU: One wrong move, one closed door.

  @malia shocked
  @music stop
  NARRATOR: [T41] Weeks later, nothing has changed.

  NARRATOR: [T42] gate's @end bad_ending fires now.
  @gate {
    @end bad_ending
  }
}
