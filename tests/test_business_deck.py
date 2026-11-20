from io import BytesIO
from zipfile import ZipFile

from pptx import Presentation
import pytest

from src.business_deck import build_business_deck
from src.session_sequence import RATE_US_URL
from src.spontaneous_demo_toolkit import demo_spontaneous_toolkit
from src.template_blueprints import text_shapes
from src.toolkit import LEVEL_LABELS


TOPIC = 'Trust between coworkers'
GAME = 'TalkLine_Game.html'


@pytest.fixture
def content():
    return {
        'subtitle': 'What makes coworkers trust each other?',
        'tagline': 'Share your reasons.',
        'opening': 'Welcome to TalkLine. Talk to the person next to you, then share one idea with the group.',
        'closing': 'Think about a choice from the game. What would you do if a coworker made that choice?',
        'warmup': ['How are you?', 'How was your day?', 'Do you like working with a team?'],
        'round1': [
            {'title': f'A team decision {number}', 'a2': f'What helps your team in case {number}?',
             'b2': f'How would you ask a new teammate for honest feedback in case {number}?',
             'c1': f'How should a manager handle feedback in case {number} if teams disagree?'}
            for number in range(1, 11)
        ],
        'game': {'mechanic': 'smart_or_sneaky', 'title': 'Smart or Sneaky?'},
    }


def _text(slide):
    return '\n'.join(shape.text for _, shape in text_shapes(slide.shapes))


def test_reference_preserves_discussion_order_and_actual_game_links(content):
    output = build_business_deck(TOPIC, content, demo_spontaneous_toolkit(TOPIC), GAME)
    deck = Presentation(BytesIO(output))
    assert (deck.slide_width.inches, deck.slide_height.inches) == (7.5, 10.0)
    slides = list(deck.slides)
    pages = [_text(slide) for slide in slides]
    assert len(slides) == 22
    assert TOPIC in pages[0] and content['subtitle'] in pages[0]
    assert content['opening'] in pages[1]
    questions = [pages[1].index(question) for question in content['warmup']]
    assert len(set(questions)) == 3
    assert 'DISCUSSION CARDS' in pages[6]
    for index, (page, card) in enumerate(zip(pages[7:17], content['round1'], strict=True), 1):
        assert f'Q{index}' in page.splitlines()
        assert all(value in page for value in card.values())
    assert '20 minutes' in pages[17]
    assert 'SMART OR SNEAKY?' in pages[18]
    assert 'Sneaky trick' in pages[19]
    assert content['closing'] in pages[20]
    assert 'RATE US HERE' in pages[21]
    assert all(slide.notes_slide.notes_text_frame.text for slide in slides)
    assert [{rel.target_ref for rel in slide.part.rels.values() if rel.is_external}
            for slide in slides if any(rel.is_external for rel in slide.part.rels.values())] == [
        {GAME}, {RATE_US_URL},
    ]
    assert 'BEYOND THE OFFICE' not in '\n'.join(pages).upper()
    with ZipFile(BytesIO(output)) as archive:
        assert archive.testzip() is None
        assert all(b'netlify' not in archive.read(name) for name in archive.namelist()
                   if name.endswith(('.xml', '.rels')))


def test_toolkit_uses_separate_levels_and_grammar(content):
    toolkit = demo_spontaneous_toolkit(TOPIC)
    slides = Presentation(BytesIO(build_business_deck(TOPIC, content, toolkit, GAME))).slides
    grammar = '\n'.join(_text(slide) for slide in slides if 'MINI GRAMMAR' in _text(slide))
    for level, label in LEVEL_LABELS.items():
        pages = [_text(slide) for slide in slides if f'Toolkit / {label}' in _text(slide)]
        combined = '\n'.join(pages)
        material = toolkit['levels'][level]
        for kind in ('vocabulary', 'phrases', 'idioms'):
            assert all(value in combined for entry in material[kind] for value in entry.values())
        assert material['mini_grammar']['pattern'] not in combined
        assert material['mini_grammar']['pattern'] in grammar
        assert all(example in grammar for example in material['mini_grammar']['examples'])


def test_refuses_wrong_game_or_external_location(content):
    toolkit = demo_spontaneous_toolkit(TOPIC)
    with pytest.raises(ValueError, match='same folder'):
        build_business_deck(TOPIC, content, toolkit, 'https://example.com/game.html')
    content['game']['mechanic'] = 'patch_notes'
    with pytest.raises(ValueError, match='Smart or Sneaky'):
        build_business_deck(TOPIC, content, toolkit, GAME)


def test_long_framing_fits_with_native_readable_type(content):
    topic = ('Building trust with coworkers during a demanding project '
             'while supporting the teams affected by the decision')
    content['subtitle'] = 'Describe the difficult conversations that happen when managers do not agree'
    content['opening'] = (
        'Welcome to TalkLine. Start by sharing one small thing that helps you feel comfortable with a new team. '
        'Think about what changed when you joined your last group. '
        'During both rounds, look for one expression from the Toolkit that you could use at work.'
    )
    deck = Presentation(BytesIO(build_business_deck(topic, content, demo_spontaneous_toolkit(topic), GAME)))
    cover = list(deck.slides[0].shapes)
    title = next(shape for shape in cover if shape.name == 'Session topic')
    subtitle = next(shape for shape in cover if shape.name == 'Session subtitle')
    assert title.text == topic
    assert subtitle.text == content['subtitle']
    assert title.top + title.height < subtitle.top
    assert subtitle.top + subtitle.height < deck.slide_height
    assert content['opening'] in _text(deck.slides[1])
