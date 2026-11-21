# TalkLine Studio

TalkLine Studio is a personal Windows app for preparing a weekly English-speaking event in Istanbul. The host enters a topic and checks the event details. Local Ollama writes the session in English. The app assembles an **editable PowerPoint** and an **animated invitation GIF** from the supplied TalkLine designs. Turkish is used for Toolkit meanings. After the initial installation, the host can generate on the laptop without a coding assistant, a paid AI API or an internet connection.

Development is currently focused on **making one full weekly session dependable** (Milestone 2) after completing Round 1 quality and layout in Spontaneous Talk and Business English. The developer handoff records the latest test results and how to pick up the work. [Current handoff](HANDOFF.md) · [Roadmap](#development-roadmap)

## Start on Windows 11

1. Open the project folder that contains `app.py`. On a new computer, install Python 3.14, LibreOffice and Ollama. Download the default model once with `ollama pull qwen3:8b`. This project has been tested with Python 3.14.5 on the host's 32 GB laptop.
2. Double-click `START_WINDOWS.bat`. It prepares the private Python environment and starts the app. Open the [local Studio](http://127.0.0.1:8501) if the browser does not open automatically.
3. Enter a topic and check the event details. Studio automatically selects one of the five TalkLine concepts from the topic before generating the session. You can choose a different concept in Settings. The usual time is 20:00. Holstory Cafe, Beşiktaş is an example venue. A fresh installation leaves the event fields blank until the host enters or saves them.
4. Review the draft, edit or regenerate a section if needed, then select **Build session files**. The two main downloads are the presentation and invitation. To play today's games locally, expand **Local game files**, extract the ZIP and open the PowerPoint inside it. Its game links expect the HTML files beside it. Opening the online feedback form requires internet.

## What works today

- **Spontaneous Talk** and **Business English** each have a full local export path. Both include ten tiered discussion slides. Their Round 2 games are *Patch Notes* and *Smart or Sneaky?*, respectively.
- **Game Night** has a full local export path with two different games. Taboo comes before the 20-minute break and Problem Solver follows it. Each game opens from its own slide.
- **Pop Culture** and **Culture Exchange** have reference decks and invitation styles. A topic assigned to either follows its five-slide prototype until the full format is implemented.
- **Recovery** reopens the latest saved draft and its matching export. Full-session generation can resume completed batches for the same concept, topic and model. A changed draft needs a fresh export. The local ZIP also contains the host guide, content data, editable invitation and preview.
- **Content quality.** The app checks structure, counts, starters and trade-offs. Round 1 discussion generation enforces topic premise permanence, eliminating false cutoffs (including the all-night buses case). Question starters rotate across cards and C1 prompts name explicit trade-offs. Toolkit translations, level progression and full sessions continue in Milestone 2.

## How a session is built

Use the matching sample's order and design. Slide counts vary by concept. The discussion sequence is **welcome and warm-up → Toolkit → mini grammar → Round 1 → break → Round 2 → cooldown → Rate Us**. Game Night uses its two-game sequence. Give the host a short opening and closing paragraph in the host materials. Keep space for the host's photo on the cover and use native, editable slide text and speaker notes.

- **Warm-up.** Ask up to three very simple, polite questions that adults can answer immediately, such as “How was your day?”
- **Toolkit.** Keep A1/A2, B1 and B2/C1 on separate pages. For each group, aim for eight common, topic-relevant vocabulary items (seven to ten allowed), plus short phrases and level-appropriate idioms. Give every item a Turkish meaning and a complete English example. Put mini grammar on separate pages with an explanation, pattern and example. Fit panels to the content. The expression has the strongest contrast, then the translation, then the example. All three must be readable.
- **Round 1 discussion.** Generate ten distinct, concrete situations about the topic. Give each one an editable slide with three stacked questions about the **same situation**. A2 invites a simple personal answer, B2 asks for a reason or comparison, and C1 introduces a meaningful choice, constraint or competing interest. Keep the topic's premise true at all three levels. Use the concept's colors and leave enough room for natural line breaks. Hosts can read and edit individual cards before export.
- **Round 2 and games.** Use the concept's speaking activity, rules and play link. Sessions use one or two standalone HTML games, exactly two for Game Night. The four implemented games each have 20 Elementary (A2–B1) and 20 Advanced (B2–C1) cards. One host controls the screen while the group speaks. The game and its controls run offline.
- **Closing.** Finish with cooldown, thanks and the approved feedback form on the final slide. Use the shared link in the session sequence. [Rate Us form](https://docs.google.com/forms/d/e/1FAIpQLSdqYPKLaeRpFTol3S32Ud4tIv0GMSwvbm2rPPOeuJFREtPMig/viewform)
- **Invitation.** Generate English copy from the actual session. Replace the topic, copy, date, time and venue in an approved slide. Preserve the original shapes, fonts, artwork, logos, placement and aspect ratio. Shorten overflowing copy. The source library contains 48 slides. The five active styles use purple for Spontaneous Talk, blue for Business, yellow for Game Night, orange for Pop Culture and green for Culture Exchange. The current GIF is landscape, 1920 × 1362, with a readable final hold.

## Development roadmap

**Start with milestone 1.** Each milestone below has a test that a new developer can run or an outcome they can observe. Keep the last working session available while making changes.

1. **Round 1 question quality and layout (completed).** The app drafts situations before questions, enforces topic premise permanence, eliminates shallow questions, and rotates starters across cards. Verified on real Ollama (`qwen3:8b`) with continuous service on the all-night buses topic, a fresh Spontaneous topic ("What if people could trade one memory each year?") and a fresh Business topic ("Remote work for managers and junior staff"). Both decks render native editable text without clipping or overflow. [Spontaneous slide renderer](src/spontaneous_deck.py) · [Business slide renderer](src/business_deck.py)
2. **Make one full weekly session dependable (current milestone).** Exercise a new Spontaneous session through the normal app on Windows. Check warm-up simplicity, Toolkit translations, examples and level progression, separate grammar pages, host notes and the closing paragraph. Interrupt generation, reopen it, edit one card, rebuild, then run the extracted session offline. Count this milestone complete when the revision on screen matches the deck, host guide, games and invitation, and a failed new run preserves earlier work.
3. **Finish the other concept formats.** Run the same full-session check on Business and Game Night, including all cards in both Game Night games. Build Pop Culture and Culture Exchange from their own supplied examples, one concept at a time. Each must produce a native editable deck in its own order, working game controls on phone and laptop, and a matching invitation on a new topic.
4. **Verify invitation fidelity.** Compare each active style with its source slide using real event details and short and long topics. Check text bounds, time and venue, original layout and aspect ratio, GIF loop and final-frame readability. Activate more of the 48 source slides as their field mappings and renders pass these checks.
5. **Verify weekly readiness on Windows.** Run the launcher from a clean setup, generate a fresh session on the target laptop, measure time and check recovery with Ollama or LibreOffice unavailable. Open the editable deck in PowerPoint, use its local game links after extraction, check the Rate Us link and play the invitation. Call the app ready for weekly use when the host can complete that sequence independently.

### Concept selection and hosting

- **Concept selection.** Use the topic to choose the session format and its matching invitation style. A host's explicit choice takes priority. The calendar is a scheduling reference. Its Week 3 and Week 4 Saturday entries disagree with its written rotation, so the app leaves dates and calendar assignments to the host. [Original calendar](references/Talkline-Concept-Calendar-v3.png)
- **Game hosting is deferred.** Keep the HTML games playable from the extracted local ZIP. Revisit public URLs and Canva link checks when the host resumes work on publishing. The approved online Rate Us form remains on the final slide.

## Where the next developer should work

Read this roadmap and the repository instructions first. Check the matching sample before changing a concept. Historical handoff files describe earlier prototypes. Use the current owner decisions and the runnable app to settle differences. Original prompts and account instructions inside reference files describe the former manual process. [Repository instructions](AGENTS.md) · [Session development guide](.cursor/skills/talkline-session/SKILL.md) · [Product specification](docs/PRODUCT_SPEC.md) · [Engineering notes](docs/IMPLEMENTATION_ROADMAP.md) · [Original handoff](docs/CHAT_HANDOFF_FA.md)

- **Generation.** The app coordinates small, local Ollama requests for each section. Discussion generation is shared by Spontaneous and Business. Game Night owns its two game mechanics. Keep section work in these modules. [Studio](app.py) · [Discussion generation](src/spontaneous_content.py) · [Business format](src/business_content.py) · [Game Night](src/game_night_content.py) · [Toolkit](src/toolkit.py) · [Language sources](docs/LEARNING_SOURCES.md)
- **Assembly and recovery.** Python owns meeting order, link targets, validation and export. Preview and host guide use the same sequence. Change the section generator and renderer together when their data contract changes, and preserve existing saved drafts. [Meeting order](src/session_sequence.py) · [Game slots](src/session_plan.py) · [Export routing](src/session_export.py) · [Saved runs](src/run_store.py) · [Batch recovery](src/checkpoints.py)
- **Design sources.** Match presentation changes to the brand guide and the relevant editable sample. For invitations, use only the invitation library. [Brand guide PDF](references/TalkLine_Brand_Guide.pdf) · [Session deck inventory](references/user_examples/index.json) · [Spontaneous reference](references/Completed_Spontaneous_Talk_23_Slides_READABLE.pptx) · [Invitation library](templates/invitations/TalkLine_Approved_Invitations.pptx) · [Invitation rules](templates/invitations/policy.json)

Run the automated suite from PowerShell in the folder containing `app.py`. Run the launcher check with Studio closed so port 8501 is available.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\check_windows_startup.py
```

Tests use repeatable fixtures. For a generation or layout change, also exercise the relevant full concept in Studio with a fresh topic and the installed model, open the output and record what passed and what still needs review. Update the status and next action here when the work advances.

See the [last verification](HANDOFF.md#last-verification) for the latest Windows checks and outstanding issues.
