"""Classical Cipher & Encoding Workbench (merged from cipher_tools/ciphers.py & decodebox.py)."""

from __future__ import annotations

import base64
import binascii
from collections import Counter
from typing import Any, Callable, Dict, Generator, List, Tuple

META: Dict[str, Any] = {
    "slug": "cipher_suite",
    "name": "Cipher & Frequency Suite",
    "category": "Crypt & Signal",
    "renderer": "text",
    "description": "Caesar/ROT brute-force, Atbash, Reverse, Vigenère, Base64/Hex/Binary, and character frequency analysis.",
    "presets": {
        "Caesar": {
            "text": "(13) Gur Chmmyr Ynj vf nyvir!",
            "mode": "Caesar Auto / Brute-Force",
            "key": "3",
        },
        "ROT13": {
            "text": "Uryyb Jbeyq! Frperg Pbqr.",
            "mode": "Caesar Auto / Brute-Force",
            "key": "",
        },
        "Atbash": {
            "text": "Gsv KfAAov Ozd",
            "mode": "Atbash",
            "key": "",
        },
        "Base64": {
            "text": "VGhlIFB1enpsZSBMYXcgVjI=",
            "mode": "Base64 Decode",
            "key": "",
        },
        "Hex": {
            "text": "5468652050757a7a6c65204c6177",
            "mode": "Hex Decode",
            "key": "",
        },
    },
    "params": [
        {
            "key": "mode",
            "label": "Cipher / Transform",
            "type": "select",
            "default": "Caesar Auto / Brute-Force",
            "options": [
                "Caesar Auto / Brute-Force",
                "Caesar Shift",
                "Atbash",
                "Reverse",
                "Vigenere Decrypt",
                "Vigenere Encrypt",
                "Base64 Decode",
                "Base64 Encode",
                "Hex Decode",
                "Hex Encode",
                "Binary Decode",
            ],
        },
        {"key": "key", "label": "Shift / Key", "type": "text", "default": ""},
    ],
}

ENGLISH_FREQ_SCORE = set("ETAOINSHRDLCUMWFGYPBVKJXQZ ")


def _caesar_shift_text(text: str, shift: int) -> str:
    out = []
    for ch in text:
        if "a" <= ch <= "z":
            out.append(chr(((ord(ch) - ord("a") + shift) % 26) + ord("a")))
        elif "A" <= ch <= "Z":
            out.append(chr(((ord(ch) - ord("A") + shift) % 26) + ord("A")))
        else:
            out.append(ch)
    return "".join(out)


def _caesar_prefixed(text: str) -> Tuple[int | None, str | None]:
    """Support cipher_tools/ciphers.py '(N)text' convention."""
    s = text.find("(")
    e = text.find(")")
    if s != -1 and e > s:
        try:
            shift = int(text[s + 1 : e])
            return shift, _caesar_shift_text(text[e + 1 :], shift)
        except ValueError:
            return None, None
    return None, None


def _atbash(text: str) -> str:
    out = []
    for ch in text:
        if "a" <= ch <= "z":
            out.append(chr(ord("a") + ord("z") - ord(ch)))
        elif "A" <= ch <= "Z":
            out.append(chr(ord("A") + ord("Z") - ord(ch)))
        else:
            out.append(ch)
    return "".join(out)


def _vigenere(text: str, key: str, decrypt: bool = True) -> str:
    clean_key = [ord(c.upper()) - ord("A") for c in key if c.isalpha()]
    if not clean_key:
        raise ValueError("Vigenère requires an alphabetic key.")
    out = []
    ki = 0
    for ch in text:
        if ch.isalpha():
            shift = clean_key[ki % len(clean_key)]
            if decrypt:
                shift = -shift
            base = ord("a") if ch.islower() else ord("A")
            out.append(chr(((ord(ch) - base + shift) % 26) + base))
            ki += 1
        else:
            out.append(ch)
    return "".join(out)


def _char_frequencies(text: str) -> List[Dict[str, Any]]:
    counts = Counter(ch.lower() for ch in text if not ch.isspace())
    total = sum(counts.values()) or 1
    return [
        {"char": ch, "count": cnt, "pct": round(cnt / total * 100, 1)}
        for ch, cnt in counts.most_common(20)
    ]


