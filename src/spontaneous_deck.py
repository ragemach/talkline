"""Fill the approved Spontaneous Talk template with editable session content."""
from copy import deepcopy
from functools import lru_cache
from io import BytesIO
import json
from pathlib import Path
import re

from PIL import ImageFont
from pptx import Presentation
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.util import Inches, Pt

from src.game_export import GAME_FILENAME
from src.session_sequence import RATE_US_URL
from src.template_blueprints import SPONTANEOUS_ROLES, verify_blueprint_source
from src.toolkit import LEVEL_LABELS, validate_level


ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT = ROOT / 'templates/spontaneous.blueprint.json'
ROW_IDS = tuple((10 + 3 * index, 12 + 3 * index) for index in range(8))
REFERENCE_GAME_RULES = (
    'Read the glitch aloud together.',
    'Discuss both patches and predict what might happen.',
    'Choose one patch and reveal its outcome.',
    'Decide whether to keep the change or reset.',
)


def _shape(slide, path):
    shapes = slide.shapes
    for index, shape_id in enumerate(path):
        shape = next(shape for shape in shapes if shape.shape_id == shape_id)
        if index < len(path) - 1:
            shapes = shape.shapes
    return shape


def _remove(slide, *ids):
    for shape_id in ids:
        element = _shape(slide, (shape_id,))._element
        element.getparent().remove(element)


def _replace_paragraph(paragraph, text):
    runs = list(paragraph.runs)
    if runs:
        runs[0].text = text
        for run in runs[1:]:
            run._r.getparent().remove(run._r)
    else:
        paragraph.add_run().text = text


def _write(slide, path, text):
    shape = _shape(slide, path)
    paragraphs = shape.text_frame.paragraphs
    lines = text.split('\n')
    if len(lines) > len(paragraphs):
        raise ValueError(f'Text does not fit template paragraph structure at {path}.')
    for index, paragraph in enumerate(paragraphs):
        _replace_paragraph(paragraph, lines[index] if index < len(lines) else '')
    return shape


@lru_cache(maxsize=32)
def _font(size, bold, italic):
    """Estimate wrapping with the Arial metrics used by the source slide."""
    names = {
        (False, False): ('arial.ttf', 'LiberationSans-Regular.ttf'),
        (True, False): ('arialbd.ttf', 'LiberationSans-Bold.ttf'),
        (False, True): ('ariali.ttf', 'LiberationSans-Italic.ttf'),
        (True, True): ('arialbi.ttf', 'LiberationSans-BoldItalic.ttf'),
    }
    for name in names[bold, italic]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size)


def _line_count(text, width, size, *, bold=False, italic=False):
    font = _font(round(size * 4), bold, italic)
    pixels = width * 4 * .96
    line = ''
    count = 1
    for word in text.split():
        candidate = f'{line} {word}' if line else word
        if font.getlength(candidate) <= pixels:
            line = candidate
            continue
        if line:
            count += 1
            line = ''
        for char in word:
            if line and font.getlength(line + char) > pixels:
                count += 1
                line = ''
            line += char
    return count


def _fit_top_level(shape, max_bottom, *, size=None, lead=None):
    """Keep the source font size and extend its native text box within its slot."""
    paragraph = shape.text_frame.paragraphs[0]
    font = paragraph.runs[0].font
    size = size or font.size.pt
    if lead is not None:
        paragraph.line_spacing = Pt(lead)
    spacing = paragraph.line_spacing
    leading = spacing.pt if hasattr(spacing, 'pt') else size * (spacing or 1.2)
    lines = _line_count(shape.text, shape.width.pt, size,
                        bold=bool(font.bold), italic=bool(font.italic))
    height = max(shape.height, Pt(lines * leading + 2))
    if shape.top + height > max_bottom:
        raise ValueError(f'Text is too long for the {shape.name} slide slot: {shape.text[:48]!r}')
    shape.height = height
    shape.text_frame.word_wrap = True
    shape.text_frame.auto_size = MSO_AUTO_SIZE.NONE


def _notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def _set_link(slide, button_path, filename):
    button = _shape(slide, button_path)
    for paragraph in button.text_frame.paragraphs:
        for run in paragraph.runs:
            if run.hyperlink.address:
                run.hyperlink.address = None
    # Keep the source text colors, including on readers that color linked runs blue.
    button.click_action.hyperlink.address = filename
    # The adjacent rectangle makes the whole template button clickable.
    _shape(slide, (*button_path[:-1], button_path[-1] - 1)).click_action.hyperlink.address = filename


def _toolkit_row(slide, index, top, heading, meaning, example):
    background, text_id = ROW_IDS[index]
    panel = _shape(slide, (background,))
    box = _shape(slide, (text_id,))
    first, second = box.text_frame.paragraphs
    first.runs[0].text = heading
    first.runs[1].text = f' / {meaning}' if meaning else ''
    _replace_paragraph(second, example)
    # Approximate a mixed-style heading as bold to reserve enough room.
    lines = _line_count(first.text, box.width.pt, 14, bold=True)
    lines += _line_count(second.text, box.width.pt, 14, italic=True)
    height = max(Inches(.85), Pt(lines * 16.8 + 12))
    panel.top = top
    panel.height = height
    box.top = top + Pt(5)
    box.height = height - Pt(8)
    return height


