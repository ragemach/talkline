from io import BytesIO
from zipfile import ZipFile

from pptx import Presentation
import pytest

from src.game_night_deck import build_game_night_deck
from src.session_sequence import RATE_US_URL
from src.spontaneous_demo_toolkit import demo_spontaneous_toolkit
from src.template_blueprints import text_shapes
from src.toolkit import LEVEL_LABELS


TOPIC = 'Changing everyday rules'
GAMES = ('TalkLine_Taboo.html', 'TalkLine_Problem_Solver.html')


@pytest.fixture
def content():
    return {
        'subtitle': 'Describe a word, then solve a problem.',
        'tagline': 'Two teams, two games.',
        'warmup': ['How are you?', 'How was your day?', 'Do you like card games?'],
        'opening': 'Welcome to TalkLine. Share a short answer with the person next to you.',
        'closing': 'Think of a clue that helped your team or a solution you would try. What made it work?',
        'games': [{'mechanic': 'taboo', 'title': 'Taboo'},
                  {'mechanic': 'problem_solver', 'title': 'Problem Solver'}],
    }


def _read(deck):
    return Presentation(BytesIO(deck))


def _text(slide):
    return '\n'.join(shape.text for _, shape in text_shapes(slide.shapes))


def test_deck_uses_reference_order_and_separate_clickable_files(content):
    output = build_game_night_deck(TOPIC, content, demo_spontaneous_toolkit(TOPIC), GAMES)
    deck = _read(output)
    assert (deck.slide_width.inches, deck.slide_height.inches) == (7.5, 10.0)
    slides = list(deck.slides)
    upper = [_text(slide).upper() for slide in slides]
    assert TOPIC in _text(slides[0])
    assert content['opening'] in _text(slides[1])
    warmups = [_text(slides[1]).index(question) for question in content['warmup']]
    assert len(set(warmups)) == 3
    expected = ('ROUND 1\nTABOO', 'TABOO- GAME RULES', '20 MINUTES',
                'ROUND 2\nROUND 2 — HTML PROBLEM SOLVER GAME',
                'PROBLEM SOLVER- GAME RULES', content['closing'].upper(), 'RATE US HERE')
    assert all(text in page for page, text in zip(upper[-7:], expected, strict=True))
    assert all(slide.notes_slide.notes_text_frame.text for slide in slides)
    assert [{rel.target_ref for rel in slide.part.rels.values() if rel.is_external}
            for slide in slides if any(rel.is_external for rel in slide.part.rels.values())] == [
        {GAMES[0]}, {GAMES[1]}, {RATE_US_URL},
    ]
    with ZipFile(BytesIO(output)) as archive:
        assert archive.testzip() is None
        assert all(b'netlify' not in archive.read(name) for name in archive.namelist()
                   if name.endswith(('.xml', '.rels')))


def test_readable_toolkit_has_all_entries_and_separate_grammar(content):
    toolkit = demo_spontaneous_toolkit(TOPIC)
    slides = list(_read(build_game_night_deck(TOPIC, content, toolkit, GAMES)).slides)
    grammar = '\n'.join(_text(slide) for slide in slides if 'Game Night Toolkit / Mini Grammar' in _text(slide))
    for level, label in LEVEL_LABELS.items():
        pages = [slide for slide in slides if f'Game Night Toolkit / {label}' in _text(slide)]
        text = '\n'.join(_text(slide) for slide in pages)
        material = toolkit['levels'][level]
        for kind in ('vocabulary', 'phrases', 'idioms'):
            assert all(value in text for entry in material[kind] for value in entry.values())
        assert material['mini_grammar']['pattern'] in grammar
        assert material['mini_grammar']['pattern'] not in text
        assert all(example in grammar for example in material['mini_grammar']['examples'])
        for slide in pages:
            entries = [shape for shape in slide.shapes if shape.name == 'Toolkit entry']
            assert entries
            entry = entries[0]
            paragraphs = entry.text_frame.paragraphs
            assert [str(run.font.color.rgb) for paragraph in paragraphs for run in paragraph.runs] == [
                'FFFFFF', 'FFE39B', 'D9E6F5',
            ]
            assert min(run.font.size.pt for paragraph in paragraphs for run in paragraph.runs) >= 12.5


def test_rejects_external_and_repeated_game_paths(content):
    toolkit = demo_spontaneous_toolkit(TOPIC)
    for paths in (('https://site.example/game.html', GAMES[1]), (GAMES[0], GAMES[0].lower())):
        with pytest.raises(ValueError, match='same folder'):
            build_game_night_deck(TOPIC, content, toolkit, paths)


def test_long_toolkit_creates_continuation_without_clearing_background(content):
    toolkit = demo_spontaneous_toolkit(TOPIC)
    extended = toolkit['levels']['b2_c1']['vocabulary']
    for item in extended:
        item['example'] += ' The decision affected several people, so we discussed the options before making changes.'
        item['turkish'] += ', farklı bir durumda dikkate alınması gereken bir şey'
    slides = list(_read(build_game_night_deck(TOPIC, content, toolkit, GAMES)).slides)
    pages = [slide for slide in slides if 'Game Night Toolkit / B2/C1' in _text(slide)]
    assert len(pages) > 1
    all_text = '\n'.join(_text(slide) for slide in pages)
    assert all(item['example'] in all_text for item in extended)
    backgrounds = [
        {rel.target_ref for rel in slide.part.rels.values() if rel.reltype.endswith('/image')}
        for slide in pages
    ]
    assert backgrounds[0] and all(item == backgrounds[0] for item in backgrounds)
