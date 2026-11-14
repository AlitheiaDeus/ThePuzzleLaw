"""Smooshed / Unspaced & Standard Morse Code Decoder.
Ported from Snippets To Integrate/ascii_morse (normalizer, alphabets, trie dictionary, beam search).
"""

from __future__ import annotations

import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple

DATA_DIR = Path(__file__).resolve().parent / "data" / "morse"

ITU_MORSE: Dict[str, str] = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
    "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
    "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
    "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
    "Y": "-.--", "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
}

SUPPLEMENTAL_WORDS: Dict[str, float] = {
    "SOS": 8.5, "HELP": 8.5, "MAYDAY": 8.0, "CQ": 7.5, "ROGER": 7.5,
    "OVER": 8.0, "OUT": 8.0, "I": 9.5, "A": 9.5, "REDDIT": 8.0,
    "PUZZLE": 8.0, "CIPHER": 7.5, "SECRET": 8.0, "MESSAGE": 8.0,
    "CODE": 8.5, "MORSE": 8.5, "DECODE": 7.5, "TEST": 8.0,
    "HELLO": 8.5, "WORLD": 8.5, "PLEASE": 8.5, "THANKS": 8.0,
    "THE": 9.5, "LAW": 8.0,
}

KNOWN_DOTS = {".", "·", "•", "●", "○", "*", "0", "O", "o", "x", "X"}
KNOWN_DASHES = {"-", "_", "—", "–", "―", "−", "1", "=", "~"}

META: Dict[str, Any] = {
    "slug": "morse_decoder",
    "name": "Morse & Smooshed Signal Decoder",
    "category": "Crypt & Signal",
    "renderer": "text",
    "description": "Decodes spaced Morse, phonetic dit/dah, binary 0/1, and unspaced/smooshed Morse streams via Trie beam search.",
    "presets": {
        "Smooshed Morse (HELLO WORLD)": {
            "text": "......-...-..---.--.---.-..-..-..",
            "mode": "Smooshed Word Beam Search",
            "language": "en",
        },
        "Spaced Morse": {
            "text": "- .... . / .--. ..- --.. --.. .-.. . / .-.. .- .--",
            "mode": "Spaced Morse Decode",
            "language": "en",
        },
        "Binary Polarity (0/1)": {
            "text": "000010100100100111",
            "mode": "Smooshed Word Beam Search",
            "language": "en",
        },
        "Encode Plaintext -> Morse": {
            "text": "THE PUZZLE LAW",
            "mode": "Encode to Morse",
            "language": "en",
        },
    },
    "params": [
        {
            "key": "mode",
            "label": "Mode",
            "type": "select",
            "default": "Smooshed Word Beam Search",
            "options": [
                "Smooshed Word Beam Search",
                "Spaced Morse Decode",
                "Encode to Morse",
            ],
        },
        {
            "key": "language",
            "label": "Lexicon Language",
            "type": "select",
            "default": "en",
            "options": ["en", "es", "fr", "de", "it", "ru"],
        },
    ],
}


def _normalize_stream(raw_text: str, strip_spaces: bool = True) -> str:
    text = raw_text.strip()
    if not text:
        return ""
    lower = text.lower()
    if any(tok in lower for tok in ("dit", "dah")):
        tokens = re.findall(r"\b(dits?|dih|dahs?|da|di)\b", lower)
        if tokens:
            return "".join("." if t in ("dit", "dits", "dih", "di") else "-" for t in tokens)

    if strip_spaces:
        text = re.sub(r"\s+", "", text)
    chars = set(text) - ({" "} if strip_spaces else set())
    if chars <= {".", "-"}:
        return text
    if len(chars) == 2:
        c1, c2 = sorted(chars)
        if c1 in KNOWN_DOTS or c2 in KNOWN_DASHES:
            dot, dash = c1, c2
        elif c2 in KNOWN_DOTS or c1 in KNOWN_DASHES:
            dot, dash = c2, c1
        else:
            dot, dash = c1, c2
        return text.translate(str.maketrans({dot: ".", dash: "-"}))

    out = []
    for ch in text:
        if ch in KNOWN_DOTS:
            out.append(".")
        elif ch in KNOWN_DASHES:
            out.append("-")
        elif not strip_spaces and ch in (" ", "/", "|"):
            out.append(ch)
    return "".join(out)