def _clone_toolkit_layout(presentation, source):
    # Source slide 4 uses only native artwork and has no shape relationships.
    # Its notes are created separately, so every continuation has unique notes.
    if any(rel.reltype.rsplit('/', 1)[-1] not in {'slideLayout', 'notesSlide'}
           for rel in source.part.rels.values()):
        raise ValueError('Toolkit template contains unmapped slide relationships.')
    slide = presentation.slides.add_slide(source.slide_layout)
    slide._element = slide.part._element = deepcopy(source._element)
    # add_slide() caches a shape collection while cloning layout placeholders.
    slide.__dict__.pop('shapes', None)
    return slide


def _finish_toolkit_page(slide, used, level, number, grammar):
    for ids in ROW_IDS[used:]:
        _remove(slide, *ids)
    label = LEVEL_LABELS[level]
    _write(slide, (4,), 'MINI GRAMMAR' if grammar else 'TOOLKIT')
    _write(slide, (5,), 'Mini Grammar' if grammar else 'Toolkit')
    _write(slide, (6,), f'{label} / {"Grammar" if grammar else "Vocabulary, phrases and idioms"}'
           + (f' / {number}' if number > 1 else ''))
    # The group contains the existing badge and caption. Enlarge the two-letter
    # badge for the wider combined level labels without lowering type size.
    badge = _shape(slide, (7,))
    badge.width = Inches(1.22)
    badge.left = (Inches(7.5) - badge.width) // 2
    _write(slide, (7, 9), label)
    _notes(slide, f'{label}: offer an example before asking learners to make their own.')


def _make_toolkit_pages(presentation, source, toolkit):
    pages = []
    for grammar in (False, True):
        for level in LEVEL_LABELS:
            material = toolkit['levels'][level]
            validate_level(material, level)
            if grammar:
                item = material['mini_grammar']
                rows = [
                    (item['title'], item['pattern'], item['explanation']),
                    *[(f'Example {index}', '', example)
                      for index, example in enumerate(item['examples'], 1)],
                ]
            else:
                rows = [
                    (f'Idiom: {item["expression"]}' if kind == 'idioms' else item['expression'],
                     item['turkish'], item['example'])
                    for kind in ('vocabulary', 'phrases', 'idioms') for item in material[kind]
                ]
            number = 1
            slide = _clone_toolkit_layout(presentation, source)
            used, top = 0, Inches(1.85)
            for row in rows:
                if used == len(ROW_IDS) or top + _toolkit_row(slide, used, top, *row) > Inches(9.42):
                    _finish_toolkit_page(slide, used, level, number, grammar)
                    pages.append(slide)
                    number += 1
                    slide = _clone_toolkit_layout(presentation, source)
                    used, top = 0, Inches(1.85)
                top += _toolkit_row(slide, used, top, *row) + Pt(5)
                used += 1
            _finish_toolkit_page(slide, used, level, number, grammar)
            pages.append(slide)
    return pages


def _arrange_slides(presentation, slides):
    order = presentation.slides._sldIdLst
    slide_ids = [slide.slide_id for slide in slides]
    retained = set(slide_ids)
    by_id = {entry.id: entry for entry in order}
    for entry in list(order):
        order.remove(entry)
        if entry.id not in retained:
            presentation.part.drop_rel(entry.rId)
    for slide_id in slide_ids:
        order.append(by_id[slide_id])


