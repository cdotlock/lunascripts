@episode main:01 "Achievement id must be uppercase" {
@achievement first_win {
  name: "First Win"
  rarity: uncommon
  description: "Win for the first time."
}
@gate {
  @end complete
}
}
