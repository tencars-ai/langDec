# Decoder Prompting Rules

How langDec instructs LLMs to produce Birkenbihl word-by-word decodings, plus
the lessons that shaped the current approach.

Stand: after the JSON→Plain-Text refactor.

---

## 1. Goal

The Birkenbihl method shows learners the **literal** word-for-word mapping
between source and target language. The decoded output is intentionally
ungrammatical in the target language — that's the point. To render the
output as two aligned monospace lines, the decoder needs **one target entry
per source word**, no more, no less.

Everything else in this document follows from that single invariant.

---

## 2. Output Format

The LLM returns **plain text** — no JSON, no markdown, no labels.

```
Source:        Eu tenho saudade de você.
Word-by-word:  Ich habe Sehnsucht von dir.
```

- One **plain-text line per source line**, in the same order as the input.
- Tokens are **whitespace-separated**.
- `len(target.split()) == len(source.split())` per line.

---

## 3. Notation Conventions

Two special markers handle the cases where a strict 1:1 word mapping is
linguistically impossible.

### 3.1 Hyphen (`-`) — one source word → multiple target words

Use when a single source word needs multiple target words to convey its
meaning. The resulting target tokens are joined into **one entry**.

```
vamos   → werden-wir          (verb + person, Portuguese future auxiliary)
à       → zu-die              (em + a contraction)
do      → von-dem             (de + o contraction)
no      → in-dem              (em + o contraction)
ao      → zu-dem              (a + o contraction)
neste   → in-diesem           (em + este contraction)
```

### 3.2 Empty brackets (`[]`) — source word with no target equivalent

Use when a source word is a linking particle, idiom filler, or grammatical
marker with no direct counterpart in the target language. The bracket acts
as a placeholder so the token count stays balanced.

```
a fazer        → []   machen      (Portuguese "a" before infinitive)
a impressionar → []   beeindrucken
do que         → von-dem []      (Portuguese comparative marker)
```

### 3.3 What NEVER happens

Two source words MUST NOT be merged into one hyphenated entry:

```
ter mostrado  →  haben-gezeigt    ← FORBIDDEN
ter mostrado  →  haben gezeigt    ← correct (two separate entries)
```

The hyphen is **strictly directional**: one source word → multiple target
words. Never the other way around.

---

## 4. Lessons Learned (chronological)

### 4.1 JSON with schema enforcement was over-engineered

We initially used OpenAI `response_format=json_schema strict` and Anthropic
`tool_use input_schema` to guarantee structural validity. It worked, but:

- System prompt was ~9000 characters with schema description + examples
  rendered as JSON. Long prompts erode rule adherence on smaller models.
- The LLM spent output tokens on JSON syntax instead of translation.
- Schema enforcement only guarantees **structure**, never **semantics**.
- Plain text is the format LLMs were trained on most heavily — they obey
  format rules better when the format is natural prose.

**Switch:** moved to plain-text output. System prompt dropped from ~9000 to
~5300 chars. Anweisungstreue measurably improved (Haiku 4.5: 243/246 →
246/246 tokens correct on the 8-sentence test corpus).

### 4.2 The LLM gets the hyphen direction wrong without explicit framing

Early prompt said: *"Concatenate grammatical helper words with '-' behind the
translated word."* Haiku 4.5 read this as **bidirectional** and produced:

```
ter mostrado  → haben-gezeigt     (two source words merged into one)
poderá oferecer → könnte-bieten   (modal + verb merged)
vai decorrer  → wird-verlaufen    (auxiliary + verb merged)
```

This destroyed the 1:1 count guarantee.

**Fix:** explicit asymmetric framing in the rule, with a negative example:

> If a source word needs MULTIPLE target words, join them with "-" into ONE
> entry. NEVER merge two source words into one entry with "-". Example:
> `ter mostrado → haben gezeigt` (two entries), NOT `haben-gezeigt`.

### 4.3 Negative examples alone are weak

Adding only the *negative* example (`NEVER produce X`) didn't change Haiku's
behavior — the same merges still occurred. The model parsed the rule but
treated common idioms (`do que`, `poderá oferecer`) as "concept-level fusion"
and applied the hyphen anyway.

