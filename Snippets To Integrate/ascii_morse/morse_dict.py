"""
Morse Word Trie and Frequency Lexicon.
Maps dictionary words to continuous Morse code prefixes and unigram frequency scores.
Prunes degenerate single-letter interpretations (suppressing E, T, S, H gibberish).
"""

import math
import os
from typing import Dict, List, Optional, Set, Tuple

from morse_alphabets import MorseAlphabet, get_alphabet

# Supplemental words essential for puzzles, radio, cryptography, and reddit
SUPPLEMENTAL_WORDS: Dict[str, float] = {
    # Distress / Radio prosigns & abbreviations
    'SOS': 8.5,
    'HELP': 8.5,
    'MAYDAY': 8.0,
    'CQ': 7.5,
    'ROGER': 7.5,
    'WILCO': 7.0,
    'OVER': 8.0,
    'OUT': 8.0,
    'QSL': 6.5,
    'QTH': 6.5,
    'CW': 6.5,
    '73': 7.0,   # Best regards in ham radio
    '88': 6.5,   # Love and kisses in ham radio

    # Essential single-letter English words
    'I': 9.5,
    'A': 9.5,

    # Reddit / Internet / Modern puzzle terms
    'REDDIT': 8.0,
    'PIKACHU': 9.0,
    'PUZZLE': 7.5,
    'CIPHER': 7.5,
    'SECRET': 8.0,
    'MESSAGE': 8.0,
    'FLAG': 7.5,
    'CTF': 7.0,
    'CODE': 8.5,
    'MORSE': 8.5,
    'DECODE': 7.5,
    'ENCODE': 7.0,
    'TEST': 8.0,
    'HELLO': 8.5,
    'WORLD': 8.5,
    'PLEASE': 8.5,
    'THANKS': 8.0,
}

# Standalone single-letter words allowed in standard English
VALID_ENGLISH_SINGLE_LETTERS: Set[str] = {'A', 'I'}

# ----------------------------------------------------------------------
# Multilingual Configurations & Transliteration
# ----------------------------------------------------------------------

CYRILLIC_TO_LATIN: Dict[str, str] = {
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ж': 'ZH', 'З': 'Z',
    'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O', 'П': 'P',
    'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'KH', 'Ц': 'TS', 'Ч': 'CH',
    'Ш': 'SH', 'Щ': 'SHCH', 'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'YU', 'Я': 'YA'
}

KATAKANA_TO_ROMAJI: Dict[str, str] = {
    'イ': 'I', 'ロ': 'RO', 'ハ': 'HA', 'ニ': 'NI', 'ホ': 'HO', 'ヘ': 'HE', 'ト': 'TO',
    'チ': 'CHI', 'リ': 'RI', 'ヌ': 'NU', 'ル': 'RU', 'ヲ': 'WO', 'ワ': 'WA', 'カ': 'KA',
    'ヨ': 'YO', 'タ': 'TA', 'レ': 'RE', 'ソ': 'SO', 'ツ': 'TSU', 'ネ': 'NE', 'ナ': 'NA',
    'ラ': 'RA', 'ム': 'MU', 'ウ': 'U', 'ヰ': 'WI', 'ノ': 'NO', 'オ': 'O', 'ク': 'KU',
    'ヤ': 'YA', 'マ': 'MA', 'ケ': 'KE', 'フ': 'FU', 'コ': 'KO', 'エ': 'E', 'テ': 'TE',
    'ア': 'A', 'サ': 'SA', 'キ': 'KI', 'ユ': 'YU', 'メ': 'ME', 'ミ': 'MI', 'シ': 'SHI',
    'ヱ': 'WE', 'ヒ': 'HI', 'モ': 'MO', 'セ': 'SE', 'ス': 'SU', 'ン': 'N',
    '゛': '"', '゜': '°',
}

