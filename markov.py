"""Markov chain fun for the whole family."""

import collections
import html
import logging
import random
import sys


def weighted_random_item(items, weight):
    """Returns a random item and its probability with items weighted by a weight function.
    Returns None for empty lists or non-positive weight sums.
    Don't you dare to use a non-deterministic weight function."""
    if not items:
        return None

    weight_sum = sum(weight(item) for item in items)
    if weight_sum <= 0:
        return None

    choice = random.random() * weight_sum
    for item in items:
        choice -= weight(item)
        if choice < 0:
            return item, weight(item) / weight_sum
    return items[-1], -1  # floating-point rounding error


def group_by(items, f):
    ret = collections.defaultdict(list)
    for item in items:
        ret[f(item)].append(item)
    return ret


def suffix(n, items):
    if len(items) <= n:
        return items
    else:
        return items[len(items)-n:]


END = object()


class Loc(collections.namedtuple('Loc', ['source', 'line_idx', 'idx'])):
    """A word in the text identified by its line and an index therein."""

    @property
    def line(self):
        return self.source[self.line_idx]

    @property
    def word(self):
        return self.line[self.idx]

    def words(self, n):
        return self.line[self.idx:self.idx+n]

    def match(self, words):
        """Returns True iff 'words' start at this loc."""
        return words == self.words(len(words))

    def next_word(self, start):
        """The word after 'start', assuming 'start' begins at this loc.
        Returns END at the end of the line,
        None if 'start' doesn't begin at this loc.
        """
        end_idx = self.idx + len(start)
        if self.match(start):
            return self.line[end_idx] if end_idx < len(self.line) else END

    def start_of_next_line(self):
        if self.line_idx+1 < len(self.source):
            return Loc(self.source, self.line_idx+1, 0)

class NGram(collections.namedtuple('NGram', ['words', 'count', 'loc'])):
    """A happy ngram and its metadata."""

    @staticmethod
    def from_loc(n, loc):
        return NGram((loc.line + (END,))[loc.idx:loc.idx+n], 1, loc)

    # it's a monoid!! Well, almost.
    def merge(self, other):
        # assert self.words == other.words
        if self.count > other.count:
            return NGram(self.words, self.count + other.count, self.loc)
        else:
            return NGram(other.words, self.count + other.count, other.loc)

    @staticmethod
    def empty():
        return NGram(None, 0, None)

    def _print_context(self, context_size):
        start_idx = self.loc.idx
        end_idx = self.loc.idx + len(self.words)
        parts = [html.escape(" ".join(self.loc.line[max(0, start_idx-context_size):start_idx])),
            "<b>{}</b>".format(html.escape(" ".join(self.loc.line[start_idx:end_idx]))),
            html.escape(" ".join(self.loc.line[end_idx:end_idx+context_size]))
        ]

        output = " ".join(filter(None, parts))

        if start_idx > context_size:
            output = "…" + output
        if end_idx+context_size < len(self.loc.line):
            output += "…"

        return output

    @staticmethod
    def print_context(ngrams, context_size=5):
        output = "<div>"
        p = 1.
        for ngram, next_ngram in zip(ngrams, ngrams[1:] + [None]):
            p *= ngram.count
            # if next_ngram is None or ngram.loc != next_ngram.loc:
            output += "{}\tp={:.3}<br/>\n".format(ngram._print_context(context_size), float(ngram.count))
        output += "p={:.3}, average n={:.2}".format(
                p,
                sum(len(ngram.words) for ngram in ngrams)/len(ngrams) if ngrams else 0.
        )
        return output + "</div>"

    @property
    def compl(self):
        return self.words[-1]

    @property
    def text(self):
        words = self.words
        if words[-1] is END:
            words = words[:-1]
        return " ".join(words)


