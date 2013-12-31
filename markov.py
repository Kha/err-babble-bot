# encoding=utf-8
# vim:noet:sw=4:ts=4

import bisect
import collections
import logging
import random
import sys


def weighted_random_key(dictionary):
	if not dictionary:
		return None

	weight_sum = sum(dictionary.values())
	if not weight_sum:
		return None

	choice = random.random() * weight_sum
	for item, weight in dictionary.items():
		choice -= weight
		if choice < 0:
			return item
	return item[-1]  # floating-point rounding error


def suffix(n, items):
	if len(items) <= n:
		return items
	else:
		return items[len(items)-n:]


END = "$$$"


def ngrams(n, words):
	"""Yields all n-grams of the word list.

	Starts with (words[0],) and continues until
	(words[-n+1], ..., words[-1], END). To make the function messier,
	additionally yields n-grams (..., words[i], END) if
	words[i] is deemed the end of a sentence.
	"""
	ngram = ()
	for word in words + [END]:
		ngram = suffix(n, ngram + (word,))
		yield ngram
		if word is not END and word[-1] in ['.', '!', '?']:
			yield suffix(n, ngram + (END,))


def group_by(a, f):
	ret = collections.defaultdict(list)
	for x in a:
		ret[f(x)].append(x)
	return ret


class NGramTable:
	"""A table for completing n-grams (where n <= max_n)."""
	def __init__(self, max_n, lines):
		assert max_n >= 2
		self._max_n = max_n

		# compute frequencies
		data = collections.Counter(ngram
				for line in lines
				for ngram in ngrams(max_n, list(map(sys.intern, line.split())))
		)

		# Change dict into sorted list for binary search.
		# First group n-grams by length, which is < n
		# for the first (n-1) grams in a line.
		self._data = {length: sorted(freqs)
				for (length, freqs) in group_by(data.items(),
					lambda freq: len(freq[0])
				).items()}

	def completions(self, n, start):
		"""Gets all n-gram completions of the given words.
		n may not be greater than max_n.
		Returns {word: total_frequency}.
		"""
		start = suffix(n-1, start)
		if len(start) < n-1:
			# Completing an n-gram at a line start,
			# get all n-grams with exactly that length.
			lengths = (len(start)+1,)
		else:
			# else get all grams with length >= n, which
			# together contain all n-grams
			lengths = range(n,self._max_n+1)

		ret = collections.defaultdict(lambda: 0)
		for length in lengths:
			data = self._data[length]
			# get all grams with start as prefix
			i = bisect.bisect_left(data, (start, 0))
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
			for k in range(n,1,-1):
				next_word = self.sample(k, text, try_end=(i>=max_len), disfavor=disfavor)
				if next_word is not None:
					chain_sum += k
					break

			if next_word in [None, END]:
				break
			completions += (next_word,)

		logging.info("max_len {}, length {}, average ngram {:.2}".format(max_len, len(completions), chain_sum/(len(completions)+1)))
		return " ".join(start + completions)
