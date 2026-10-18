# ASCII Morse Code Solver (`ascii_morse`)

A high-performance algorithmic solver for **unspaced (continuous / "smooshed") Morse code**—the classic `r/morsecode` dilemma where dots and dashes are chained into a single unsegmented stream without spaces.

Rather than producing degenerate single-letter sequences (`ETTTETEEETTEETT`), this tool indexes words directly into a continuous **Morse-Word Trie**, performs **Beam Search / DFS** with unigram log-probability scoring, and writes a ranked report of legible word permutations directly to a `.txt` file.

---

## Features
- **Dictionary-Backed Beam Search**: Uses empirical unigram log-probabilities derived from Google Web 1T and ENABLE1 wordlists (~16,400 clean English words).
- **Suppression of E/T Gibberish**: Restricts standalone single letters strictly to `'A'` and `'I'`, permanently solving the single-letter spam problem.
- **Symbol Auto-Detection**: Normalizes arbitrary symbols (`.`, `-`, `*`, `0`/`1`, `_`, `•`, `—`, phonetic `dit`/`dah`).
- **Multi-Variant Signal Search**: Can simultaneously evaluate Standard, Inverted (`.` $\leftrightarrow$ `-`), Reversed (right-to-left), and Inverted-Reversed signals.
- **Multi-Alphabet Support**: Supports ITU International, American Railroad, Continental / Accented European, Russian Cyrillic, and Japanese Wabun.
- **LLM Pipeline Ready**: Embeds pre-formatted LLM prompts in output files and supports direct piping into local LLMs (e.g. Ollama).

---

## Quick Usage

```powershell
# 1. Basic decode - dumps permutations to permutations.txt in English:
python morse_permutations.py "...---..."

# 2. Decode in another language (Russian, French, German, Spanish, Italian, Japanese):
python morse_permutations.py "-...-..---...-.-.-----..-" --lang ru
python morse_permutations.py "-...-..---...-.-.-----..-" --lang fr
python morse_permutations.py "-...-..---...-.-.-----..-" --lang de

# 3. Symmetric bookend chops (automatically trims ends while bookends are symmetric):
python morse_permutations.py "-...-..---...-.-.-----..-" --chops

# 4. Continuous sentence (e.g. HELLO WORLD) to custom output file:
python morse_permutations.py "......-...-..---.-----.-..-..-.." -o solved.txt

# 5. Test Standard, Inverted, Reversed, and Inverted-Reversed signals with Chops:
python morse_permutations.py "-...-..---...-.-.-----..-" --chops --all-transforms

# 6. Include a structured LLM prompt block at the bottom of the dump:
python morse_permutations.py "......-...-..---.-----.-..-..-.." --llm-prompt -o report.txt

# 7. Pipe permutations directly to a local LLM via Ollama:
python morse_permutations.py "...---..." --pipe-llm "ollama run mistral"
```

---

## CLI Options

| Argument | Description | Default |
|---|---|---|
| `morse_code` or `-c, --code` | Raw Morse string | Positional |
| `-i, --input` | Input text file containing Morse code | None |
| `-o, --output` | Output text file path | `permutations.txt` |
| `-l, --lang` | Language lexicon: `en`, `es`, `fr`, `de`, `ru`, `it`, `ja` | `en` |
| `-a, --alphabet` | Alphabet: `itu`, `continental`, `american`, `cyrillic`, `wabun` | Auto by `--lang` |
| `--chops [N]` | Symmetric bookend chops: trims matched symbols from ends. Auto-detects until symmetry breaks if N is omitted | `0` (off) |
| `-b, --beam-width` | Search beam width | `500` |
| `-m, --max-permutations` | Maximum permutations to output (`0` = unlimited) | `1000` |
| `--min-word-len` | Minimum word length filter | `1` |
| `--all-transforms` | Tests Standard, Inverted, Reversed, and Inverted-Reversed streams | `False` |
| `--exhaustive` | Forces exhaustive DFS search (best for short strings $\le 30$) | `False` |
| `--dict` | Path to custom external wordlist | Built-in |
| `--llm-prompt` | Appends a formatted LLM prompt to the output file | `False` |
| `--pipe-llm` | Shell command to pipe the LLM prompt to on stdin | None |
