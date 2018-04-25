from __future__ import print_function
# This module contains benchmark functions for different history suggestions algorithms.

import os
from multiprocessing import Pool
import tqdm
import Levenshtein
from idlesporklib.IdlePrehistory import Prehistory

ph = Prehistory(os.path.expanduser('~'))
history = ph.get()


# 800045
def score02(i):
    line = history[i]
    s = len(line)
    altp = 0
    for j, line2 in enumerate(history[i-1:None:-1]):
        altp += 1
        if altp >= s:
            break
        if len(line)*len(line2) < 100000:
            s = min(s, altp + Levenshtein.distance(line, line2))
        elif line == line2:
            s = min(s, altp)
    return s


# 748796
def score03(i, chars=3):
    line = history[i]
    s = len(line)
    altp = [0 for _ in range(chars)]
    for j, line2 in enumerate(history[i-1:None:-1]):
        for c in range(chars):
            if line[:c] == line2[:c]:
                altp[c] += 1
                if len(line) > c and len(line2) > c and len(line[c:])*len(line2[c:]) < 100000:
                    s = min(s, altp[c] + c + Levenshtein.distance(line[c:], line2[c:]))
                elif line == line2:
                    s = min(s, altp[c] + c)

        if min(altp) >= s:
            break

    return s


# 745968
def score2(i, chars=3):
    line = history[i]
    s = len(line)
    altp = [0 for _ in range(chars)]
    ctrlp = [0 for _ in range(chars)]

    for j, line2 in enumerate(history[i-1:None:-1]):
        if min(altp) < s:
            for c in range(chars):
                if line[:c] == line2[:c]:
                    altp[c] += 1
                    if len(line) > c and len(line2) > c and len(line[c:])*len(line2[c:]) < 100000:
                        s = min(s, altp[c] + c + Levenshtein.distance(line[c:], line2[c:]))
                    elif line == line2:
                        s = min(s, altp[c] + c)

        if min(ctrlp) < s and j > 0 and i > 0 and line2 == history[i-1]:
            line2 = history[i - j]
            for c in range(chars):
                if line[:c] == line2[:c]:
                    ctrlp[c] += 1
                    if len(line) * len(line2) < 100000:
                        s = min(s, ctrlp[c] + c + Levenshtein.distance(line[c:], line2[c:]))
                    elif line == line2:
                        s = min(s, ctrlp[c] + c)

        if min(altp) >= s and min(ctrlp) >= s:
            break
    return s


# 743067
def score3(i, chars=3):
    line = history[i]
    s = len(line)
    altp = [0 for _ in range(chars)]
    ctrlp = [0 for _ in range(chars)]

    for j, line2 in enumerate(history[i-1:None:-1]):
        if min(altp) < s:
            for c in range(chars):
                if line[:c] == line2[:c]:
                    altp[c] += 1
                    if len(line) > c and len(line2) > c and len(line[c:])*len(line2[c:]) < 100000:
                        s = min(s, altp[c] + c + Levenshtein.distance(line[c:], line2[c:]))
                    elif line == line2:
                        s = min(s, altp[c] + c)

        if (min(ctrlp) < s and j > 0 and i > 0 and
                (line2 == history[i-1] or
                     (len(line2) > 20 and len(line) > 10 and len(line2)*len(history[i-1]) < 100000 and
                              Levenshtein.distance(line, history[i-1]) < len(line2) / 2))):
            line2 = history[i - j]
            for c in range(chars):
                if line[:c] == line2[:c]:
                    ctrlp[c] += 1
                    if len(line) > c and len(line2) > c and len(line) * len(line2) < 100000:
                        s = min(s, ctrlp[c] + c + Levenshtein.distance(line[c:], line2[c:]))
                    elif line == line2:
                        s = min(s, ctrlp[c] + c)

        if min(altp) >= s and min(ctrlp) >= s:
            break
    return s


def scoreit(func):
    p = Pool(10)
    score = 0
    for s in tqdm.tqdm(p.imap_unordered(func, range(len(history))), total=len(history)):
        score += s
    p.close()
    p.join()
    return score


def main():
    print(scoreit(score3))


if __name__ == "__main__":
    main()
