from markov import *
import unittest

class NGramTableTestCase(unittest.TestCase):
    def test_completions(self):
        table = NGramTable(["fox fox fox. fox fox"])
        self.assertEqual(table.get_start_gram(3), ("fox","fox","fox."))
        self.assertEqual(table.completions(("fox",)), {"fox": 2, "fox.": 1, END: 1})
        self.assertEqual(table.completions(("fox","fox")), {"fox.": 1, END: 1})
        self.assertEqual(table.completions(("fox","fox.")), {"fox": 1})
        self.assertEqual(table.completions(("fox.","fox")), {"fox": 1})
        self.assertEqual(table.completions(("fox.","fox","fox")), {END: 1})
