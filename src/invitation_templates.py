"""Approved invitation library. Select original slides; edit text without rebuilding design."""
from io import BytesIO
from pathlib import Path
import re
from zipfile import ZipFile
from lxml import etree as E

SOURCE=Path(__file__).resolve().parents[1]/'templates/invitations/TalkLine_Approved_Invitations.pptx'
INVITATION_LANGUAGE='en'
NS={'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
    'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
    'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
PALETTES={'spontaneous':{'A976E3'},'business':{'5EC9F3','56AEFF'},
          'game_night':{'FCE08B'},'pop_culture':{'FF914D'},'culture_exchange':{'00BF63'}}


def catalog(source=SOURCE):
    with ZipFile(source) as archive:
        presentation=E.fromstring(archive.read('ppt/presentation.xml'))
        relationships=E.fromstring(archive.read('ppt/_rels/presentation.xml.rels'))
        targets={r.get('Id'):'ppt/'+r.get('Target') for r in relationships}
        result=[]
        for number,identifier in enumerate(presentation.find('p:sldIdLst',NS),1):
            member=targets[identifier.get('{'+NS['r']+'}id')]
            root=E.fromstring(archive.read(member))
            background=root.xpath('//p:bg//a:srgbClr/@val',namespaces=NS)
            blocks={}
            for shape in root.xpath('//p:sp[p:txBody]',namespaces=NS):
                shape_id=shape.find('p:nvSpPr/p:cNvPr',NS).get('id')
                blocks[shape_id]=[''.join(p.xpath('.//a:t/text()',namespaces=NS))
                                  for p in shape.findall('p:txBody/a:p',NS)]
            color=background[0] if background else None
            result.append({'slide':number,'member':member,'background':color,'blocks':blocks,
                           'category':next((k for k,v in PALETTES.items() if color in v),'other')})
        return result


def choose_template(category,topic,source=SOURCE):
    candidates=[s for s in catalog(source) if s['category']==category and s['blocks']]
    if not candidates: raise ValueError('No approved source template for this category.')
    words=set(re.findall(r'\w+',topic.casefold()))-{'the','a','of','and','talk','english'}
    def rank(slide):
        text=' '.join(p for block in slide['blocks'].values() for p in block).casefold()
        return (sum(word in text for word in words), 'hey talkliners' in text)
    return max(candidates,key=rank)


def instantiate(slide_number,replacements,source=SOURCE):
    """Replace every text paragraph; preserve all shapes, styles, images and original size.

    replacements maps shape IDs to paragraph lists, matching the selected catalog entry.
    All blocks must be supplied explicitly. The caller must bind dates/venues to
    user metadata rather than copy historical values from the selected reference.
    No automatic font shrinking, recoloring or geometric changes are permitted.
    """
    entry=next((s for s in catalog(source) if s['slide']==slide_number),None)
    if not entry or not entry['blocks']: raise ValueError('Select a nonempty approved slide.')
    if set(replacements)!=set(entry['blocks']): raise ValueError('Replace every source text block.')
    with ZipFile(source) as archive:
        root=E.fromstring(archive.read(entry['member']))
        for shape in root.xpath('//p:sp[p:txBody]',namespaces=NS):
            shape_id=shape.find('p:nvSpPr/p:cNvPr',NS).get('id')
            paragraphs=shape.findall('p:txBody/a:p',NS)
            values=replacements[shape_id]
            if not isinstance(values,list) or len(values)!=len(paragraphs):
                raise ValueError(f'Preserve the paragraph count in block {shape_id}.')
            for paragraph,value in zip(paragraphs,values):
                nodes=paragraph.findall('a:r/a:t',NS)
                original=''.join(node.text or '' for node in nodes)
                if not isinstance(value,str) or len(value)>max(len(original),1):
                    raise ValueError(f'Text exceeds source capacity in block {shape_id}. Shorten the text.')
                if not nodes and value: raise ValueError('Cannot add text to an empty source paragraph.')
                # Retain original run formatting and paragraph structure.
                old_lengths=[len(node.text or '') for node in nodes]
                position=0
                total=sum(old_lengths)
                for index,node in enumerate(nodes):
                    end=len(value) if index==len(nodes)-1 else position+round(len(value)*old_lengths[index]/max(total,1))
                    node.text=value[position:end]
                    position=end
        presentation=E.fromstring(archive.read('ppt/presentation.xml'))
        slide_list=presentation.find('p:sldIdLst',NS)
        for index,identifier in enumerate(list(slide_list),1):
            if index!=slide_number: slide_list.remove(identifier)
        output=BytesIO()
        with ZipFile(output,'w') as result:
            for member in archive.infolist():
                data=archive.read(member.filename)
                if member.filename==entry['member']: data=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
                if member.filename=='ppt/presentation.xml': data=E.tostring(presentation,xml_declaration=True,encoding='UTF-8',standalone=True)
                result.writestr(member,data)
        return output.getvalue()
