# encoding=utf-8
# vim:noet:sw=4:ts=4

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


END = object()


def ngrams(n, words):
	"""Yields all n-grams of the word list.

	Starts with (words[0],) and continues until
	(..., words[-1], END). To make the function messier,
	additionally yields n-grams (..., words[i], END) if
	words[i] is deemed the end of a sentence.
	"""
	ngram = ()
	for word in words + [END]:
		ngram = suffix(n, ngram + (word,))
		yield ngram
		if word is not END and word[-1] in ['.', '!', '?']:
			yield suffix(n, ngram + (END,))


class MarkovChain:
	"""A frequency table of n-grams.

	n-grams are represented as k-tuples, where k may be less
	than n for the text's first grams, and the last item may
	be END to signify a sentence end.
	"""

	def __init__(self, n):
		assert(n >= 2)
		self._n = n
		# {(n-1)-gram: next-word: total-frequency}
		self._data = collections.defaultdict(lambda: 0)

	def add(self, text):
		words = list(map(sys.intern, text.split()))
		for ngram in ngrams(self._n, words):
			self._data[ngram] += 1

	def completions(self, words, n=None):
		"""Returns a dict {word: frequency}, where 'word' is a
		valid n-gram completion of the given word list.

		n may be any integer not larger than the n passed to the
		constructor.
		"""
		if n is None:
			n = self._n
		assert n <= self._n

		words = suffix(n-1, words)
		n = min(n, len(words)+1)
		ret = {ngram[n-1]: self._data[ngram] for ngram in self._data
				if len(ngram) >= n and ngram[:n-1] == words}
		freq_sum = sum(ret.values())
		return {word: ret[word] / freq_sum for word in ret}

	def sample(self, words, try_end=False, disfavor=None, n=None):
		"""Returns a random word that is a valid n-gram completion
		of the given word list.

		If 'try_end', prefer sentence ends.
		Weigh words in freq dict 'disfavor' negatively.
		n may be any integer not larger than the n passed to the
		constructor.
		"""
		completions = self.completions(words, n)
		if try_end and END in completions:
			return END

		for word in disfavor:
			if word in completions:
				completions[word] *= 1.0 - disfavor[word]
		return weighted_random_key(completions)


class MarkovChains:
	"""A collection of MarkovChain objects of length 2...n+1 for
	fully abusing Andrey Markov's works for recreational uses.
	"""

	def __init__(self, n):
		self._chain = MarkovChain(n+1)
		self._n = n

	def add(self, text):
		self._chain.add(text)

	def sample(self, start="", max_len=20):
		"""Completes the given text with random words from the Markov chains.

		Incrementally samples the next word from an n-gram, avoiding
		(n+1)-gram completions and falling back to smaller n if no
		completions are found. Returns if END was chosen,
		no completion at all could be found, max_len words have been
		produced and END could be found, or 5*max_len words have been
		produced.
		"""

		n = max(min(self._n, max_len-1), 2)

		start = tuple(start.split())
		completions = ()
		chain_sum = 0
		for i in range(5*max_len):
			text = start + completions
			disfavor = self._chain.completions(text, n+1) if len(text) >= n else {}
			for k in range(n,1,-1):
				next_word = self._chain.sample(text, try_end=(i>=max_len), disfavor=disfavor, n=k)
				if next_word is not None:
					chain_sum += k
					break


			if next_word in [None, END]:
				break
			completions += (next_word,)

		logging.info("max_len {}, length {}, average ngram {:.2}".format(max_len, len(completions), chain_sum/(len(completions)+1)))
		return " ".join(start + completions)
