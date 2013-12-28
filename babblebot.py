# encoding=utf-8
# vim:noet:sw=4:ts=4

import urllib.request

from markov import MarkovChains

from errbot import BotPlugin, botcmd


class BabbleBot(BotPlugin):
	def configure(self, configuration):
		super().configure(configuration)
		if self.config is None:
			self.config = self.get_configuration_template()
		for error in self.reload():
			logging.warn(error)

	def get_configuration_template(self):
		return {'NGRAM_N': 3, 'SOURCES': ['http://www.gutenberg.org/cache/epub/2229/pg2229.txt']}

	def check_configuration(self, configuration):
		super().check_configuration(configuration)

	def reload(self):
		self.model = MarkovChains(self.config['NGRAM_N'])
		for source in self.config['SOURCES']:
			try:
				f = urllib.request.urlopen(source)
			except urllib.error.URLError:
				yield "Couldn't retrieve babble source: " + source
				continue
			with f:
				for line in f.readlines():
					self.model.add(line.decode())

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
		return self.model.sample(start=args)

	@botcmd
	def babble_sources(self, mess, args):
		"""Lists all babble sources."""
		return "\n".join("{} {}".format(idx, source) for idx, source in
				enumerate(self.config['SOURCES']))

	@botcmd
	def babble_sources_add(self, mess, args):
		"""Adds a URL as a new babble source."""
		self.config['SOURCES'].append(args)
		for msg in self.babble_reload(mess, args):
			yield msg

	@botcmd
	def babble_sources_remove(self, mess, args):
		"""Removes the babble source with the given index."""
		del self.config['SOURCES'][int(args)]
		for msg in self.babble_reload(mess, args):
			yield msg
