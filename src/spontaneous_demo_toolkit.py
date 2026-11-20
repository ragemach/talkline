"""Editable Demo Toolkit for the approved What If discussion and Patch Notes cards."""
from src.toolkit_library import entry

_WORDS = {
    'a2': (
        ('rule', 'kural', 'I would change one rule at school.'),
        ('choose', 'seçmek', 'Which idea would you choose?'),
        ('try', 'denemek', 'I want to try a different way.'),
        ('safe', 'güvenli', 'Is it safe to fly to work?'),
        ('fair', 'adil', 'I think the new rule is fair.'),
        ('help', 'yardım etmek', 'Can this idea help more people?'),
        ('keep', 'korumak, sürdürmek', 'Let’s keep the old rule.'),
        ('change', 'değiştirmek', 'Can we change the plan?'),
    ),
    'b1': (
        ('habit', 'alışkanlık', 'How would the new rule change your habits?'),
        ('option', 'seçenek', 'The second option gives everyone more time.'),
        ('benefit', 'yarar', 'One benefit is that people could get home sooner.'),
        ('problem', 'sorun', 'The biggest problem is that the rule only helps some people.'),
        ('improve', 'iyileştirmek', 'A small change might improve the plan.'),
        ('effect', 'etki', 'The change could have a surprising effect on families.'),
        ('risk', 'risk', 'What risk would you accept to make life easier?'),
        ('solution', 'çözüm', 'We need a solution that works for people who walk to work.'),
    ),
    'b2_c1': (
        ('trade-off', 'bir kazanç için verilen ödün', 'There is a trade-off between speed and privacy.'),
        ('assumption', 'varsayım', 'The plan rests on the assumption that everyone has a phone.'),
        ('drawback', 'sakınca', 'The main drawback is that people have fewer choices.'),
        ('unintended', 'amaçlanmamış', 'The rule had an unintended effect on small shops.'),
        ('justify', 'gerekçelendirmek', 'How would you justify the extra cost?'),
        ('priority', 'öncelik', 'Would safety still be your priority if the change saved time?'),
        ('feasible', 'uygulanabilir', 'The idea sounds fair, but is it feasible in a crowded city?'),
        ('consequence', 'sonuç', 'Consider the long-term consequences before you choose a patch.'),
    ),
}

_PHRASES = {
    'a2': (
        ('I think', 'bence', 'I think the second patch is better.'),
        ('I’m not sure', 'emin değilim', 'I’m not sure this rule will help.'),
        ('I would choose', '... seçerdim', 'I would choose the safer rule.'),
    ),
    'b1': (
        ('It depends on', '... bağlı', 'It depends on how often the problem happens.'),
        ('In that case', 'o durumda', 'In that case, I would keep the first patch.'),
        ('The main reason is', 'asıl neden şu ki', 'The main reason is that fewer people would have to wait.'),
    ),
    'b2_c1': (
        ('The upside is', 'olumlu yanı şu ki', 'The upside is that people could travel without cars.'),
        ('In the long run', 'uzun vadede', 'In the long run, the change could save money.'),
        ('That would only work if', 'bu ancak ... olursa işe yarar', 'That would only work if everyone understood the rules.'),
    ),
}

_GRAMMAR = {
    'a2': ('Can and can’t', 'Use can for ability or possibility. Use can’t when something is impossible.',
           'can / can’t + base verb', ['We can try a different rule.', 'You can’t change the answer after the vote.']),
    'b1': ('First conditional', 'Use the first conditional for a real possibility and its likely result.',
           'If + present simple, will + base verb',
           ['If we keep this patch, people will need less time.', 'If the rule changes, I will ask for help.']),
    'b2_c1': ('Looking back at a choice', 'Use the third conditional to imagine a different result in the past.',
              'If + past perfect, would have + past participle',
              ['If we had kept the rule, we would have avoided the delay.',
               'If they had considered the risks, they would have chosen another patch.']),
}


def demo_spontaneous_toolkit(topic):
    levels = {}
    for level in _WORDS:
        title, explanation, pattern, examples = _GRAMMAR[level]
        levels[level] = {
            'vocabulary': [entry(*item) for item in _WORDS[level]],
            'phrases': [entry(*item) for item in _PHRASES[level]],
            'idioms': [],
            'mini_grammar': {'title': title, 'explanation': explanation, 'pattern': pattern,
                             'examples': list(examples)},
        }
    levels['b2_c1']['idioms'] = [
        entry('draw the line', 'sınır koymak', 'I draw the line at a rule that takes away people’s privacy.'),
        entry('the lesser of two evils', 'iki kötü seçenekten daha az kötü olanı',
              'A short delay seemed like the lesser of two evils.'),
    ]
    return {'schema_version': 1, 'topic': topic.strip(), 'model': None, 'levels': levels,
            'review_status': 'demo_sample', 'source': 'Editorial Demo for the What If sample activities.'}
