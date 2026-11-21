# TalkLine Studio — repository instructions for Codex

Read the [current handoff](HANDOFF.md) and [README roadmap](README.md#development-roadmap) at the start of each session. The handoff gives the next task and the latest verification. Read `docs/PRODUCT_SPEC.md` for acceptance criteria, `docs/IMPLEMENTATION_ROADMAP.md` for engineering detail and `docs/CHAT_HANDOFF_FA.md` for project history. Inspect the relevant code and supplied references before changing a workflow.

For session flow or export work, also read the project skill at
`.cursor/skills/talkline-session/SKILL.md`.

## Your role
You are **building a reusable local software product**, NOT creating each weekly presentation in a coding chat. Once complete, the owner launches TalkLine Studio and supplies just a topic (with optional editable event metadata).

## Constraints
- User: Windows 11 / 32GB RAM / Python 3.14 already installed / beginner programmer. Explain in clear concise English unless another language is explicitly requested. This supersedes older Persian communication instructions in historical handoff documents. Keep Turkish Toolkit meanings as required product content.
- At every session start, automatically read `C:/Users/kians/.codex/skills/humanizer/SKILL.md` and apply it in embedded mode to prose. If that local file is unavailable, mention it briefly and continue in plain English. Preserve facts, uncertainty, citations, code, commands, paths and schemas.
- Generate new sessions with installed local Ollama and free local tools. Fixed examples support tests and reopening older work. Weekly generation must work independently of Codex.
- Select the concept automatically from the topic before generating a session. Honor a manual choice and use the resolved concept throughout generation and invitation export. The calendar is a reference for the host.
- The host receives two main files, an editable concept-specific PowerPoint with notes and an animated invitation GIF at the original template ratio. Each session also generates one or two HTML games (exactly two for Game Night). Keep their relative links working in the extracted ZIP. Public game hosting is deferred. Typical use is one session weekly.
- Preserve reference branding, template geometry and readability. No invented dates, exact venues or survey URLs. No unsafe/offensive party-game humor.
- Check the per-concept status in the README. The two short-session concepts still use the five-slide prototype.
- No deleting system Python. Fix dependencies in venv; use side-by-side 3.12 only if diagnosed needed.
- Avoid major untested rewrites; implement one milestone, test it and report limits honestly. Keep changes in this folder. Review environment commands before running anything destructive.

## Continuing development

Follow the first open milestone in the README unless the owner sets a different priority. Use the existing test suite and run the affected workflow. Before handing off, update `HANDOFF.md` with changes, reasons for decisions, test results, remaining issues and the next action. Update the README when a milestone or product decision changes. Treat the starter demo and earlier milestone reports as historical evidence.
