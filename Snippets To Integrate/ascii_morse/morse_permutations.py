"""
Braindead r/morsecode Solver - Unspaced / Continuous Morse Permutation Generator.

Takes continuous Morse strings (no spaces, e.g. from Reddit posts), resolves all valid
dictionary-word permutations, prunes single-letter degenerate noise (ETTTETEE),
and writes a scored report of all candidate decodings to a text file.
"""

import argparse
import os
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from morse_alphabets import MorseAlphabet, get_alphabet
from morse_dict import (
    LANGUAGE_CONFIGS,
    MorseDictionary,
    get_default_dictionary,
    transliterate_word,
)
from normalizer import get_all_signal_variants, normalize_morse_stream


class PermutationResult:
    """Represents a single valid segmentation of an unspaced Morse string."""

    __slots__ = ('words', 'score', 'morse_slices', 'char_breakdowns', 'variant')

    def __init__(
        self,
        words: List[str],
        score: float,
        morse_slices: List[str],
        char_breakdowns: List[str],
        variant: str = "Standard",
    ):
        self.words = words
        self.score = score
        self.morse_slices = morse_slices
        self.char_breakdowns = char_breakdowns
        self.variant = variant

    @property
    def text(self) -> str:
        return " ".join(self.words)

    def display_text(self, language: str = "en") -> str:
        """Returns decoded text with Latin transliteration for non-Latin scripts (Cyrillic, Katakana)."""
        base = " ".join(self.words)
        if language in ('ru', 'ja'):
            trans = " ".join(transliterate_word(w, language) for w in self.words)
            return f"{base}  [{trans}]"
        return base

    @property
    def word_count(self) -> int:
        return len(self.words)


class MorseSolver:
    """Core search engine for unspaced Morse code."""

    def __init__(self, dictionary: MorseDictionary):
        self.dictionary = dictionary
        self.alphabet = dictionary.alphabet

    def solve(
        self,
        morse_stream: str,
        beam_width: int = 500,
        max_permutations: int = 1000,
        exhaustive: bool = False,
        variant_name: str = "Standard",
    ) -> List[PermutationResult]:
        """
        Searches for valid word segmentations of morse_stream.
        Uses Beam Search or Exhaustive DFS depending on input length and flags.
        """
        n = len(morse_stream)
        if n == 0:
            return []

        # Decide whether to run exhaustive DFS or Beam Search
        # If exhaustive requested or short string (<= 25 symbols) and max_permutations high
        if exhaustive:
            raw_paths = self._search_dfs(morse_stream, max_permutations=max_permutations)
        else:
            raw_paths = self._search_beam(morse_stream, beam_width=beam_width, max_permutations=max_permutations)

        # Build PermutationResult objects
        results: List[PermutationResult] = []
        for score, words, morse_slices in raw_paths:
            # Build character-by-character breakdown
            char_breakdowns = []
            for word in words:
                char_codes = [self.alphabet.encode_char(ch) or '?' for ch in word]
                char_breakdowns.append(" ".join(char_codes))

            results.append(
                PermutationResult(
                    words=words,
                    score=score,
                    morse_slices=morse_slices,
                    char_breakdowns=char_breakdowns,
                    variant=variant_name,
                )
            )

        # Sort descending by score (most probable first)
        results.sort(key=lambda r: r.score, reverse=True)
        if max_permutations > 0:
            results = results[:max_permutations]

        return results

    def _search_dfs(
        self,
        morse_stream: str,
        max_permutations: int = 1000,
    ) -> List[Tuple[float, List[str], List[str]]]:
        """Exhaustive DFS for discovering 100% of valid permutations on short inputs."""
        n = len(morse_stream)
        results: List[Tuple[float, List[str], List[str]]] = []

        def dfs(idx: int, path_score: float, path_words: List[str], path_slices: List[str]):
            if max_permutations > 0 and len(results) >= max_permutations:
                return
            if idx == n:
                results.append((path_score, list(path_words), list(path_slices)))
                return

            for next_idx, word, log_p in self.dictionary.trie.match_prefixes(morse_stream, idx):
                word_slice = morse_stream[idx:next_idx]
                dfs(next_idx, path_score + log_p, path_words + [word], path_slices + [word_slice])

        dfs(0, 0.0, [], [])
        return results

    def _search_beam(
        self,
        morse_stream: str,
        beam_width: int = 500,
        max_permutations: int = 1000,
    ) -> List[Tuple[float, List[str], List[str]]]:
        """Dynamic programming / Beam Search for medium-to-long inputs."""
        n = len(morse_stream)
        # dp[i] = list of (score, words, morse_slices) ending at index i
        dp: Dict[int, List[Tuple[float, List[str], List[str]]]] = {0: [(0.0, [], [])]}

        for i in range(n):
            if i not in dp:
                continue

            current_paths = dp[i]
            matches = self.dictionary.trie.match_prefixes(morse_stream, i)

            for next_i, word, log_p in matches:
                word_slice = morse_stream[i:next_i]
                if next_i not in dp:
                    dp[next_i] = []

                for prev_score, words, slices in current_paths:
                    dp[next_i].append((prev_score + log_p, words + [word], slices + [word_slice]))

            # Prune states that advanced past i
            for k in list(dp.keys()):
                if k > i and len(dp[k]) > beam_width:
                    dp[k].sort(key=lambda x: x[0], reverse=True)
                    dp[k] = dp[k][:beam_width]

        final_paths = dp.get(n, [])
        return final_paths


