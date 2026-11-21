# TalkLine Studio developer handoff

Updated 21 November 2026. Work in the folder containing `app.py`. The host uses this Windows app for a weekly English-speaking event. Studio should take a topic and produce an editable PowerPoint and a matching invitation GIF with local Ollama. The README holds the product requirements and milestone order. This file records where work stopped and how to pick it up. [Roadmap](README.md#development-roadmap)

## Pick up here

Studio reopened the saved Turkish Food session and exported a 28-slide PowerPoint. Its Toolkit still has confirmed translation errors. All 236 automated tests passed.

1. Fix the local Toolkit generator and review first. In the Turkish Food draft, a B1 phrase puts “Bu yemek ne kadar sıcak?” in the English field and “How hot is this dish?” in the Turkish field. A B2/C1 entry translates “meze” as “tatlı” (dessert). All 36 vocabulary, phrase and idiom entries have a translation field. A presence check alone misses both errors. Keep mini-grammar explanations and examples in English as specified. Regenerate and check the corrected output through Studio.
2. Open the exported PowerPoint in desktop PowerPoint to check text fit and editing. Extract the ZIP and play through the game from the slide link. Check the host guide in a browser.
3. Repeat the language and export checks on a new topic.

### Findings and fixes from 21 November

- **Full presentation generation.** The Turkish Food ZIP contains the 28-slide `TalkLine_Presentation.pptx` (3.6 MB), `TalkLine_Invitation.gif`, `TalkLine_Invitation.pptx`, `TalkLine_Invitation.png`, `TalkLine_Host_Guide.html`, `TalkLine_Game.html`, `TalkLine_Toolkit.html` and `content.json`.
- **Review schema expansion:** The local AI review validator in `src/ai_content.py` previously failed when Ollama generated comprehensive reviews longer than 240/450 characters. Expanded `REVIEW_SCHEMA['properties']['summary']['maxLength']` to 1000 and `message` to 600.
- **Review false-positive filtering:** Ollama previously included complimentary feedback (such as "No issues detected" or "Appropriate for level") inside warning issues. In both `src/ai_content.py` and `app.py`, these praise notes are filtered out, displaying an advisory success state when no actionable defects remain.
- **Diagnostic Build warnings:** When the Build button was grayed out, the UI previously gave no clear explanation. Added warning callouts in `app.py` explaining missing prerequisites (such as mismatched inputs, ungenerated Toolkit, or unacknowledged critical review issues).
- **Toolkit duplicate validation:** When duplicate expressions occurred across vocabulary and phrases, `validate_level` in `src/toolkit.py` now reports the exact duplicate names in the exception message, and prompt rules demand distinct expressions across categories.
- **Game title disambiguation:** In `src/spontaneous_content.py`, `_game_batches` now automatically disambiguates duplicate card titles or scenarios across consecutive batches, preventing collisions during 40-card game generation.
- **Full workflow routing:** The concept selector in `app.py` explicitly indicates which workflows produce full 25-slide presentations versus 5-slide prototypes, preventing accidental prototype fallbacks.

## Recent changes and reasons

- **Modernized Studio interface.** The Streamlit app in `app.py` now uses a custom design system with TalkLine brand colors, clean card containers, and responsive typography. The header features a live status bar indicating Ollama model connectivity, detected session concept, and offline status. Event metadata renders as a four-column summary grid rather than a raw Python dictionary. Warm-up questions render in individual three-column cards instead of a raw list. Round 1 cards display the scene statement in a dedicated callout box alongside color-coded CEFR badges for A2 Personal, B2 Social, and C1 Dilemma. The Topic Toolkit renders vocabulary, phrases, and idioms as separate chips with Turkish meaning badges and italicized examples, while grammar rules render in structured pattern cards. The export center displays a prominent completion banner, direct PowerPoint and GIF download buttons, and offline extraction guidance. All existing widget keys and AppTest contract expectations were preserved.
- **Round 1 questions.** Generation and repair share the same tier guidance. A2 asks about concrete experience, B2 compares social perspectives and C1 asks about a trade-off. The prompts omit complete sample questions after the model copied some into unrelated sessions. New generations check for direct requests to disclose personal pay and allow general or hypothetical pay discussions.
- **Repair validation and starter variety.** In `_reviewed_round_batch`, cards flagged for shallow prompts or missing trade-offs must pass `_TRADE_OFF_REGEX` before repair acceptance. Starter duplication checks now report the exact repeated opener to Ollama during retries.
- **Round 1 editing and preview.** The generator and Studio editor use `ROUND_CARD_TEXT_LIMITS` in `src/content_rules.py` for the full text of each tier. A2 allows 160 characters, B2 and C1 allow 175 each. A regression test edits all three beyond the previous editor limits, reopens the draft, and compares the saved text with the PowerPoint, notes, host guide and JSON. The Studio preview also preserves older cards with different scenes in each tier. The header reflects the selected concept and the event summary shows missing details.
- **One local workflow.** A new session uses an installed Ollama model. The Demo selector was removed from Studio. Fixed examples still support repeatable tests and older saved projects. This keeps the host's weekly workflow independent of Codex.
- **Concept selection.** Entering a topic selects the format before generation. One choice drives the deck, game and invitation, so the invitation cannot switch a new session into a different concept during export. Settings has a manual override. An interrupted automatic run remembers its concept. Reopening a saved automatic session retains its choice and downloads even if the installed model changes. The calendar is a scheduling reference. [Studio](app.py) · [Classifier](src/invitation_content.py) · [Saved state](src/run_state.py) · [Checkpoints](src/checkpoints.py)
- **Session coverage.** Spontaneous Talk, Business English and Game Night have full local export paths. Pop Culture and Culture Exchange still generate five-slide prototypes. All five have an approved invitation style. Preserve the source invitation's design and aspect ratio when replacing its English text and event details. [Export routing](src/session_export.py) · [Invitation rules](templates/invitations/policy.json)
- **Games and links.** The host deferred public game hosting. The PowerPoint opens the HTML games beside it after the ZIP is extracted. Keep the approved Rate Us link on the closing slide. The preview, host guide and exporter share the meeting order. [Meeting order and link](src/session_sequence.py)
- **References.** The seven-page brand guide and concept calendar are in the repository and were checked against the supplied originals. Use them and the matching concept deck when changing a session. [Brand guide](references/TalkLine_Brand_Guide.pdf) · [Calendar](references/Talkline-Concept-Calendar-v3.png)

## Last verification

On Windows 11 with Python 3.14.5 and local `qwen3:8b`:
1. The full automated suite passed all 236 tests in 146 seconds (`.\.venv\Scripts\python.exe -m pytest -q`).
2. **Windows launcher check:** Passed (`.\.venv\Scripts\python.exe scripts\check_windows_startup.py`).
3. Studio's Build button exported an isolated copy of the saved Turkish Food draft. A fresh Studio instance reopened the same export byte for byte. The ZIP passed its integrity check and contained eight files, including a 28-slide presentation and an 18-frame looping invitation measuring 1920 × 1362 pixels. The PowerPoint links point to the bundled game and the approved Rate Us form. The local verification output is `output/weekly-turkish-food/TalkLine_Session.zip`. Studio stores personal drafts separately in `user_data/last_run.zip`. The checks here cover file structure, persistence and link targets. The language issues above and playback in desktop PowerPoint still need attention.

Run these checks from PowerShell in the app folder:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Close Studio before the launcher check so port 8501 is available. For a content change, also generate with the installed model and inspect the resulting slides. [App tests](tests/test_app.py) · [Discussion tests](tests/test_spontaneous_content.py)

## Keep this file current

At the end of a work session, update the date, the next task and the verification results. Record what changed, why the choice matters to the next developer, and any issue they can reproduce. Label a proposed approach as a proposal until it works in the app. When the owner changes a product decision or a milestone passes, update the README roadmap too.
