"""Fill the approved Business English PowerPoint with an editable session."""
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import re

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from src.game_night_deck import (
    CARD_GAP, COLUMNS, FULL_COLUMN, GRAMMAR_GAP, GRAMMAR_TOP, PAGE_BOTTOM, TOOLKIT_TOP,
    _button, _card, _card_height, _layout_toolkit, _maximum_cards, _only, _round_panel,
    _template,
)
from src.session_sequence import RATE_US_URL
from src.spontaneous_deck import _arrange_slides, _fit_top_level, _notes, _remove, _shape, _write
from src.template_blueprints import verify_blueprint_source
from src.toolkit import LEVEL_LABELS, validate_level


REFERENCE = (
    Path(__file__).resolve().parents[1] / 'references' / 'user_examples'
    / 'Talkline Business Beyond the Office.pptx'
)
BLUEPRINT = {
    'source_file': REFERENCE.name,
    'source_sha256': 'a62da9f9ca71de93cf32267a507990957981505ba3ab6dc763a8796371196510',
}
NAVY = '1E2744'
WHITE = 'FFFFFF'
RULES = (
    ('Choose your level', 'Play Elementary (A2–B1) or Advanced (B2–C1).'),
    ('Read the workplace situation', 'Ask someone to read it aloud.'),
    ('Discuss both sides', 'Give a reason for calling it smart or sneaky.'),
    ('Reveal the twist', 'Choose Smart move or Sneaky trick to see what happens.'),
    ('Reflect and continue', 'Did the twist change your mind? Explain, then move on.'),
)


def _add_text(slide, name, value, x, y, width, bottom, size, *,
              bold=False, color=NAVY, alignment=PP_ALIGN.LEFT, lead=None):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(width), Pt(2))
    box.name = name
    frame = box.text_frame
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    paragraph = frame.paragraphs[0]
    paragraph.alignment = alignment
    run = paragraph.add_run()
    run.text = ' '.join(value.split())
    run.font.bold = bold
    run.font.name = 'Arial'
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)
    _fit_top_level(box, Inches(bottom), size=size, lead=lead or size + 2)
    return box


def _clone_business_page(presentation, source):
    """Copy the blue slide design and its artwork, then write new host notes."""
    slide = presentation.slides.add_slide(source.slide_layout)
    element = deepcopy(source._element)
    relationships = {}
    for rel in source.part.rels.values():
        kind = rel.reltype.rsplit('/', 1)[-1]
        if kind == 'image' and not rel.is_external:
            relationships[rel.rId] = slide.part.relate_to(rel.target_part, rel.reltype)
        elif kind not in {'slideLayout', 'notesSlide'}:
            raise ValueError('Business Toolkit contains an unmapped relationship.')
    for node in element.iter():
        for attr in ('r:embed', 'r:link', 'r:id'):
            name = qn(attr)
            old_id = node.get(name)
            if old_id in relationships:
                node.set(name, relationships[old_id])
    slide._element = slide.part._element = element
    slide.__dict__.pop('shapes', None)
    return slide


def _level_pages(presentation, source, label, level):
    items = [(kind, item) for kind in ('vocabulary', 'phrases', 'idioms') for item in level[kind]]
    layout = _layout_toolkit(items)
    pages = [source, *[_clone_business_page(presentation, source) for _ in layout[1:]]]
    for number, (slide, columns) in enumerate(zip(pages, layout, strict=True), 1):
        _only(slide, 2, 4, 7, 10, 13)
        _write(slide, (10, 12), f'Toolkit / {label}')
        _write(slide, (13, 15), 'Vocabulary, phrases and idioms for both rounds.')
        _write(slide, (7, 9), f'Toolkit / {label} / {number} of {len(layout)}')
        bounds = (FULL_COLUMN,) if len(columns) == 1 else COLUMNS
        for (x, width), entries in zip(bounds, columns, strict=True):
            card_width = width - .26
            height = .28 + sum(_card_height(item, card_width) + CARD_GAP for item in entries)
            _round_panel(slide, x, TOOLKIT_TOP, width, height, NAVY)
            y = TOOLKIT_TOP + .14
            for item in entries:
                y += _card(slide, x + .13, y, card_width, item) + CARD_GAP
        _notes(slide, f'{label} Toolkit. Ask learners to use one expression in both rounds.')
    return pages


