---
name: talkline-session
description: Maintains TalkLine Studio's meeting sequence, levelled Toolkit, host guide, and local export workflow. Use when changing session order, wrap-up activities, game placement, or the ZIP.
---

# TalkLine session development

Work in the nested `TalkLine_Studio_CODEX_HANDOFF/` application folder. Read
`docs/PRODUCT_SPEC.md` and `docs/IMPLEMENTATION_ROADMAP.md` before changing
the workflow. Compare against the corresponding approved sample when its
concept has a different meeting order.

1. Give the Toolkit eight vocabulary items per group by default, with Turkish
   meanings and English examples. Follow them with short phrases and applicable
   idioms, such as “walk on eggshells” when the topic calls for it. Give idioms
   their figurative Turkish meaning and a natural English example. Keep the
   A1/A2, B1 and B2/C1 pages distinct and mini grammar separate.
   Fill panels to the content and keep text readable when adding pages.
2. Use a predictable meeting sequence from the welcome to the closing.
   The discussion format uses warm-up, Toolkit, mini grammar, Round 1
   discussion, break and Round 2 game. The Game Night target places Taboo
   before the break and Problem Solver after it, as shown in the supplied deck.
3. End with cooldown, thanks and the approved Rate Us form. Use the saved form
   when the owner supplies one. Link only assets actually in the export, and
   tell the host when an external link needs internet.
4. Keep the meeting order in application code and let the local model supply
   the creative content. The app and exported kit should work independently
   of Codex skills. Use the same sequence for the preview and the host guide.
5. Run the matching app and export tests. Check fresh and stale topic cases,
   audit ZIP links after extraction and render changed PowerPoint layouts.
   Use the installed PPTX skill for file checks and the local browser for
   HTML interactions.
