"""Standalone readable Toolkit export, with escaped content and no network assets."""
from html import escape
from src.toolkit import LEVEL_LABELS


def toolkit_html(toolkit):
    e = lambda value: escape(str(value), quote=True)
    sections = []
    for level, data in toolkit['levels'].items():
        parts = [f'<section><h2>{e(LEVEL_LABELS[level])} / Vocabulary, phrases and idioms</h2>']
        for kind in ('vocabulary', 'phrases', 'idioms'):
            if data[kind]:
                parts.append(f'<h3>{e(kind.title())}</h3>')
            for item in data[kind]:
                parts.append(f'<article><h4>{e(item["expression"])}</h4><p lang="tr">{e(item["turkish"])}</p><p>{e(item["example"])}</p></article>')
        grammar = data['mini_grammar']
        parts.append(f'</section><section><h2>{e(LEVEL_LABELS[level])} / Grammar</h2>')
        parts.append(f'<h3>Mini grammar: {e(grammar["title"])}</h3><p>{e(grammar["explanation"])}</p><p><strong>{e(grammar["pattern"])}</strong></p>')
        parts.extend(f'<p>{e(example)}</p>' for example in grammar['examples'])
        parts.append('</section>')
        sections.append(''.join(parts))
    return f'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TalkLine Toolkit: {e(toolkit['topic'])}</title>
<style>body{{font:18px/1.6 Arial,sans-serif;color:#202331;background:#f4f5f7;margin:0;padding:24px}}main{{max-width:900px;margin:auto}}section{{background:white;padding:28px;margin:24px 0;border-radius:12px}}h1,h2,h3,h4{{line-height:1.3}}h4{{margin-bottom:0}}article{{border-left:4px solid #344d88;padding-left:18px;margin:24px 0}}article p{{margin:6px 0}}@media print{{body{{background:white;padding:0}}section{{break-before:page}}}}</style>
<main><h1>TalkLine Toolkit</h1><p>{e(toolkit['topic'])}</p>
<p>Review status: {e(toolkit['review_status'])}. Suggested teaching levels; review before use.</p>
{''.join(sections)}</main></html>'''
