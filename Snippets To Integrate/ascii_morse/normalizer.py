"""
Morse Code Normalizer and Signal Cleaner.
Automatically handles arbitrary dot/dash representations, phonetic transcriptions (dit/dah),
Unicode symbols, and generates standard, inverted, reversed, and inverted-reversed signal variants.
"""

import re
from typing import Dict, List, Optional, Tuple

# Common representations
KNOWN_DOTS = {'.', '·', '•', '●', '○', '*', '0', 'O', 'o', 'x', 'X'}
KNOWN_DASHES = {'-', '_', '—', '–', '―', '−', '1', '=', '~'}


def normalize_morse_stream(raw_text: str, strip_spaces: bool = True) -> str:
    """
    Cleans raw text and converts it into a standard ASCII '.' and '-' string.
    Supports phonetic dits/dahs, arbitrary binary symbols, and Unicode bullets/dashes.
    """
    text = raw_text.strip()
    if not text:
        return ""

    # Check for phonetic words (e.g., "dit dit dit dah dah dah" or "di di di da da da")
    lower_text = text.lower()
    if 'dit' in lower_text or 'dah' in lower_text or 'di' in lower_text or 'da' in lower_text:
        # Tokenize phonetic morse
        tokens = re.findall(r'\b(dits?|dih|dahs?|da|di)\b', lower_text)
        if tokens:
            morse_chars = []
            for t in tokens:
                if t in ('dit', 'dits', 'dih', 'di'):
                    morse_chars.append('.')
                elif t in ('dah', 'dahs', 'da'):
                    morse_chars.append('-')
            return "".join(morse_chars)

    # If strip_spaces is True, eliminate all spaces and newlines
    if strip_spaces:
        text = re.sub(r'\s+', '', text)

    # Analyze distinct characters in the stream
    chars = set(text)
    if strip_spaces and ' ' in chars:
        chars.remove(' ')

    # Fast path: already purely '.' and '-'
    if chars <= {'.', '-'}:
        return text

    # Automatic symbol detection for pair of distinct characters (e.g. 0/1, */-, o/-)
    if len(chars) == 2:
        c1, c2 = list(chars)
        # Determine which is dot and which is dash
        c1_is_dot = c1 in KNOWN_DOTS
        c2_is_dash = c2 in KNOWN_DASHES
        c2_is_dot = c2 in KNOWN_DOTS
        c1_is_dash = c1 in KNOWN_DASHES

        if c1_is_dot or c2_is_dash:
            dot_char, dash_char = c1, c2
        elif c2_is_dot or c1_is_dash:
            dot_char, dash_char = c2, c1
        else:
            # Fallback: shorter or first ordered is dot
            dot_char, dash_char = (c1, c2) if c1 < c2 else (c2, c1)

        trans = str.maketrans({dot_char: '.', dash_char: '-'})
        return text.translate(trans)

    # Direct substitution based on known symbols
    result = []
    for ch in text:
        if ch in KNOWN_DOTS:
            result.append('.')
        elif ch in KNOWN_DASHES:
            result.append('-')
        elif not strip_spaces and ch in (' ', '/', '|'):
            result.append(' ')
        # ignore or skip unknown chars

    return "".join(result)


def invert_morse(morse_str: str) -> str:
    """Inverts Morse polarity: '.' becomes '-' and '-' becomes '.'."""
    trans = str.maketrans({'.': '-', '-': '.'})
    return morse_str.translate(trans)


def reverse_morse(morse_str: str) -> str:
    """Reverses the Morse sequence (read right-to-left)."""
    return morse_str[::-1]


def get_all_signal_variants(morse_str: str) -> Dict[str, str]:
    """
    Returns standard, inverted, reversed, and inverted-reversed variants
    to account for polarity inversions or reverse-recorded signals.
    """
    standard = morse_str
    inverted = invert_morse(standard)
    reversed_str = reverse_morse(standard)
    inverted_reversed = invert_morse(reversed_str)

    variants = {'Standard': standard}
    if inverted != standard:
        variants['Inverted (Dits <-> Dahs)'] = inverted
    if reversed_str != standard and reversed_str != inverted:
        variants['Reversed (Right-to-Left)'] = reversed_str
    if inverted_reversed != standard and inverted_reversed != inverted and inverted_reversed != reversed_str:
        variants['Inverted + Reversed'] = inverted_reversed

    return variants
