"""
Standalone end-to-end smoke test for the JSON Birkenbihl decoder.

Runs the 5 pt→de reference sentences (and a few en→de extras if available)
through the real LLM. Useful for fast prompt iteration without spinning up
Streamlit.

USAGE
-----
PowerShell:
  $env:ANTHROPIC_API_KEY = "sk-ant-..."          # for Claude
  $env:OPENAI_API_KEY    = "sk-..."              # for OpenAI (optional)
  python tests\test_decoder_e2e.py               # defaults to anthropic
  python tests\test_decoder_e2e.py openai        # explicit provider
  python tests\test_decoder_e2e.py anthropic pt  # provider + lang pair filter

Only one of the API keys is required (whichever provider you pick).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Make the repo root importable when running from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.decoder import WordByWordDecoder
from services.llm_service import build_llm_service


TEST_SUITES: dict[tuple[str, str], list[str]] = {
    ("pt", "de"): [
        "Eu tenho saudade de você.",
        "Ela está com fome agora.",
        "Nós vamos chegar tarde hoje à noite.",
        "O menino que eu vi ontem é o filho do meu vizinho.",
        "Quanto mais eu estudo, menos eu entendo.",
    ],
}


def _run_pair(decoder: WordByWordDecoder, src: str, tgt: str, sentences: list[str]) -> None:
    print()
    print("=" * 80)
    print(f"  {src.upper()} → {tgt.upper()}  ({len(sentences)} sentences)")
    print("=" * 80)

    text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(sentences))
    print()
    print("INPUT:")
    print(text)
    print()

    start = time.perf_counter()
    result = decoder.decode(text, source_lang=src, target_lang=tgt, max_line_length=80)
    elapsed = time.perf_counter() - start

    print("DECODED OUTPUT:")
    print(result.aligned_text)
    print()
    if result.comments:
        print("COMMENTS:")
        print(result.comments)
        print()
    print(f"[elapsed: {elapsed:.2f}s]")


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    provider = argv[1] if len(argv) > 1 else "anthropic"
    pair_filter = argv[2] if len(argv) > 2 else None

    env_var = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}.get(provider)
    if not env_var:
        print(f"Unknown provider: {provider!r}. Use 'anthropic' or 'openai'.")
        return 2
    api_key = os.environ.get(env_var)
    if not api_key:
        print(f"Set {env_var} in your environment first.")
        return 2

    print(f"Provider: {provider}")
    service = build_llm_service(provider, api_key)
    print(f"Service name: {service.name}")
    decoder = WordByWordDecoder(service)

    pairs = list(TEST_SUITES.keys())
    if pair_filter:
        pairs = [p for p in pairs if pair_filter in p]
        if not pairs:
            print(f"No test suite matches filter {pair_filter!r}.")
            return 2

    for src, tgt in pairs:
        _run_pair(decoder, src, tgt, TEST_SUITES[(src, tgt)])

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
