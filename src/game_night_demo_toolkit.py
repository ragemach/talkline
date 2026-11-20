"""Language for the offline Taboo and Problem Solver demonstration."""
from src.toolkit_library import entry


_WORDS = {
    'a2': (
        ('clue', 'ipucu', 'I can give you one more clue.'),
        ('guess', 'tahmin etmek', 'Can you guess the word?'),
        ('team', 'takım', 'Our team has two points.'),
        ('turn', 'sıra', 'It is your turn to speak.'),
        ('point', 'puan', 'You get one point for a correct answer.'),
        ('skip', 'atlamak', 'Let’s skip this card and try the next one.'),
        ('correct', 'doğru', 'Is that the correct answer?'),
        ('describe', 'tarif etmek', 'Describe the place without saying its name.'),
    ),
    'b1': (
        ('suggest', 'önermek', 'I suggest sharing the supplies between the two groups.'),
        ('solution', 'çözüm', 'Our solution gives both teams more time.'),
        ('practical', 'uygulanabilir', 'We want a practical way to solve the problem.'),
        ('budget', 'bütçe', 'Our budget is enough for a small room.'),
        ('prepare', 'hazırlamak', 'We need a minute to prepare our idea.'),
        ('deadline', 'son tarih', 'Can we finish the plan before the deadline?'),
        ('convince', 'ikna etmek', 'How will you convince them to try your idea?'),
        ('alternative', 'başka bir seçenek', 'As an alternative, we could meet outside.'),
    ),
    'b2_c1': (
        ('constraint', 'kısıt', 'The main constraint is the short time we have.'),
        ('feasible', 'uygulanabilir', 'Is this plan feasible on a limited budget?'),
        ('trade-off', 'bir kazanç için verilen ödün', 'There is a trade-off between speed and accuracy.'),
        ('viable', 'işlerliği olan', 'The library is still a viable meeting place.'),
        ('justify', 'gerekçelendirmek', 'Can you justify spending more on transport?'),
        ('prioritise', 'öncelik vermek', 'We should prioritise seats for people who need them.'),
        ('drawback', 'sakınca', 'The main drawback is the extra travel time.'),
        ('consensus', 'görüş birliği', 'The team reached a consensus after hearing both ideas.'),
    ),
}

_PHRASES = {
    'a2': (
        ('It looks like', '... gibi görünüyor', 'It looks like a small guitar.'),
        ('You use it to', 'bunu ... için kullanırsın', 'You use it to open a bottle.'),
        ('Is it a ...?', 'Bu bir ... mı?', 'Is it a ticket?'),
    ),
    'b1': (
        ('We could try', '... deneyebiliriz', 'We could try asking another team for help.'),
        ('The problem is that', 'sorun şu ki', 'The problem is that we only have one room.'),
        ('One reason is that', 'nedenlerden biri şu ki', 'One reason is that the later bus costs less.'),
    ),
    'b2_c1': (
        ('provided that', '... olması koşuluyla', 'The plan works provided that we can borrow a car.'),
        ('The main benefit would be', 'başlıca faydası ... olurdu', 'The main benefit would be a shorter wait.'),
        ('A fair compromise would be', 'adil bir uzlaşma ... olurdu', 'A fair compromise would be to split the cost.'),
    ),
}

_GRAMMAR = {
    'a2': ('Describing a use', 'Use an infinitive to say what an object is used for.',
           'use + object + to + base verb', ('You use a key to open a door.', 'We use a timer to count the seconds.')),
    'b1': ('Making suggestions', 'Use could when you want to offer an idea for the group to consider.',
           'subject + could + base verb', ('We could borrow an extra table.', 'Our team could share a ride.')),
    'b2_c1': ('Stating a condition', 'Use provided that to state the condition a plan depends on.',
              'main clause + provided that + clause',
              ('We can start early provided that everyone agrees.', 'The venue will work provided that it has enough seats.')),
}


def demo_game_night_toolkit(topic):
    levels = {}
    for level, words in _WORDS.items():
        title, explanation, pattern, examples = _GRAMMAR[level]
        levels[level] = {
            'vocabulary': [entry(*item) for item in words],
            'phrases': [entry(*item) for item in _PHRASES[level]],
            'idioms': [],
            'mini_grammar': {'title': title, 'explanation': explanation, 'pattern': pattern,
                             'examples': list(examples)},
        }
    levels['b2_c1']['idioms'].append(
        entry('think on your feet', 'hızlı düşünüp anında çözüm bulmak',
              'When the timer ran out, we had to think on our feet.'),
    )
    return {'schema_version': 1, 'topic': topic.strip(), 'model': None, 'levels': levels,
            'review_status': 'demo_sample', 'source': 'Editorial Game Night Demo.'}
