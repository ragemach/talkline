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
    BUSINESS_GAME_FILE, FULL_BUSINESS, FULL_GAME_NIGHT, FULL_SPONTANEOUS, FULL_WORKFLOWS, GAME_NIGHT_FILES,
    TOOLKIT_HTML_FILENAME, TOOLKIT_PPTX_FILENAME, build_session_sequence, presentation_filename,
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
    workflow = metadata.get('workflow')
    full = workflow in FULL_WORKFLOWS.values()
    if full and (toolkit is None or toolkit.get('topic') != topic):
        raise ValueError('Generate the Toolkit for this topic before exporting the session.')
    toolkit_files = {}
    if workflow == FULL_SPONTANEOUS:
        from src.game_export import build_leveled_patch_game
        from src.spontaneous_content import validate_spontaneous
        from src.spontaneous_deck import build_spontaneous_deck
        validate_spontaneous(brief)
        games = {GAME_FILENAME: build_leveled_patch_game(topic, brief['game'])}
        deck = build_spontaneous_deck(topic, brief, toolkit=toolkit, game_file=GAME_FILENAME)
    elif workflow == FULL_GAME_NIGHT:
        from src.game_night_content import validate_game_night
        from src.game_night_deck import build_game_night_deck
        from src.game_night_export import build_game_night_game
        validate_game_night(brief)
        games = {filename: build_game_night_game(topic, game)
                 for filename, game in zip(GAME_NIGHT_FILES, brief['games'], strict=True)}
        deck = build_game_night_deck(topic, brief, toolkit, GAME_NIGHT_FILES)
    elif workflow == FULL_BUSINESS:
        from src.business_content import validate_business
        from src.business_deck import build_business_deck
        from src.game_export import build_smart_or_sneaky_game
        validate_business(brief)
        games = {BUSINESS_GAME_FILE: build_smart_or_sneaky_game(topic, brief['game'])}
        deck = build_business_deck(topic, brief, toolkit, BUSINESS_GAME_FILE)
    else:
        games = {GAME_FILENAME: build_patch_game(topic, brief['game_cards'])}
        deck = build_mini_deck(topic, brief, game_file=GAME_FILENAME)
    if toolkit is not None:
        toolkit_files[TOOLKIT_HTML_FILENAME] = toolkit_html(toolkit)
        if not full:
            toolkit_files[TOOLKIT_PPTX_FILENAME] = build_toolkit_pptx(toolkit)
    stages = build_session_sequence(metadata, brief, include_toolkit=toolkit is not None)
    guide = build_host_guide(topic, stages)

    category = metadata['concept']
    if category == 'auto':
        category = detect_category(topic, model)
    # Keep the invitation prompt small. The two discussion titles and the
    # activity name are enough; the model does not need all forty cards.
    invitation_brief = brief
    if workflow == FULL_SPONTANEOUS:
        invitation_brief = {
            'subtitle': brief['subtitle'], 'tagline': brief['tagline'],
            'round1': brief['round1'][:2], 'game_title': brief['game']['title'],
        }
    elif workflow == FULL_GAME_NIGHT:
        invitation_brief = {
            'subtitle': brief['subtitle'], 'tagline': brief['tagline'],
            'round_descriptions': (
                'Play Taboo. Describe the target without using the forbidden clues. '
                'Your team has to guess the word from what you can say.',
                'Play Problem Solver. Work as a team to pitch a solution and explain why it would work.',
            ),
        }
    elif workflow == FULL_BUSINESS:
        invitation_brief = {
            'subtitle': brief['subtitle'], 'tagline': brief['tagline'],
            'round_descriptions': (
                f"Share your experience of {topic} and compare different approaches.",
                'Play Smart or Sneaky? Weigh both sides of a business move before revealing a twist.',
            ),
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
        'stage': workflow if full else 'prototype',
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
        archive.writestr(HOST_GUIDE_FILENAME, guide)
        for filename, contents in (games | toolkit_files).items():
            archive.writestr(filename, contents)
        archive.writestr('content.json', json.dumps(payload, ensure_ascii=False, indent=2))
    return SessionExport(package.getvalue(), picture.size)
