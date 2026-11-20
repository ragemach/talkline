"""Build one offline kit from the same validated revision used by the app."""
from dataclasses import dataclass
from io import BytesIO
import json
import zipfile

from src import invitation_export
from src.game_export import GAME_FILENAME, build_patch_game
from src.host_guide import HOST_GUIDE_FILENAME, build_host_guide
from src.invitation_content import detect_category, prepare_invitation
from src.render_assets import build_mini_deck
from src.session_sequence import (
    FULL_SPONTANEOUS, TOOLKIT_HTML_FILENAME, TOOLKIT_PPTX_FILENAME,
    build_prototype_sequence, presentation_filename,
)
from src.settings import EventDetails
from src.toolkit_export import toolkit_html
from src.toolkit_pptx import build_toolkit_pptx


@dataclass(frozen=True)
class SessionExport:
    archive: bytes
    invitation_size: tuple[int, int]


def build_session_export(metadata, brief, toolkit=None, *, review=None,
                         review_warning=None, reviewed_flagged_content=False):
    topic = metadata['topic']
    model = metadata['model']
    full = metadata.get('workflow') == FULL_SPONTANEOUS
    stages = build_prototype_sequence(brief, include_toolkit=toolkit is not None, full=full)
    toolkit_files = {}
    if full:
        from src.game_export import build_leveled_patch_game
        from src.spontaneous_content import validate_spontaneous
        from src.spontaneous_deck import build_spontaneous_deck
        if toolkit is None or toolkit.get('topic') != topic:
            raise ValueError('Generate the Toolkit for this topic before exporting the session.')
        validate_spontaneous(brief)
        game = build_leveled_patch_game(topic, brief['game'])
        deck = build_spontaneous_deck(topic, brief, toolkit=toolkit, game_file=GAME_FILENAME)
        toolkit_files[TOOLKIT_HTML_FILENAME] = toolkit_html(toolkit)
    else:
        game = build_patch_game(topic, brief['game_cards'])
        deck = build_mini_deck(topic, brief, game_file=GAME_FILENAME)
        if toolkit is not None:
            toolkit_files = {TOOLKIT_HTML_FILENAME: toolkit_html(toolkit),
                             TOOLKIT_PPTX_FILENAME: build_toolkit_pptx(toolkit)}
    guide = build_host_guide(topic, stages)

    category = metadata['concept']
    if category == 'auto':
        category = detect_category(topic, model)
    # Keep the invitation prompt small. The two discussion titles and the
    # activity name are enough; the model does not need all forty cards.
    invitation_brief = brief
    if full:
        invitation_brief = {
            'subtitle': brief['subtitle'], 'tagline': brief['tagline'],
            'round1': brief['round1'][:2], 'game_title': brief['game']['title'],
        }
    event = EventDetails(metadata['venue'], metadata['date'], metadata['time'])
    invitation = prepare_invitation(topic, invitation_brief, event, category, model)
    picture = invitation_export.render_invitation(invitation['pptx'])
    gif = invitation_export.animate_invitation(picture)
    preview = BytesIO()
    picture.save(preview, format='PNG')
    invitation_meta = {key: value for key, value in invitation.items() if key != 'pptx'}
    invitation_meta['size'] = list(picture.size)
    payload = {
        'schema_version': 2 if full else 1,
        'stage': FULL_SPONTANEOUS if full else 'prototype',
        'topic': topic, 'event': {key: metadata[key] for key in ('venue', 'date', 'time')},
        'engine': {'mode': metadata['mode'], 'model': model},
        'content': brief, 'review': review, 'review_warning': review_warning,
        'user_reviewed_flagged_prototype': reviewed_flagged_content,
        'invitation': invitation_meta, 'session_sequence': stages,
    }
    if full:
        payload['toolkit'] = toolkit
    package = BytesIO()
    with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(presentation_filename(metadata), deck)
        archive.writestr('TalkLine_Invitation.gif', gif)
        archive.writestr('TalkLine_Invitation.pptx', invitation['pptx'])
        archive.writestr('TalkLine_Invitation.png', preview.getvalue())
        archive.writestr(GAME_FILENAME, game)
        archive.writestr(HOST_GUIDE_FILENAME, guide)
        for filename, contents in toolkit_files.items():
            archive.writestr(filename, contents)
        archive.writestr('content.json', json.dumps(payload, ensure_ascii=False, indent=2))
    return SessionExport(package.getvalue(), picture.size)
