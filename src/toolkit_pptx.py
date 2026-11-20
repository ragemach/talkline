"""Editable Toolkit export using the owner's Business English slide XML."""
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from lxml import etree as ET
from src.toolkit import validate_level, LEVEL_LABELS
from PIL import ImageFont

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'references/user_examples/Talkline Business Beyond the Office.pptx'
NS = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
REL = 'http://schemas.openxmlformats.org/package/2006/relationships'
CT = 'http://schemas.openxmlformats.org/package/2006/content-types'
SLOTS = ('21','27','28','29','30','31','35','36','37','38')
TEXT_COLORS = ('FFFFFF', 'F2C94C', 'A8BDD9')
PANEL_COLOR = '1E2744'


def _apply_text_hierarchy(shape, grammar_examples=False):
    """Local export policy: expression > translation > usage example contrast."""
    for index, paragraph in enumerate(shape.findall('p:txBody/a:p', NS)):
        color = TEXT_COLORS[2] if grammar_examples and index > 0 else TEXT_COLORS[min(index, 2)]
        for run in paragraph.findall('a:r', NS):
            props = run.find('a:rPr', NS)
            if props is None:
                props = ET.Element(f'{{{NS["a"]}}}rPr')
                run.insert(0, props)
            for fill in list(props):
                if ET.QName(fill).localname in ('solidFill','gradFill','noFill','pattFill','blipFill','grpFill'):
                    props.remove(fill)
            fill = ET.Element(f'{{{NS["a"]}}}solidFill')
            # Fill precedes font declarations in DrawingML run properties.
            insert_at = next((i for i, child in enumerate(props)
                              if ET.QName(child).localname in ('latin','ea','cs','sym','hlinkClick','hlinkMouseOver')), len(props))
            props.insert(insert_at, fill)
            ET.SubElement(fill, f'{{{NS["a"]}}}srgbClr', val=color)


def _set(root, shape_id, lines):
    shape = next(s for s in root.findall('.//p:sp', NS)
                 if s.find('p:nvSpPr/p:cNvPr', NS).get('id') == shape_id)
    body = shape.find('p:txBody/a:bodyPr', NS)
    if body is not None: body.set('wrap', 'square')
    paragraphs = shape.findall('p:txBody/a:p', NS)
    if len(lines) > len(paragraphs):
        raise ValueError(f'Template shape {shape_id} lacks text paragraphs')
    for i, paragraph in enumerate(paragraphs):
        texts = paragraph.findall('.//a:t', NS)
        if texts:
            texts[0].text = lines[i] if i < len(lines) else ''
            for node in texts[1:]:
                node.text = ''


EMU_PER_PT = 12700
COLUMN_WIDTH = 2560320
PANEL_SPAN = 3196595
TEXT_TOP = 2472273
PANEL_TOP = 1776727
PANEL_PADDING = 18 * EMU_PER_PT
CAPACITY = 450


@lru_cache(maxsize=2)
def _font(bold, zoom):
    return ImageFont.truetype('arialbd.ttf' if bold else 'ariali.ttf',
                             round((56 if bold else 52) * zoom))


def _entry_height(lines, width, zoom=1):
    limit = width / EMU_PER_PT * 4 * .96
    total = 6 * zoom
    for index, line in enumerate(lines):
        font = _font(index == 0, zoom)
        for paragraph in line.splitlines() or ['']:
            row = ''
            count = 1
            for word in paragraph.split():
                if row and font.getlength(row + ' ' + word) > limit:
                    count += 1
                    row = ''
                if font.getlength(word) > limit:
                    for char in word:
                        if row and font.getlength(row + char) > limit:
                            count += 1
                            row = ''
                        row += char
                else:
                    row = f'{row} {word}' if row else word
            total += count * (16.8 if index == 0 else 15.6) * zoom
    return total


def _paginate(entries):
    """Find the fewest pages in reading order and prefer shorter, balanced panels."""
    heights = {
        width: [_entry_height(lines, width) for lines in entries]
        for width in (COLUMN_WIDTH, COLUMN_WIDTH + PANEL_SPAN)
    }
    narrow, wide = heights.values()
    size = len(entries)

    @lru_cache(maxsize=None)
    def best(start):
        if start == size:
            return (0, 0), ()
        choices = []

        def consider(end, panels, cost):
            tail = best(end)
            if tail is not None:
                (pages, penalty), rest = tail
                choices.append(((1 + pages, cost + penalty), (panels, *rest)))

        for end in range(start + 1, size + 1):
            height = sum(wide[start:end])
            if height > CAPACITY:
                break
            consider(end, (entries[start:end],), height / 2 if height <= CAPACITY / 2 else height)
        for split in range(start + 1, size):
            left = sum(narrow[start:split])
            if left > CAPACITY:
                break
            for end in range(split + 1, size + 1):
                right = sum(narrow[split:end])
                if right > CAPACITY:
                    break
                consider(end, (entries[start:split], entries[split:end]),
                         max(left, right) + abs(left - right))
        return min(choices, key=lambda choice: choice[0]) if choices else None

    result = best(0)
    if result is None:
        raise ValueError('Toolkit entry is too long for a readable page')
    return result[1]


def _group(tree, id):
    return next(shape for shape in tree.findall('p:grpSp', NS)
                if shape.find('p:nvGrpSpPr/p:cNvPr', NS).get('id') == id)


