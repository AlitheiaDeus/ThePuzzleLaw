"""
Morse Code Alphabets and Character Mappings.
Supports International Morse (ITU), American Railroad Morse, Continental Accents,
Cyrillic Morse, and extensible mappings for cryptography and puzzle solving.
"""

from typing import Dict, Optional, Tuple

# ----------------------------------------------------------------------
# 1. ITU Standard International Morse Code (ITU-R M.1677-1)
# ----------------------------------------------------------------------
ITU_MORSE: Dict[str, str] = {
    # Latin Alphabet
    'A': '.-',     'B': '-...',   'C': '-.-.',   'D': '-..',
    'E': '.',      'F': '..-.',   'G': '--.',    'H': '....',
    'I': '..',     'J': '.---',   'K': '-.-',    'L': '.-..',
    'M': '--',     'N': '-.',     'O': '---',    'P': '.--.',
    'Q': '--.-',   'R': '.-.',    'S': '...',    'T': '-',
    'U': '..-',    'V': '...-',   'W': '.--',    'X': '-..-',
    'Y': '-.--',   'Z': '--..',

    # Digits
    '0': '-----',  '1': '.----',  '2': '..---',  '3': '...--',
    '4': '....-',  '5': '.....',  '6': '-....',  '7': '--...',
    '8': '---..',  '9': '----.',

    # Standard Punctuation & Signs
    '.': '.-.-.-', ',': '--..--', '?': '..--..', "'": '.----.',
    '!': '-.-.--', '/': '-..-.',  '(': '-.--.',  ')': '-.--.-',
    '&': '.-...',  ':': '---...', ';': '-.-.-.', '=': '-...-',
    '+': '.-.-.',  '-': '-....-', '_': '..--.-', '"': '.-..-.',
    '$': '...-..-', '@': '.--.-.',
}

# Common Prosigns (transcribed as contiguous letters or standalone symbols)
ITU_PROSIGNS: Dict[str, str] = {
    'SOS': '...---...',   # Distress signal
    'CQ': '-.-.--.-',     # Calling any station
    'AR': '.-.-.',        # End of transmission (+)
    'AS': '.-...',        # Wait (&)
    'BT': '-...-',        # Break / separator (=)
    'CT': '-.-.-',        # Start of transmission
    'KN': '-.--.',        # Specific station answer only
    'SK': '...-.-',       # End of contact
    'HH': '........',     # Error / correction
}

# ----------------------------------------------------------------------
# 2. Continental / Extended European Accents (Latin extensions)
# ----------------------------------------------------------------------
CONTINENTAL_EXTENSIONS: Dict[str, str] = {
    'Ä': '.-.-',     'À': '.--.-',    'Å': '.--.-',    'É': '..-..',
    'È': '.-..-',    'Ë': '..-..',    'Ê': '-..-',     'Ö': '---.',
    'Ü': '..--',     'ß': '...--..',  'Ñ': '--.--',    'Ç': '-.-..',
    'CH': '----',    'Š': '----',     'Ø': '---.',
}

# ----------------------------------------------------------------------
# 3. American Morse Code (Railroad / Telegraph Morse)
# Historically used in North America; differs in letter representations
# and utilizes varying dash lengths / internal spaces.
# In continuous ASCII, internal element spaces are represented as short dits/dahs.
# ----------------------------------------------------------------------
AMERICAN_MORSE: Dict[str, str] = {
    'A': '.-',     'B': '-...',   'C': '.. .',   'D': '-..',
    'E': '.',      'F': '.-.',    'G': '--.',    'H': '....',
    'I': '..',     'J': '-.-.',   'K': '-.-',    'L': '---',      # Long dash
    'M': '--',     'N': '-.',     'O': '. .',    'P': '.....',
    'Q': '..-.',   'R': '. ..',   'S': '...',    'T': '-',
    'U': '..-',    'V': '...-',   'W': '.--',    'X': '.-..',
    'Y': '.. ..',  'Z': '... .',  '&': '. ...',
    '0': '----',   '1': '.--.',   '2': '..-..',  '3': '...-.',
    '4': '....-',  '5': '---',    '6': '......', '7': '--..',
    '8': '-....',  '9': '-..-',
}

