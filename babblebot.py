# encoding=utf-8

import logging
import random
import time
import urllib.request

import markov

from errbot import BotPlugin, botcmd


class BabbleBot(BotPlugin):
    def __init__(self):
        super().__init__()
        self.ngrams = []

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
        return {'NGRAM_N': 3, 'CONTEXT_SIZE': 5, 'ANSWER_PROBABILITY': 0.5,
                'ANSWER_COOLDOWN_HOURS': 24}

    def check_configuration(self, configuration):
        super().check_configuration(configuration)

    def reload(self):
        self.table = markov.NGramTable()
        for source in self['sources']:
            try:
                f = urllib.request.urlopen(source)
            except:
                yield "Couldn't retrieve babble source: " + source
                continue
            with f:
                self.table.add_source(line.decode() for line in f.readlines())
        self.sampler = markov.MarkovSampler(self.config['NGRAM_N'], self.table)

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
        text, ngrams = self.sampler.sample_best(start=args, max_len=random.randint(1, 20), times=5)
        self.ngrams = ngrams
        return text

    @botcmd
    def wtfwheredidthatcomefrom(self, mess, args):
        return markov.NGram.print_context(self.ngrams, self.config['CONTEXT_SIZE'])

    @botcmd
    def context(self, mess, args):
        return self.wtfwheredidthatcomefrom(mess, args)

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

    @botcmd
    def askguybrush(self, mess, args):
        if not args or args[-1] != '?':
            return "That's not a question, stupid."

        sample = self.sampler.sample_answer(args, max_len=random.randint(1, 20))
        if sample:
            text, self.ngrams = sample
        else:
            text, self.ngrams = self.sampler.sample_best(max_len=random.randint(1, 20))
            text = "Uhm. " + text

        return text


    def callback_message(self, conn, mess):
        body = mess.getBody()
        # TODO: Hack around err invoking callbacks even on commands.
        # Add support for this on the err side.
        if body and body[0] != '!' and body[-1] == '?':
            if 'last_answer' in self and \
               time.time() - self['last_answer'] < 3600 * self.config['ANSWER_COOLDOWN_HOURS']:
                return
            if random.random() > self.config['ANSWER_PROBABILITY']:
                return

            sample = self.sampler.sample_answer(body, max_len=random.randint(1, 20), min_prefix=3)
            if sample:
                text, self.ngrams = sample
                self.send(mess.getFrom(), text, message_type=mess.getType())
                self['last_answer'] = time.time()
