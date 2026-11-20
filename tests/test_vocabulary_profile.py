from src.vocabulary_profile import vocabulary_index, profile_evidence


def test_local_profiles_load_both_sources():
    index = vocabulary_index()
    assert len(index) > 7000
    levels = {match['level'] for matches in index.values() for match in matches}
    assert {'A2','B1','B2','C1'} <= levels


def test_unknown_word_is_not_certified():
    data = {'levels': {'a2': {'vocabulary': [{'expression': 'nonexistentwordxyz'}]}}}
    assert profile_evidence(data)[0]['status'] == 'not_found'
