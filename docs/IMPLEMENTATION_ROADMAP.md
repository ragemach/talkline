# TalkLine Studio implementation roadmap

## Delivery order

Use the TalkLine Brand Guide and the corresponding supplied deck as the session
reference. The program assembles a welcome and warm-up, Toolkit and mini grammar,
Round 1, break, Round 2, cooldown, and the approved Rate Us close. The opening
and closing paragraphs go into the host's materials. Concept examples determine
the order for exceptions such as Game Night. Ollama runs locally and produces
content. Application code owns the sequence, template bindings and exports.

1. **Working baseline.** Keep Windows startup, Demo and local Ollama usable.
   Preserve the last successful draft and matching ZIP when a run fails or the
   browser closes. The saved-run and launcher checks passed.
2. **First complete session.** Connect Spontaneous Talk from the app through ten
   tiered discussion cards, the Toolkit, one playable levelled game, an editable
   deck, the host guide and the original-template GIF. Check the extracted ZIP
   offline and run a fresh topic through local Ollama.
3. **Weekly workflow.** Let the owner review, edit or regenerate one section and
   keep the others. Recover completed sections after interruptions. Finish this
   workflow before repeating it across concepts.
4. **Remaining concepts.** Add the supplied Business, Culture Exchange and Pop
   Culture formats. Add Game Night with its two different games. Each concept
   gets a full package and a render check before it is called ready.
5. **Weekly readiness.** Test Windows startup, real-model runs, resume, file
   links, phone-sized game controls and broken-dependency recovery. Mark the
   app ready only when a new weekly topic can be generated and run without Codex.
   Online publishing is a separate workflow for a verified eligible free account.

Work through the stages in this order. A Demo proves packaging and navigation.
A fresh local-model run is the content-generation check. Record what each test
actually covers.

Owner scope: one personal session roughly weekly. Slide count and sequence follow
the concept and approved sample, not a universal 23-slide structure. Every session
has one or two HTML games; Game Night has two. Preserve invitation source geometry
and aspect ratio. See [research and decisions](ARCHITECTURE_DECISION_FA.md).

## Current implementation

Windows/Python 3.14 bootstrap, local Ollama qwen3:8b, critique and section
regeneration, saved event defaults, original-template invitation export and five
invitation styles are present. The Windows launcher health check passed.

Spontaneous Talk, Business English and Game Night can build complete offline Demo
kits. Each produces an editable presentation with speaker notes, a Toolkit with
separate levels and grammar, a host guide, game files, and an original-template
invitation GIF. Spontaneous Talk includes ten tiered discussions followed by
Patch Notes. Business English uses its blue reference deck with Smart or Sneaky. Game
Night has Taboo before the break and Problem Solver after it. Each game uses
twenty Elementary and twenty Advanced cards. The two game difficulty bands and
three forbidden clues for Taboo follow the current HTML contract. The Toolkit
retains its three learner groups.

Pop Culture and Culture Exchange still use a short prototype. Live Business AI
generation needs a test on a fresh topic. Online game publishing, Canva import
verification, and broader weekly-use testing remain open.

## R0 — shared session plan and template blueprints

Spontaneous Talk now has a reproducible reference inventory:
`scripts/catalogue_templates.py` creates `templates/spontaneous.blueprint.json`.
It records all 23 source slides, nested text shape paths, local geometry, run
font information, notes and a source fingerprint. Explicit bindings identify
48 fields for the cover, warm-up, ten discussion cards and cooldown. Source
changes and missing bound fields are rejected. The Spontaneous Talk and Game
Night renderers create native slides and use the matching offline game links.

The prototype saves its latest successful draft and matching ZIP locally. The
app restores the saved event details on reopening and hides downloads when the
form or content belongs to a different revision. Failed generation and export
attempts leave the previous successful work available.

Started: `src/session_plan.py` validates ordered game slots, code-assigned IDs,
supported mechanics and per-concept game counts. This is a planning foundation
for the shared plan. The app uses the same meeting sequence for preview and export.