**Fix:** combine three things:
1. The rule itself, asymmetrically phrased.
2. A **positive** example showing the correct shape.
3. A **negative** example showing the forbidden shape.
4. The empty-bracket escape valve `[]` for unsolvable 2→1 cases.

After this, the same model produced 246/246 perfectly.

### 4.4 Empty brackets solved the 2→1 idiomatic case

Some source pairs genuinely have only one target equivalent — e.g. Portuguese
`do que` (comparative marker) is just `als` in German. Without an escape
valve, the LLM either merged into `als` (1 token, count-1) or rephrased.

**Fix:** `[]` is a legitimate target entry. `do que → von-dem []` preserves
the count, lets the learner see "the second source word has no direct
counterpart," and keeps the alignment intact.

The same mechanism handles the European Portuguese pre-infinitive `a`:
`a fazer → [] machen`.

### 4.5 The per-word fallback is a hidden source of weird output

When a Birkenbihl-line mismatch triggers per-word fallback, the decoder
makes one `translate_word()` call per source token. Haiku 4.5 likes to
explain proper names: a single call for `"Italo"` once returned:

```
Italo (This is a proper name/noun that remains the same in German)
```

That whole string then landed as a `TokenPair.target_token` and blew up the
column alignment.

**Fix in `translate_word`:**
1. **Tighter system prompt:** explicit prohibition of parentheses,
   explanations, alternatives, and quotes. Plus: "If proper name → return
   UNCHANGED."
2. **`max_tokens = 64`** caps any runaway explanation at the API layer.
3. **`_clean_word_translation`** post-processor: strips `(…)` asides, takes
   only the first non-empty line, collapses any internal whitespace to a
   hyphen.

**Fix in the main-path parser:**
4. **`_extract_word_by_word_lines`** drops lines that are purely
   parenthetical (`(...)`) and strips inline parentheticals from kept lines.

### 4.6 What didn't help

- **Sprach-paar-spezifische Hint-Listen** alone (just disambiguations
  without examples) — Haiku ignored them under prompt-length pressure.
- **Long system prompts with redundant rules** — the 9000-char JSON-era
  prompt led to *worse* adherence than the 5300-char plain-text version.
- **Numbered list prefixes in the user prompt** (`1.`, `2.`) — Haiku
  occasionally treated them as source tokens and translated them to `eins`,
  `zwei`. Replaced with `[L1]`, `[L2]` brackets and explicit "these are line
  labels, not tokens to decode."

---

## 5. The Final Rule Set

### 5.1 Universal rules (`prompts/_default.yaml`)

```
1. The output must have EXACTLY the same number of entries (whitespace-
   separated tokens) as the source has words. Each source word gets exactly
   ONE target entry.

2. If a source word needs MULTIPLE target words to convey its meaning, join
   them with "-" into ONE entry — e.g. "vamos → werden-wir", "à → zu-die".

3. If a source word has NO direct target equivalent (linking particles,
   idiom fillers, infinitive markers), use "[]" (empty square brackets) as
   its target entry.

4. NEVER merge two source words into one entry with "-". The hyphen rule is
   ONLY for one source word producing multiple target words — never the
   reverse.

5. Preserve the original source word order.

6. If the output sounds fluent and natural, it is WRONG. Birkenbihl is
   intentionally literal.

7. Preserve the source word's capitalization. EXCEPTION: German nouns may
   keep their canonical capitalization.
```

### 5.2 Anti-patterns (also in `_default.yaml`)

- Merging two source words into one hyphenated target.
- Outputting fewer or more target entries than source words.
- Natural rephrasing.
- Markdown formatting, code fences, headers, prose.
- Filled square brackets `[werden]`, `[note: ...]` — only empty `[]` is allowed.
- Multiple alternatives separated by `/` or `or`.

### 5.3 Pair-specific rules (`prompts/<src>_<tgt>.yaml`)

Each language pair adds rules for its idiosyncrasies. For Portuguese → German
(`pt_de.yaml`), the key entries are:

- **Contractions** (preposition + article) → hyphenated single entry:
  `do → von-dem`, `na → in-der`, `à → zu-die`.
