"""Business English drafts for the approved deck and Smart or Sneaky game."""
from pathlib import Path
import re

from pptx import Presentation

from src.spontaneous_content import (
    DiscussionFormat,
    discussion_game,
    generate_discussion,
    regenerate_discussion_section,
    validate_discussion,
)


_REFERENCES = Path(__file__).resolve().parents[1] / 'references'
_DECK_REFERENCE = _REFERENCES / 'user_examples' / 'Talkline Business Beyond the Office.pptx'
_GAME_REFERENCE = _REFERENCES / 'Business_Game_Smart_or_Sneaky.html'
_DISCUSSION_TITLES = (
    'First Impressions', 'A Day at Work', 'Colleagues and Friends', 'Your Dream Job',
    'Time for Yourself', 'What Makes a Good Salary?', 'Leading a Team', 'When Plans Go Wrong',
    'Workplace Values', 'The Future of Work',
)
_ANGLES = {
    'elementary': (
        'a first-day introduction', 'a shift change', 'helping a new teammate',
        'checking a price', 'a crowded shop', 'a delay', 'a missed message',
        'an online review', 'a discount sign', 'a shared calendar', 'a team lunch',
        'apologizing to a customer', 'returning a product', 'a staff recommendation',
        'an unexpected request', 'a fair rota', 'learning a task', 'a small mistake',
        'a shared goal', 'a work sample',
    ),
    'advanced': (
        'a hiring decision', 'a long-term partnership', 'how credit is allocated',
        'ownership of a mistake', 'equal access to training', 'a brand’s public promises',
        'recognizing unofficial work', 'an internal promotion', 'a supply deadline',
        'how fees are disclosed', 'selective performance data', 'customer privacy',
        'a conflict of interest', 'workload during a merger', 'regional expectations',
        'a paid sponsorship', 'compensation transparency', 'a sustainability claim',
        'an executive exception', 'automation and accountability',
    ),
}
_FORMAT = DiscussionFormat(
    'smart_or_sneaky', 'Smart or Sneaky?', (
        'Choose the level that suits your group.',
        'Read the business move aloud and hear a reason from each side.',
        'Choose Smart move or Sneaky trick to reveal a twist.',
        'Say if the new information changes your mind, then continue.',
    ), (
        'a first meeting', 'an ordinary workday', 'relationships at work', 'career ambitions',
        'private time', 'compensation', 'leadership', 'recovering from a setback',
        'a conflict about values', 'a change in working practices',
    ), _ANGLES,
    'Each scenario describes a realistic workplace or business move that people can '
    'reasonably see as clever or questionable. In choice_a give a short reason someone '
    'might call the move smart. In choice_b give a short reason someone might call it sneaky. '
    'In outcome_a and outcome_b reveal two different plausible twists specific to those '
    'perspectives. The twists should give players a reason to rethink their judgment; '
    'do not announce a correct answer or tell them how to vote.',
)
_GAME_TITLES = {
    'elementary': (
        'Only Two Left', 'One Cent Less', 'The Singer’s Shampoo', 'Buy One, Get One',
        'A Free Month', 'The Coffee Stamp Card', 'Free Delivery', 'Perfect Phone Photos',
        'The New Box', 'Cookies and Music', 'A Free Taste', 'A Note on Your Cup',
        'Staff Favourite', 'Real Customers', 'The Funny Sandwich', 'Try Them Outside',
        'Choose Your Adverts', 'Strawberry Juice', 'The Top Drink', 'We Miss You',
    ),
    'advanced': (
        'The Original Price', 'This Is Not an Ad', 'Customers Also Bought',
        'The Green Leaf', 'A Limited Edition', 'The Late Reminder', 'The Founder’s Story',
        'Five-Star Reviews', 'The Premium Label', 'Friendly Branding', 'A Flavour Vote',
        'Correcting the Advert', 'Personalised Fitness Ads', 'Making Fun of Yourself',
        'Trending Right Now', 'The Honest Review', 'An Ad-Free Experience',
        'Clinically Tested', 'A Forgotten Cart', 'Handmade-Looking Packaging',
    ),
}
_REFERENCE_CARD = re.compile(r"\{ move: '([^'\r\n]+)', twist: '([^'\r\n]+)' \}")


def _demo_round1():
    deck = Presentation(_DECK_REFERENCE)
    rounds = []
    for title, slide in zip(_DISCUSSION_TITLES, list(deck.slides)[7:17], strict=True):
        questions = {shape.shape_id: shape.text.strip()
                     for shape in slide.shapes if shape.has_text_frame}
        rounds.append({'title': title, 'a2': questions[15], 'b2': questions[21], 'c1': questions[27]})
    # The sample repeats the first card's B2 question at C1 and uses a B2 imperative on card four.
    rounds[0]['c1'] = 'How can hiring teams distinguish a strong first impression from genuine skill?'
    rounds[3]['b2'] = 'Would you choose a job you enjoy with average pay or one you dislike with excellent pay? Why?'
    return rounds


def _demo_game():
    source = _GAME_REFERENCE.read_text(encoding='utf-8-sig')
    levels = {}
    for level, titles in _GAME_TITLES.items():
        array = source.partition(f'const {level}Cards = [')[2].partition('];')[0]
        pairs = _REFERENCE_CARD.findall(array)
        # Keep the reference move and reveal. The verdict buttons add two lenses to discuss it.
        levels[level] = [
            {
                'title': title, 'scenario': move,
                'choice_a': 'It is a clever business move.',
                'choice_b': 'It puts the customer at a disadvantage.',
                'outcome_a': f'{twist} Would you still call it smart?',
                'outcome_b': f'{twist} What would make this move fair?',
            }
            for title, (move, twist) in zip(titles, pairs, strict=True)
        ]
    return discussion_game(levels, _FORMAT)


def _demo_business():
    return {
        'subtitle': 'Work, choices and the people behind them',
        'tagline': 'Discuss the choices people make at work and in business.',
        'opening': 'Welcome to TalkLine Business English. Start with a quick chat, then share how you handle everyday decisions at work or school.',
        'closing': 'Think of one work decision you discussed and one game twist that made you pause. Would you make the same choice now? Share an expression you used.',
        'warmup': ['How are you?', 'How was your day?', 'What do you do after work or school?'],
        'round1': _demo_round1(),
        'game': _demo_game(),
    }


def generate_business(topic, model=None, *, resume=None, on_progress=None):
    """Build a Business English draft from the supplied Demo or local Ollama."""
    return generate_discussion(topic, model, _FORMAT, _demo_business,
                               resume=resume, on_progress=on_progress)


def validate_business(content):
    """Check Business draft structure without changing it."""
    return validate_discussion(content, _FORMAT)


def regenerate_business_section(topic, content, section, model, feedback=''):
    """Replace only the requested Business English section."""
    return regenerate_discussion_section(topic, content, section, model, feedback,
                                         _FORMAT, _demo_business)