# ----------------------------------------------------------------------
# 4. Russian / Cyrillic Morse Code
# Mappings of Cyrillic letters to standard Morse signals
# ----------------------------------------------------------------------
CYRILLIC_MORSE: Dict[str, str] = {
    'А': '.-',     'Б': '-...',   'В': '.--',    'Г': '--.',
    'Д': '-..',    'Е': '.',      'Ж': '...-',   'З': '--..',
    'И': '..',     'Й': '.---',   'К': '-.-',    'Л': '.-..',
    'М': '--',     'Н': '-.',     'О': '---',    'П': '.--.',
    'Р': '.-.',    'С': '...',    'Т': '-',      'У': '..-',
    'Ф': '..-.',   'Х': '....',   'Ц': '-.-.',   'Ч': '---.',
    'Ш': '----',   'Щ': '--.-',   'Ъ': '--.--',  'Ы': '-.--',
    'Ь': '-..-',   'Э': '..-..',  'Ю': '..--',   'Я': '.-.-',
}

# ----------------------------------------------------------------------
# 5. Japanese Wabun Code (Katakana)
# ----------------------------------------------------------------------
WABUN_MORSE: Dict[str, str] = {
    'イ': '.-',     'ロ': '.-.-',   'ハ': '-...',   'ニ': '-.-.',
    'ホ': '-..',    'ヘ': '.',      'ト': '..-..',  'チ': '..-.',
    'リ': '--.',    'ヌ': '....',   'ル': '-.--.',  'ヲ': '.---',
    'ワ': '-.-',    'カ': '.-..',   'ヨ': '--',     'タ': '-.',
    'レ': '---',    'ソ': '---.',   'ツ': '.--.',   'ネ': '--.-',
    'ナ': '.-.',    'ラ': '...',    'ム': '-',      'ウ': '..-',
    'ヰ': '.-..-',  'ノ': '..--',   'オ': '.-...',  'ク': '...-',
    'ヤ': '.--',    'マ': '-..-',   'ケ': '-.--',   'フ': '--..',
    'コ': '----',   'エ': '-.---',  'テ': '.-.--',  'ア': '--.--',
    'サ': '-.-.-',  'キ': '-.-..',  'ユ': '-..--',  'メ': '-...-',
    'ミ': '..-.-',  'シ': '--.-.',  'ヱ': '.--..',  'ヒ': '--..-',
    'モ': '-..-.',  'セ': '.---.',  'ス': '---.-',  'ン': '.-.-.',
    '゛': '..',     '゜': '..-..',
}


class MorseAlphabet:
    """Encapsulates a Morse code alphabet and bidirectional lookup tables."""

    def __init__(self, name: str, char_to_morse: Dict[str, str]):
        self.name = name
        self.char_to_morse = {k.upper(): v for k, v in char_to_morse.items()}
        # Reverse lookup: morse -> list of chars (since in some alphabets multiple chars may share a code)
        self.morse_to_char: Dict[str, list[str]] = {}
        for char, code in self.char_to_morse.items():
            self.morse_to_char.setdefault(code, []).append(char)

    def encode_char(self, char: str) -> Optional[str]:
        return self.char_to_morse.get(char.upper())

    def encode_word(self, word: str) -> Optional[str]:
        """Encodes an entire word into contiguous (unspaced) Morse code."""
        result = []
        for ch in word.upper():
            code = self.encode_char(ch)
            if code is None:
                return None
            result.append(code)
        return "".join(result)

    def decode_morse(self, morse_token: str) -> list[str]:
        """Returns all possible characters for a single Morse token."""
        return self.morse_to_char.get(morse_token, [])


# Pre-built alphabet instances
ALPHABETS: Dict[str, MorseAlphabet] = {
    'itu': MorseAlphabet('ITU International', ITU_MORSE),
    'continental': MorseAlphabet('Continental / European', {**ITU_MORSE, **CONTINENTAL_EXTENSIONS}),
    'american': MorseAlphabet('American Railroad', AMERICAN_MORSE),
    'cyrillic': MorseAlphabet('Russian Cyrillic', CYRILLIC_MORSE),
    'wabun': MorseAlphabet('Japanese Wabun', WABUN_MORSE),
}


def get_alphabet(name: str = 'itu') -> MorseAlphabet:
    """Retrieves a MorseAlphabet by key (default: 'itu')."""
    key = name.lower().strip()
    if key in ALPHABETS:
        return ALPHABETS[key]
    raise ValueError(f"Unknown alphabet: {name}. Available: {list(ALPHABETS.keys())}")
