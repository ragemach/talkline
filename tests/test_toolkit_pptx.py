from io import BytesIO
from zipfile import ZipFile
from lxml import etree as E
from pptx import Presentation
from src.toolkit_pptx import build_toolkit_pptx, TEMPLATE, NS
from src.toolkit_library import sample_toolkit
from src.toolkit_pptx import TEXT_COLORS, PANEL_COLOR


def test_export_colors_have_readable_ordered_contrast():
    def luminance(value):
        c = [int(value[i:i+2],16)/255 for i in (0,2,4)]
        return sum(w*(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4)
                   for w,v in zip((.2126,.7152,.0722),c))
    ratios = [(luminance(c)+.05)/(luminance(PANEL_COLOR)+.05) for c in TEXT_COLORS]
    assert ratios[0] > ratios[1] > ratios[2] >= 4.5
    with ZipFile(BytesIO(build_toolkit_pptx(sample_toolkit()))) as z:
        root = E.fromstring(z.read('ppt/slides/slide100.xml'))
        shape = next(s for s in root.findall('.//p:sp',NS)
                     if s.find('p:nvSpPr/p:cNvPr',NS).get('id') == '500')
        paragraphs = shape.findall('p:txBody/a:p',NS)
        assert tuple(p.find('a:r/a:rPr/a:solidFill/a:srgbClr',NS).get('val')
                     for p in paragraphs[:3]) == TEXT_COLORS


def test_all_content_editable_and_template_geometry_preserved():
    data = sample_toolkit()
    output = build_toolkit_pptx(data)
    deck = Presentation(BytesIO(output))
    assert len(deck.slides) <= 7
    text = '\n'.join(s.text for slide in deck.slides for s in slide.shapes if s.has_text_frame)
    for material in data['levels'].values():
        for kind in ('vocabulary','phrases','idioms'):
            for item in material[kind]:
                for value in item.values(): assert value in text
        for example in material['mini_grammar']['examples']: assert example in text
    with ZipFile(TEMPLATE) as original, ZipFile(BytesIO(output)) as result:
        a = E.fromstring(original.read('ppt/slides/slide3.xml'))
        b = E.fromstring(result.read('ppt/slides/slide100.xml'))
        for shape in a.findall('.//p:sp',NS):
            sid=shape.find('p:nvSpPr/p:cNvPr',NS).get('id')
            if sid not in ('3','5','6','8','9','11','12','14','15'): continue
            match=next(s for s in b.findall('.//p:sp',NS) if s.find('p:nvSpPr/p:cNvPr',NS).get('id')==sid)
            assert E.tostring(shape.find('p:spPr',NS)) == E.tostring(match.find('p:spPr',NS))


def test_ten_words_do_not_disappear():
    data=sample_toolkit()
    data['levels']['a2']['vocabulary'].extend([
        {'expression':f'extra{i}','turkish':'ek','example':f'This is extra{i}.'} for i in (1,2)])
    deck=Presentation(BytesIO(build_toolkit_pptx(data)))
    assert len(deck.slides)<=8
    text='\n'.join(s.text for slide in deck.slides for s in slide.shapes if s.has_text_frame)
    assert 'extra2' in text


def test_levels_and_grammar_never_share_pages():
    deck = Presentation(BytesIO(build_toolkit_pptx(sample_toolkit())))
    def text_shapes(collection):
        for shape in collection:
            if shape.has_text_frame:
                yield shape
            if shape.shape_type == 6:
                yield from text_shapes(shape.shapes)
    for slide in deck.slides:
        shapes = {s.shape_id: s.text for s in text_shapes(slide.shapes)}
        assert 20 in shapes
        labels = {shapes[i] for i in (20,34) if i in shapes}
        assert len(labels) == 1
        assert labels <= {'A1/A2','B1','B2/C1'}
        entries = '\n'.join(text for sid,text in shapes.items() if sid >= 500)
        if 'GRAMMAR' in shapes[6]:
            assert 'Grammar examples' in entries
            assert 'Mini grammar' in shapes[9]
        else:
            assert 'Grammar examples' not in entries
            assert 'Vocabulary, phrases and idioms' in shapes[9]


def test_panels_follow_entries_without_unused_columns():
    deck = Presentation(BytesIO(build_toolkit_pptx(sample_toolkit())))
    for slide in deck.slides:
        panels = [shape for shape in slide.shapes if shape.shape_id in (16, 25)]
        entries = [shape for shape in slide.shapes if shape.shape_id >= 500]
        assert len(panels) in (1, 2)
        for panel in panels:
            contained = [entry for entry in entries
                         if panel.left <= entry.left < panel.left + panel.width]
            assert contained
            content_bottom = max(entry.top + entry.height for entry in contained)
            assert 0 <= panel.top + panel.height - content_bottom <= 19 * 12700
        if any(entry.text.startswith('Grammar examples') for entry in entries):
            assert len(panels) == 1
