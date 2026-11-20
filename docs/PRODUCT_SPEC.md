# TalkLine Studio — Product specification (for Codex)

## Owner clarifications after the handoff (2026-11-17)

Invitations are English only. Use the supplied 48-slide invitation library as the
design source, replacing text/date/time/venue and selecting among existing colors.
Preserve original composition and aspect ratio; this overrides the earlier portrait
GIF specification for those samples. Animation is allowed while preserving design.
Each session needs one or two standalone HTML games; Game Night needs two.
The owner explicitly selected Vercel Free for HTML-game hosting and rejected
Netlify. Target a static Vercel-compatible game archive. No paid upgrade or Pro
trial is authorized. Hosting limits and terms still apply; technical deployment
success does not establish eligibility for commercial use. The owner confirmed
paid/business-related events. No Vercel account or deployment has been verified.
Game links go in Canva/the presentation.
The final Rate Us hyperlink must use the real Google Form from the supplied brand
guide: https://docs.google.com/forms/d/e/1FAIpQLSdqYPKLaeRpFTol3S32Ud4tIv0GMSwvbm2rPPOeuJFREtPMig/viewform
These are requirements, not claims that the full game/publishing pipeline exists.

The owner uses this for one personal session approximately weekly. Slide count
and sequence vary by concept and supplied sample; 23 is not a universal limit.
See `ARCHITECTURE_DECISION_FA.md` and the revised roadmap for the development plan.

Toolkit depth clarification: each level requires seven to ten vocabulary entries,
excluding phrases, idioms and grammar. Default to eight vocabulary items plus
three phrases per level, each with Turkish meaning and English usage example.
Spread this content across approved Toolkit page layouts; do not shrink text to
fit all entries onto one slide. The current readable HTML sample has this depth;
full slide integration remains pending.

Grouping clarification (2026-11-18): the exact teaching groups are A1/A2, B1,
and B2/C1. Do not mix these groups on an exported page. Grammar uses separate
pages from vocabulary, phrases and idioms. Minimize pages only within those
boundaries. The existing internal `a2` key is retained for saved-file compatibility
and now represents the combined A1/A2 teaching group.

## Outcome
Develop a **local Windows 11 application**. Codex is the **developer**, not the runtime content-generation backend. The owner launches TalkLine Studio, enters one topic, reviews optional saved date/time/venue preferences, clicks Generate and receives a complete self-contained event kit. **No usage-based paid AI API** required by the shipped application.

## Hardware / compatibility
Windows 11, 32 GB RAM, Python 3.14; observed NVIDIA RTX 3050 with 6 GB VRAM. Use installed Ollama `qwen3:8b` locally, measure full-session performance and optionally support other local models. Keep a transparent Demo fallback and virtual environments. Do not uninstall system Python. Initial dependencies/model need internet; routine generation runs locally.

## Deliverables per event
1. **Editable PowerPoint**: concept-specific slide count and sequence from the approved sample. Very simple warm-ups, levelled Toolkit with Turkish meanings and English usage examples, mini grammar explanations/patterns/examples, discussion or games appropriate to that concept, break/cooldown/evaluation and speaker notes. Preserve native editable shapes, typography and design. Use approved extra pages instead of shrinking fonts. Discussion sessions normally include ten tiered situations; Game Night follows its two-game sample.
2. **One or two offline interactive HTML games**, exactly two for Game Night. Twenty Elementary (A2–B1) and twenty Advanced (B2–C1) original cards per game where compatible with the selected mechanic. One host controls the screen. Support mechanic-specific data and interactions, not a universal A/B format. Inline CSS/JS; responsive at 375 px and laptop; no runtime network dependency. Test all cards, state, levels, replay and duplicates.
3. **Animated invitation GIF**: use only supplied invitation PPTX designs; English text, original geometry, fonts, artwork and aspect ratio. Current sample export is landscape 1920×1362. Looping, readable animation and long final hold; MP4 optional, GIF required. Select existing concept colors. Metadata is user-entered/saved; never invent dates or permanent addresses. User confirmed default time 20:00; Holstory Cafe, Beşiktaş is an authorized example venue.
4. **Complete ZIP** containing presentation, game, GIF, JSON/metadata and optionally preview assets. Relative links must work after extraction; include a fallback open-the-HTML instruction.

## Quality gates
- Content: no empty placeholder, duplicate scenario, unsound causal consequences, mismatched CEFR, invented dates, or expressions falsely called official Toolkit.
- Slides: render/check all slides visually, speaker notes present, text in bounds, font readable/contrast acceptable; preserve reference visual structure and allow actual PowerPoint editing. Test links.
- Game: deterministic schema/count tests + browser UI tests for both levels all cards, Patch A/B, Keep/Reset, Back, Restart, level switch, replay, mobile sizes.
- GIF: verify file type, dimensions matching source aspect ratio, frame count, timing, loop, legibility/contrast and file size; never claim GIF is lossless.
- Offline: no CDN/network dependency in delivered game and exported kit; no paid API keys.
- Reliability: local model can produce malformed/uninspired text. Validate, retry bounded times, show warnings and allow regeneration/editing of a single section.

## Reusability
- TalkLine varies across sessions: Spontaneous Talk, Business English and themed speaking games. Avoid hardwiring a single Reality Has a Glitch topic or Patch Notes flow.
- Templates/layouts are controlled assets, not rewritten from model output. Generation should emit structured content, **not arbitrary PowerPoint layout instructions**.
- The owner wants one-click generation after installation, not a per-session Codex conversation.

## Start by verifying prototype
Read the actual existing code. Do not claim full presentations or playable games already exist. Preserve the verified baseline; develop the next roadmap milestone with appropriate tests. Separate verified outcomes from plans.
