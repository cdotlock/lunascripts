@episode main:01 "Brave check requires attr" {
@choice {
  @option A brave "Try it." {
    check {
      dc: 12
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
