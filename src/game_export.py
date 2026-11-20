"""Export standalone, host-led discussion games with two choices per card."""
import json
from pathlib import Path
from html import escape
from string import Template

from src.game_content import validate_game

GAME_FILENAME = 'TalkLine_Game.html'
TEMPLATE = Path(__file__).resolve().parents[1] / 'templates' / 'games' / 'patch_notes.html'
CARD_FIELDS = ('title', 'glitch', 'patch_a', 'patch_b', 'consequence_a', 'consequence_b')
CHOICE_FIELDS = ('title', 'scenario', 'choice_a', 'choice_b', 'outcome_a', 'outcome_b')


def _render_game(topic, title, data, rules=(), *, mechanic='patch_notes'):
    # Prevent model text from terminating the inert JSON script element.
    payload = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
    instructions = '<ol>' + ''.join(f'<li>{escape(rule)}</li>' for rule in rules) + '</ol>' if rules else ''
    if mechanic == 'smart_or_sneaky':
        intro = 'Is this move smart or sneaky? Hear a reason from each side before revealing the twist.'
        closing = 'Which move changed your mind, and why?'
    else:
        intro = 'Discuss the glitch, choose a patch together, then decide whether to keep it.'
        closing = 'Which patch would you actually use, and why?'
    return Template(TEMPLATE.read_text(encoding='utf-8')).substitute(
        topic=escape(topic), title=escape(title), cards=payload, instructions=instructions,
        mechanic=mechanic, intro=intro, closing=closing,
    )


def build_patch_game(topic, cards):
    if not cards or any(not isinstance(card.get(key), str) or not card[key].strip()
                        for card in cards for key in CARD_FIELDS):
        raise ValueError('Patch Notes needs complete speaking cards.')
    data = [{key: card[key] for key in CARD_FIELDS} for card in cards]
    return _render_game(topic, 'Patch Notes', data)


def _build_leveled_choice_game(topic, game, mechanic):
    validate_game(game, mechanic)
    decks = {
        level: [{target: card[source] for target, source in zip(CARD_FIELDS, CHOICE_FIELDS)}
                for card in game[level]]
        for level in ('elementary', 'advanced')
    }
    return _render_game(topic, game['title'], decks, game['rules'], mechanic=mechanic)


def build_leveled_patch_game(topic, game):
    """Build an offline game from the raw Patch Notes payload for both levels."""
    return _build_leveled_choice_game(topic, game, 'patch_notes')


def build_smart_or_sneaky_game(topic, game):
    """Build a verdict game with no scoring from the raw Smart or Sneaky payload."""
    return _build_leveled_choice_game(topic, game, 'smart_or_sneaky')
