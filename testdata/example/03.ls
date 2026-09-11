@episode main:03 "Bad Idea #3" {

  // ===== Mauricio's bedroom, afternoon — Thursday =====

  @bg mauricios_bedroom_afternoon fade

  NARRATOR: Thursday. 4 PM. The first time I've been inside Mauricio Reyes's house since I was ten.
  NARRATOR: It looks different from how I remember. Smaller. Older. The wallpaper in the hallway is peeling. But his room is clean. Extremely clean. Books everywhere -- shelves, desk, floor stacks. Jane Eyre, Wuthering Heights, The Catcher in the Rye. A worn copy of The Unhoneymooners with dog-eared pages.

  @mauricio sitting_desk

  MALIA [neutral_surprised]: You have more books than the school library.
  MAURICIO [neutral_flat]: The school library has seventeen copies of Lord of the Flies and none of Toni Morrison. That's not a library. That's a crime scene.

  INNER_THOUGHT: He just made a literary joke.
  INNER_THOUGHT: An actually funny literary joke.
  INNER_THOUGHT: I'm going to pretend I didn't almost smile.

  @malia sitting_edge

  MAURICIO [neutral_opening_book]: Jane Eyre. Dual perspectives. I take Rochester, you take Jane.
  MALIA [neutral_competitive]: I want Rochester.
  MAURICIO [neutral_flat]: You are Jane.
  MALIA [neutral_narrowing]: What is that supposed to mean?
  MAURICIO [neutral_calm]: It means you're stubborn, principled, and you'd rather walk into a storm than admit you need someone to hold the umbrella.

  INNER_THOUGHT: ...
  INNER_THOUGHT: That is both the most annoying and the most accurate thing anyone has ever said about me.

  MALIA [neutral_recovering]: Fine. Jane it is. But only because her chapters are better.
  MAURICIO [neutral_almost_smile]: They're not.

  NARRATOR: We work for two hours. He doesn't talk much. But when he does, every sentence is about the book and somehow also not about the book.
  NARRATOR: "Rochester lies because the truth would cost him everything."
  NARRATOR: "Jane doesn't leave because she stops loving him. She leaves because she loves herself more."
  NARRATOR: I keep catching myself staring at the way he underlines passages. He uses a ruler. Every line is straight.

  @sfx stomach_growl

  MAURICIO: When did you last eat?
  MALIA [neutral_embarrassed]: That's none of your business.

  @mauricio standing_plate fade

  MAURICIO: My mom made extra.
  MALIA [neutral_surprised]: You're... feeding me?
  MAURICIO [neutral_flat]: You can't analyze nineteenth-century feminist literature on an empty stomach. That's not generosity. That's academic standards.

  INNER_THOUGHT: He brought me food and framed it as an academic necessity.
  INNER_THOUGHT: I don't know whether to be annoyed or touched.
  INNER_THOUGHT: I'm both.

  // ===== The fight downstairs =====

  @sfx arguing_muffled
  &mauricio standing_jaw_tight

  @sfx glass_breaking

  @mauricio standing_controlled

  MAURICIO [neutral_low]: Stay here.

  INNER_THOUGHT: I know what just happened downstairs. I've been hearing it through the walls for years.

  @mauricio standing_blank

  INNER_THOUGHT: I could pretend I didn't notice. Walk out. Say "see you next week." Keep the wall between us.
  INNER_THOUGHT: Or I could--

  @choice {
    @option A safe "[Say something.]" {
      MALIA [neutral_quiet]: Mauricio.
      MALIA [neutral_quiet]: You don't have to explain anything. But I want you to know--
      MALIA [neutral_honest]: My parents used to fight too. Before my mom left. I used to sing to my little sister to cover the sound.
      MALIA [neutral_quiet]: I'm not saying I understand your situation. I'm saying I had my own version of it.

      @mauricio neutral_quiet

      MAURICIO [neutral_very_quiet]: What did you sing?
      MALIA [neutral_small_smile]: Dusk Till Dawn. Zayn. Every single night for a year.

      MAURICIO [neutral_low]: You should go home, Malia.

      INNER_THOUGHT: He used my actual name. Not "Hernandez." Not "Butterfly." My name.
      INNER_THOUGHT: It sounded different in his voice than it does in anyone else's.

      MALIA: My window's always open. In case you need somewhere that's not here.

      @affection mauricio +3
      @butterfly "Shared personal pain with Mauricio and offered him an open window"
    }
    @option B safe "[Leave without saying anything.]" {
      MALIA [neutral_normal]: Okay. Same time next week?

      @mauricio neutral_nod

      INNER_THOUGHT: I didn't say anything.
      INNER_THOUGHT: Because what would I say? "Are you okay?" He's clearly not okay.
      INNER_THOUGHT: "I'm sorry?" He doesn't want my sorry. He doesn't want anything from me except to finish this project and go back to ignoring each other.
      INNER_THOUGHT: But.
      INNER_THOUGHT: That butterfly on his keychain.
      INNER_THOUGHT: Why does he carry a butterfly?

      @butterfly "Left Mauricio's house without acknowledging the family situation"
    }
  }

  // ===== Malia's kitchen, evening =====

  @bg malias_kitchen_evening fade

  @samuel neutral_warm

  SAMUEL: So. The Reyes boy. You're doing a project together?
  MALIA: Yeah. English literature. Jane Eyre.
  SAMUEL [neutral_stirring]: Good book. He seems like a serious kid.
  MALIA [neutral_too_fast]: He's fine. It's just a project.
  SAMUEL [neutral_knowing_smile]: I didn't say it wasn't.

  @sfx phone_buzz

  // Group chat — rendered as sequential phone messages
  @phone {
    @text from MARK: party at Kelly Baker's tomorrow night. who's in
    @text from JOSIE: IN
    @text from TYLER: party tomorrow night. who's in
  }

  @phone {
    @text from MARK: hernandez?
    @text from MARK: hernandez
    @text from MARK: HERNANDEZ
    @text from MARK: I will come to your house
    @text to MARK: Fine. I'm in.
  }

  @phone {
    @text from ELIAS: Hey. Mark gave me your number. Hope that's okay. I wanted to ask -- have you read anything by Sylvia Plath? I'm looking for a recommendation for someone.
  }

  INNER_THOUGHT: Elias Hall is texting me. About Sylvia Plath. On a Friday night.
  INNER_THOUGHT: "For someone." Who is "someone"?
  INNER_THOUGHT: Also, since when does Elias text people? He's the most antisocial person in our entire friend group.

  @phone {
    @text to ELIAS: The Bell Jar. start there. who's it for?
    @text from ELIAS: Myself. I just didn't want to say that and sound pretentious.
  }

  INNER_THOUGHT: He asked for a recommendation but said "for someone" instead of "for me" because he didn't want to seem pretentious.
  INNER_THOUGHT: That's either very endearing or very calculated.
  INNER_THOUGHT: I genuinely cannot tell.

  @phone {
    @text to ELIAS: not pretentious. good taste actually.
    @text from ELIAS: Thanks. Goodnight, Malia.
  }

  INNER_THOUGHT: "Goodnight, Malia."
  INNER_THOUGHT: Period at the end and everything. Elias Hall is the only person under 25 who uses periods in texts sincerely.

  NARRATOR: Three conversations open. Easton's unread text from this morning. Elias's polite sign-off. And the text from Mauricio: "nice curtains, Butterfly."


  @gate {
    @next main:04
  }
}
