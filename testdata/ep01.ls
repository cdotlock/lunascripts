@episode main:01 "Butterfly" {

  // ===== Scene 1: Malia's bedroom, morning =====

  @bg set malias_bedroom_morning
  &music calm_morning
  &malia neutral_phone

  NARRATOR: Senior year. Day one. Status: already complicated.
  YOU: Another year. Same mess.

  @phone {
    @text from EASTON: Can we talk? I miss you.
    @text from EASTON: I know I messed up.
  }

  YOU: Eight months and he still won't stop.
  @malia worried

  // ===== Scene 2: School entrance =====

  @bg set school_front fade
  &music upbeat_school
  &malia neutral_flat
  &josie cheerful_wave

  JOSIE: Malia! Over here!
  @josie bubble heart
  MALIA: Hey, Jo.
  JOSIE: New year, new Malia. That's the plan, right?
  YOU: If only it were that simple.

  // ===== Scene 3: Hallway =====

  @bg set school_hallway fade
  &josie nervous_whisper
  JOSIE: Don't look. Three o'clock.

  @mauricio neutral_smirk

  MAURICIO: Hey, Butterfly.
  @josie bubble sweat
  @trick hold "Hold your breath until he walks past."
  YOU: He hasn't called me that in eight years.

  // ===== Scene 4: Classroom + minigame =====

  @bg set school_classroom fade
  &music tense_strings
  &malia neutral_flat

  NARRATOR: Mr. Chen paired them together. Of course he did.

  @minigame qte_challenge "Mr. Chen pairs Malia and Mauricio for the opening reading exercise — they trade lines from Jane Eyre while the rest of the class watches to see who flinches first. The player taps to match Malia's pacing to a rhythm meter, recovering after each misstep so she keeps her composure; three short rounds, best timing wins. Win and Malia reads the closing line with a steady voice; stumble and Mauricio finishes it for her."

  // ===== Scene 5: Cafeteria + core choice =====

  @bg set school_cafeteria fade
  &music casual_lunch
  &mark grin_confident
  &malia neutral_flat

  MARK: Yo, Malia! Sit with us!
  @sfx crowd_noise

  @easton vulnerable_hopeful

  NARRATOR: Easton is walking toward your table.

  @choice {
    @option A brave "Let him come." {
      check {
        attr: CHA
        dc: 12
      }
      @if (check.success) {
        @easton relieved
        EASTON: Can I sit?
        MALIA: You have two minutes.
        @affection easton +2
        &butterfly "Accepted Easton's approach at the cafeteria"
        @achievement FACED_EASTON {
          name: "Eye Contact"
          rarity: uncommon
          description: "You let him come close. Didn't look away."
        }
      } @else {
        @easton hurt
        MALIA: I... I can't do this.
        EASTON: Malia, please
        MALIA: Not here. Not now.
        @butterfly "Tried to face Easton but lost courage"
      }
    }
    @option B safe "Have Mark make a scene." {
      @mark grin_mischief
      MARK: HEY EASTON! You want some of my mystery casserole?
      @mark bubble music
      YOU: Thank god for Mark.
      @butterfly "Had Mark create a diversion to avoid Easton"
    }
  }

  // ===== Scene 6: Gymnasium =====

  @bg set school_gymnasium fade
  &music ambient_gym
  &malia neutral_flat
  &josie excited

  JOSIE: Did you see Elias in practice today?
  YOU: I was trying not to.

  @elias neutral_calm

  NARRATOR: He didn't say a word. He didn't have to.
  @malia bubble heart

  // ===== Scene 7: Night bedroom =====

  @bg set malias_bedroom_night fade
  &music night_piano
  &malia neutral_phone

  YOU: Day one. Survived. Barely.

  @phone {
    @text from UNKNOWN: nice curtains, Butterfly
  }

  @malia shocked
  YOU: ...How does he know which window is mine?


  // ===== Routing =====

  @gate {
    @if (A.fail): @next main/bad/001:01
    @else: @next main:02
  }
}