def build_spontaneous_deck(topic, content, toolkit=None, game_file=GAME_FILENAME, *, feedback_url=RATE_US_URL):
    """Produce the approved meeting flow, using new native text and local links."""
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*\.html', game_file, flags=re.ASCII):
        raise ValueError('The game HTML must be a filename in the same folder as the deck.')
    if len(content['warmup']) != 3 or len(content['round1']) != 10:
        raise ValueError('Spontaneous Talk needs three warm-ups and ten Round 1 cards.')
    if toolkit is not None and toolkit['topic'].strip().casefold() != topic.strip().casefold():
        raise ValueError('The Toolkit belongs to a different session topic.')
    blueprint = json.loads(BLUEPRINT.read_text(encoding='utf-8'))
    source = ROOT / 'references' / blueprint['source_file']
    verify_blueprint_source(blueprint, source)
    presentation = Presentation(source)
    slides = list(presentation.slides)
    if len(slides) != len(SPONTANEOUS_ROLES):
        raise ValueError('The approved Spontaneous Talk template has changed.')
    presentation.core_properties.title = topic
    presentation.core_properties.subject = 'TalkLine Spontaneous Talk'

    cover, warmup = slides[:2]
    cover_title = _write(cover, (7,), topic)
    _fit_top_level(cover_title, Inches(8.86))
    subtitle = _write(cover, (8,), content['subtitle'])
    subtitle.top = max(subtitle.top, cover_title.top + cover_title.height + Pt(4))
    _fit_top_level(subtitle, Inches(9.52))
    footer = _shape(cover, (9,))
    footer.top = max(footer.top, subtitle.top + subtitle.height + Pt(8))
    if footer.top + footer.height > presentation.slide_height:
        raise ValueError('The session title and subtitle are too long for the cover.')
    for path, value in {
        (24, 26): 'TALKLINE / LIVE',
        (27, 29): 'LET’S',
        (30, 32): 'TALK',
        (33, 35): 'YOUR TURN TO SPEAK',
        (38, 40): 'SHARE\nAND LISTEN',
        (43, 45): 'JOIN IN',
    }.items():
        _write(cover, path, value)
    _notes(cover, f'Welcome the group to TalkLine. Tonight’s topic is {topic}. {content["tagline"]}')

    opening = _write(warmup, (6,), content['opening'])
    _fit_top_level(opening, Inches(3.25))
    first_question = _shape(warmup, (10,))
    shift = max(0, opening.top + opening.height + Pt(14) - first_question.top)
    for marker_id, box_id, question in zip((7, 11, 15), (10, 14, 18), content['warmup']):
        marker = _shape(warmup, (marker_id,))
        marker.top += shift
        box = _write(warmup, (box_id,), question)
        box.top += shift
        _fit_top_level(box, box.top + Inches(1.0))
    _shape(warmup, (19,)).top = Inches(6.87) + shift
    _notes(warmup, f'{content["opening"]}\n\nOffer one prompt at a time and let quieter speakers go in pairs first.')

    intro = slides[6]
    if toolkit is None:
        paragraphs = _shape(intro, (7,)).text_frame.paragraphs
        _replace_paragraph(paragraphs[2], 'Give a reason or an example.')
    _notes(intro, 'Use one of the three levels on each card. Let each pair choose the version that suits them.')
    for number, card in enumerate(content['round1'], 8):
        slide = slides[number - 1]
        for field in blueprint['slides'][number - 1]['fields']:
            key = field['content_key']
            if key is None:
                continue
            role = key.rsplit('.', 1)[-1]
            shape = _write(slide, field['shape_path'], card[role])
            if role == 'title':
                shape.top = Inches(.68)
                _fit_top_level(shape, Inches(1.45), lead=26)
            else:
                _fit_top_level(shape, shape.top + Inches(1.72))
        _notes(slide, f'{card["title"]}\nChoose A2, B2 or C1. Follow up with “Why?” or “Can you give an example?”')

    _notes(slides[17], 'Give the group a break and announce what time to return.')
    game = content['game']
    _write(slides[18], (16, 18), 'THE CHOICE IS YOURS')
    _write(slides[18], (8, 10), '\n'.join((
        'A glitch changes an everyday situation.',
        'Discuss both fixes and try one.',
        'Reveal its outcome, then choose KEEP or RESET.',
        '',
        f'{len(game["elementary"])} cards per level / 1 host',
    )))
    _notes(slides[18], 'Choose Elementary or Advanced. Let the group discuss the patches before revealing the outcome.')
    for path, rule in zip(((11, 13), (17, 19), (23, 25), (29, 31)), REFERENCE_GAME_RULES):
        _write(slides[19], path, rule)
    _notes(slides[19], '\n'.join(REFERENCE_GAME_RULES))
    _write(slides[20], (8, 10), 'PATCH NOTES')
    _set_link(slides[20], (2, 4), game_file)
    _notes(slides[20], f'Extract the ZIP. Click PLAY, or open {game_file} directly in a browser if PowerPoint blocks the local link.')

    cooldown = slides[21]
    original = _shape(cooldown, (14, 16)).text_frame.paragraphs[0].runs[0]
    _remove(cooldown, 11, 14, 17, 19, 22, 25, 27, 30)
    text = cooldown.shapes.add_textbox(Inches(.76), Inches(2.08), Inches(5.98), Inches(1.0))
    paragraph = text.text_frame.paragraphs[0]
    run = paragraph.add_run()
    run._r.insert(0, deepcopy(original._r.get_or_add_rPr()))
    run.text = content['closing']
    run.font.size = Pt(19)
    text.text_frame.margin_left = text.text_frame.margin_right = 0
    text.text_frame.margin_top = text.text_frame.margin_bottom = 0
    text.text_frame.vertical_anchor = MSO_ANCHOR.TOP
    _fit_top_level(text, Inches(6.4))
    _shape(cooldown, (9,)).height = text.height + Inches(.46)
    _notes(cooldown, content['closing'])
    _set_link(slides[22], (3, 5), feedback_url)
    _notes(slides[22], 'Thank the group and invite feedback. The Rate Us form requires internet.')

    toolkit_pages = _make_toolkit_pages(presentation, slides[3], toolkit) if toolkit else []
    _arrange_slides(presentation, [*slides[:2], *toolkit_pages, *slides[6:]])
    result = BytesIO()
    presentation.save(result)
    return result.getvalue()
