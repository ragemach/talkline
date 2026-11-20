from copy import deepcopy
from io import BytesIO
import hashlib
import json
from zipfile import ZipFile
from lxml import etree as E
import pytest
from src.invitation_templates import SOURCE,NS,catalog,instantiate,INVITATION_LANGUAGE


def test_invitation_policy_is_english_and_preserves_source_design():
    policy=json.loads((SOURCE.parent/'policy.json').read_text(encoding='utf-8'))
    assert INVITATION_LANGUAGE==policy['language']=='en'
    assert 'shape_geometry' in policy['preserve']
    assert policy['source']==SOURCE.name


def test_text_replacement_preserves_design_and_all_assets():
    before_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    entry=next(s for s in catalog() if s['category']=='spontaneous')
    replacements=deepcopy(entry['blocks'])
    for key,paragraphs in replacements.items():
        replacements[key]=['Hi' if len(text)>=2 else text for text in paragraphs]
    result=instantiate(entry['slide'],replacements)
    with ZipFile(SOURCE) as original,ZipFile(BytesIO(result)) as changed:
        assert set(original.namelist())==set(changed.namelist())
        for name in original.namelist():
            if name not in (entry['member'],'ppt/presentation.xml'):
                assert original.read(name)==changed.read(name),name
        old=E.fromstring(original.read(entry['member']))
        new=E.fromstring(changed.read(entry['member']))
        assert old.xpath('//a:t/text()',namespaces=NS)!=new.xpath('//a:t/text()',namespaces=NS)
        for root in (old,new):
            for node in root.xpath('//a:t',namespaces=NS): node.text=''
        assert E.tostring(old)==E.tostring(new)
        presentation=E.fromstring(changed.read('ppt/presentation.xml'))
        assert len(presentation.find('p:sldIdLst',NS))==1
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==before_hash


def test_all_existing_text_paragraphs_survive_identity_substitution():
    # Exercise every nonempty design in the supplied 48-slide library.
    for entry in catalog():
        if not entry['blocks']: continue
        with ZipFile(BytesIO(instantiate(entry['slide'],deepcopy(entry['blocks'])))) as changed,ZipFile(SOURCE) as original:
            actual=E.fromstring(changed.read(entry['member']))
            expected=E.fromstring(original.read(entry['member']))
            assert actual.xpath('//a:t/text()',namespaces=NS)==expected.xpath('//a:t/text()',namespaces=NS)


def test_long_content_is_rejected_instead_of_reformatting():
    entry=next(s for s in catalog() if s['category']=='spontaneous')
    replacements=deepcopy(entry['blocks'])
    first=next(iter(replacements))
    replacements[first][0]='A'*10000
    with pytest.raises(ValueError,match='Shorten'): instantiate(entry['slide'],replacements)
