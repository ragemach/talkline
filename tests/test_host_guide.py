from html.parser import HTMLParser

import pytest

from src.host_guide import build_host_guide


class DocumentLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        if tag == 'a':
            self.links.append(dict(attrs)['href'])


def test_guide_keeps_stage_order_and_links_to_sibling_files():
    guide = build_host_guide('Travel & work', [
        {'title': 'Welcome', 'instructions': 'Say hello.'},
        {'title': 'Speaking game', 'instructions': 'Choose a card.',
         'prompts': ['Do you agree? <script>'],
         'files': [('Open game', 'TalkLine_Game.html')]},
    ])
    document = DocumentLinks()
    document.feed(guide)
    assert document.links == ['TalkLine_Game.html']
    assert 'script' not in document.tags
    assert 'Travel &amp; work' in guide
    assert 'Do you agree? &lt;script&gt;' in guide
    assert guide.index('Welcome') < guide.index('Speaking game')


@pytest.mark.parametrize('filename', [
    '../Game.html', '/Game.html', 'nested/Game.html', 'C:\\Game.html',
    'https://example.test/Game.html', 'javascript:alert(1)', 'Game.html#fragment',
])
def test_guide_refuses_links_outside_the_kit(filename):
    with pytest.raises(ValueError, match='simple kit filename'):
        build_host_guide('Travel', [
            {'title': 'Speaking game', 'instructions': 'Choose a card.',
             'files': [('Open game', filename)]},
        ])


def test_feedback_form_uses_an_explicit_opt_in_link():
    url = 'https://docs.google.com/forms/example?foo=1&bar=2'
    guide = build_host_guide('Travel', [
        {'title': 'Rate Us', 'instructions': 'Share feedback.', 'feedback_url': url},
    ])
    document = DocumentLinks()
    document.feed(guide)
    assert document.links == [url]
    assert 'Open Rate Us form (internet required)' in guide


@pytest.mark.parametrize('url', ['http://forms.gle/example', 'javascript:alert(1)',
                                 'https:///example', 'https://login@forms.gle/example'])
def test_feedback_rejects_invalid_urls(url):
    with pytest.raises(ValueError, match='HTTPS URL'):
        build_host_guide('Travel', [
            {'title': 'Rate Us', 'instructions': 'Share feedback.', 'feedback_url': url},
        ])
