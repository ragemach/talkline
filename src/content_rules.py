"""Shared content requirements clarified by the owner, not inferred from old samples."""
import re

# Characters available for the scene and its question together on a discussion slide.
ROUND_CARD_TEXT_LIMITS = {'a2': 160, 'b2': 175, 'c1': 175}

WARMUP_GUIDANCE = (
    'Warm-ups must be VERY simple, polite everyday check-ins or preferences, accessible to A2. '
    'For example: How are you? How was your day? How was your week? Do you like watching movies? '
    'Use one short question per item, at most 12 words. A short answer is enough. '
    'Avoid hypotheticals, abstract discussion, debate, embarrassment, confessions or sensitive '
    'personal disclosures. Warm-ups need not closely match the topic. Save depth for Round 1. '
)


def validate_warmups(questions):
    for index,question in enumerate(questions):
        if len(re.findall(r"\b[\w]+(?:['’][\w]+)*\b",question))>12 or question.count('?')>1:
            raise ValueError(f'warmup.{index}: use one very simple question of at most 12 words.')
    # Length is a mechanical safeguard, not evidence of CEFR or politeness.


def validate_usage_example(value,path):
    if '...' in value or '…' in value or len(value.split())<2 or not value.rstrip().endswith(('.','!','?','”','"')):
        raise ValueError(f'{path}: provide a complete usage sentence, not an unfinished phrase.')
