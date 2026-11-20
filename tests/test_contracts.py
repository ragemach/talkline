from copy import deepcopy
import pytest
from src.contracts import validate_full_kit
from src.settings import EventDetails


@pytest.fixture
def kit():
    def game_card(i):
        return {'id':f'game-{i}','title':f'Travel problem {i}',
                'scenario':f'Your train stops at platform {i}. What will you do?',
                'choice_a':'Ask a passenger for help.','outcome_a':'You meet a helpful new friend.',
                'choice_b':'Find the station information desk.','outcome_b':'You learn about a different route.'}
    return {
        'schema_version':1,'topic':'Unexpected Travel Adventures',
        'event':{'venue':'','date':'','time':'','feedback_url':''},
        'deck':{
            'subtitle':'What could happen on your next trip?',
            'warmup':['Where would you like to go?','Who do you travel with?','What do you pack first?'],
            'toolkit':{level:[{'kind':'phrase','expression':f'Travel phrase {i}',
                              'turkish':'Örnek anlam','example':'We ended up taking the train.'}
                             for i in range(3)] for level in ('a2','b1','b2_c1')},
            'mini_grammar':{level:{'title':'Making plans','explanation':'Use going to for plans.',
                            'pattern':'be + going to + base verb',
                            'examples':['I am going to travel.','We are going to book a room.']}
                            for level in ('a2','b1','b2_c1')},
            'round1':[{'id':f'round-{i}','title':f'Journey {i}',
                       'a2':f'What do you choose in travel situation {i}?',
                       'b2':f'How would you handle travel situation {i}?',
                       'c1':f'Which compromises would shape your response to situation {i}?',
                       'speaker_notes':'Invite learners to explain their choices.'} for i in range(10)],
            'game_rules':['Read the scenario.','Discuss two choices.','Reveal one consequence.','Keep or reset.'],
            'cooldown':['What surprised you?','Which idea will you try?','Who changed your mind?'],
            'speaker_notes':{section:'Invite everyone to speak without pressure.' for section in
                             ('cover','warmup','toolkit','mini_grammar','round1_intro',
                              'break','round2_intro','how_to_play','play','cooldown','feedback')},
        },
        'game':{'mechanic':'patch_notes','title':'Travel surprises',
                'elementary':[game_card(i) for i in range(20)],
                'advanced':[game_card(i) for i in range(20,40)]},
        'invitation':{'headline':'Unexpected Travel Adventures','tagline':'Talk about your next adventure.'},
    }


def test_full_contract_accepts_complete_fixture(kit):
    # This synthetic fixture tests the contract, not creativity or real CEFR quality.
    assert validate_full_kit(kit,expected_event=EventDetails()) is kit


@pytest.mark.parametrize('damage', ['count','id','title','choice','scenario','round_duplicate','blank','example','metadata','length'])
def test_full_contract_rejects_invalid_data(kit,damage):
    if damage=='count': kit['game']['advanced'].pop()
    if damage=='id': kit['game']['advanced'][0]['id']=kit['game']['elementary'][0]['id']
    if damage=='title': kit['game']['advanced'][0]['title']=kit['game']['elementary'][0]['title']+'!'
    if damage=='choice': kit['game']['elementary'][0]['choice_b']=kit['game']['elementary'][0]['choice_a']
    if damage=='scenario': kit['game']['advanced'][0]['scenario']=kit['game']['elementary'][0]['scenario']
    if damage=='round_duplicate': kit['deck']['round1'][1]['a2']=kit['deck']['round1'][0]['a2']
    if damage=='blank': kit['deck']['round1'][0]['a2']='  '
    if damage=='example': kit['deck']['toolkit']['a2'][0]['example']='Travel'
    if damage=='metadata': kit['event']['date']='invented by model'
    if damage=='length': kit['game']['elementary'][0]['scenario']='word '*36
    with pytest.raises(ValueError): validate_full_kit(kit,expected_event=EventDetails())


def test_missing_toolkit_turkish_meaning_is_rejected(kit):
    del kit['deck']['toolkit']['a2'][0]['turkish']
    with pytest.raises(ValueError,match='turkish'): validate_full_kit(kit)


@pytest.mark.parametrize('kind',['vocabulary','phrase','idiom'])
def test_every_toolkit_kind_requires_a_complete_example(kit,kind):
    entry=kit['deck']['toolkit']['a2'][0]
    entry['kind']=kind
    entry['example']="I'd like to..."
    with pytest.raises(ValueError,match='complete usage sentence'): validate_full_kit(kit)


def test_each_grammar_level_requires_an_explanation(kit):
    del kit['deck']['mini_grammar']['b1']['explanation']
    with pytest.raises(ValueError,match='explanation'): validate_full_kit(kit)


def test_warmup_rejects_long_discussion_questions(kit):
    kit['deck']['warmup'][0]='If your journey unexpectedly changed tomorrow, which assumptions about cultural identity would you reconsider?'
    with pytest.raises(ValueError,match='very simple'): validate_full_kit(kit)
