"""Version 1 content contract for the future full kit, independent of any layout.

The current UI still exports the small prototype. Full-kit renderers will consume this
contract in M2/M3; accepting a contract is not evidence of semantic or visual quality.
"""
import re
from jsonschema import Draft202012Validator
from src.settings import EventDetails
from src.content_rules import validate_warmups, validate_usage_example


def text(maximum=240):
    return {'type':'string','minLength':1,'maxLength':maximum,'pattern':r'\S'}


def obj(properties):
    return {'type':'object','properties':properties,'required':list(properties),
            'additionalProperties':False}


def items(schema, count):
    return {'type':'array','items':schema,'minItems':count,'maxItems':count}


TOOLKIT_ENTRY = obj({'kind':{'enum':['vocabulary','phrase','idiom']},
                     'expression':text(70),'turkish':text(120),'example':text(180)})
GRAMMAR_ENTRY = obj({'title':text(70),'explanation':text(),'pattern':text(150),
                     'examples':items(text(180),2)})
ROUND_CARD = obj({'id':text(30),'title':text(60),'a2':text(180),'b2':text(),
                  'c1':text(),'speaker_notes':text(600)})
GAME_CARD = obj({'id':text(30),'title':text(60),'scenario':text(),
                 'choice_a':text(140),'outcome_a':text(),
                 'choice_b':text(140),'outcome_b':text()})
EVENT_SCHEMA = obj({field:{'type':'string','maxLength':60} for field in ('venue','date','time')}
                   | {'feedback_url':{'type':'string','maxLength':500}})

FULL_KIT_SCHEMA = obj({
    'schema_version':{'const':1,'type':'integer'},
    'topic':text(110),
    'event':EVENT_SCHEMA,
    'deck':obj({
        'subtitle':text(150),
        'warmup':items(text(160),3),
        'toolkit':obj({level:{'type':'array','items':TOOLKIT_ENTRY,'minItems':3,'maxItems':6}
                       for level in ('a2','b1','b2_c1')}),
        'mini_grammar':obj({level:GRAMMAR_ENTRY for level in ('a2','b1','b2_c1')}),
        'round1':items(ROUND_CARD,10),
        'game_rules':items(text(160),4),
        'cooldown':items(text(160),3),
        'speaker_notes':obj({section:text(600) for section in
                             ('cover','warmup','toolkit','mini_grammar','round1_intro',
                              'break','round2_intro','how_to_play','play','cooldown','feedback')}),
    }),
    'game':obj({
        'mechanic':{'enum':['patch_notes','smart_or_sneaky']},
        'title':text(80),
        'elementary':items(GAME_CARD,20),
        'advanced':items(GAME_CARD,20),
    }),
    'invitation':obj({'headline':text(110),'tagline':text(100)}),
})


def normalized(value):
    return ' '.join(re.findall(r'\w+',value.casefold()))


def _distinct(values, path):
    normalized_values = [normalized(value) for value in values]
    if len(set(normalized_values)) != len(normalized_values):
        raise ValueError(f'{path}: duplicate content.')


def validate_full_kit(data, *, expected_event=None):
    error = next(Draft202012Validator(FULL_KIT_SCHEMA).iter_errors(data),None)
    if error:
        path='.'.join(map(str,error.absolute_path)) or 'kit'
        raise ValueError(f'{path}: {error.message}')
    event=EventDetails(**data['event'])
    if expected_event is not None and event != expected_event:
        raise ValueError('event: generated details differ from the explicit user metadata.')
    _distinct(data['deck']['warmup'],'deck.warmup')
    validate_warmups(data['deck']['warmup'])
    _distinct(data['deck']['cooldown'],'deck.cooldown')
    _distinct([card['title'] for card in data['deck']['round1']],'deck.round1 titles')
    for level in ('a2','b2','c1'):
        _distinct([card[level] for card in data['deck']['round1']],f'deck.round1.{level} prompts')
    for level, entries in data['deck']['toolkit'].items():
        _distinct([entry['expression'] for entry in entries],f'toolkit.{level}')
        for entry in entries:
            validate_usage_example(entry['example'],f'toolkit.{level}.{entry["expression"]}')
    for level,grammar in data['deck']['mini_grammar'].items():
        for example in grammar['examples']:
            validate_usage_example(example,f'mini_grammar.{level}')
    all_cards=data['deck']['round1']+data['game']['elementary']+data['game']['advanced']
    _distinct([card['id'] for card in all_cards],'card IDs across kit')
    game_cards=data['game']['elementary']+data['game']['advanced']
    _distinct([card['title'] for card in game_cards],'game titles')
    _distinct([card['scenario'] for card in game_cards],'game scenarios')
    for level in ('elementary','advanced'):
        for card in data['game'][level]:
            _distinct([card['choice_a'],card['choice_b']],f"{card['id']} choices")
            _distinct([card['outcome_a'],card['outcome_b']],f"{card['id']} outcomes")
            if level == 'elementary':
                for key in ('scenario','choice_a','choice_b','outcome_a','outcome_b'):
                    if len(card[key].split())>35:
                        raise ValueError(f"{card['id']}.{key}: Elementary text exceeds 35 words.")
    return data
