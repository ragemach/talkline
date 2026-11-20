"""Mechanic-specific content boundary for the new session pipeline.

Only structural checks: acceptance does not certify CEFR or creative quality.
Model data has no IDs; binding assigns them deterministically without mutation.
"""
from copy import deepcopy
from jsonschema import Draft202012Validator
from src.contracts import text, obj, items, normalized
from src.session_plan import SessionOutline


CHOICE_CARD = obj({key: text(240) for key in (
    'title', 'scenario', 'choice_a', 'choice_b', 'outcome_a', 'outcome_b')})
CARD_SCHEMAS = {
    'taboo': obj({'word': text(70), 'forbidden': items(text(70), 3)}),
    'problem_solver': obj({'title': text(70), 'situation': text(240),
                           'challenge': text(240)}),
    'patch_notes': CHOICE_CARD,
    'smart_or_sneaky': CHOICE_CARD,
}


def game_schema(mechanic):
    if mechanic not in CARD_SCHEMAS:
        raise ValueError('Unsupported game mechanic')
    return obj({'mechanic': {'const': mechanic}, 'title': text(80),
                'rules': items(text(180), 4),
                'elementary': items(deepcopy(CARD_SCHEMAS[mechanic]), 20),
                'advanced': items(deepcopy(CARD_SCHEMAS[mechanic]), 20)})


def _distinct(values, label):
    keys = [normalized(value) for value in values]
    if any(not key for key in keys) or len(keys) != len(set(keys)):
        raise ValueError(f'{label}: empty or duplicate content')


def validate_game(data, mechanic):
    error = next(Draft202012Validator(game_schema(mechanic)).iter_errors(data), None)
    if error:
        path = '.'.join(map(str, error.absolute_path)) or 'game'
        raise ValueError(f'{path}: {error.message}')
    cards = data['elementary'] + data['advanced']
    identity = 'word' if mechanic == 'taboo' else 'title'
    _distinct([card[identity] for card in cards], identity)
    if mechanic != 'taboo':
        field = 'situation' if mechanic == 'problem_solver' else 'scenario'
        _distinct([card[field] for card in cards], field)
    for level in ('elementary', 'advanced'):
        for card in data[level]:
            if mechanic == 'taboo':
                _distinct([card['word'], *card['forbidden']], 'Taboo words')
            elif mechanic in ('patch_notes', 'smart_or_sneaky'):
                _distinct([card['choice_a'], card['choice_b']], 'choices')
                _distinct([card['outcome_a'], card['outcome_b']], 'outcomes')
            if level == 'elementary':
                fields = [value for value in card.values() if isinstance(value, str)]
                if any(len(value.split()) > 35 for value in fields):
                    raise ValueError('Elementary field exceeds 35 words')
    return data


def bind_games(outline: SessionOutline, payloads: list[dict]) -> list[dict]:
    if len(payloads) != len(outline.games):
        raise ValueError('Content count does not match planned games')
    result = []
    for slot, payload in zip(outline.games, payloads):
        validate_game(payload, slot.mechanic)
        bound = deepcopy(payload)
        bound['id'] = slot.id
        for level in ('elementary', 'advanced'):
            for index, card in enumerate(bound[level], 1):
                card['id'] = f'{slot.id}-{level}-{index}'
        result.append(bound)
    return result