class _TrieNode:
    __slots__ = ("children", "words")

    def __init__(self) -> None:
        self.children: Dict[str, _TrieNode] = {}
        self.words: List[Tuple[str, float]] = []


class _MorseTrie:
    def __init__(self) -> None:
        self.root = _TrieNode()

    def insert(self, code: str, word: str, score: float) -> None:
        node = self.root
        for sym in code:
            node = node.children.setdefault(sym, _TrieNode())
        node.words.append((word, score))

    def match_prefixes(self, stream: str, start: int) -> List[Tuple[int, str, float]]:
        matches: List[Tuple[int, str, float]] = []
        node = self.root
        idx = start
        n = len(stream)
        while idx < n:
            sym = stream[idx]
            node = node.children.get(sym)
            if node is None:
                break
            idx += 1
            for w, sc in node.words:
                matches.append((idx, w, sc))
        return matches


def _encode_word(word: str) -> Optional[str]:
    parts = []
    for ch in word.upper():
        code = ITU_MORSE.get(ch)
        if code is None:
            return None
        parts.append(code)
    return "".join(parts)


@lru_cache(maxsize=8)
def _load_trie(lang: str) -> Tuple[_MorseTrie, int]:
    trie = _MorseTrie()
    freq_map = {
        "en": "english_words_freq.txt",
        "es": "es_freq.txt",
        "fr": "fr_freq.txt",
        "de": "de_freq.txt",
        "it": "it_freq.txt",
        "ru": "ru_freq.txt",
    }
    freq_path = DATA_DIR / freq_map.get(lang, "english_words_freq.txt")
    enable_path = DATA_DIR / "enable1.txt" if lang == "en" else None

    enable_words: Optional[Set[str]] = None
    if enable_path and enable_path.exists():
        enable_words = {l.strip().upper() for l in enable_path.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip()}

    raw_counts: Dict[str, float] = {}
    total = 0.0
    if freq_path.exists():
        with freq_path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                w = parts[0].upper()
                if enable_words is not None and w not in enable_words and w not in SUPPLEMENTAL_WORDS:
                    continue
                try:
                    cnt = float(parts[1]) if len(parts) > 1 else 1000.0
                except ValueError:
                    cnt = 1000.0
                raw_counts[w] = cnt
                total += cnt
                if len(raw_counts) >= 25000:
                    break

    for w, sc in SUPPLEMENTAL_WORDS.items():
        eq = (10 ** (sc - 1.0)) * 1000.0
        if w not in raw_counts or raw_counts[w] < eq:
            raw_counts[w] = eq
            total += eq

    total = max(total, 1.0)
    count = 0
    for w, cnt in raw_counts.items():
        if len(w) == 1 and w not in ("A", "I"):
            continue
        code = _encode_word(w)
        if code:
            lp = math.log10(cnt / total)
            if len(w) == 1:
                lp = min(lp, -3.5)
            trie.insert(code, w, lp)
            count += 1
    return trie, count


