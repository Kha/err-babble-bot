"""Markov chain fun for the whole family."""
# vim:noet:sw=4:ts=4

import bisect
import collections
import logging
import random
import sys


def weighted_random_key(dictionary):
	"""Returns a random key with keys weighted by their respective value.
	Returns None for empty dicts non-positive weight sums."""
	if not dictionary:
		return None

	weight_sum = sum(dictionary.values())
	if weight_sum <= 0:
		return None

	choice = random.random() * weight_sum
	for item, weight in dictionary.items():
		choice -= weight
		if choice < 0:
			return item
	return dictionary.keys()[-1]  # floating-point rounding error


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


class NGramTable:
	"""A table for completing n-grams."""

	class Loc(collections.namedtuple('Loc', ['line', 'idx'])):
		@property
		def word(self):
			return self.line[self.idx]

		def next_word(self, start):
			end_idx = self.idx + len(start)
			if start == self.line[self.idx:end_idx]:
				return self.line[end_idx] if end_idx < len(self.line) else END

	def __init__(self, lines):
		self._lines = [tuple(sys.intern(word) for word in line.split()) for line in lines]
		self._locs = group_by((NGramTable.Loc(line, idx) for line in self._lines for idx, word in enumerate(line)),
		                      lambda loc: loc.word)

	def get_start_gram(self, n):
		return random.choice(self._lines)[:n]

	def completions(self, start):
		"""Gets all n-gram completions of the given words.
		Returns {word: total_frequency}.
		"""
		next_words = (loc.next_word(start) for loc in self._locs[start[0]])
		return collections.Counter(filter(None, next_words))

	def normalized_completions(self, start):
		"""Gets completions with relative frequencies (accumulating to 1)."""
		completions = self.completions(start)
		freq_sum = sum(completions.values())
		if not freq_sum:
			return {}
		else:
			return {compl: freq / freq_sum for (compl, freq) in completions.items()}


class MarkovSampler:
	"""A very customized markov chain sampler."""
	def __init__(self, n, lines):
		self.n = n
		self._table = NGramTable(lines)

	def sample(self, start, try_end=False, disfavor=None):
		"""Returns a random word that is a valid n-gram completion
		of the given word list.

		If 'try_end', prefer sentence ends.
		Weigh words in freq dict 'disfavor' negatively.
		n may not be larger than self.n+1.
		"""
		completions = self._table.completions(start)
		if try_end and END in completions:
			return END

		for word in disfavor:
			if word in completions:
				completions[word] *= 1.0 - disfavor[word]
		return weighted_random_key(completions)

	def sample_many(self, start="", max_len=20):
		"""Completes the given text with random words from multiple n-gram sources.

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
			completions = ()
			chain_sum = 0
		else:
			completions = self._table.get_start_gram(n)
			chain_sum = len(completions) + 1

		for i in range(5*max_len):
			text = start + completions
			disfavor = self._table.normalized_completions(suffix(n+1, text)) if len(text) >= n else {}
			for k in range(n, 1, -1):
				next_word = self.sample(suffix(k, text), try_end=(i>=max_len), disfavor=disfavor)
				if next_word is not None:
					chain_sum += k
					break

			if next_word in [None, END]:
				break
			completions += (next_word,)

		logging.info("max_len {}, length {}, average ngram {:.2}".format(max_len, len(completions), chain_sum/(len(completions)+1)))
		return completions

	def sample_best(self, start="", max_len=20, times=5):
		"""Invokes sample_many 'times' times and returns the output with the smallest difference to max_len."""
		samples = [self.sample_many(start, max_len) for i in range(times)]
		samples = [sample for sample in samples if sample]
		if not samples:
			text = ("LOOK BEHIND YOU A THREE-HEADED MONKEY",)
		else:
			text = min(samples, key=lambda text: abs(len(text) - max_len))
		if start:
			text = (start,) + text
		return " ".join(text)
