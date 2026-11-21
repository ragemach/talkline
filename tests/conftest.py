import pytest


@pytest.fixture
def round_model_cards():
    scenes = (
        'A coffee shop opens before sunrise', 'Two friends share a small table',
        'The menu has no prices', 'The shop offers a free refill',
        'A neighbour brings a reusable cup', 'The last table has a broken chair',
        'A customer asks to pay in cash', 'The shop offers a quiet hour',
        'Staff share tips at the end of a shift', 'The coffee shop closes on Sundays',
    )
    questions = (
        ('When would you go there?', 'How does an early opening help you?', 'Who should cover the extra cost when there are few customers?'),
        ('Where would you sit?', 'What makes a shared table pleasant or awkward?', 'Should the café decide how long a group can stay? Why?'),
        ('How would you find out the price?', 'Why might a menu leave out prices?', 'What minimum price information should a customer be given?'),
        ('What drink would you refill?', 'Which is better, a refill or a lower first price? Why?', 'When do free refills become wasteful enough to limit?'),
        ('Which cup would you take there?', 'Why do some customers forget to bring reusable cups?', 'How could staff check the cups without holding up the queue?'),
        ('Where could you find a safe seat?', 'How should staff explain the wait to customers?', 'When is it fair to reserve seats in a busy shop?'),
        ('What would you say to the cashier?', 'Which costs matter when customers pay in cash?', 'Who is left out if a shop only accepts cards?'),
        ('When would you visit for a quiet chat?', 'Why might some customers prefer a busy hour?', 'Should staff enforce a quiet hour if it means turning a group away?'),
        ('How would you thank the staff?', 'What is an advantage of sharing tips across the team?', 'How could the staff reward extra effort while sharing tips fairly?'),
        ('Who would you meet on a Sunday?', 'Why do some customers prefer visiting on Saturday instead?', 'What should an owner consider before asking staff to work Sundays?'),
    )
    return [
        {'title': f'Coffee Shop {index}', 'scene': scene, 'a2': a2, 'b2': b2, 'c1': c1}
        for index, (scene, (a2, b2, c1)) in enumerate(zip(scenes, questions, strict=True), 1)
    ]


@pytest.fixture
def round_review():
    def response(count, revisions=None):
        revisions = revisions or {}
        checks = []
        for number in range(1, count + 1):
            quote, finding = revisions.get(number, ('', 'The shop scene and questions match the topic.'))
            checks.append({'card': number, 'quote': quote, 'finding': finding,
                           'status': 'revise' if number in revisions else 'pass'})
        return {'checks': checks}
    return response


@pytest.fixture
def round_model_batches(round_model_cards, round_review):
    return [
        (
            {'cards': [{key: card[key] for key in ('title', 'scene')} for card in batch]},
            {'cards': [{tier: card[tier] for tier in ('a2', 'b2', 'c1')} for card in batch]},
            round_review(len(batch)),
        )
        for batch in (round_model_cards[:5], round_model_cards[5:])
    ]