def _english_likeness(text: str) -> int:
    up = text.upper()
    score = sum(1 for c in up if c in "ETAOINSHRDLU")
    for w in ("THE", "AND", "IS", "IN", "TO", "OF", "PUZZLE", "CODE", "LAW"):
        if w in up:
            score += 10
    return score


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    raw_text = str(state.get("text", ""))
    mode = str(params.get("mode") or state.get("mode") or "Caesar Auto / Brute-Force")
    key = str(params.get("key") if params.get("key") not in (None, "") else state.get("key", ""))
    freqs = _char_frequencies(raw_text)

    yield {
        "type": "start",
        "state": {
            "text": raw_text,
            "mode": mode,
            "key": key,
            "output": "",
            "candidates": [],
            "frequencies": freqs,
        },
        "highlights": {},
        "desc": f"Loaded {len(raw_text)} chars ({len(freqs)} unique symbols) -> {mode}",
        "stats": {"length": len(raw_text), "unique": len(freqs)},
    }

    if should_abort():
        return

    candidates: List[Dict[str, Any]] = []
    output = ""

    if mode == "Caesar Auto / Brute-Force":
        explicit_shift, explicit_res = _caesar_prefixed(raw_text)
        if explicit_shift is not None and explicit_res is not None:
            candidates.append({"label": f"Explicit Shift ({explicit_shift:+d})", "text": explicit_res})
            output = explicit_res
        all_rots = []
        for s in range(1, 26):
            dec = _caesar_shift_text(raw_text, -s)
            all_rots.append((_english_likeness(dec), s, dec))
        all_rots.sort(key=lambda x: x[0], reverse=True)
        for score, s, dec in all_rots[:8]:
            candidates.append({"label": f"ROT-{s:02d} (score {score})", "text": dec})
        if not output and all_rots:
            output = all_rots[0][2]

    elif mode == "Caesar Shift":
        shift = int(key) if key.strip().lstrip("-+").isdigit() else 13
        output = _caesar_shift_text(raw_text, shift)
        candidates.append({"label": f"Shift {shift:+d}", "text": output})

    elif mode == "Atbash":
        output = _atbash(raw_text)
        candidates.append({"label": "Atbash (A<->Z)", "text": output})

    elif mode == "Reverse":
        output = raw_text[::-1]
        candidates.append({"label": "Reversed String", "text": output})

    elif mode in ("Vigenere Decrypt", "Vigenere Encrypt"):
        output = _vigenere(raw_text, key or "KEY", decrypt=(mode == "Vigenere Decrypt"))
        candidates.append({"label": f"{mode} (key={key or 'KEY'})", "text": output})

    elif mode == "Base64 Decode":
        padded = raw_text.strip()
        padded += "=" * ((4 - len(padded) % 4) % 4)
        raw_bytes = base64.b64decode(padded, validate=False)
        output = raw_bytes.decode("utf-8", errors="replace")
        candidates.append({"label": "Base64 UTF-8", "text": output})

    elif mode == "Base64 Encode":
        output = base64.b64encode(raw_text.encode("utf-8")).decode("ascii")
        candidates.append({"label": "Base64 Encoded", "text": output})

    elif mode == "Hex Decode":
        cleaned = "".join(raw_text.split())
        output = binascii.unhexlify(cleaned).decode("utf-8", errors="replace")
        candidates.append({"label": "Hex UTF-8", "text": output})

    elif mode == "Hex Encode":
        output = raw_text.encode("utf-8").hex()
        candidates.append({"label": "Hex Encoded", "text": output})

    elif mode == "Binary Decode":
        bits = "".join(ch for ch in raw_text if ch in "01")
        chunks = [bits[i : i + 8] for i in range(0, len(bits) - (len(bits) % 8), 8)]
        output = "".join(chr(int(b, 2)) for b in chunks)
        candidates.append({"label": f"8-bit ASCII ({len(chunks)} bytes)", "text": output})

    yield {
        "type": "solution",
        "state": {
            "text": raw_text,
            "mode": mode,
            "key": key,
            "output": output,
            "candidates": candidates,
            "frequencies": freqs,
        },
        "highlights": {},
        "desc": f"Decoded with {mode}: {output[:60]}",
        "stats": {"candidates": len(candidates), "output_len": len(output)},
    }
