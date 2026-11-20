"""Offline level lookup from attributed CEFR-J and Octanove profiles.

Headword matching is evidence, not sense-specific CEFR certification.
"""
import csv
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'references/open_language_profiles'


@lru_cache(maxsize=1)
def vocabulary_index():
    index = {}
    for filename in ('cefrj-vocabulary-profile-1.5.csv', 'octanove-vocabulary-profile-c1c2-1.0.csv'):
        with (ROOT / filename).open(encoding='utf-8-sig', newline='') as handle:
            for row in csv.DictReader(handle):
                key = row['headword'].strip().casefold()
                index.setdefault(key, []).append({'level': row['CEFR'], 'part_of_speech': row['pos'],
                    'source': filename, 'url': 'https://github.com/openlanguageprofiles/olp-en-cefrj'})
    return index


def profile_evidence(toolkit):
    index = vocabulary_index()
    evidence = []
    for level, material in toolkit['levels'].items():
        for item in material['vocabulary']:
            matches = index.get(item['expression'].strip().casefold(), [])
            expected = {'B2', 'C1'} if level == 'b2_c1' else {'A1', 'A2'} if level == 'a2' else {'B1'}
            status = ('not_found' if not matches else
                      'level_match' if any(m['level'] in expected for m in matches) else 'check_level')
            evidence.append({'expression': item['expression'], 'teaching_level': level,
                             'status': status, 'matches': matches})
    return evidence