def _beam_decode(stream: str, trie: _MorseTrie, beam_width: int = 120) -> List[Tuple[float, List[str]]]:
    n = len(stream)
    if n == 0:
        return []
    dp: Dict[int, List[Tuple[float, List[str]]]] = {0: [(0.0, [])]}
    for i in range(n):
        if i not in dp:
            continue
        for nxt_i, word, lp in trie.match_prefixes(stream, i):
            bucket = dp.setdefault(nxt_i, [])
            for sc, words in dp[i]:
                bucket.append((sc + lp, words + [word]))
        for k in list(dp.keys()):
            if k > i and len(dp[k]) > beam_width:
                dp[k].sort(key=lambda x: x[0], reverse=True)
                dp[k] = dp[k][:beam_width]
    finals = dp.get(n, [])
    finals.sort(key=lambda x: x[0], reverse=True)
    return finals[:15]


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    raw_text = str(state.get("text", ""))
    mode = str(params.get("mode") or state.get("mode") or "Smooshed Word Beam Search")
    lang = str(params.get("language") or state.get("language") or "en")

    yield {
        "type": "start",
        "state": {"text": raw_text, "mode": mode, "language": lang, "output": "", "candidates": []},
        "highlights": {},
        "desc": f"Processing Morse signal ({mode}, lang={lang})",
        "stats": {"raw_len": len(raw_text)},
    }

    if should_abort():
        return

    if mode == "Encode to Morse":
        words = raw_text.upper().split()
        spaced = " / ".join(" ".join(ITU_MORSE.get(ch, "?") for ch in w) for w in words)
        smooshed = "".join(ITU_MORSE.get(ch, "") for ch in raw_text.upper())
        cands = [
            {"label": "Spaced ITU Morse", "text": spaced},
            {"label": "Smooshed (Unspaced)", "text": smooshed},
        ]
        yield {
            "type": "solution",
            "state": {"text": raw_text, "mode": mode, "language": lang, "output": spaced, "candidates": cands},
            "highlights": {},
            "desc": f"Encoded {len(words)} words to ITU Morse",
            "stats": {"symbols": len(smooshed)},
        }
        return

    if mode == "Spaced Morse Decode":
        rev_itu = {v: k for k, v in ITU_MORSE.items()}
        norm = _normalize_stream(raw_text, strip_spaces=False)
        word_chunks = re.split(r"\s*/\s*|\s{2,}", norm.strip())
        decoded_words = []
        for wc in word_chunks:
            letters = [rev_itu.get(tok, "?") for tok in wc.split() if tok]
            decoded_words.append("".join(letters))
        out = " ".join(decoded_words)
        yield {
            "type": "solution",
            "state": {
                "text": raw_text,
                "mode": mode,
                "language": lang,
                "output": out,
                "candidates": [{"label": "Spaced ITU", "text": out}],
            },
            "highlights": {},
            "desc": f"Decoded spaced Morse: {out}",
            "stats": {"words": len(decoded_words)},
        }
        return

    # Smooshed Word Beam Search (checks Standard, Inverted, Reversed)
    norm = _normalize_stream(raw_text, strip_spaces=True)
    trie, dict_size = _load_trie(lang)
    inv = norm.translate(str.maketrans({".": "-", "-": "."}))
    rev = norm[::-1]
    variants = [("Standard", norm)]
    if inv != norm:
        variants.append(("Inverted (· <-> -)", inv))
    if rev != norm and rev != inv:
        variants.append(("Reversed", rev))

    all_cands: List[Dict[str, Any]] = []
    best_output = ""
    for vname, stream in variants:
        if should_abort():
            return
        hits = _beam_decode(stream, trie)
        for score, words in hits[:6]:
            txt = " ".join(words)
            if not best_output:
                best_output = txt
            all_cands.append({"label": f"{vname} (score {score:.2f})", "text": txt})

    if not all_cands:
        yield {
            "type": "failed",
            "state": {"text": raw_text, "mode": mode, "language": lang, "output": "", "candidates": []},
            "highlights": {},
            "desc": f"No valid word segmentation found for stream '{norm[:40]}'",
            "stats": {"dict_words": dict_size},
        }
        return

    yield {
        "type": "solution",
        "state": {
            "text": raw_text,
            "mode": mode,
            "language": lang,
            "output": best_output,
            "candidates": all_cands,
        },
        "highlights": {},
        "desc": f"Top match: {best_output} ({len(all_cands)} candidates)",
        "stats": {"dict_words": dict_size, "candidates": len(all_cands)},
    }