LANGUAGE_CONFIGS: Dict[str, Dict] = {
    'en': {
        'name': 'English',
        'default_alphabet': 'itu',
        'freq_file': 'english_words_freq.txt',
        'enable_file': 'enable1.txt',
        'single_letters': {'A', 'I'},
        'accents': {},
    },
    'es': {
        'name': 'Spanish',
        'default_alphabet': 'continental',
        'freq_file': 'es_freq.txt',
        'enable_file': None,
        'single_letters': {'A', 'Y', 'O', 'E', 'U'},
        'accents': {'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U', 'Ü': 'U'},
    },
    'fr': {
        'name': 'French',
        'default_alphabet': 'continental',
        'freq_file': 'fr_freq.txt',
        'enable_file': None,
        'single_letters': {'A', 'Y', 'O'},
        'accents': {'À': 'A', 'Â': 'A', 'È': 'E', 'Ê': 'E', 'Ë': 'E', 'Î': 'I', 'Ï': 'I', 'Ô': 'O', 'Ù': 'U', 'Û': 'U'},
    },
    'de': {
        'name': 'German',
        'default_alphabet': 'continental',
        'freq_file': 'de_freq.txt',
        'enable_file': None,
        'single_letters': set(),
        'accents': {'Ä': 'AE', 'Ö': 'OE', 'Ü': 'UE', 'ß': 'SS'},
    },
    'ru': {
        'name': 'Russian Cyrillic',
        'default_alphabet': 'cyrillic',
        'freq_file': 'ru_freq.txt',
        'enable_file': None,
        'single_letters': {'Я', 'И', 'В', 'С', 'К', 'О', 'У', 'А'},
        'accents': {},
    },
    'it': {
        'name': 'Italian',
        'default_alphabet': 'continental',
        'freq_file': 'it_freq.txt',
        'enable_file': None,
        'single_letters': {'A', 'E', 'I', 'O'},
        'accents': {'À': 'A', 'È': 'E', 'É': 'E', 'Ì': 'I', 'Ò': 'O', 'Ù': 'U'},
    },
    'ja': {
        'name': 'Japanese Wabun',
        'default_alphabet': 'wabun',
        'freq_file': None,
        'enable_file': None,
        'single_letters': set(),
        'accents': {},
    },
}

# Embedded core vocabulary for Japanese Wabun (Katakana)
JAPANESE_WABUN_WORDS: List[Tuple[str, float]] = [
    ("アイ", -3.0),      # AI (Love)
    ("スシ", -3.2),      # SUSHI
    ("サケ", -3.5),      # SAKE
    ("ネコ", -3.5),      # NEKO (Cat)
    ("イヌ", -3.5),      # INU (Dog)
    ("ミズ", -3.2),      # MIZU (Water)
    ("ソラ", -3.5),      # SORA (Sky)
    ("ハナ", -3.5),      # HANA (Flower)
    ("ツキ", -3.5),      # TSUKI (Moon)
    ("ホシ", -3.5),      # HOSHI (Star)
    ("ユキ", -3.6),      # YUKI (Snow)
    ("カゼ", -3.5),      # KAZE (Wind)
    ("ヒカリ", -3.8),    # HIKARI (Light)
    ("トモ", -3.6),      # TOMO (Friend)
    ("ココロ", -3.5),    # KOKORO (Heart)
    ("ウミ", -3.6),      # UMI (Sea)
    ("ヤマ", -3.6),      # YAMA (Mountain)
    ("カワ", -3.6),      # KAWA (River)
    ("モリ", -3.6),      # MORI (Forest)
    ("ヒト", -3.0),      # HITO (Person)
    ("オトコ", -3.4),    # OTOKO (Man)
    ("オンナ", -3.4),    # ONNA (Woman)
    ("サヨナラ", -4.0),  # SAYONARA
    ("アリガトウ", -3.8),# ARIGATOU
    ("コンニチハ", -4.0),# KONNICHIWA
    ("ニホン", -3.2),    # NIHON (Japan)
    ("トーキョー", -3.5),# TOKYO
    ("ハル", -3.6),      # HARU (Spring)
    ("ナツ", -3.6),      # NATSU (Summer)
    ("アキ", -3.6),      # AKI (Autumn)
    ("フユ", -3.6),      # FUYU (Winter)
    ("アメ", -3.5),      # AME (Rain)
    ("クモ", -3.6),      # KUMO (Cloud)
    ("テ", -4.5),        # TE (Hand)
    ("メ", -4.5),        # ME (Eye)
    ("ハ", -4.5),        # HA (Tooth)
    ("ヒ", -4.5),        # HI (Sun/Fire)
    ("キ", -4.5),        # KI (Tree/Spirit)
]


