// Feature Parade EP02 — 补全剩余枚举 + ending: complete
// 目标: char_show + char_look transition=dissolve、rarity rare/epic/legendary、==/!=/>/<

@episode main:02 "Parade Finale" {

  // ================================================================
  // SCENE 1 — char_show (单角色出场)
  // ================================================================

  @bg set cafeteria
  &music lunch
  &mark grin

  NARRATOR: [T30] char_show 新语法 — 单角色出场，引擎从 gamestate.MC 派生位置。

  // ================================================================
  // SCENE 2 — char_look transition=dissolve
  // ================================================================

  NARRATOR: [T31] char_look with transition=dissolve (Malia and Mauricio change looks).
  @malia smile dissolve
  @mauricio almost_smile dissolve

  // ================================================================
  // SCENE 3 — 剩余比较运算符 ==, !=, >, <
  // ================================================================

  NARRATOR: [T32] Comparison op == (strict equal).
  @if (affection.easton == 3) {
    YOU: [T32a] affection.easton == 3 exactly.
  } @else @if (affection.easton != 0) {
    YOU: [T32b] affection.easton != 0 fallback.
  } @else {
    YOU: [T32c] all comparison fell through.
  }

  NARRATOR: [T33] Comparison op > and < on engine value.
  @if (san > 50) {
    MALIA: [T33a] san > 50 branch.
  } @else @if (san < 50) {
    MALIA: [T33b] san < 50 branch.
  }

  // ================================================================
  // SCENE 4 — rarity rare / epic / legendary
  // ================================================================

  NARRATOR: [T34] Three achievements below cover rarity rare / epic / legendary (uncommon was in T21).

  @if (EP01_FACED_EASTON) {
    @achievement RARE_COURAGE {
      name: "Quiet Courage"
      rarity: rare
      description: "You faced him twice."
    }
    NARRATOR: [T34a] rarity=rare unlocked.
  }

  @if (EP01_COMPLETE && affection.easton >= 3) {
    @achievement EPIC_BOND {
      name: "Full Circle"
      rarity: epic
      description: "Two episodes. Still standing together."
    }
    NARRATOR: [T34b] rarity=epic unlocked.
  }

  @if (EP01_COMPLETE && EP01_FACED_EASTON && affection.easton >= 5) {
    @achievement LEGENDARY_PARADE {
      name: "Parade Monarch"
      rarity: legendary
      description: "Every choice, every risk. You took the hard road."
    }
    NARRATOR: [T34c] rarity=legendary unlocked.
  }

  // ================================================================
  // ENDING — complete (via @gate { @end complete })
  // ================================================================

  @bg set gym fade
  &music night
  YOU: [T35] Final @gate { @end complete } — story wraps, credits roll.
  @signal mark EP02_DONE

  @gate {
    @end complete
  }
}
