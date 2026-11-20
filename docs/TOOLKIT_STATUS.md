# Toolkit verification, 2026-11-17

Real local export check, 2026-11-19: `scripts/smoke_toolkit.py --export`
completed example generation, advisory review, JSON, HTML and a seven-slide PPTX.
The review returned eight findings, including duplicate/contradictory advice and
references to translations absent from the seed. No corrections were applied
automatically. Review completion is not content approval.

## Update, 2026-11-19

The current grouped export has separate A1/A2, B1 and B2/C1 pages and dedicated
grammar pages. The editorial sample exports to seven slides with all words,
meanings and examples retained. Text colour priority remains expression, Turkish
meaning, English example. PPTX validation passed for TalkLine_Toolkit_Grouped.pptx.

137 offline tests passed, including an app-level PowerPoint export with network
access blocked and a check that changing topics hides stale export controls.
The grouping regression test now inspects nested template groups correctly.
The old four-slide mixed-group export is superseded by the grouped file.

Use `scripts/smoke_toolkit.py --export` to exercise real local Ollama generation,
review, HTML and PPTX export. This does not certify language quality or rendering
fit for arbitrary topics. The exporter still uses the Business English template.

117 offline tests passed after adding separate local semantic review. The app
shows findings and explicitly reports failed reviews while preserving content.

A real qwen3:8b run for Office Boundaries completed generation and review and
saved output/toolkit-reviewed.json. It is a diagnostic artifact, not approved
teaching material. It still contains inaccurate translations, weak level
progression and unnatural usage examples. The same-model review also produced
incorrect advice, including rejecting a genuine idiom. Do not automatically
apply its corrections or describe a completed review as quality approval.

The temporary smoke command failed only while printing Turkish characters to a
Windows cp1252 console, after saving the UTF-8 file. The reusable
scripts/smoke_toolkit.py writes UTF-8 and prints ASCII status only.

Next quality work: improve generation/review prompts and model settings against
reviewed multilingual examples, compare multiple fresh topics, and support human
editing before slide insertion. Template insertion remains unimplemented.
