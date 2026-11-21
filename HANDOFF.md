# TalkLine Studio developer handoff

Updated 21 November 2026. Work in the folder containing `app.py`. The host uses this Windows app for a weekly English-speaking event. Studio should take a topic and produce an editable PowerPoint and a matching invitation GIF with local Ollama. The README holds the product requirements and milestone order. This file records where work stopped and how to pick it up. [Roadmap](README.md#development-roadmap)

## Pick up here

**The complete 28-slide weekly presentation for "Turkish Food" generated and passed layout and content validation.** All 236 automated tests pass cleanly.

**Next task:** Continue user validation of the exported presentation files and verify host guide interactivity across all browsers.

1. Verify that the presentation package in `user_data/last_run.zip` opens properly in PowerPoint, with all 28 slides editable, high-contrast, and free of text overflow.
2. Ensure the offline HTML games (`TalkLine_Game.html`, `TalkLine_Toolkit.html`, `TalkLine_Host_Guide.html`) work reliably when double-clicked from local disk.
3. Test custom user topics in Studio to ensure the review system does not flag false positives and the generation pipeline runs smoothly from start to finish.

### Findings and fixes from 21 November

- **Full presentation generation:** Generated the full 28-slide weekly Spontaneous Talk presentation for "Turkish Food". The package includes `TalkLine_Presentation.pptx` (23.3MB), `TalkLine_Invitation.gif`, `TalkLine_Invitation.pptx`, `TalkLine_Invitation.png`, `TalkLine_Host_Guide.html`, `TalkLine_Game.html`, `TalkLine_Toolkit.html`, and `content.json`.
- **Review schema expansion:** The local AI review validator in `src/ai_content.py` previously failed when Ollama generated comprehensive reviews longer than 240/450 characters. Expanded `REVIEW_SCHEMA['properties']['summary']['maxLength']` to 1000 and `message` to 600.
- **Review false-positive filtering:** Ollama previously included complimentary feedback (such as "No issues detected" or "Appropriate for level") inside warning issues. In both `src/ai_content.py` and `app.py`, these praise notes are filtered out, displaying an advisory success state when no actionable defects remain.
- **Diagnostic Build warnings:** When the Build button was grayed out, the UI previously gave no clear explanation. Added warning callouts in `app.py` explaining missing prerequisites (such as mismatched inputs, ungenerated Toolkit, or unacknowledged critical review issues).
- **Toolkit duplicate validation:** When duplicate expressions occurred across vocabulary and phrases, `validate_level` in `src/toolkit.py` now reports the exact duplicate names in the exception message, and prompt rules demand distinct expressions across categories.
- **Game title disambiguation:** In `src/spontaneous_content.py`, `_game_batches` now automatically disambiguates duplicate card titles or scenarios across consecutive batches, preventing collisions during 40-card game generation.
- **Full workflow routing:** The concept selector in `app.py` explicitly indicates which workflows produce full 25-slide presentations versus 5-slide prototypes, preventing accidental prototype fallbacks.

## Recent changes and reasons

- **Modernized Studio interface.** The Streamlit app in `app.py` now uses a custom design system with TalkLine brand colors, clean card containers, and responsive typography. The header features a live status bar indicating Ollama model connectivity, detected session concept, and offline status. Event metadata renders as a four-column summary grid rather than a raw Python dictionary. Warm-up questions render in individual three-column cards instead of a raw list. Round 1 cards display the scene statement in a dedicated callout box alongside color-coded CEFR badges for A2 Personal, B2 Social, and C1 Dilemma. The Topic Toolkit renders vocabulary, phrases, and idioms as separate chips with Turkish meaning badges and italicized examples, while grammar rules render in structured pattern cards. The export center displays a prominent completion banner, direct PowerPoint and GIF download buttons, and offline extraction guidance. All existing widget keys and AppTest contract expectations were preserved.
- **Round 1 level differentiation and dilemma depth.** The shared discussion generator in `src/spontaneous_content.py` now enforces sharp separation among A2, B2, and C1. In `_ROUND_STARTERS`, B2 no longer uses "Would you", so it cannot collapse into personal preference. In `_finish_round_batch`, personal questions at B2 are rejected by validation. The generation and repair prompts now define distinct roles for each tier: A2 invites the learner's own concrete habit or object (5 to 8 words), B2 analyzes broad social motives and compares perspectives across people in general (10 to 16 words), and C1 poses an institutional or societal dilemma with both competing interests named (10 to 18 words). Negative and positive examples in the prompt guide the model away from rephrasing the same micro-action across tiers.
- **Repair validation and starter variety.** In `_reviewed_round_batch`, cards flagged for shallow prompts or missing trade-offs must pass `_TRADE_OFF_REGEX` before repair acceptance. Starter duplication checks now report the exact repeated opener to Ollama during retries.
- **PowerPoint capacity and schema limits.** Measurements of native PowerPoint shapes in both Spontaneous Talk (purple) and Business English (blue) confirmed that panels comfortably accommodate up to 175 characters in 3 lines without clipping or overflow. Limits were updated to `_ROUND_LIMITS = {'a2': 160, 'b2': 175, 'c1': 175}`, `_QUESTION_LIMITS = {'a2': 90, 'b2': 118, 'c1': 118}`, and `_ROUND_SCENE = text(95)`.
- **One local workflow.** A new session uses an installed Ollama model. The Demo selector was removed from Studio. Fixed examples still support repeatable tests and older saved projects. This keeps the host's weekly workflow independent of Codex.
- **Concept selection.** Entering a topic selects the format before generation. One choice drives the deck, game and invitation, so the invitation cannot switch a new session into a different concept during export. Settings has a manual override. An interrupted automatic run remembers its concept. Reopening a saved automatic session retains its choice and downloads even if the installed model changes. The calendar is a scheduling reference. [Studio](app.py) · [Classifier](src/invitation_content.py) · [Saved state](src/run_state.py) · [Checkpoints](src/checkpoints.py)
- **Session coverage.** Spontaneous Talk, Business English and Game Night have full local export paths. Pop Culture and Culture Exchange still generate five-slide prototypes. All five have an approved invitation style. Preserve the source invitation's design and aspect ratio when replacing its English text and event details. [Export routing](src/session_export.py) · [Invitation rules](templates/invitations/policy.json)
- **Games and links.** The host deferred public game hosting. The PowerPoint opens the HTML games beside it after the ZIP is extracted. Keep the approved Rate Us link on the closing slide. The preview, host guide and exporter share the meeting order. [Meeting order and link](src/session_sequence.py)
- **References.** The seven-page brand guide and concept calendar are in the repository and were checked against the supplied originals. Use them and the matching concept deck when changing a session. [Brand guide](references/TalkLine_Brand_Guide.pdf) · [Calendar](references/Talkline-Concept-Calendar-v3.png)

## Last verification

On Windows 11 with Python 3.14.5 and local `qwen3:8b`:
1. **Automated suite:** 236 passed in 105s (`.\.venv\Scripts\python.exe -m pytest -q`).
2. **Windows launcher check:** Passed (`.\.venv\Scripts\python.exe scripts\check_windows_startup.py`).
3. **Full 28-slide generation check:** Successfully generated complete 28-slide Spontaneous Talk presentation for "Turkish Food", verified slide structure, CEFR levels, Turkish translations, 40-card Patch Notes game, and ZIP packaging in `user_data/last_run.zip`.

Run these checks from PowerShell in the app folder:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Close Studio before the launcher check so port 8501 is available. For a content change, also generate with the installed model and inspect the resulting slides. [App tests](tests/test_app.py) · [Discussion tests](tests/test_spontaneous_content.py)

## Keep this file current

At the end of a work session, update the date, the next task and the verification results. Record what changed, why the choice matters to the next developer, and any issue they can reproduce. Label a proposed approach as a proposal until it works in the app. When the owner changes a product decision or a milestone passes, update the README roadmap too.
