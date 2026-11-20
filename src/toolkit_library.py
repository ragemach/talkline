"""Small editorial seed library. Teacher approval and wider coverage are pending."""
from copy import deepcopy


def entry(expression, turkish, example):
    return dict(expression=expression, turkish=turkish, example=example)


OFFICE_BOUNDARIES = {
    'a2': {
        'vocabulary': [entry('busy', 'meşgul', 'I am busy now. Can we talk after lunch?'),
                       entry('break', 'mola', 'I take a short break after lunch.')],
        'phrases': [entry('Can we talk later?', 'Daha sonra konuşabilir miyiz?',
                          'Can we talk later? I need to finish this email.')],
        'idioms': [],
        'mini_grammar': dict(title='Can for polite requests',
            explanation='Use can to ask someone to do something. Add please to sound polite.',
            pattern='Can + subject + base verb?',
            examples=['Can you call me after lunch, please?', 'Can we talk tomorrow?'])},
    'b1': {
        'vocabulary': [entry('available', 'müsait', 'I am available for a meeting after two.'),
                       entry('interrupt', 'sözünü veya işini bölmek',
                             'Please do not interrupt me while I am on a call.')],
        'phrases': [entry('I would prefer to', '... yapmayı tercih ederim',
                          'I would prefer to discuss this during working hours.')],
        'idioms': [entry('call it a day', 'bugünlük işi bırakmak',
                         'Let’s call it a day and finish the report tomorrow.')],
        'mini_grammar': dict(title='First conditional for practical agreements',
            explanation='Use this pattern for a possible future situation and its result. Use the present simple after if.',
            pattern='If + present simple, will + base verb',
            examples=['If you send the details today, I will reply tomorrow.',
                      'If the meeting finishes early, we will take a break.'])},
    'b2_c1': {
        'vocabulary': [entry('workload', 'iş yükü', 'My workload is too heavy to accept another project this week.'),
                       entry('assertive', 'kendini açık ve kararlı biçimde ifade eden',
                             'You can be assertive about your working hours without being rude.')],
        'phrases': [entry('I can commit to', '... yapmayı taahhüt edebilirim',
                          'I can commit to finishing the report by Friday, but not by Wednesday.')],
        'idioms': [
            entry('draw the line', 'bir sınır koymak; daha fazlasını kabul etmemek',
                  'I can occasionally work late, but I draw the line at answering emails on holiday.'),
            entry('walk on eggshells', 'birini kızdırmamak için her sözüne ve davranışına çok dikkat etmek',
                  'I felt like I was walking on eggshells around my manager after I said I couldn’t take weekend calls.')],
        'mini_grammar': dict(title='Polite hypothetical boundaries',
            explanation='Use would with a conditional clause to explain what would make a request possible. This can soften a refusal while stating a clear condition.',
            pattern='I would be able to + verb + if + past simple',
            examples=['I would be able to help if we moved the deadline to Friday.',
                      'I would have more time for this if someone else handled the weekly report.'])},
}


_EXTRA_VOCABULARY = {
    'a2': [
        ('help', 'yardım etmek', 'I can help you after I finish my work.'),
        ('finish', 'bitirmek', 'I finish work at six and go home.'),
        ('late', 'geç', 'Please do not call me late at night.'),
        ('early', 'erken', 'I arrive early so I can work in a quiet office.'),
        ('quiet', 'sessiz', 'I need a quiet place for this call.'),
        ('weekend', 'hafta sonu', 'I spend the weekend with my family.')],
    'b1': [
        ('request', 'istek; talep', 'I cannot accept every request when I am busy.'),
        ('task', 'görev', 'I need to finish this task before I start another one.'),
        ('urgent', 'acil', 'Is this urgent, or can we discuss it tomorrow?'),
        ('respect', 'saygı göstermek', 'Please respect my lunch break and call me later.'),
        ('schedule', 'program; zaman çizelgesi', 'My schedule is full, but I have time on Thursday.'),
        ('refuse', 'reddetmek', 'You can refuse extra work politely when you have too much to do.')],
    'b2_c1': [
        ('prioritize', 'öncelik vermek; öncelik sırasına koymak', 'We need to prioritize existing commitments before accepting new requests.'),
        ('delegate', 'bir görevi başkasına devretmek', 'Could you delegate the routine tasks so I can focus on the deadline?'),
        ('overwhelmed', 'iş veya sorumluluklar altında bunalmış', 'I feel overwhelmed when several people expect an immediate reply.'),
        ('reasonable', 'makul', 'A reasonable deadline would allow us to finish without working all weekend.'),
        ('expectation', 'beklenti', 'There is an unspoken expectation that everyone will answer messages after work.'),
        ('compromise', 'uzlaşma', 'We reached a compromise: I will attend remotely instead of travelling on my day off.')],
}
_EXTRA_PHRASES = {
    'a2': [
        ('I need some time.', 'Biraz zamana ihtiyacım var.', 'I need some time. Can I reply after lunch?'),
        ('Is tomorrow OK?', 'Yarın uygun mu?', 'Is tomorrow OK? I am busy today.')],
    'b1': [
        ('Could we agree on', '... konusunda anlaşabilir miyiz?', 'Could we agree on a time for calls so I can plan my day?'),
        ('I already have plans.', 'Zaten başka planlarım var.', 'I already have plans, so I cannot stay late tonight.')],
    'b2_c1': [
        ('That falls outside', 'Bu, ... kapsamı dışında kalıyor', 'That falls outside my responsibilities, but I can suggest someone who can help.'),
        ('Something would have to wait.', 'Bir şeyin beklemesi gerekecek.', 'Something would have to wait. Which task should I postpone to make room for this?')],
}
for _level in OFFICE_BOUNDARIES:
    OFFICE_BOUNDARIES[_level]['vocabulary'].extend(entry(*row) for row in _EXTRA_VOCABULARY[_level])
    OFFICE_BOUNDARIES[_level]['phrases'].extend(entry(*row) for row in _EXTRA_PHRASES[_level])


def lookup_toolkit(topic):
    # Exact topic matching prevents unrelated material being presented as relevant.
    if topic.strip().casefold() != 'office boundaries':
        return None
    return deepcopy(OFFICE_BOUNDARIES)


def sample_toolkit():
    return {'schema_version': 1, 'topic': 'Office Boundaries',
            'model': None, 'levels': deepcopy(OFFICE_BOUNDARIES),
            'review_status': 'editorial_seed_teacher_review_pending',
            'source': 'Local editorial seed library; not generated by Ollama'}