def build_llm_prompt(raw_stream: str, results: List[PermutationResult], top_n: int = 20) -> str:
    """Formats the top results into an LLM prompt ready for piping or copy-pasting."""
    candidates_text = []
    for rank, res in enumerate(results[:top_n], start=1):
        candidates_text.append(f"{rank}. {res.text} (Score: {res.score:.2f}, Words: {res.word_count})")

    prompt = f"""You are an expert cryptanalyst and Morse code specialist reviewing an unspaced Morse code puzzle.
The raw continuous Morse code signal is:
"{raw_stream}"

An algorithmic dictionary solver identified the following candidate word-level decodings, ranked by linguistic probability:

{chr(10).join(candidates_text)}

Tasks:
1. Determine which candidate decoding is the most coherent, intentional human message.
2. If there are multiple reasonable interpretations, explain the differences.
3. If the message appears to suffer from a minor transmission error (e.g. a dropped or extra dit/dah), identify the likely intended word.
4. Output your final recommended plaintext clearly.
"""
    return prompt


def compute_symmetric_chops(stream: str, requested_chops: int) -> Tuple[int, List[Tuple[int, str, str, str]], int]:
    """
    Computes symmetric bookend chops while stream[i] == stream[-1-i].
    Returns (num_chops, chop_details, max_symmetric) where chop_details contains:
      (level, chopped_stream, left_trimmed, right_trimmed)
    """
    n = len(stream)
    max_symmetric = 0
    while max_symmetric < n // 2:
        if stream[max_symmetric] == stream[-1 - max_symmetric]:
            max_symmetric += 1
        else:
            break

    if requested_chops == -1:
        # Auto mode: chop until symmetry is broken
        num_chops = max_symmetric
    else:
        num_chops = min(requested_chops, n // 2)

    chop_details = []
    for k in range(1, num_chops + 1):
        sub_stream = stream[k:-k]
        left_sym = stream[k - 1]
        right_sym = stream[-k]
        chop_details.append((k, sub_stream, left_sym, right_sym))

    return num_chops, chop_details, max_symmetric


def write_permutations_file(
    filepath: str,
    raw_input: str,
    normalized_stream: str,
    alphabet_name: str,
    results_by_level: Optional[Dict[int, Dict[str, List[PermutationResult]]]] = None,
    elapsed_time: float = 0.0,
    dict_word_count: int = 0,
    language: str = "en",
    chop_meta: Optional[Dict[int, Tuple[str, str, str]]] = None,
    include_llm_prompt: bool = True,
    as_json: bool = False,
    verbose: bool = False,
    results_by_variant: Optional[Dict[str, List[PermutationResult]]] = None,
) -> None:
    """Writes a lean, LLM-parseable permutation report (text or JSON)."""
    import json

    if results_by_level is None:
        if results_by_variant is not None:
            results_by_level = {0: results_by_variant}
        else:
            results_by_level = {0: {}}

    total_permutations = sum(len(res) for lvl in results_by_level.values() for res in lvl.values())

    # Count breakdown by variant / transform type
    variant_totals: Dict[str, int] = {}
    for lvl_results in results_by_level.values():
        for vname, results in lvl_results.items():
            variant_totals[vname] = variant_totals.get(vname, 0) + len(results)

    # Count breakdown by level (Full vs Chops)
    level_totals: Dict[int, int] = {
        lvl: sum(len(results) for results in lvl_results.values())
        for lvl, lvl_results in results_by_level.items()
    }

    # Bead / symbol count breakdown
    n_dits = normalized_stream.count('.')
    n_dahs = normalized_stream.count('-')

    # 1. Output as JSON if requested or if filename ends in .json
    if as_json or filepath.lower().endswith('.json'):
        data = {
            "metadata": {
                "raw_input": raw_input,
                "normalized_morse": normalized_stream,
                "symbols": len(normalized_stream),
                "symbol_counts": {"dits": n_dits, "dahs": n_dahs},
                "alphabet": alphabet_name,
                "language": language,
                "dictionary_size": dict_word_count,
                "elapsed_seconds": round(elapsed_time, 3),
                "total_permutations": total_permutations,
                "variant_breakdown": variant_totals,
                "level_breakdown": {("full" if k == 0 else f"chop_{k}"): v for k, v in level_totals.items()},
            },
            "permutations": {},
        }
        for level in sorted(results_by_level.keys()):
            lvl_key = "full" if level == 0 else f"chop_{level}"
            lvl_data = {}
            if level > 0 and chop_meta and level in chop_meta:
                sub_s, l_t, r_t = chop_meta[level]
                lvl_data["_meta"] = {
                    "level": level,
                    "symbols": len(sub_s),
                    "stream": sub_s,
                    "trimmed_left": l_t,
                    "trimmed_right": r_t,
                }
            for vname, results in results_by_level[level].items():
                lvl_data[vname] = [
                    {
                        "rank": idx,
                        "score": round(r.score, 2),
                        "text": r.display_text(language),
                        "words": r.word_count,
                    }
                    for idx, r in enumerate(results, start=1)
                ]
            data["permutations"][lvl_key] = lvl_data

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return

    # 2. Output as lean, high-density text format (LLM friendly)
    lines: List[str] = [
        f"# Morse Permutation Report",
        f"# Input:    {normalized_stream} ({len(normalized_stream)} symbols: {n_dits} dits '.', {n_dahs} dahs '-')",
        f"# Language: {language.upper()} | Alphabet: {alphabet_name}",
        f"# Lexicon:  {dict_word_count:,} words | Time: {elapsed_time:.3f}s",
        f"# Matches:  {total_permutations:,} total permutation(s) found",
    ]
    if variant_totals:
        var_breakdown_str = " | ".join(f"{v}: {cnt:,}" for v, cnt in variant_totals.items())
        lines.append(f"# Variants: {var_breakdown_str}")
    if chop_meta and len(chop_meta) > 0:
        lvl_breakdown_str = " | ".join(
            f"{'Full' if lvl == 0 else f'Chop {lvl}'}: {cnt:,}"
            for lvl, cnt in sorted(level_totals.items())
        )
        lines.append(f"# Chops:    {len(chop_meta)} symmetric level(s) evaluated ({lvl_breakdown_str})")
    lines.append("")

    if total_permutations == 0:
        lines.append("# NO VALID WORD PERMUTATIONS FOUND.")
    else:
        for level in sorted(results_by_level.keys()):
            lvl_results = results_by_level[level]
            if level == 0:
                sec_header = f"[FULL SIGNAL: {normalized_stream}]"
            else:
                sub_s, l_t, r_t = chop_meta[level] if chop_meta else ("", "", "")
                sec_header = f"[CHOP {level}: Trimmed '{l_t}' & '{r_t}' -> {len(sub_s)} syms: {sub_s}]"

            for variant_name, results in lvl_results.items():
                if not results:
                    continue
                lines.append(f"{sec_header} - {variant_name} ({len(results)} matches)")
                for rank, r in enumerate(results, start=1):
                    if verbose:
                        lines.append(f"{rank:4d}. [Score: {r.score:6.2f}] {r.display_text(language)} ({r.word_count} words)")
                        lines.append(f"      Slices: {' / '.join(r.morse_slices)}")
                        lines.append(f"      Chars:  {' / '.join(r.char_breakdowns)}")
                    else:
                        lines.append(f"{rank:4d}. [Score: {r.score:6.2f}] {r.display_text(language)} ({r.word_count} words)")
                lines.append("")

    if include_llm_prompt and total_permutations > 0:
        best_results = []
        for lvl in sorted(results_by_level.keys()):
            for v_res in results_by_level[lvl].values():
                if v_res:
                    best_results.extend(v_res[:10])
        best_results.sort(key=lambda r: r.score, reverse=True)
        if best_results:
            lines.append("--------------------------------------------------------------------------------")
            lines.append("LLM PROMPT (Context prompt for downstream LLM evaluation):")
            lines.append("--------------------------------------------------------------------------------")
            lines.append(build_llm_prompt(normalized_stream, best_results[:25], top_n=25))

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))