- **Periphrastic future** (`ir + infinitive`): each word stays separate,
  the auxiliary keeps person via hyphen: `vamos chegar → werden-wir ankommen`.
- **Subject pronoun present** → don't repeat person in the verb:
  `eu tenho → ich habe` (not `ich habe-ich`).
- **Pre-infinitive `a`** → `[]`: `a impressionar → [] beeindrucken`.
- **Comparative `do que`** → `von-dem []`.

Plus a `disambiguation` list of high-error words (e.g. `mais → mehr`,
NEVER `aber`) and `critical_reminders` that are repeated in the user
prompt for prominence.

---

## 6. Implementation Map

| File | Role |
|---|---|
| `prompts/_default.yaml` | Universal rules + anti-patterns shared across all language pairs |
| `prompts/<src>_<tgt>.yaml` | Pair-specific rules, examples, disambiguations, critical reminders |
| `prompts/__init__.py` | `load_prompt_config(src, tgt)` — YAML loader with `lru_cache` |
| `services/prompt_builder.py` | `build_system_prompt(cfg)` + `build_user_prompt(cfg, lines)` |
| `services/llm_service.py` | API adapters + `_parse_birkenbihl_text_response` parser + `_clean_word_translation` post-processor for per-word fallback |
| `domain/decoder.py` | Chunking, parallel calls, column alignment, list-marker preprocessing |

---

## 7. Adding a New Language Pair

1. Create `prompts/<src>_<tgt>.yaml`. Minimum contents:
   - `source_lang_name`, `target_lang_name`
   - `rules:` block with pair-specific grammar quirks
   - 3–5 `examples` showing the expected output style
   - `disambiguation:` list of common LLM mistakes for this pair
   - `critical_reminders:` 3–4 rules that should appear in the user prompt
2. Add the language to `utils/ui.py` `LANGUAGES` dict (if not already there).
3. Test with the standalone runner: `python tests/test_decoder_e2e.py`.
4. Iterate the YAML based on what the LLM gets wrong — the disambiguation
   list is the right place for "this word always confuses the model."

The universal rules in `_default.yaml` apply automatically; pair-specific
rules layer on top.

---

## 8. Known Limitations

- **Per-word fallback quality is lower** than the main Birkenbihl call.
  Each token is translated in isolation without sentence context, so
  ambiguous words (e.g. `vi` could be "I saw" or "you saw") may go wrong.
- **The empty `[]` may swallow meaningful particles.** A learner sees
  `do que → von-dem []` and might assume `que` is meaningless, but it's
  actually the comparative marker. Birkenbihl-purists prefer wordy expansions
  here; we sided with the literal mechanic.
- **Haiku 4.5 is the floor.** Sonnet 4.6 or Opus 4.7 would handle the
  remaining edge cases (proper-name explanations, etc.) more reliably.
  The current Haiku-tuned prompts will work even better on the larger
  models, but at higher cost.
- **Language-aware tokenization** (e.g. splitting Portuguese clitics before
  the LLM sees them) is deliberately out of scope; the hyphen + bracket
  notation absorbs the asymmetry at the target side instead.

---

## 9. Test Corpus

The 8 Portuguese sentences in `tests/test_decoder_e2e.py` are the standing
regression test for prompt iterations. They cover:

- Proper names (`Italo`, `Ferreira`, `Raglan`, `Manu Bay`)
- Personal-infinitive clitics (`tira-nos`)
- Contractions (`do`, `da`, `no`, `na`, `à`)
- Past auxiliaries (`ter mostrado`)
- Pre-infinitive `a` (`a surfar`, `a impressionar`, `a considerarem`,
  `a revelar`)
- Periphrastic future (`vai decorrer`)
- Modal + infinitive (`poderá oferecer`)
- Comparative idiom (`do que`)
- Reflexive (`se pensava`)
- Relative pronoun with human antecedent (`que`)

Target after the refactor: **246/246 tokens correct** (Σ source = Σ target,
no merges, no omissions).

---

*Last updated: after the JSON→plain-text refactor and `translate_word`
hardening (per-word fallback).*