def _grammar_pages(presentation, source, toolkit):
    rows = [('grammar', (label, toolkit['levels'][level]['mini_grammar']))
            for level, label in LEVEL_LABELS.items()]
    layout = []
    while rows:
        count = _maximum_cards(rows, FULL_COLUMN[1], PAGE_BOTTOM - GRAMMAR_TOP, GRAMMAR_GAP)
        if not count:
            raise ValueError('A mini grammar is too long for a Business English page.')
        layout.append(rows[:count])
        rows = rows[count:]
    pages = [source, *[_clone_business_page(presentation, source) for _ in layout[1:]]]
    for slide, entries in zip(pages, layout, strict=True):
        _only(slide, 2, 4, 22)
        y = GRAMMAR_TOP
        x, width = FULL_COLUMN
        for item in entries:
            y += _card(slide, x, y, width, item) + GRAMMAR_GAP
        _notes(slide, 'Model the grammar pattern and ask each group for a workplace example of its own.')
    return pages


def _build_cover(slide, topic, content):
    _remove(slide, 10, 16)  # The source photo placeholder sits behind the real photo.
    title = _add_text(slide, 'Session topic', topic, .35, 8.03, 6.8, 9.18, 23,
                      bold=True, alignment=PP_ALIGN.CENTER, lead=24)
    subtitle_y = max(8.77, title.top.inches + title.height.inches + .08)
    subtitle = _add_text(slide, 'Session subtitle', content['subtitle'], .35, subtitle_y, 6.8,
                         9.64, 14, alignment=PP_ALIGN.CENTER)
    footer = _shape(slide, (19,))
    footer.top = max(footer.top, subtitle.top + subtitle.height + Pt(4))
    _notes(slide, f'Welcome to TalkLine Business English. Tonight’s topic is {topic}. {content["tagline"]}')


def _intro_text(slide, value, bottom, shape_ids):
    _remove(slide, 18)
    box = _add_text(slide, 'Host introduction', value, .5, 3.38, 6.5, bottom, 12.5, lead=14)
    shift = max(0, box.top + box.height + Pt(7) - _shape(slide, (21,)).top)
    for shape_id in shape_ids:
        _shape(slide, (shape_id,)).top += shift


def _build_warmup(slide, content):
    _write(slide, (7, 9), 'Warm-up / Business English')
    _intro_text(slide, content['opening'], 4.28, (21, 23, 26, 28, 31, 33, 36, 37, 38))
    for shape_id, question in zip((38, 36, 37), content['warmup'], strict=True):
        shape = _shape(slide, (shape_id,))
        _template(slide, (shape_id,), question, shape.top.inches + .74, lead=18)
    _notes(slide, f'{content["opening"]}\nGive everyone a turn. Invite short answers and a friendly follow-up.')


def _build_discussion(slide, card):
    _add_text(slide, 'Discussion card title', card['title'], 2.08, .96, 4.9, 1.88, 24, bold=True)
    for (tier, shape_id, background) in (('a2', 15, 10), ('b2', 21, 16), ('c1', 27, 22)):
        panel = _shape(slide, (background,))
        _template(slide, (shape_id,), card[tier], panel.top.inches + panel.height.inches - .04, lead=18)
    _notes(slide, f'{card["title"]}\nLet participants choose A2, B2 or C1. Ask them for a reason or a specific example.')