class NGramTable:
    """A table for completing n-grams."""

    def __init__(self):
        self._sources = []
        self._locs = {}

    def add_source(self, lines):
        lines = [tuple(sys.intern(word) for word in line.split()) for line in lines]
        self._sources.append(lines)
        self._refresh_locs()

    def _refresh_locs(self):
        # to at least speed up the search for the first word of an n-gram,
        # save a mapping from a word to all its locs
        self._locs = group_by((Loc(source, line_idx, idx)
                               for source in self._sources
                               for line_idx, line in enumerate(source)
                               for idx, word in enumerate(line)),
                              lambda loc: loc.word)

    @property
    def num_lines(self):
        return sum(map(len, self._sources))

    def get_start_gram(self, n):
        """Returns a random n-gram starting a line."""
        loc = random.choice([Loc(source, line, 0)
                             for source in self._sources
                             for line in range(len(source))])
        return NGram.from_loc(n, loc)._replace(count=1/self.num_lines)

    def ngrams(self, words):
        """Returns all NGram objects with the specified words."""
        if words[0] in self._locs:
            for loc in self._locs[words[0]]:
                ngram = NGram.from_loc(len(words), loc)
                if ngram.words == words:
                    yield ngram

    def completions(self, start):
        """Gets all n-gram completions of the given words.
        Returns {compl: ngram}.
        """
        ret = collections.defaultdict(NGram.empty)
        for loc in self._locs[start[0]]:
            compl = loc.next_word(start)
            if compl:
                ret[compl] = ret[compl].merge(NGram.from_loc(len(start) + 1, loc))
        return ret

    def normalized_completions(self, start):
        """Gets completions with relative frequencies (accumulating to 1).
        Returns {compl: freq}.
        """
        completions = self.completions(start)
        freq_sum = sum(ngram.count for ngram in completions.values())
        if not freq_sum:
            return {}
        else:
            return {compl: ngram.count / freq_sum for (compl, ngram) in completions.items()}


class MarkovSampler:
    """A very customized markov chain sampler."""
    def __init__(self, n, table):
        self.n = n
        self._table = table

    def sample(self, start, try_end=False, disfavor=None):
        """Returns a random word that is a valid n-gram completion
        of the given word list.

        If 'try_end', prefer sentence ends.
        Weigh words in freq dict 'disfavor' negatively.
        Replace the result's 'count' field with the sample probability (eeevil).
        """
        completions = self._table.completions(start)
        if try_end and END in completions:
            return completions[END]._replace(count=1)

        res = weighted_random_item(list(completions),
                weight=lambda word: completions[word].count * (1.0 - disfavor.get(word, 0))
        )
        if not res:
            return None
        word, p = res
        return completions[word]._replace(count=p)

    def sample_many(self, start="", max_len=20):
        """Completes the given text with random n-grams from multiple gram sources.

        Incrementally samples the next word from an n-gram, avoiding
        (n+1)-gram completions and falling back to smaller n if no
        completions are found. Returns if END was chosen,
        no completion at all could be found, max_len words have been
        produced and END could be found, or 5*max_len words have been
        produced.
        """

        n = max(min(self.n, max_len-1), 2)

        start = tuple(start.split())
        if start:
            ngrams = []
            compls = ()
        else:
            ngrams = [self._table.get_start_gram(n)]
            compls = ngrams[0].words

        for i in range(5*max_len):
            text = start + compls
            disfavor = self._table.normalized_completions(suffix(n, text)) if len(text) >= n else {}
            for k in range(n-1, 0, -1):
                ngram = self.sample(suffix(k, text), try_end=(i >= max_len), disfavor=disfavor)
                if ngram is not None:
                    break

            if not ngram:
                break
            ngrams.append(ngram)
            if ngram.compl is END:
                break
            compls += (ngram.compl,)

        logging.info("max_len {}, length {}, average ngram {:.2}".format(
            max_len, len(ngrams),
            sum(len(ngram.words) for ngram in ngrams)/len(ngrams) if len(ngrams) else 0.
        ))
        return compls, ngrams

    def sample_best(self, start="", max_len=20, times=5):
        """Invokes sample_many 'times' times and returns the output with the smallest difference to max_len."""
        samples = [self.sample_many(start, max_len) for i in range(times)]
        # filter out empty completions
        samples = [sample for sample in samples if sample[1]]
        if not samples:
            text = ("LOOK BEHIND YOU A THREE-HEADED MONKEY",)
            ngrams = []
        else:
            text, ngrams = min(samples, key=lambda sample: abs(len(sample[0]) - max_len))
        if start:
            text = (start,) + text
        return " ".join(text), ngrams

    def sample_answer(self, question, max_len=20, times=5, min_prefix=2):
        question = tuple(question.split() + [END])
        for n in range(self.n+1, min_prefix-1, -1):
            ngrams = list(self._table.ngrams(question[-n:]))
            if ngrams:
                ngram = random.choice(ngrams)
                next_loc = ngram.loc.start_of_next_line()
                if next_loc:
                    next_ngram = NGram.from_loc(self.n, next_loc)
                    text, ngrams = self.sample_best(next_ngram.text, max_len, times)
                    return text, [ngram, next_ngram] + ngrams
