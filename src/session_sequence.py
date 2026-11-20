"""Keep the preview, host guide and export links in the same meeting order."""
from src.game_export import GAME_FILENAME
from src.game_night_export import RULES

PRESENTATION_FILENAME = 'TalkLine_Prototype.pptx'
FULL_PRESENTATION_FILENAME = 'TalkLine_Presentation.pptx'
FULL_SPONTANEOUS = 'spontaneous-v1'
FULL_GAME_NIGHT = 'game-night-v1'
FULL_BUSINESS = 'business-v1'
FULL_WORKFLOWS = {
    'spontaneous': FULL_SPONTANEOUS, 'game_night': FULL_GAME_NIGHT, 'business': FULL_BUSINESS,
}
GAME_NIGHT_FILES = ('TalkLine_Taboo.html', 'TalkLine_Problem_Solver.html')
BUSINESS_GAME_FILE = 'TalkLine_Smart_or_Sneaky.html'
TOOLKIT_HTML_FILENAME = 'TalkLine_Toolkit.html'
TOOLKIT_PPTX_FILENAME = 'TalkLine_Toolkit.pptx'
RATE_US_URL = (
    'https://docs.google.com/forms/d/e/'
    '1FAIpQLSdqYPKLaeRpFTol3S32Ud4tIv0GMSwvbm2rPPOeuJFREtPMig/viewform'
)


def presentation_filename(metadata):
    if metadata.get('workflow') in FULL_WORKFLOWS.values():
        return FULL_PRESENTATION_FILENAME
    return PRESENTATION_FILENAME


def game_filenames(metadata):
    return {
        FULL_GAME_NIGHT: GAME_NIGHT_FILES, FULL_BUSINESS: (BUSINESS_GAME_FILE,),
    }.get(metadata.get('workflow'), (GAME_FILENAME,))


def _opening_stages(brief, include_toolkit, full):
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
    return stages


def _closing_stages(brief, full, feedback_url):
    return [
        {'title': 'Cooldown', 'instructions': 'Give each person a chance to reflect before closing.',
         'prompts': ['What idea will you remember from tonight?',
                     'Which word or phrase would you use again?']},
        {'title': 'Rate Us and thank everyone', 'instructions': (
            brief['closing'] if full else 'Thank the group for joining and invite them to leave feedback.'),
         'feedback_url': feedback_url},
    ]


def build_prototype_sequence(brief, *, include_toolkit=False, feedback_url=RATE_US_URL, full=False):
    stages = _opening_stages(brief, include_toolkit, full)
    game = brief['game'] if full else None
    smart_or_sneaky = game is not None and game['mechanic'] == 'smart_or_sneaky'
    break_instructions = 'Set a return time that works for the group.'
    if full:
        break_instructions = ('Take a 20-minute break and tell the group when to return.' if smart_or_sneaky
                              else 'Take a 15–20 minute break and tell the group when to return.')
    stages.extend([
        {'title': 'Round 1: Discussion', 'instructions': (
            'Read a prompt at a level that suits your group. Give pairs a chance to '
            'talk, then invite a few people to share. The prompts below include '
            'all the discussion cards from this run.'),
         'prompts': [
             f"{card['title']} ({level.upper()}). {card[level]}"
             for card in brief['round1'] for level in ('a2', 'b2', 'c1')
         ]},
        {'title': 'Break', 'instructions': break_instructions},
        {'title': f"Round 2: {game['title']}" if full else 'Round 2: Patch Notes',
         'instructions': ' '.join(game['rules']) if full else (
             'Read the glitch, discuss both patches and choose one together. '
             'Reveal its outcome and decide whether to keep it or reset.'),
         'files': [('Open the speaking game', BUSINESS_GAME_FILE if smart_or_sneaky else GAME_FILENAME)]},
    ])
    return stages + _closing_stages(brief, full, feedback_url)


def build_session_sequence(metadata, brief, *, include_toolkit, feedback_url=RATE_US_URL):
    workflow = metadata.get('workflow')
    if workflow != FULL_GAME_NIGHT:
        return build_prototype_sequence(brief, include_toolkit=include_toolkit,
                                        feedback_url=feedback_url, full=workflow in FULL_WORKFLOWS.values())
    stages = _opening_stages(brief, include_toolkit, full=True)
    for number, (game, filename) in enumerate(zip(brief['games'], GAME_NIGHT_FILES, strict=True), 1):
        stages.append({'title': f"Round {number}: {game['title']}",
                       'instructions': ' '.join(RULES[game['mechanic']]),
                       'files': [(f"Play {game['title']}", filename)]})
        if number == 1:
            stages.append({'title': 'Break', 'instructions': 'Take a 20-minute break and announce when to return.'})
    return stages + _closing_stages(brief, full=True, feedback_url=feedback_url)
