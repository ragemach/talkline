"""Session activity planning foundation; not a full generated-content contract."""
from dataclasses import dataclass


CONCEPTS = frozenset(('spontaneous', 'business', 'pop_culture',
                      'culture_exchange', 'game_night'))
MECHANICS = frozenset(('patch_notes', 'smart_or_sneaky', 'taboo', 'problem_solver'))


@dataclass(frozen=True)
class GameSlot:
    id: str
    mechanic: str


@dataclass(frozen=True)
class SessionOutline:
    concept: str
    games: tuple[GameSlot, ...]

    def __post_init__(self):
        if self.concept not in CONCEPTS:
            raise ValueError('Unknown session concept')
        if not isinstance(self.games, tuple):
            raise ValueError('Games must be an immutable tuple')
        expected = (2,) if self.concept == 'game_night' else (1, 2)
        if len(self.games) not in expected:
            raise ValueError('Game Night requires two games; other sessions need one or two')
        for index, game in enumerate(self.games, 1):
            if not isinstance(game, GameSlot) or game.id != f'game-{index}':
                raise ValueError('Game identifiers must match their ordered slots')
            if game.mechanic not in MECHANICS:
                raise ValueError('Unsupported game mechanic')


def plan_games(concept: str, mechanics: list[str]) -> SessionOutline:
    """Assign stable IDs in code; never take game identifiers from model output."""
    return SessionOutline(concept, tuple(
        GameSlot(f'game-{index}', mechanic)
        for index, mechanic in enumerate(mechanics, 1)
    ))