def _build_game(intro, rules, filename):
    _write(intro, (7, 9), 'Round 2 / Smart or Sneaky?')
    _write(intro, (15, 17), 'SMART OR SNEAKY?')
    _write(intro, (18,), 'Read the workplace situation.\nDiscuss both judgments.\nReveal the twist.')
    _notes(intro, 'Host-led game. Hear a reason from each side and then reveal the plot twist.')
    _write(rules, (10, 12), 'Smart or Sneaky? / Rules')
    _write(rules, (13, 15), 'Support your judgment with a reason.')
    for index, (heading, body) in enumerate(RULES):
        _write(rules, (23 + 10 * index, 25 + 10 * index), f'{heading}\n{body}')
    _button(rules, (66, 68), (66, 67), filename)
    _notes(rules, '\n'.join(f'{heading}. {body}' for heading, body in RULES)
           + f'\nClick Open the Game Link or open {filename} from the same folder.')


def _build_cooldown(slide, content):
    _intro_text(slide, content['closing'], 4.28, (21, 23, 26, 28, 31, 32))
    for shape_id, prompt in ((31, 'Which Smart or Sneaky twist changed your mind?'),
                             (32, 'Which expression will you try next time?')):
        shape = _shape(slide, (shape_id,))
        _template(slide, (shape_id,), prompt, shape.top.inches + .63)
    _notes(slide, content['closing'])


def build_business_deck(topic, content, toolkit, game_file, *, feedback_url=RATE_US_URL):
    """Build the 22-slide sample sequence, with continuations for long Toolkit entries."""
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*\.html', game_file, flags=re.ASCII):
        raise ValueError('The game HTML must be a filename in the same folder as the deck.')
    if len(content['warmup']) != 3 or len(content['round1']) != 10:
        raise ValueError('Business English needs three warm-ups and ten Round 1 cards.')
    if content['game']['mechanic'] != 'smart_or_sneaky':
        raise ValueError('Business English uses Smart or Sneaky for Round 2.')
    if toolkit['topic'].strip().casefold() != topic.strip().casefold():
        raise ValueError('The Toolkit belongs to a different session topic.')
    for level in LEVEL_LABELS:
        validate_level(toolkit['levels'][level], level)

    verify_blueprint_source(BLUEPRINT, REFERENCE)
    presentation = Presentation(REFERENCE)
    slides = list(presentation.slides)
    presentation.core_properties.title = topic
    presentation.core_properties.subject = 'TalkLine Business English'
    _build_cover(slides[0], topic, content)
    _build_warmup(slides[1], content)

    toolkit_slides = []
    for index, (level, label) in enumerate(LEVEL_LABELS.items(), 2):
        toolkit_slides.extend(_level_pages(presentation, slides[index], label, toolkit['levels'][level]))
    grammar_slides = _grammar_pages(presentation, slides[5], toolkit)

    discussion_intro = slides[6]
    _remove(discussion_intro, 15)
    _add_text(discussion_intro, 'Round 1 heading', 'DISCUSSION CARDS', .4, 4.95, 6.7, 5.7, 28,
              bold=True, alignment=PP_ALIGN.CENTER)
    _template(discussion_intro, (18,), content['subtitle'], 6.74)
    _notes(discussion_intro, 'Ten discussion cards. Let each group pick one level per card.')
    for slide, card in zip(slides[7:17], content['round1'], strict=True):
        _build_discussion(slide, card)

    _write(slides[17], (18, 20), '20 minutes / Smart or Sneaky is up next.')
    _notes(slides[17], 'Take a 20-minute break and tell everyone when to return.')
    _build_game(slides[18], slides[19], game_file)
    _build_cooldown(slides[20], content)
    _button(slides[21], (20, 22), (20, 21), feedback_url)
    for paragraph in _shape(slides[21], (5, 7)).text_frame.paragraphs:
        for run in paragraph.runs:
            run.font.color.rgb = RGBColor.from_string(NAVY)
    _notes(slides[21], 'Thank the group and invite feedback. The Rate Us form needs internet.')
    _arrange_slides(presentation, [*slides[:2], *toolkit_slides, *grammar_slides, *slides[6:]])
    result = BytesIO()
    presentation.save(result)
    return result.getvalue()
