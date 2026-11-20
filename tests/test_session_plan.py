import pytest

from src.session_plan import GameSlot, SessionOutline, plan_games


def test_game_night_preserves_distinct_mechanics_and_order():
    plan = plan_games('game_night', ['taboo', 'problem_solver'])
    assert plan.games == (GameSlot('game-1', 'taboo'),
                          GameSlot('game-2', 'problem_solver'))


@pytest.mark.parametrize('mechanics', [[], ['taboo'], ['taboo'] * 3])
def test_game_night_rejects_incomplete_or_extra_games(mechanics):
    with pytest.raises(ValueError):
        plan_games('game_night', mechanics)


@pytest.mark.parametrize('concept', ['spontaneous', 'business', 'pop_culture', 'culture_exchange'])
def test_other_concepts_allow_one_or_two_games(concept):
    assert len(plan_games(concept, ['taboo']).games) == 1
    assert len(plan_games(concept, ['taboo', 'problem_solver']).games) == 2
    with pytest.raises(ValueError):
        plan_games(concept, [])
    with pytest.raises(ValueError):
        plan_games(concept, ['taboo'] * 3)


def test_invalid_concept_mechanic_and_duplicate_ids_rejected():
    with pytest.raises(ValueError):
        plan_games('unknown', ['taboo'])
    with pytest.raises(ValueError):
        plan_games('business', ['unknown'])
    with pytest.raises(ValueError):
        SessionOutline('game_night', (GameSlot('game-1', 'taboo'),
                                     GameSlot('game-1', 'problem_solver')))
