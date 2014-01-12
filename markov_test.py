from markov import *
import unittest

class NGramTableTestCase(unittest.TestCase):
    def test_completions(self):
        table = NGramTable(4, ["fox fox fox. fox fox"])
        self.assertEqual(table.completions(4, ()), {"fox": 1})
        self.assertEqual(table.completions(4, ("fox",)), {"fox": 1})
        self.assertEqual(table.completions(4, ("fox","fox")), {"fox.": 1})
        self.assertEqual(table.completions(4, ("fox","fox","fox.")), {"fox": 1})
        self.assertEqual(table.completions(4, ("fox","fox","fox.","fox")), {"fox": 1})
        self.assertEqual(table.completions(4, ("fox","fox","fox.","fox","fox")), {END: 1})

        self.assertEqual(table.completions(2, ()), {"fox": 1})
        self.assertEqual(table.completions(2, ("fox",)), {"fox": 2, "fox.": 1, END: 1})
        self.assertEqual(table.completions(2, ("fox","fox")), {"fox": 2, "fox.": 1, END: 1})
        self.assertEqual(table.completions(2, ("fox","fox","fox.")), {"fox": 1})