def build_toolkit_pptx(toolkit):
    pages = []
    for section in ('Vocabulary, phrases and idioms', 'Mini grammar'):
        for level in ('a2', 'b1', 'b2_c1'):
            material = toolkit['levels'][level]
            validate_level(material, level)
            if section != 'Mini grammar':
                entries = [[item['expression'], item['turkish'], item['example']]
                           for kind in ('vocabulary', 'phrases') for item in material[kind]]
                entries.extend([f"Idiom · {item['expression']}", item['turkish'], item['example']]
                               for item in material['idioms'])
            else:
                grammar = material['mini_grammar']
                entries = [[grammar['title'], grammar['pattern'], grammar['explanation']],
                           ['Grammar examples', *grammar['examples']]]
            for panels in _paginate(entries):
                pages.append((LEVEL_LABELS[level], section, panels))
    with ZipFile(TEMPLATE) as source:
        files = {name: source.read(name) for name in source.namelist()}
    presentation = ET.fromstring(files['ppt/presentation.xml'])
    slide_list = presentation.find('p:sldIdLst', NS)
    for child in list(slide_list): slide_list.remove(child)
    rels = ET.fromstring(files['ppt/_rels/presentation.xml.rels'])
    for child in list(rels):
        if child.get('Type','').endswith('/slide'): rels.remove(child)
    content = ET.fromstring(files['[Content_Types].xml'])
    for index, (label, section, panels) in enumerate(pages, 100):
        source_number = 3
        root = ET.fromstring(files['ppt/slides/slide3.xml'])
        mapping = {'6':['TOOLKIT / GRAMMAR' if section == 'Mini grammar' else 'TOOLKIT'], '9':[label + ' / ' + section],
                   '12':[toolkit['topic']], '15':[section],
                   '20':[label], '24':[label], '34':[label]}
        for shape, lines in mapping.items(): _set(root, shape, lines)
        shapes = root.findall('.//p:sp',NS)
        base = deepcopy(next(s for s in shapes if s.find('p:nvSpPr/p:cNvPr',NS).get('id') == '27'))
        for shape in shapes:
            if shape.find('p:nvSpPr/p:cNvPr',NS).get('id') in SLOTS:
                shape.getparent().remove(shape)
        tree = root.find('p:cSld/p:spTree',NS)
        tree.remove(_group(tree, '22'))  # Duplicate right heading behind the panel.
        wide = len(panels) == 1
        if wide:
            for group_id in ('25', '32'):
                tree.remove(_group(tree, group_id))
        text_width = COLUMN_WIDTH + PANEL_SPAN if wide else COLUMN_WIDTH
        number = 500
        for column, entries in enumerate(panels):
            # Sparse pages can use larger type while remaining on the same page.
            zoom = 1
            if wide:
                for candidate in (1.6, 1.35):
                    if sum(_entry_height(lines, text_width, candidate) for lines in entries) <= CAPACITY:
                        zoom = candidate
                        break
            heights = [_entry_height(lines, text_width, zoom) for lines in entries]
            panel_id = '16' if column == 0 else '25'
            panel_size = _group(tree, panel_id).find('p:grpSpPr/a:xfrm/a:ext', NS)
            panel_size.set('cy', str(TEXT_TOP - PANEL_TOP + round(sum(heights) * EMU_PER_PT) + PANEL_PADDING))
            if wide:
                panel_size.set('cx', str(int(panel_size.get('cx')) + PANEL_SPAN))
                label = _group(tree, '18').find('p:grpSpPr/a:xfrm/a:off', NS)
                label.set('x', str(int(label.get('x')) + PANEL_SPAN // 2))
            top = TEXT_TOP
            for lines, height in zip(entries, heights):
                shape = deepcopy(base)
                props = shape.find('p:nvSpPr/p:cNvPr', NS)
                props.set('id', str(number))
                props.set('name', f'Toolkit entry {number}')
                transform = shape.find('p:spPr/a:xfrm', NS)
                offset = transform.find('a:off', NS)
                offset.set('x', str(598054 if column == 0 else 3829664))
                offset.set('y', str(top))
                size = transform.find('a:ext', NS)
                size.set('cx', str(text_width))
                size.set('cy', str(round(height * EMU_PER_PT)))
                tree.append(shape)
                _set(root, str(number), lines)
                _apply_text_hierarchy(shape, grammar_examples=lines[0] == 'Grammar examples')
                if zoom != 1:
                    for node in shape.findall('.//a:rPr', NS):
                        if 'sz' in node.attrib:
                            node.set('sz', str(round(int(node.get('sz')) * zoom)))
                    for node in shape.findall('.//a:lnSpc/a:spcPts', NS):
                        node.set('val', str(round(int(node.get('val')) * zoom)))
                top += round(height * EMU_PER_PT)
                number += 1
        name = f'ppt/slides/slide{index}.xml'
        files[name] = ET.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
        slide_rels = ET.fromstring(files[f'ppt/slides/_rels/slide{source_number}.xml.rels'])
        for child in list(slide_rels):
            if child.get('Type','').endswith(('/notesSlide','/comments')): slide_rels.remove(child)
        files[f'ppt/slides/_rels/slide{index}.xml.rels'] = ET.tostring(slide_rels)
        rid = f'rIdToolkit{index}'
        ET.SubElement(rels, f'{{{REL}}}Relationship', Id=rid, Type=NS['r']+'/slide', Target=f'slides/slide{index}.xml')
        ET.SubElement(slide_list, f'{{{NS["p"]}}}sldId', id=str(1000+index), attrib={f'{{{NS["r"]}}}id':rid})
        ET.SubElement(content, f'{{{CT}}}Override', PartName='/'+name,
                      ContentType='application/vnd.openxmlformats-officedocument.presentationml.slide+xml')
    files['ppt/presentation.xml'] = ET.tostring(presentation)
    files['ppt/_rels/presentation.xml.rels'] = ET.tostring(rels)
    files['[Content_Types].xml'] = ET.tostring(content)
    output = BytesIO()
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for name, data in files.items(): archive.writestr(name, data)
    return output.getvalue()