def preprocess_argv(argv: List[str]) -> List[str]:
    """
    Detects if an argument starting with '-' or '--' is actually a Morse code string
    (e.g. '---...---') rather than a command line flag, and reorders it after flags.
    """
    known_flags = {
        '-h', '--help', '-i', '--input', '-o', '--output',
        '-a', '--alphabet', '-b', '--beam-width', '-m', '--max-permutations',
        '-c', '--code', '-l', '--lang', '--chops', '--json', '--verbose',
        '--min-word-len', '--allow-single-letters', '--all-transforms',
        '--exhaustive', '--dict', '--llm-prompt', '--pipe-llm'
    }
    morse_symbols = {'.', '-', '*', '_', '0', '1', '•', '—', '·', '●'}

    flags: List[str] = []
    morse_arg: Optional[str] = None

    i = 0
    while i < len(argv):
        arg = argv[i]
        if morse_arg is None and set(arg) <= morse_symbols and arg not in known_flags:
            morse_arg = arg
            i += 1
            continue
        flags.append(arg)
        i += 1

    if morse_arg is not None:
        flags.extend(['--', morse_arg])

    return flags


def main():
    parser = argparse.ArgumentParser(
        description="Unspaced / continuous Morse code solver. Brute-forces word permutations and dumps to a text file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Decode unspaced Morse string directly in English:
  python morse_permutations.py "...---..."

  # Decode in Russian Cyrillic:
  python morse_permutations.py "-...-..---...-.-.-----..-" --lang ru

  # Automatic symmetric bookend chops (until symmetry is broken):
  python morse_permutations.py "-...-..---...-.-.-----..-" --chops

  # Try standard, inverted, reversed, and inverted-reversed signal variants:
  python morse_permutations.py "---...---" --all-transforms

  # Pipe directly into Ollama:
  python morse_permutations.py "...---..." --pipe-llm "ollama run mistral"
        """,
    )

    parser.add_argument("morse_code", nargs="?", default=None, help="Raw Morse code string (unspaced or spaced)")
    parser.add_argument("-c", "--code", help="Raw Morse code string (explicit flag)")
    parser.add_argument("-i", "--input", help="Path to input text file containing Morse code")
    parser.add_argument("-o", "--output", default="permutations.txt", help="Path to output text file (default: permutations.txt)")
    parser.add_argument(
        "-l", "--lang",
        default="en",
        choices=["en", "es", "fr", "de", "ru", "it", "ja"],
        help="Target language lexicon (default: en). Choices: en, es, fr, de, ru, it, ja",
    )
    parser.add_argument(
        "-a", "--alphabet",
        default=None,
        choices=["itu", "continental", "american", "cyrillic", "wabun"],
        help="Morse alphabet mapping (default: auto-detected from --lang)",
    )
    parser.add_argument(
        "--chops",
        nargs="?",
        const=-1,
        type=int,
        default=0,
        help="Symmetric bookend chops: test trimming symbols from both ends. If no number is given, chops automatically until bookend symmetry breaks (s[i] != s[-1-i]).",
    )
    parser.add_argument("-b", "--beam-width", type=int, default=500, help="Beam width for search (default: 500)")
    parser.add_argument("-m", "--max-permutations", type=int, default=1000, help="Max permutations to output (default: 1000, 0=unlimited)")
    parser.add_argument("--min-word-len", type=int, default=1, help="Minimum character length per word (default: 1)")
    parser.add_argument("--allow-single-letters", action="store_true", help="Allow all standalone single letters (WARNING: produces E/T spam)")
    parser.add_argument("--all-transforms", action="store_true", help="Test Standard, Inverted, Reversed, and Inverted-Reversed signals")
    parser.add_argument("--exhaustive", action="store_true", help="Force exhaustive DFS search (best for short strings <= 30 symbols)")
    parser.add_argument("--dict", dest="custom_dict", help="Path to custom wordlist file")
    parser.add_argument("--json", action="store_true", help="Output report in clean, structured JSON format")
    parser.add_argument("--verbose", action="store_true", help="Include deep debug breakdowns (Morse slices & char breakdowns)")
    parser.add_argument("--llm-prompt", action="store_true", help="Include formatted LLM prompt in output file")
    parser.add_argument("--pipe-llm", help="Shell command to pipe the LLM prompt to (e.g. 'ollama run mistral')")

    cleaned_argv = preprocess_argv(sys.argv[1:])
    args = parser.parse_args(cleaned_argv)

    # Get input string
    raw_input = ""
    if args.code:
        raw_input = args.code.strip()
    elif args.input:
        if not os.path.exists(args.input):
            print(f"[-] Error: Input file '{args.input}' not found.", file=sys.stderr)
            sys.exit(1)
        with open(args.input, 'r', encoding='utf-8') as f:
            raw_input = f.read().strip()
    elif args.morse_code:
        raw_input = args.morse_code.strip()
    else:
        parser.print_help()
        sys.exit(1)

    # Normalize input stream
    normalized_stream = normalize_morse_stream(raw_input)
    if not normalized_stream:
        print("[-] Error: Input did not contain recognizable Morse symbols (dots/dashes).", file=sys.stderr)
        sys.exit(1)

    print(f"[+] Raw input:        {raw_input[:60]}{'...' if len(raw_input) > 60 else ''}")
    print(f"[+] Normalized Morse: {normalized_stream} ({len(normalized_stream)} symbols)")

    # Language & alphabet selection
    target_lang = args.lang.lower().strip()
    lang_cfg = LANGUAGE_CONFIGS.get(target_lang, LANGUAGE_CONFIGS['en'])
    alphabet_key = args.alphabet if args.alphabet else lang_cfg['default_alphabet']
    alphabet = get_alphabet(alphabet_key)

    print(f"[+] Language:         {lang_cfg['name']} ({target_lang})")
    print(f"[+] Morse Alphabet:   {alphabet.name} ({alphabet_key})")
    print(f"[+] Loading dictionary ({lang_cfg['name']})...")
    t_start_load = time.time()

    if args.custom_dict:
        dict_obj = MorseDictionary(
            alphabet=alphabet,
            language=target_lang,
            allow_single_letters=args.allow_single_letters,
            min_word_len=args.min_word_len,
        )
        dict_obj.load_custom_wordlist(args.custom_dict)
    else:
        dict_obj = get_default_dictionary(
            alphabet=alphabet,
            language=target_lang,
            allow_single_letters=args.allow_single_letters,
            min_word_len=args.min_word_len,
        )

    t_load = time.time() - t_start_load
    print(f"[+] Loaded {dict_obj.trie.total_words:,} words in {t_load:.3f}s")

    # Symmetric bookend chops
    chop_meta: Dict[int, Tuple[str, str, str]] = {}
    levels_to_run: List[Tuple[int, str, str, str]] = [(0, normalized_stream, "", "")]

    if args.chops != 0:
        num_chops, chop_details, max_sym = compute_symmetric_chops(normalized_stream, args.chops)
        print(f"[+] Symmetric chops requested: {num_chops} level(s) available.")
        if max_sym < len(normalized_stream) // 2:
            s_left = normalized_stream[max_sym]
            s_right = normalized_stream[-1 - max_sym]
            print(f"[+] Note: Bookend symmetry breaks at index {max_sym} ('{s_left}' vs '{s_right}')")
        for k, sub_s, l_t, r_t in chop_details:
            chop_meta[k] = (sub_s, l_t, r_t)
            levels_to_run.append((k, sub_s, l_t, r_t))

    # Execute search
    solver = MorseSolver(dict_obj)
    results_by_level: Dict[int, Dict[str, List[PermutationResult]]] = {}
    t_start_solve = time.time()

    for level, stream, l_trim, r_trim in levels_to_run:
        results_by_variant: Dict[str, List[PermutationResult]] = {}
        if args.all_transforms:
            variants = get_all_signal_variants(stream)
        else:
            variants = {'Standard': stream}

        for variant_label, s_stream in variants.items():
            res = solver.solve(
                morse_stream=s_stream,
                beam_width=args.beam_width,
                max_permutations=args.max_permutations,
                exhaustive=args.exhaustive,
                variant_name=variant_label,
            )
            if res or not args.all_transforms:
                results_by_variant[variant_label] = res

        results_by_level[level] = results_by_variant

    elapsed_solve = time.time() - t_start_solve
    total_found = sum(len(res) for lvl in results_by_level.values() for res in lvl.values())

    print(f"[+] Search completed in {elapsed_solve:.3f}s")
    print(f"[+] Found {total_found} total word permutations across {len(levels_to_run)} level(s)")

    # Display Top results to console
    for level in sorted(results_by_level.keys()):
        lvl_res = results_by_level[level]
        if level == 0:
            header = "=== FULL SIGNAL ==="
        else:
            sub_s, l_t, r_t = chop_meta[level]
            header = f"=== CHOP LEVEL {level} (Trimmed '{l_t}' & '{r_t}' -> {len(sub_s)} symbols) ==="

        has_any = any(bool(r) for r in lvl_res.values())
        if has_any:
            print(f"\n{header}")
            for variant_label, res in lvl_res.items():
                if res:
                    print(f"  [{variant_label}]:")
                    for idx, r in enumerate(res[:3], start=1):
                        print(f"    #{idx} [Score: {r.score:6.2f}] \"{r.display_text(target_lang)}\" ({r.word_count} words)")

    # Write output report to text or JSON file
    write_permutations_file(
        filepath=args.output,
        raw_input=raw_input,
        normalized_stream=normalized_stream,
        alphabet_name=alphabet.name,
        language=target_lang,
        results_by_level=results_by_level,
        elapsed_time=elapsed_solve,
        dict_word_count=dict_obj.trie.total_words,
        chop_meta=chop_meta if chop_meta else None,
        include_llm_prompt=args.llm_prompt or bool(args.pipe_llm),
        as_json=args.json,
        verbose=args.verbose,
    )
    print(f"\n[+] Successfully dumped all permutations to: {args.output}")

    # Pipe to LLM if requested
    if args.pipe_llm and total_found > 0:
        flat_results = []
        for lvl in sorted(results_by_level.keys()):
            for v_res in results_by_level[lvl].values():
                flat_results.extend(v_res)
        flat_results.sort(key=lambda r: r.score, reverse=True)
        prompt = build_llm_prompt(normalized_stream, flat_results[:25])
        print(f"[+] Piping LLM prompt to command: {args.pipe_llm}")
        try:
            proc = subprocess.Popen(
                args.pipe_llm,
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = proc.communicate(input=prompt)
            print("\n[+] LLM Response:")
            print(stdout)
            if stderr:
                print(f"[-] LLM stderr: {stderr}", file=sys.stderr)
        except Exception as e:
            print(f"[-] Error piping to LLM command: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