Added `src/game_content.py`: mechanic-specific payload validation and binding to
ordered slots. Taboo has a target and three forbidden words; Problem Solver has
a situation and challenge; choice games retain choices/outcomes. Each payload
requires twenty cards per level, rejects duplicate identities and model-provided
IDs, and receives stable IDs during binding. Full-session demos and local
generation use the structural validators. Check language level and relevance
when reviewing the generated material.

- Introduce version 2 without silently reinterpreting the existing v1 contract:
  concept, template, event metadata, ordered activities, games[], levelled Toolkit,
  invitation content, review status and local/verified online links.
- Catalogue supplied presentation layouts and editable fields per concept.
- Model mechanic-specific requirements; do not force Taboo or Problem Solver into
  two-choice cards. Require exactly two games for Game Night. Assign IDs in code.
- Save generation checkpoints; invalidate dependent artifacts after edits.
- Acceptance: tests reject wrong game counts, incompatible mechanics, invented
  event metadata and stale artifacts; existing Demo/invitation tests still pass.

## R1 — complete content for one concept

- Start with Spontaneous Talk, generalize after one complete session works.
- Simple warm-ups; levelled vocabulary, phrases and idioms with Turkish meanings
  and full English examples; mini grammar explanations, patterns and examples.
- Generate real activities before promotional descriptions, in resumable batches
  with bounded retries. Critique is advisory; retain human editing/regeneration.
- Acceptance: fresh-topic validated full plan, not a synthetic test fixture.

## R2 — first complete editable presentation

- Render approved concept-specific flow, speaker notes and actual activity rules.
- Preserve native shapes, fonts, artwork and geometry. Reuse approved Toolkit
  pages for extra space rather than shrinking fonts.
- Render/inspect every slide and check editing in PPTX. Do not invent game URLs.
- Acceptance: complete fresh-topic deck following the supplied sample structure.

## R3 — first HTML game and complete offline kit

- One reusable mechanic with independent generated data: twenty Elementary and
  twenty Advanced cards where the selected mechanic calls for them.
- Inline assets, no network dependency; host controls, keyboard/mobile support.
- Browser tests cover all cards, levels, reveal state, back/restart/replay and
  mechanic-specific choices. Test relative links after ZIP extraction.
- Export deck, game, original-template GIF, JSON and links.txt in one ZIP.
- Acceptance: complete fresh-topic event works with network disconnected.

## R4 — Game Night and remaining concepts

- Implement both mechanics required by the Game Night sample, two independent
  HTML files and corresponding presentation pages.
- Add Business English, Pop Culture and Culture Exchange using their own samples.
- Replace hardcoded Patch Notes selection with compatible mechanic selection.
- Acceptance: each concept passes content, rendering, game and package checks.

## R5 — free publishing and verified presentation links

- Owner selected Vercel Free and explicitly rejected Netlify. Export a static
  archive retaining old event paths; verify the connected account and deployment
  capability before claiming publication. No paid upgrade or Pro trial.
- Keep hosting limits/terms distinct from technical HTML compatibility. Commercial
  events are confirmed; do not certify plan eligibility from deployment success.
- Verify real game URLs before final online PPTX; keep offline links available.
- Use the real Rate Us form and links.txt for manual Canva link placement.
- Test actual Canva import for fonts/layout/links; do not promise untested fidelity.
- Automatic authenticated publishing follows account setup as a later integration.

## R6 — reliable UI and Windows convenience

- Progress, cancellation, checkpoints, history and interruption recovery.
- Separate services from Streamlit; workers do not directly call UI APIs.
- Preserve launcher; evaluate EXE packaging after full-kit stability.
- Measure full-session speed/resources on actual 6 GB GPU, test startup/install,
  and write short Persian instructions.

## Working rules

Preserve working components, avoid broad rewrites, test executable milestones.
No paid runtime AI. Do not infer dates from the unanchored calendar or silently
resolve its conflicting Saturday entries. Never describe planned features as done.