def transliterate_word(word: str, language: str) -> str:
    """Provides Romanized Latin transliteration for non-Latin alphabets (Cyrillic, Katakana)."""
    lang = language.lower().strip()
    if lang == 'ru':
        return "".join(CYRILLIC_TO_LATIN.get(c, c) for c in word.upper())
    elif lang == 'ja':
        return "".join(KATAKANA_TO_ROMAJI.get(c, c) for c in word)
    return word


class TrieNode:
    __slots__ = ('children', 'terminal_words')

    def __init__(self):
        self.children: Dict[str, TrieNode] = {}
        # List of (word, score) ending at this node
        self.terminal_words: List[Tuple[str, float]] = []


class MorseTrie:
    """Prefix tree indexed by Morse symbols ('.' and '-')."""

    def __init__(self):
        self.root = TrieNode()
        self.total_words = 0

    def insert(self, morse_code: str, word: str, score: float) -> None:
        """Inserts a word into the trie under its continuous Morse string."""
        node = self.root
        for symbol in morse_code:
            if symbol not in node.children:
                node.children[symbol] = TrieNode()
            node = node.children[symbol]
        node.terminal_words.append((word, score))
        self.total_words += 1

    def match_prefixes(self, morse_stream: str, start_idx: int) -> List[Tuple[int, str, float]]:
        """
        Traverses the trie matching morse_stream from start_idx.
        Returns all matches as (end_idx, word, score).
        """
        matches: List[Tuple[int, str, float]] = []
        node = self.root
        n = len(morse_stream)
        idx = start_idx

        while idx < n:
            sym = morse_stream[idx]
            if sym not in node.children:
                break
            node = node.children[sym]
            idx += 1
            if node.terminal_words:
                for word, score in node.terminal_words:
                    matches.append((idx, word, score))

        return matches


