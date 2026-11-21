# TalkLine Studio implementation roadmap

## Where to start

Follow the [ordered roadmap and acceptance checks in the README](../README.md#development-roadmap). The R0–R6 labels below group engineering work by subsystem. Several groups already have working code. The immediate product milestone is Round 1 quality and layout in the two discussion formats.

The app selects a concept from the topic before generation and uses it for both
the session format and invitation style. The host can override it. Local Ollama
writes the content for the editable PowerPoint and invitation GIF. Game links
open the HTML files beside the deck after ZIP extraction. The final slide links
to the approved Rate Us form.

Use the TalkLine Brand Guide and the corresponding supplied deck as the session
reference. The program assembles a welcome and warm-up, Toolkit and mini grammar,
Round 1, break, Round 2, cooldown, and the approved Rate Us close. The opening
and closing paragraphs go into the host's materials. Concept examples determine
the order for exceptions such as Game Night. Ollama runs locally and produces
content. Application code owns the sequence, template bindings and exports.

Keep the example fixtures for offline tests of packaging and navigation. A fresh
local-model run verifies content generation. Record what each test covers.

Owner scope: one personal session roughly weekly. Slide count and sequence follow
the concept and approved sample, not a universal 23-slide structure. Every session
has one or two HTML games; Game Night has two. Preserve invitation source geometry
and aspect ratio. See [research and decisions](ARCHITECTURE_DECISION_FA.md).

## Current implementation

Windows/Python 3.14 bootstrap, local Ollama qwen3:8b, critique and section
regeneration, saved event defaults, original-template invitation export and five
invitation styles are present. The Windows launcher health check passed.

Spontaneous Talk, Business English and Game Night have local generation and offline export paths.
Each produces an editable presentation with speaker notes, a Toolkit with
separate levels and grammar, a host guide, game files, and an original-template
invitation GIF. Spontaneous Talk includes ten tiered discussions followed by
Patch Notes. Business English uses its blue reference deck with Smart or Sneaky. Game
Night has Taboo before the break and Problem Solver after it. Each game uses
twenty Elementary and twenty Advanced cards. The two game difficulty bands and
three forbidden clues for Taboo follow the current HTML contract. The Toolkit
retains its three learner groups.

Pop Culture and Culture Exchange still use a short prototype. Live Business AI
generation needs a test on a fresh topic. Broader weekly-use tests remain open.

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

- Extend the full-session version 2 export without silently reinterpreting the existing v1 contract:
  concept, template, event metadata, ordered activities, games[], levelled Toolkit,
  invitation content, review status and working links to the local games and Rate Us.
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

- Verify the existing Game Night mechanics, their two independent HTML files
  and corresponding presentation pages on a fresh topic.
- Verify the existing Business English flow. Build Pop Culture and Culture
  Exchange from their own samples.
- Replace hardcoded Patch Notes selection with compatible mechanic selection.
- Acceptance: each concept passes content, rendering, game and package checks.

## R5 — public game hosting (deferred)

The owner has paused publishing and its Canva link checks. Weekly readiness
uses the local HTML files in the extracted session folder. [Current decisions](../README.md#concept-selection-and-hosting)

## R6 — reliable UI and Windows convenience

- Progress, cancellation, checkpoints, history and interruption recovery.
- Separate services from Streamlit; workers do not directly call UI APIs.
- Preserve launcher; evaluate EXE packaging after full-kit stability.
- Measure full-session speed and resources on the target 6 GB GPU, check Windows
  startup and installation, and write short instructions in plain English.

## Working rules

Preserve working components, avoid broad rewrites, test executable milestones.
No paid runtime AI. Do not infer dates from the unanchored calendar or silently
resolve its conflicting Saturday entries. Never describe planned features as done.
