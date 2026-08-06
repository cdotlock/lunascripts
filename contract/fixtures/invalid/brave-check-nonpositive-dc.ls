@episode main:01 "Brave check requires positive dc" {
@choice {
  @option A brave "Try it." {
    check {
      attr: courage
      dc: 0
    }
  }
  @option B safe "Leave it." {
    NARRATOR: You step away.
  }
}
@gate {
  @end complete
}
}
