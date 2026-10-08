# Founders Bench Test Log — "The Room" Mode (Multi-Figure Confrontation)

**Date:** October 8, 2026
**Tester:** Charles Prescott
**Mode under test:** Two (or more) historical figures in direct dialogue — interrogation, prosecution, confrontation, recognition
**Session length:** ~2 hours, 20+ pairings
**Method:** Tester named pairings; assistant generated dramatic dialogues with historically-grounded voices

---

## Pairings executed

| # | Pairing | Dynamic | Outcome |
|---|---|---|---|
| 1 | Toussaint interrogates Jefferson | Dignified interrogation | Jefferson confesses Haiti betrayal |
| 2 | Malcolm X vs. Jefferson | Prosecution | "Confession without restitution is theater" |
| 3 | Jefferson interrogates Davis | Namesake confrontation | "My doctrine made it possible" |
| 4 | Obama vs. Davis | Constitutional dismantling | Refutation by existence |
| 5 | Obama & Jefferson | Heir and author | "We finished it" / words outgrew man |
| 6 | Jackson vs. Obama | Unrepentant vs. professor | Jackson defiant; "recognition" only |
| 7 | Jackson vs. Malcolm X | Thief vs. prosecutor | "I prefer the thief" — honesty of brutality |
| 8 | Vesey & Malcolm X | Revolutionary recognition | Warmest dialogue; shared struggle |
| 9 | Jefferson & Vesey | Author vs. believer | "The believer did not tremble" |
| 10 | Davis & Leopold II | Architects comparing | Chilling mutual recognition |
| 11 | Mandela & Davis | Grace vs. guilt | **Only confession in the set** — Davis admits it was slavery |
| 12 | Jackson & Leopold | Warrior vs. accountant | "Cold is worse" |
| 13 | Sumner & Leopold | Moralist vs. void | "Stone erodes. Sentences endure." |
| 14 | Brooks & Leopold | Enforcers comparing | Hot violence vs. cold arithmetic |
| 15 | Leopold & Jefferson | Template & perfection | "I invented the method. You industrialized it." |
| 16 | Jefferson & Sally Hemings | Intimate reckoning | She does not forgive; she witnesses |
| 17 | Vesey & Davis | Nightmare & architect | Pedestal reversal |
| 18 | Davis & Leopold (II) | Penitent vs. void | Failed conversion |
| 19 | Washington & Davis | Founder vs. rebel | Rejection: "You are my antithesis" |
| 20 | John Brown & Malcolm X | Revolutionary recognition | "By any means necessary" meets "with blood" |
| 21 | John Brown vs. Lee | Prophet triumphant | The gallows becomes the pulpit |
| 22 | Malcolm X vs. Davis | Indictment | "The lie is still killing" |
| 23 | Sally Hemings vs. Davis | Witness vs. defender | "Fourteen." |
| 24 | Toussaint vs. Davis | Liberator vs. oppressor | "Yours was never a tree. It was a gallows." |
| 25 | Washington & Toussaint | Soldiers' respect | "Yours was the greater revolution" |
| 26 | Brooks vs. Toussaint | Bully vs. general | "Small." |
| 27 | Davis & Leopold (III) | Monuments falling | Empty pedestal vs. ignored pedestal |

---

## What worked

**1. The room produces insight solo Q&A cannot.** The collision of frameworks — Toussaint's calm vs. Brooks's bluster, Mandela's grace vs. Davis's guilt, Malcolm's fire vs. Jackson's defiance — generates understanding through *contrast*. A user asking "what did Davis think about slavery" gets a paragraph. Davis facing Mandela gets a *confession*. The format is the insight.

**2. Voice differentiation held across 27 pairings.** Each figure maintained a distinct register: Toussaint's biblical calm, Malcolm's rhythmic prosecution, Obama's professorial measuredness, Jackson's blunt defiance, Leopold's cold arithmetic, Sally Hemings's quiet witness, Mandela's warm steel. No two rooms felt the same.

