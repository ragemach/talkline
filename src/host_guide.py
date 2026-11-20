"""Render a printable, offline run sheet for the meeting host."""
from html import escape
import re
from urllib.parse import urlsplit


HOST_GUIDE_FILENAME = 'TalkLine_Host_Guide.html'
_KIT_FILENAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]*\.[A-Za-z0-9]+')


def _feedback_link(url: str) -> str:
    if not isinstance(url, str) or any(char.isspace() or char == '\\' for char in url):
        raise ValueError('Use an HTTPS URL for the Rate Us form.')
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username is not None:
        raise ValueError('Use an HTTPS URL for the Rate Us form.')
    return f'<p class="files"><a href="{escape(url, quote=True)}">Open Rate Us form (internet required)</a></p>'


def build_host_guide(topic: str, stages: list[dict]) -> str:
    """Render ordered stages with optional prompts, kit files and feedback link."""
    rendered_stages = []
    for stage in stages:
        parts = [
            '<li>',
            f'<h2>{escape(stage["title"])}</h2>',
            f'<p>{escape(stage["instructions"])}</p>',
        ]
        prompts = stage.get('prompts', [])
        if prompts:
            parts.append('<ul>')
            parts.extend(f'<li>{escape(prompt)}</li>' for prompt in prompts)
            parts.append('</ul>')
        files = stage.get('files', [])
        if files:
            parts.append('<ul class="files" aria-label="Files for this stage">')
            for label, filename in files:
                if not _KIT_FILENAME.fullmatch(filename):
                    raise ValueError(f'Host guide links must use a simple kit filename: {filename!r}')
                parts.append(f'<li><a href="{filename}">{escape(label)}</a></li>')
            parts.append('</ul>')
        if stage.get('feedback_url'):
            parts.append(_feedback_link(stage['feedback_url']))
        parts.append('</li>')
        rendered_stages.append('\n'.join(parts))
    instructions = ''
    if any(stage.get('files') for stage in stages):
        instructions = '<p>Extract the ZIP and keep the files together to use the links in this guide.</p>'
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>{escape(topic)} | TalkLine host guide</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: #f3f6fb; color: #17233b; font: 1.0625rem/1.55 system-ui, sans-serif; overflow-wrap: anywhere; }}
main {{ max-width: 54rem; margin: auto; padding: clamp(1.1rem, 4vw, 2.5rem); }}
header {{ border-bottom: 3px solid #284f91; padding-bottom: .75rem; margin-bottom: 1.5rem; }}
h1 {{ font-size: clamp(1.8rem, 6vw, 2.6rem); line-height: 1.15; margin: .25rem 0 .5rem; }}
h2 {{ font-size: 1.3rem; line-height: 1.25; margin: 0 0 .35rem; }}
p {{ margin: .35rem 0; }}
ol {{ margin: 0; padding-left: 1.65rem; }}
ol > li {{ padding: 0 0 1rem .45rem; margin-bottom: 1rem; border-bottom: 1px solid #aab8cf; }}
ol > li::marker {{ color: #284f91; font-weight: bold; }}
ul {{ margin: .55rem 0 0; padding-left: 1.25rem; }}
.files {{ list-style: none; padding-left: 0; }}
.files li + li {{ margin-top: .25rem; }}
a {{ color: #15477d; text-decoration: underline; text-underline-offset: .15em; }}
a:focus-visible {{ outline: 2px solid #15477d; outline-offset: 3px; }}
@media print {{
  @page {{ margin: 16mm; }}
  body {{ background: #fff; color: #000; font-size: 11pt; }}
  main {{ padding: 0; max-width: none; }}
  h2 {{ break-after: avoid; }}
  ol > li {{ break-inside: avoid; }}
  a {{ color: #000; }}
  .files a::after {{ content: " (" attr(href) ")"; font-weight: normal; }}
}}
</style>
</head>
<body>
<main>
<header>
<p>TalkLine Studio · Host guide</p>
<h1>{escape(topic)}</h1>
{instructions}
</header>
<ol aria-label="Meeting order">
{''.join(rendered_stages)}
</ol>
</main>
</body>
</html>'''
