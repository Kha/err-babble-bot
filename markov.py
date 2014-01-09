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


def init(items):
	return items[:len(items)-1]


def suffix(n, items):
	if len(items) <= n:
		return items
	else:
		return items[len(items)-n:]


START = "" # For sorting. I'm so sorry.
END = object()


def ngrams(n, words):
	"""Yields all n-grams of the word list.

	Starts with (START, ..., START, words[0],) and continues until
	(words[-n+1], ..., words[-1], END). To make the function messier,
	additionally yields n-grams (..., words[i], END) if
	words[i] is deemed the end of a sentence.
	"""
	ngram = n * (START,)
	for word in words + [END]:
		ngram = ngram[1:] + (word,)
		yield ngram
		if word is not END and word[-1] in ['.', '!', '?']:
			yield ngram[1:] + (END,)


def pad_left(tup, width, pad_item):
	return (width-len(tup)) * (pad_item,) + tup


class NGramTable:
	"""A table for completing n-grams (where n <= max_n)."""
	def __init__(self, max_n, lines):
		assert max_n >= 2
		self.max_n = max_n

		# compute frequencies
		data = collections.Counter(ngram
				for line in lines
				for ngram in ngrams(max_n, [sys.intern(word) for word in line.split()])
		)

		# change dict into sorted list for binary search
		self._data = sorted(data.items(), key=lambda item: init(item[0]))

	def completions(self, n, start):
		"""Gets all n-gram completions of the given words.
		n may not be greater than max_n.
		Returns {word: total_frequency}.
		"""
		assert n <= self.max_n
		start = suffix(n-1, start)

		if len(start) < n-1:
			# pad from left, then do a max_n completion
			start = pad_left(start, self.max_n-1, START)
			n = self.max_n-1

		ret = collections.defaultdict(lambda: 0)
		data = self._data
		# lookup all n-grams with start as prefix
		i = bisect.bisect_left(data, (start,))
		while i < len(data) and data[i][0][:len(start)] == start:
			ret[data[i][0][len(start)]] += data[i][1]
			i += 1
		return ret

	def normalized_completions(self, n, start):
		"""Gets completions with relative frequencies (accumulating to 1)."""
		completions = self.completions(n, start)
		freq_sum = sum(completions.values())
		if not freq_sum:
			return {}
		else:
			return {compl: freq / freq_sum for (compl, freq) in completions.items()}


class MarkovSampler:
	"""A very customized markov chain sampler."""
	def __init__(self, n, lines):
		self.n = n
		self._table = NGramTable(n+1, lines)

	def sample(self, n, start, try_end=False, disfavor=None):
		"""Returns a random word that is a valid n-gram completion
		of the given word list.

		If 'try_end', prefer sentence ends.
		Weigh words in freq dict 'disfavor' negatively.
		n may not be larger than self.n+1.
		"""
		completions = self._table.completions(n, start)
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
		completions = ()
		chain_sum = 0
		for i in range(5*max_len):
			text = start + completions
			disfavor = self._table.normalized_completions(n+1, text) if len(text) >= n else {}
			for k in range(n, 1, -1):
				next_word = self.sample(k, text, try_end=(i>=max_len), disfavor=disfavor)
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
