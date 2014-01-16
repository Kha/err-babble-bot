from markov import *
import unittest

class NGramTableTestCase(unittest.TestCase):

    def assertFreqsEqual(self, compls, freqs):
        self.assertEqual({compl: ngram.count for compl, ngram in compls.items()}, freqs)

    def test_completions(self):
        table = NGramTable(["fox fox fox. fox fox"])
        self.assertEqual(table.get_start_gram(3).words, ("fox","fox","fox."))

        self.assertFreqsEqual(table.completions(("fox",)), {"fox": 2, "fox.": 1, END: 1})
        self.assertFreqsEqual(table.completions(("fox","fox")), {"fox.": 1, END: 1})
        self.assertFreqsEqual(table.completions(("fox","fox.")), {"fox": 1})
        self.assertFreqsEqual(table.completions(("fox.","fox")), {"fox": 1})
        self.assertFreqsEqual(table.completions(("fox.","fox","fox")), {END: 1})
