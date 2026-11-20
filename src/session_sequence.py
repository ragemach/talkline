"""Host sequence for the files produced by the current prototype."""
from src.game_export import GAME_FILENAME

PRESENTATION_FILENAME = 'TalkLine_Prototype.pptx'
FULL_PRESENTATION_FILENAME = 'TalkLine_Presentation.pptx'
FULL_SPONTANEOUS = 'spontaneous-v1'
TOOLKIT_HTML_FILENAME = 'TalkLine_Toolkit.html'
TOOLKIT_PPTX_FILENAME = 'TalkLine_Toolkit.pptx'
RATE_US_URL = (
    'https://docs.google.com/forms/d/e/'
    '1FAIpQLSdqYPKLaeRpFTol3S32Ud4tIv0GMSwvbm2rPPOeuJFREtPMig/viewform'
)


def presentation_filename(metadata):
    if metadata.get('workflow') == FULL_SPONTANEOUS:
        return FULL_PRESENTATION_FILENAME
    return PRESENTATION_FILENAME


def build_prototype_sequence(brief, *, include_toolkit=False, feedback_url=RATE_US_URL, full=False):
    """Keep activity order predictable and only link files included in the export."""
    stages = [
        {'title': 'Welcome',
         'instructions': brief['opening'] if full else 'Introduce the topic and invite everyone to take a turn.',
         'files': [('Presentation', FULL_PRESENTATION_FILENAME)] if full
                  else [('Sample presentation', PRESENTATION_FILENAME)]},
        {'title': 'Warm-up', 'instructions': 'Ask an easy question and give each person time to answer.',
         'prompts': list(brief['warmup'])},
    ]
    if include_toolkit:
        stages.extend([
            {'title': 'Toolkit', 'instructions': (
                'Start with the vocabulary, then use the shorter phrases and any idioms. '
                'Choose the A1/A2, B1 or B2/C1 material that fits the group.'),
             'files': [('Read the Toolkit', TOOLKIT_HTML_FILENAME),
                       ('Open the editable Toolkit slides',
                        FULL_PRESENTATION_FILENAME if full else TOOLKIT_PPTX_FILENAME)]},
            {'title': 'Mini grammar', 'instructions': (
                'Use the separate grammar section for the same level. '
                'Read an example, then ask learners to make a sentence of their own.'),
             'files': [('Read the grammar section in the Toolkit', TOOLKIT_HTML_FILENAME)]},
        ])
    stages.extend([
        {'title': 'Round 1: Discussion', 'instructions': (
            'Read a prompt at a level that suits your group. Give pairs a chance to '
            'talk, then invite a few people to share. The prompts below include '
            'all the discussion cards from this run.'),
         'prompts': [
             f"{card['title']} ({level.upper()}). {card[level]}"
             for card in brief['round1'] for level in ('a2', 'b2', 'c1')
         ]},
        {'title': 'Break', 'instructions': 'Take a 15–20 minute break and tell the group when to return.'
         if full else 'Set a return time that works for the group.'},
        {'title': f"Round 2: {brief['game']['title']}" if full else 'Round 2: Patch Notes', 'instructions': (
            'Read the glitch, discuss both patches and choose one together. '
            'Reveal its outcome and decide whether to keep it or reset.'),
         'files': [('Open the speaking game', GAME_FILENAME)]},
        {'title': 'Cooldown', 'instructions': 'Give each person a chance to reflect before closing.',
         'prompts': ['What idea will you remember from tonight?',
                     'Which word or phrase would you use again?']},
        {'title': 'Rate Us and thank everyone', 'instructions': (
            brief['closing'] if full else 'Thank the group for joining and invite them to leave feedback.'),
         'feedback_url': feedback_url},
    ])
    return stages
