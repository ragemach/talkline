"""Map one saved draft to its matching export and editable event inputs."""
from jsonschema import Draft202012Validator

from src.ai_content import REVIEW_SCHEMA, _validate
from src.checkpoints import content_fingerprint
from src.invitation_content import LABELS
from src.session_sequence import FULL_SPONTANEOUS
from src.settings import EventDetails, UserSettings
from src.toolkit import LEVELS, REVIEW_SCHEMA as TOOLKIT_REVIEW_SCHEMA, validate_level

DRAFT_KEYS = ('metadata', 'brief', 'toolkit', 'event_toolkit', 'review', 'review_warning')
EVENT_WIDGETS = {
    'topic': 'topic_input', 'venue': 'venue_input', 'date': 'date_input',
    'time': 'time_input', 'concept': 'concept_input',
}
DEMO_MODE = 'Demo (works immediately, no AI)'
LOCAL_MODE = 'Local Ollama AI (free)'


def draft_from_state(state):
    return {key: state[key] for key in DRAFT_KEYS if key in state}


def toolkit_for_event(draft):
    metadata = draft.get('metadata')
    if metadata:
        for key in ('toolkit', 'event_toolkit'):
            toolkit = draft.get(key)
            if toolkit and toolkit['topic'] == metadata['topic']:
                return toolkit
    return None


def set_toolkit(state, toolkit):
    previous = toolkit_for_event(draft_from_state(state))
    if previous and previous['topic'] != toolkit['topic']:
        state['event_toolkit'] = previous
    else:
        state.pop('event_toolkit', None)
    state['toolkit'] = toolkit


def export_revision(draft):
    """Bind an archive to the content, metadata and review used to build it."""
    if 'brief' not in draft:
        return None
    return content_fingerprint({
        'metadata': draft['metadata'],
        'brief': draft['brief'],
        'toolkit': toolkit_for_event(draft),
        'review': draft.get('review'),
        'review_warning': draft.get('review_warning'),
    })


def set_event_widgets(state):
    if metadata := state.get('metadata'):
        for field, key in EVENT_WIDGETS.items():
            state[key] = metadata[field]
    elif toolkit := state.get('toolkit'):
        state['topic_input'] = toolkit['topic']


def _check_topic(topic):
    if not isinstance(topic, str) or not topic.strip() or len(topic) > 110:
        raise ValueError('Saved topic is invalid.')


def validate_draft(draft):
    """Check fields the app reads before putting a saved draft into the UI."""
    if set(draft) - set(DRAFT_KEYS) or ('brief' in draft) != ('metadata' in draft):
        raise ValueError('Saved draft has an unsupported structure.')
    if 'metadata' in draft:
        meta = draft['metadata']
        required = set(EVENT_WIDGETS) | {'mode', 'model'}
        if not isinstance(meta, dict) or not required <= meta.keys():
            raise ValueError('Saved event details are incomplete.')
        _check_topic(meta['topic'])
        EventDetails(meta['venue'], meta['date'], meta['time'])
        if meta['concept'] not in ['auto', *LABELS] or meta['mode'] not in (DEMO_MODE, LOCAL_MODE):
            raise ValueError('Saved concept or engine is unsupported.')
        if meta['mode'] == LOCAL_MODE:
            UserSettings(model=meta['model'])
        elif meta['model'] is not None:
            raise ValueError('Saved Demo run has an unexpected model.')
        workflow = meta.get('workflow')
        if workflow == FULL_SPONTANEOUS and meta['concept'] == 'spontaneous':
            from src.spontaneous_content import validate_spontaneous
            validate_spontaneous(draft['brief'])
        elif workflow is None:
            _validate(draft['brief'])
        else:
            raise ValueError('Saved session workflow is unsupported.')
    if 'review' in draft:
        if 'brief' not in draft or not Draft202012Validator(REVIEW_SCHEMA).is_valid(draft['review']):
            raise ValueError('Saved review is invalid.')
    if 'review_warning' in draft and not isinstance(draft['review_warning'], str):
        raise ValueError('Saved review warning is invalid.')
    for key in ('toolkit', 'event_toolkit'):
        if key not in draft:
            continue
        toolkit = draft[key]
        if not isinstance(toolkit, dict):
            raise ValueError('Saved Toolkit is invalid.')
        _check_topic(toolkit.get('topic'))
        levels = toolkit.get('levels')
        if not isinstance(levels, dict) or set(levels) != set(LEVELS):
            raise ValueError('Saved Toolkit is missing a level.')
        for level, material in levels.items():
            validate_level(material, level)
        if not isinstance(toolkit.get('review_status'), str):
            raise ValueError('Saved Toolkit is missing its review status.')
        if 'review' in toolkit and not Draft202012Validator(TOOLKIT_REVIEW_SCHEMA).is_valid(toolkit['review']):
            raise ValueError('Saved Toolkit review is invalid.')
        if 'review_error' in toolkit and not isinstance(toolkit['review_error'], str):
            raise ValueError('Saved Toolkit review error is invalid.')
        profile = toolkit.get('vocabulary_profile', [])
        if not isinstance(profile, list) or any(
            not isinstance(row, dict) or not isinstance(row.get('status'), str)
            or not isinstance(row.get('expression'), str) for row in profile
        ):
            raise ValueError('Saved Toolkit vocabulary profile is invalid.')
    if 'event_toolkit' in draft and (
        'metadata' not in draft or draft['event_toolkit']['topic'] != draft['metadata']['topic']
    ):
        raise ValueError('Saved event Toolkit belongs to a different topic.')
