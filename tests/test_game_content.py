from copy import deepcopy
import pytest
from src.game_content import bind_games, validate_game
from src.session_plan import plan_games


def fixture_game(mechanic):
    def card(i):
        if mechanic == 'taboo':
            return {'word': f'word {i}', 'forbidden': ['first', 'second', 'third']}
        if mechanic == 'problem_solver':
            return {'title': f'problem {i}', 'situation': f'situation {i}',
                    'challenge': 'Find a solution together.'}
        return {'title': f'title {i}', 'scenario': f'scenario {i}',
                'choice_a': 'Stay here.', 'choice_b': 'Go outside.',
                'outcome_a': 'You wait.', 'outcome_b': 'You leave.'}
    return {'mechanic': mechanic, 'title': 'Synthetic validation fixture',
            'rules': ['Explain.', 'Discuss.', 'Listen.', 'Continue.'],
            'elementary': [card(i) for i in range(20)],
            'advanced': [card(i) for i in range(20, 40)]}


@pytest.mark.parametrize('mechanic', ['taboo', 'problem_solver', 'patch_notes', 'smart_or_sneaky'])
def test_binding_preserves_payload_and_assigns_unique_ids(mechanic):
    game = fixture_game(mechanic)
    original = deepcopy(game)
    bound = bind_games(plan_games('business', [mechanic]), [game])[0]
    assert game == original
    assert len({c['id'] for level in ('elementary', 'advanced') for c in bound[level]}) == 40


def test_two_distinct_games_bind_and_reject_swapped_content():
    plan = plan_games('game_night', ['taboo', 'problem_solver'])
    games = [fixture_game('taboo'), fixture_game('problem_solver')]
    bound = bind_games(plan, games)
    assert bound[1]['elementary'][0]['id'] == 'game-2-elementary-1'
    with pytest.raises(ValueError):
        bind_games(plan, games[::-1])
    with pytest.raises(ValueError):
        bind_games(plan, games[:1])


@pytest.mark.parametrize('fault', ['missing', 'extra', 'duplicate', 'forbidden', 'model_id'])
def test_taboo_invalid_content_rejected(fault):
    game = fixture_game('taboo')
    if fault == 'missing':
        game['elementary'].pop()
    elif fault == 'extra':
        game['advanced'].append(deepcopy(game['advanced'][0]))
    elif fault == 'duplicate':
        game['advanced'][0]['word'] = ' WORD  0! '
    elif fault == 'forbidden':
        game['elementary'][0]['forbidden'][0] = 'word 0'
    else:
        game['elementary'][0]['id'] = 'invented'
    with pytest.raises(ValueError):
        validate_game(game, 'taboo')


def test_choice_and_problem_shapes_are_not_interchangeable():
    game = fixture_game('problem_solver')
    game['elementary'][0]['choice_a'] = 'Unwanted choice'
    with pytest.raises(ValueError):
        validate_game(game, 'problem_solver')
    game = fixture_game('patch_notes')
    game['elementary'][0]['choice_b'] = 'stay here!'
    with pytest.raises(ValueError):
        validate_game(game, 'patch_notes')
