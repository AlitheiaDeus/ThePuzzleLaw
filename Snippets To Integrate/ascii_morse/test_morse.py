"""
Unit Tests for Unspaced Morse Code Permutation Solver.
"""

import os
import unittest

from morse_alphabets import get_alphabet
from morse_dict import get_default_dictionary
from morse_permutations import MorseSolver, write_permutations_file
from normalizer import get_all_signal_variants, normalize_morse_stream


class TestMorseSolver(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.alphabet = get_alphabet('itu')
        cls.dictionary = get_default_dictionary(alphabet=cls.alphabet)
        cls.solver = MorseSolver(cls.dictionary)

    def test_normalizer_symbol_variants(self):
        self.assertEqual(normalize_morse_stream('...---...'), '...---...')
        self.assertEqual(normalize_morse_stream('000111000'), '...---...')
        self.assertEqual(normalize_morse_stream('***---***'), '...---...')
        self.assertEqual(normalize_morse_stream('dit dit dit dah dah dah dit dit dit'), '...---...')
        self.assertEqual(normalize_morse_stream('...___...'), '...---...')

    def test_signal_inversion_and_reversal(self):
        variants = get_all_signal_variants('...---..-')
        self.assertIn('Standard', variants)
        self.assertIn('Inverted (Dits <-> Dahs)', variants)
        self.assertIn('Reversed (Right-to-Left)', variants)
        self.assertEqual(variants['Inverted (Dits <-> Dahs)'], '---...--.')

    def test_sos_detection(self):
        results = self.solver.solve('...---...')
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0].text, 'SOS')

    def test_hello_world_detection(self):
        # Unspaced "HELLO WORLD":
        # HELLO: ......-...-..---
        # WORLD: .-----.-..-..-..
        stream = '......-...-..---.-----.-..-..-..'
        results = self.solver.solve(stream, beam_width=500, max_permutations=20)
        self.assertTrue(len(results) > 0)
        # Check that HELLO WORLD is #1
        self.assertEqual(results[0].text, 'HELLO WORLD')

    def test_suppression_of_et_spam(self):
        # By default, single letters other than A and I should not appear as standalone words
        results = self.solver.solve('...---...')
        for r in results:
            for w in r.words:
                if len(w) == 1:
                    self.assertIn(w, {'A', 'I'}, f"Found prohibited single letter: {w}")

    def test_output_file_writing(self):
        out_path = os.path.join(os.path.dirname(__file__), 'test_out.txt')
        results = self.solver.solve('...---...')
        write_permutations_file(
            filepath=out_path,
            raw_input='...---...',
            normalized_stream='...---...',
            alphabet_name='ITU International',
            results_by_variant={'Standard': results},
            elapsed_time=0.001,
            dict_word_count=1000,
            include_llm_prompt=True,
        )
        self.assertTrue(os.path.exists(out_path))
        with open(out_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('SOS', content)
        self.assertIn('LLM PROMPT', content)
        if os.path.exists(out_path):
            os.remove(out_path)

    def test_symmetric_chops_computation(self):
        from morse_permutations import compute_symmetric_chops

        # The 25-symbol bracelet string:
        # Index 0: '-', -1: '-' -> match
        # Index 1: '.', -2: '.' -> match
        # Index 2: '.', -3: '.' -> match
        # Index 3: '.', -4: '-' -> mismatch!
        # Should detect exactly 3 chops before symmetry breaks
        stream = '-...-..---...-.-.-----..-'
        num_chops, chop_details, max_sym = compute_symmetric_chops(stream, requested_chops=-1)
        self.assertEqual(num_chops, 3)
        self.assertEqual(max_sym, 3)
        self.assertEqual(len(chop_details), 3)
        self.assertEqual(chop_details[0][1], stream[1:-1])
        self.assertEqual(chop_details[1][1], stream[2:-2])
        self.assertEqual(chop_details[2][1], stream[3:-3])

    def test_multilingual_loading(self):
        # Russian
        ru_dict = get_default_dictionary(language='ru')
        self.assertEqual(ru_dict.alphabet.name, 'Russian Cyrillic')
        self.assertTrue(ru_dict.trie.total_words > 5000)

        # French
        fr_dict = get_default_dictionary(language='fr')
        self.assertEqual(fr_dict.alphabet.name, 'Continental / European')
        self.assertTrue(fr_dict.trie.total_words > 5000)

        # Japanese Wabun
        ja_dict = get_default_dictionary(language='ja')
        self.assertEqual(ja_dict.alphabet.name, 'Japanese Wabun')
        self.assertTrue(ja_dict.trie.total_words > 0)


if __name__ == '__main__':
    unittest.main()