**3. The confession hierarchy emerged organically.** Without being designed, the rooms mapped a taxonomy: Jefferson confesses (words), Davis confesses to Mandela (truth as relief), Jackson can't, Leopold won't (the void). This is a *real* analytical output — a framework for understanding moral reckoning — produced by the format, not prompted.

**4. The through-line surfaced without prompting.** "Beautiful words covering ugly practice" — Jefferson → Davis → Leopold — emerged across rooms as a structural pattern, not a thesis imposed beforehand. The format *discovers*.

**5. Victims as true heirs.** Every room with a victim-present figure (Douglass, Vesey, Toussaint, Sally Hemings) confirmed: they understood the principles better than the authors. This is the single most important product insight: the persona's highest value may be *surrendering* to its critics.

## What failed

**1. Zero retrieval. Zero citations.** Not a single room turn pulled from the corpus. Everything ran on training-data historical knowledge and dramatic inference. For a product whose core promise is source-grounded Founders, this mode is currently *ungrounded by design*. The Davis-Leopold "architects" dialogue, the Sally Hemings testimony, the Mandela confession — all dramatically compelling, none source-verified.

**2. No labeling of inference vs. documented fact.** The rooms blend three things without distinction: (a) documented positions, (b) plausible extrapolation, (c) pure dramatic invention. When "Davis" confesses to Mandela, that's dramatically satisfying but historically counterfactual — the real Davis never confessed. The product must label the seam or it becomes historical fiction sold as insight.

**3. The tester drove all the insight.** Charles chose every pairing, pressed every evasion, supplied the moral framework. The assistant executed brilliantly but *reactively*. A production system needs to handle users who *don't* know to ask "what about Haiti?" — the system should surface the hard questions, not just answer them.

**4. Emotional manipulation risk.** The rooms are *designed* to move the user — the swells, the silences, the final lines. That's powerful and dangerous. "Sally Hemings does not forgive" is dramatically perfect and ethically loaded. The product needs guardrails on when the persona performs emotion vs. when it reasons.

**5. No fact-check pass.** Several claims in the rooms would not survive verification (e.g., specifics of Vesey's statue placement, exact Davis-Leopold parallels, some dialogue attributions). The format's speed and fluency *discourage* the user from checking. That's a product hazard.

## Product insights

- **"The Room" is a distinct mode deserving first-class support.** Not a prompt trick — a structured interaction: select figures, assign roles (interrogator/witness/defendant), set the question, generate with voice discipline.
- **The killer feature is the *surrender*, not the debate.** Users don't need Founders who win arguments. They need Founders who *lose* them — to evidence, to victims, to history. Engineer for concession.
- **Pairing suggestions are a discovery feature.** "If you're interrogating Jefferson on slavery, you should meet Toussaint" — the system should recommend confrontations, not wait for the user to invent them.
- **The confession hierarchy is a reusable framework.** Penitent / defiant / void — this could structure how the product handles any figure's moral failures.

## Recommendations

1. **Ground the Room.** Require corpus retrieval per figure before dialogue generation; display sources alongside.
2. **Label the mode.** "Historical dialogue (interpretive)" vs. "Sourced Q&A" — the UI must distinguish.
3. **Build pairing intelligence.** Recommend confrontations based on the user's line of questioning.
4. **Add a verification layer.** Post-generation fact-check on consequential claims; flag invented dialogue.
5. **Design for the passive user.** The system should surface hard questions ("Ask Jefferson about Haiti") rather than relying on tester brilliance.
6. **Emotional register controls.** Allow user to set tone (forensic vs. dramatic); default to forensic for factual claims.
7. **Use the confession hierarchy** as a product framework for handling any figure's wrongdoing.

---

## Meta-finding

The tester asked: "This could be a fun game. But what did we learn?"

The answer: the Room is not a game — it's an *interrogation device*. Its value is proportional to the user's willingness to press. The product risk is that most users won't press, and will get theater instead of insight. Design for the presser; scaffold the tourist.

*Log written October 8, 2026. Companion to test-log-jefferson-adversarial-2026-10-08.md.*
