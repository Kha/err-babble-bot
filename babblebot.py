# encoding=utf-8
# vim:noet:sw=4:ts=4

import logging
import random
import urllib.request

from markov import MarkovSampler

from errbot import BotPlugin, botcmd


class BabbleBot(BotPlugin):
	def activate(self):
		super().activate()
		if 'sources' not in self:
			self['sources'] = ['http://www.gutenberg.org/cache/epub/2229/pg2229.txt']
		for error in self.reload():
			logging.warn(error)

	def configure(self, configuration):
		super().configure(configuration)
		if self.config is None:
			self.config = self.get_configuration_template()

	def get_configuration_template(self):
		return {'NGRAM_N': 3}

	def check_configuration(self, configuration):
		super().check_configuration(configuration)

	def reload(self):
		lines = []
		for source in self['sources']:
			try:
				f = urllib.request.urlopen(source)
			except:
				yield "Couldn't retrieve babble source: " + source
				continue
			with f:
				lines += [line.decode() for line in f.readlines()]
		self.model = MarkovSampler(self.config['NGRAM_N'], lines)

	@botcmd
	def babble_reload(self, mess, args):
		"""Reloads all babble sources."""
		yield 'Reloading...'
		for error in self.reload():
			yield error
		yield 'Done.'

	@botcmd
	def babble(self, mess, args):
		"""Babbles or babble-completes."""
		return self.model.sample_best(start=args, max_len=random.randint(1, 20), times=5)

	@botcmd
	def babble_sources(self, mess, args):
		"""Lists all babble sources."""
		return "\n".join("{} {}".format(idx, source) for idx, source in
				enumerate(self['sources']))

	@botcmd
	def babble_sources_add(self, mess, args):
		"""Adds a URL as a new babble source."""
		sources = self['sources']
		sources.append(args)
		self['sources'] = sources
		for msg in self.babble_reload(mess, args):
			yield msg

	@botcmd
	def babble_sources_remove(self, mess, args):
		"""Removes the babble source with the given index."""
		sources = self['sources']
		del sources[int(args)]
		self['sources'] = sources
		for msg in self.babble_reload(mess, args):
			yield msg
