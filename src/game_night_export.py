"""Render one validated Game Night activity as a standalone HTML file."""

from html import escape
import json
from pathlib import Path
from string import Template

from src.game_content import validate_game


TEMPLATE = Path(__file__).resolve().parents[1] / 'templates' / 'games' / 'game_night.html'
RULES = {
    'taboo': (
        'Keep the card screen where only the clue giver can see it.',
        'Describe the target without using the target word or any forbidden clues.',
        'Use Correct for a guess, Forbidden word for a lost card, or Skip to pass.',
        'After the timer ends, switch teams. Each correct guess scores one point.',
    ),
    'problem_solver': (
        'The active team reads the problem and prepares a solution.',
        'Present the solution to the other team and explain why it would work.',
        'The other team gives the solution one, two, or three points.',
        'Switch roles for the next problem and continue until the deck is finished.',
    ),
}


def build_game_night_game(topic, game):
    """Build one Taboo or Problem Solver game from the unbound game payload."""
    mechanic = game.get('mechanic')
    if mechanic not in RULES:
        raise ValueError('Game Night export supports Taboo and Problem Solver.')
    validate_game(game, mechanic)

    # The game receives only its own two levels. Escape '<' in script text so
    # a generated card cannot end the inert JSON script element.
    data = {
        'mechanic': mechanic,
        'decks': {level: game[level] for level in ('elementary', 'advanced')},
    }
    payload = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
    instructions = ''.join(f'<li>{escape(rule)}</li>' for rule in RULES[mechanic])
    return Template(TEMPLATE.read_text(encoding='utf-8')).substitute(
        title=escape(game['title']),
        topic=escape(topic),
        game_data=payload,
        instructions=instructions,
    )