class MorseDictionary:
    """
    Manages vocabulary, frequency scoring, and Morse Trie construction across languages.
    """

    def __init__(
        self,
        alphabet: Optional[MorseAlphabet] = None,
        language: str = "en",
        allow_single_letters: bool = False,
        min_word_len: int = 1,
    ):
        self.language = language.lower().strip()
        lang_cfg = LANGUAGE_CONFIGS.get(self.language, LANGUAGE_CONFIGS['en'])
        self.alphabet = alphabet or get_alphabet(lang_cfg['default_alphabet'])
        self.allow_single_letters = allow_single_letters
        self.allowed_single_letters = lang_cfg.get('single_letters', set())
        self.accents = lang_cfg.get('accents', {})
        self.min_word_len = min_word_len
        self.trie = MorseTrie()
        self.word_scores: Dict[str, float] = {}

    def load_from_freq_file(
        self,
        filepath: str,
        enable_filepath: Optional[str] = None,
        max_words: int = 50000,
    ) -> None:
        """
        Loads words and raw counts, computing true unigram log-probabilities: log10(count / total_tokens).
        Cross-references an ENABLE1 wordlist if available to filter out crawl noise.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Dictionary file not found: {filepath}")

        enable_words: Optional[Set[str]] = None
        if enable_filepath and os.path.exists(enable_filepath):
            with open(enable_filepath, 'r', encoding='utf-8', errors='ignore') as f:
                enable_words = {line.strip().upper() for line in f if line.strip()}

        raw_counts: Dict[str, float] = {}
        total_tokens = 0.0

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                word = parts[0].upper()
                # If enable_words is provided, strictly filter against it (unless in supplemental)
                if enable_words is not None and word not in enable_words and word not in SUPPLEMENTAL_WORDS:
                    continue

                try:
                    count = float(parts[1]) if len(parts) > 1 else 1000.0
                except (ValueError, IndexError):
                    count = 1000.0

                raw_counts[word] = count
                total_tokens += count
                if len(raw_counts) >= max_words:
                    break

        # For English, inject supplemental words with high default frequencies (e.g. 10M tokens)
        if self.language == 'en':
            for word, score in SUPPLEMENTAL_WORDS.items():
                equiv_count = 10 ** (score - 1.0) * 1000.0
                if word not in raw_counts or raw_counts[word] < equiv_count:
                    raw_counts[word] = equiv_count
                    total_tokens += equiv_count

        if total_tokens <= 0:
            total_tokens = 1.0

        # Compute empirical unigram log-probability: log10(P(word))
        for word, count in raw_counts.items():
            self.word_scores[word] = math.log10(count / total_tokens)

        self._build_trie()

    def load_custom_wordlist(self, filepath: str, default_log_prob: float = -5.0) -> None:
        """Loads an arbitrary newline-separated wordlist with a default log probability."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Custom wordlist not found: {filepath}")

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                word = line.strip().upper()
                if word and not word.startswith('#'):
                    self.word_scores[word] = default_log_prob

        self._build_trie()

    def _build_trie(self) -> None:
        """Encodes all valid words into continuous Morse strings in the trie."""
        self.trie = MorseTrie()
        for word, log_p in self.word_scores.items():
            # Apply length filters
            if len(word) < self.min_word_len:
                continue

            # Check single-letter constraint
            if len(word) == 1:
                if not self.allow_single_letters and word not in self.allowed_single_letters:
                    # Skip garbage single letters (E, T, S, H, etc.)
                    continue
                # Moderate single-letter probabilities so they don't drown out multi-letter words
                log_p = min(log_p, -3.5)

            morse_str = self.alphabet.encode_word(word)
            if morse_str:
                self.trie.insert(morse_str, word, log_p)

            # Fallback encoding with stripped/normalized accents if applicable
            if self.accents:
                w_norm = "".join(self.accents.get(ch, ch) for ch in word)
                if w_norm != word:
                    morse_norm = self.alphabet.encode_word(w_norm)
                    if morse_norm and morse_norm != morse_str:
                        self.trie.insert(morse_norm, word, log_p)


def get_default_dictionary(
    alphabet: Optional[MorseAlphabet] = None,
    language: str = "en",
    allow_single_letters: bool = False,
    min_word_len: int = 1,
) -> MorseDictionary:
    """Convenience factory to load the appropriate language frequency dictionary."""
    lang = language.lower().strip()
    if lang not in LANGUAGE_CONFIGS:
        raise ValueError(f"Unsupported language: {language}. Supported: {list(LANGUAGE_CONFIGS.keys())}")

    lang_cfg = LANGUAGE_CONFIGS[lang]
    selected_alphabet = alphabet or get_alphabet(lang_cfg['default_alphabet'])

    dict_obj = MorseDictionary(
        alphabet=selected_alphabet,
        language=lang,
        allow_single_letters=allow_single_letters,
        min_word_len=min_word_len,
    )

    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Japanese Wabun embedded handling
    if lang == 'ja':
        for word, log_p in JAPANESE_WABUN_WORDS:
            dict_obj.word_scores[word] = log_p
        dict_obj._build_trie()
        return dict_obj

    freq_filename = lang_cfg.get('freq_file')
    enable_filename = lang_cfg.get('enable_file')

    freq_path = os.path.join(base_dir, 'data', freq_filename) if freq_filename else None
    enable_path = os.path.join(base_dir, 'data', enable_filename) if enable_filename else None

    if freq_path and os.path.exists(freq_path):
        dict_obj.load_from_freq_file(
            filepath=freq_path,
            enable_filepath=enable_path if (enable_path and os.path.exists(enable_path)) else None,
            max_words=30000,
        )
    else:
        # Fallback to supplemental words
        for word, score in SUPPLEMENTAL_WORDS.items():
            dict_obj.word_scores[word] = -4.0
        dict_obj._build_trie()

    return dict_obj

