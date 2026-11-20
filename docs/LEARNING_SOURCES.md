# Toolkit reference sources

## Offline integration added

Open Language Profiles provides downloadable CEFR-J vocabulary (7,799 rows),
grammar (500 rows) and Octanove C1/C2 vocabulary (2,136 rows). These are row counts,
not unique word counts. Copies, original terms and SHA-256 source manifests are
stored in references/open_language_profiles. CEFR-J permits commercial reuse
with attribution; Octanove is CC BY-SA 4.0.
Source: https://github.com/openlanguageprofiles/olp-en-cefrj

Toolkit generation now automatically looks up each vocabulary headword offline
and stores source-level evidence. The UI flags absent or mismatched levels.
This does not check word sense, translations or topical usefulness. Grammar data
is downloaded but not integrated: the publisher notes partial English translation.
Existing Oxford/Cambridge/British Council links remain editorial references.

Other candidates researched: Wiktionary for meanings (CC BY-SA obligations) and
Tatoeba for attributed sentence examples. Neither is imported or used at runtime;
both need quality filtering and neither alone supplies reliable CEFR labels.

Researched 2026-11-17. The app exposes these links in its reference panel.
These are editorial sources, not an imported or validated local dataset.

## Vocabulary

[Oxford 3000/5000](https://www.oxfordlearnersdictionaries.com/wordlists/oxford3000-5000)
is the primary selection reference. Oxford 3000 covers core A1–B2 words; the
additional Oxford 5000 entries extend vocabulary through B2–C1. Select by level,
part of speech and topic. Check the intended meaning rather than spelling alone.
[Publisher explanation](https://www.oxfordlearnersdictionaries.com/about/wordlists/oxford3000-5000)

[Cambridge English–Turkish](https://dictionary.cambridge.org/dictionary/english-turkish/)
is the bilingual reference. Its stated coverage includes English Vocabulary Profile
A1–B2 words; it is not a complete C1 Turkish wordlist. Check advanced meanings
individually and write contextual Turkish meanings and examples.

## Grammar

Use the British Council sections for the required range:

- [A1–A2](https://learnenglish.britishcouncil.org/free-resources/grammar/a1-a2)
- [B1–B2](https://learnenglish.britishcouncil.org/free-resources/grammar/b1-b2)
- [C1](https://learnenglish.britishcouncil.org/free-resources/grammar/c1)

These provide a lesson map. Store original short explanations, patterns and
topic-specific examples. Retain the published band separately from our teaching
level; a combined band does not establish an exact individual CEFR level.

## Using references in the application

Free website access is not permission to redistribute a dictionary database or
lesson collection. British Council's general reuse permission is personal and
non-commercial. English Profile says its vocabulary and grammar data are not
licensed for commercial purposes; do not bundle those databases for paid events.
[British Council terms](https://www.britishcouncil.org/terms),
[English Profile licensing](https://englishprofile.org/?menu=contact-us)

Use these sources for editorial checking. Write original teaching material and
keep source links; verify rights before importing any third-party dataset.
No bulk scraping is implemented or required for normal offline operation.

Next implementation: each entry stores expression, part of speech, intended
meaning, topic tags, source URL, source band, suggested teaching level, Turkish
meaning, original example and review status. Keep B2/C1 metadata distinct even
when displayed as one advanced group. Choose eight topic-relevant words per
level (seven to ten permitted), plus separate phrases, idioms and grammar.
Generate examples from those meanings; flag missing library coverage explicitly.

The Office Boundaries seed is still editorial draft material. The source panel
does not retroactively verify it. Automated source-backed selection and full
presentation insertion remain pending.
