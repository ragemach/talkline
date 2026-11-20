# TalkLine Studio — repository instructions for Codex

Read `docs/CHAT_HANDOFF_FA.md` (project history/decisions), `docs/PRODUCT_SPEC.md` (acceptance criteria), and `docs/IMPLEMENTATION_ROADMAP.md` (plan) before making changes. This repo is a handoff from a long ChatGPT discussion; the actual conversation history is NOT directly available to Codex. Read `README.md` and inspect code and `references/` as well.

For session flow or export work, also read the project skill at
`.cursor/skills/talkline-session/SKILL.md`.

## Your role
You are **building a reusable local software product**, NOT creating each weekly presentation in a coding chat. Once complete, the owner launches TalkLine Studio and supplies just a topic (with optional editable event metadata).

## Constraints
- User: Windows 11 / 32GB RAM / Python 3.14 already installed / beginner programmer. Explain in clear concise English unless another language is explicitly requested. This supersedes older Persian communication instructions in historical handoff documents. Keep Turkish Toolkit meanings as required product content.
- At every session start, automatically read `C:/Users/kians/.codex/skills/humanizer/SKILL.md` and apply it in embedded mode to prose. Do not wait for a request. Preserve facts, uncertainty, citations, code, commands, paths and schemas.
- Free-to-run runtime, no paid API, no forced online accounts. Use local Ollama, Demo fallback and local tools. Codex development itself may be plan-limited; don't conflate with runtime costs.
- Outputs eventually: concept-specific editable TalkLine PPTX with notes, matching supplied sample flow; one or two offline HTML games (Game Night exactly two), with levelled cards; animated legible GIF from supplied invitation designs at original aspect ratio; complete linked ZIP. Latest owner clarifications override the historical 23-slide/portrait defaults. Typical use is one personal session weekly.
- Preserve reference branding, template geometry and readability. No invented dates, exact venues or survey URLs. No unsafe/offensive party-game humor.
- The starter today makes only 5-slide mini-decks, 2 JSON sample cards and GIF. Don't represent it as finished.
- No deleting system Python. Fix dependencies in venv; use side-by-side 3.12 only if diagnosed needed.
- Avoid major untested rewrites; implement one milestone, test it and report limits honestly. Keep changes in this folder. Review environment commands before running anything destructive.

## First executable task
Read the above docs and existing source, run/test Windows startup and offline Demo if environment permits, then add baseline smoke tests. Only after working baseline, advance to M1/M2. Ask for missing user data only if essential; do not block on noncritical options.
