#####
# From Peter Norvig's excellent page
#   http://norvig.com/spell-correct.html
#

import re
from collections import Counter


def get_words(text):
    return re.findall(r'\w+', text.lower())


def candidates(word, all_words):
    """Generate possible spelling corrections for word."""
    return known([word], all_words) or known(edits1(word), all_words) or known(edits2(word), all_words) or [word]


def known(words, all_words):
    """The subset of `words` that appear in the dictionary of WORDS."""
    return set(w for w in words if w in all_words)


def edits1(word):
    """All edits that are one edit away from `word`."""
    letters = 'abcdefghijklmnopqrstuvwxyz'
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = [L + R[1:] for L, R in splits if R]
    transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
    replaces = [L + c + R[1:] for L, R in splits if R for c in letters]
    inserts = [L + c + R for L, R in splits for c in letters]
    return set(deletes + transposes + replaces + inserts)


def edits2(word):
    """All edits that are two edits away from `word`."""
    return (e2 for e1 in edits1(word) for e2 in edits1(e1))
