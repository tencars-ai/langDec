# Vokabeluniversum — Fachkonzept

**Produkt:** langDec · **Stand:** 2026-08-08 · **Branch:** `verbiverse-concept`
**Status:** Konzept zum Review. Kein Code, keine Migration ausgeführt.

Dieses Dokument beschreibt die Erweiterung des Decoders von **vorformatiertem Text** zu einem
**strukturierten Token-Modell**, und die darauf aufbauende sprachunabhängige Konzeptschicht, aus
der über alle Texte eines Nutzers hinweg ein *Vokabeluniversum* wächst.

Verwandte Dokumente:
- [`vokabeluniversum_overview.md`](vokabeluniversum_overview.md) — Einstieg und Lesereihenfolge
- [`target_architecture.md`](target_architecture.md) — Plattformen, zentrale DB, Sync
- [`cross_lingual_similarity_concept.md`](cross_lingual_similarity_concept.md) — Ähnlichkeit, False Friends
- [`decoder-prompting-rules.md`](decoder-prompting-rules.md) — die Prompt-Regeln, die hier geschützt werden

---

## 1. Ausgangslage und Motivation

### 1.1 Das Problem

`WordByWordDecoder.decode()` liefert heute `DecoderResult(aligned_text, comments, debug_info)` —
`aligned_text` ist eine **fertig formatierte Zeichenkette**, zweizeilig, an `max_line_length`
umgebrochen. Darstellung und Speicherformat sind damit verschmolzen. Gespeichert wird diese
Zeichenkette als `texts.decoded_text`.

Daraus folgen vier Blockaden:

1. **Der häufigste Fehlerfall ist nicht reparierbar.** Das LLM verschiebt regelmäßig um **genau ein
   Token**. Danach ist der Rest der Zeile durchgehend falsch zugeordnet, obwohl *jede einzelne
   Übersetzung korrekt ist*. Die einzige Abhilfe ist heute eine Neugenerierung mit ungewissem
   Ausgang.
2. **Kein Wort ist adressierbar.** Klickbare Wörter, ein Eigenschaften-Panel, Read-Along-Markierung
   — alles braucht Token-Granularität.
3. **Das Wörterbuch kann sich nicht selbst füllen**, weil aus einer formatierten Zeichenkette
   nicht verlässlich rückgewonnen werden kann, welches Zielwort zu welchem Quellwort gehörte.
4. **Der Umbruch ist im Speicher eingebrannt.** `TODO.md:122` verlangt ausdrücklich, dass die
   Konfiguration des Zeilenumbruchs nur die Ausgabe betrifft und im Speicherformat irrelevant ist.
   Heute ist das Gegenteil der Fall — und die Umbruchbreite zum Speicherzeitpunkt ist nirgends
   festgehalten.

### 1.2 Der eigentliche Grund für die Struktur: Reparatur

Der stärkste Grund für ein Token-Modell ist **nicht** Analyse, sondern **Reparatur**.

Liegen die Tokens als Zeilen vor, ist der Off-by-one-Fehler ein **Spaltenversatz**: eine Zelle
einfügen oder löschen, der Rest rutscht nach, Text neu rendern. Aus einem Totalausfall wird ein
Zwei-Klick-Fix.

Dass die heutige Maschinerie diesen Fall **abschneidet statt korrigierbar zu machen**, steht in
ihren eigenen Docstrings. `_parse_birkenbihl_text_response` in `services/llm_service.py` notiert:

> *"padding/truncating a mid-line mismatch shifts every token after the divergence point, which
> reads as garbled rather than merely incomplete."*

Genau dieser Effekt wird mit der Tabelle vom Nutzer in Sekunden behebbar. Das macht die
Korrektur-UI zum **billigsten hochwertigen Feature des ganzen Konzepts**: sie braucht kein LLM,
keine Migration und keine neue Abhängigkeit — nur das Zeilenmodell und den Renderer.

### 1.3 Der zweite Zweck: das Eigenschaften-Panel

Im decodierten Text soll ein Wort anklickbar sein und rechts einen Bereich öffnen mit Wortart,
Zeitform, Genus, Übersetzungsvarianten und Lernstatus. Das erledigt zugleich den Near-term-Punkt
*"Clickable word-by-word output (single-word lookup)"* aus `TODO.md`.

---

## 2. Das Token-Modell

### 2.1 Die neun Spalten und ihre echten Quellen

Der zentrale Befund der Analyse: **nur zwei Spalten brauchen wirklich neue Information.**

| # | Spalte | Quelle | Aufwand |
|---|---|---|---|
| 1 | `source_token` | existiert: `_tokenize()` in `domain/decoder.py:333` | frei |
| 2 | `target_token` | existiert: `line_results[idx]["words"]` | frei |
| 3 | `sentence_no` | **neu, aber reine Python-Logik** (§2.3) | frei |
| 6 | `source_len` | `len()` — heute Basis von `TokenPair.column_width` | frei, **nicht speichern** |
| 7 | `target_len` | `len()` | frei, **nicht speichern** |
| 8 | `comment` | Enrichment-Call (§3) | billig |
| 9 | `context_target` | **Alignment der bereits berechneten Gesamtübersetzung** (§2.2) | 1 Call, keine neue Übersetzung |
| 4 | `pos` | **neu** — braucht Linguistik | Enrichment-Call |
| 5 | `tense` | **neu**, nur wenn `pos ∈ {VERB, AUX}` | Enrichment-Call |

**Spalten 6 und 7 werden nicht persistiert.** Sie sind abgeleitete Daten; in SQL sind sie
`length(source_token)`. Sie zu speichern erzeugte eine zweite Wahrheit, die bei jeder Korrektur
mitgepflegt werden müsste. In der angezeigten Tabelle stehen sie trotzdem — berechnet beim Lesen.

**Genus** steht ebenfalls in der angezeigten Tabelle, wird aber **auf dem Lemma gespeichert**
(§4.3), nicht auf dem Token. Gleiches Prinzip: eine Wahrheit, zwei Sichten.

### 2.2 Spalte 9: Alignment statt Zweitübersetzung

Die Gesamtübersetzung läuft heute bereits **parallel** zum Decode — `pages/0_Start.py` startet drei
Futures in einem `ThreadPoolExecutor(max_workers=3)`: Übersetzung, TTS, Decode. Bei Google kommt
sie sehr schnell zurück.

Spalte 9 **aligniert dieses vorhandene Ergebnis** auf die Quelltokens. Das ist ein
Zuordnungs-Call, **keine zusätzliche Übersetzung**.

Konsequenzen:

- **Die Providerfrage löst sich von selbst.** Die Spalte stammt aus dem konfigurierten
  Übersetzungsprovider, weil sie aus dessen Ergebnis abgeleitet ist.
- **Didaktisch wertvoller** als eine Wörterbuch-Baseline: *"der Decode sagt X, die flüssige
  Übersetzung benutzt Y"* zeigt dem Lernenden genau den Unterschied zwischen wörtlich und
  idiomatisch — das Kernthema der Birkenbihl-Methode.
- **Läuft nach dem Decode** im Hintergrund, damit der Nutzer den decodierten Text bereits liest.
- **Nicht zuordenbare Tokens bleiben leer.** Bewusst — siehe die Schweigeregeln in
  [`cross_lingual_similarity_concept.md`](cross_lingual_similarity_concept.md).
- **Weitere Varianten pro Wort** liefert ein Button im Eigenschaften-Panel: nutzerausgelöst, ein
  Wort, damit kein Rate-Limit-Risiko.

### 2.3 Satznummer: vollständig deterministisch

Die Regel ist ohne LLM umsetzbar: Trennung an `.` `!` `?`, **nicht** an `-` oder `;`,
Bulletpoint-Liste zählt als ein Satz. Umsetzung als eigenes reines Modul (`domain/sentences.py`),
offline testbar ohne API-Key.

**`_SENTENCE_END_RE` (`domain/decoder.py:51`) darf dabei nicht wiederverwendet werden.** Sie steuert
heute ausschließlich die LLM-Chunk-Grenzen in `_slice_paragraph` (`decoder.py:228`). Ändert man
sie, ändert sich die Chunk-Zusammensetzung, damit das, was jeder LLM-Call sieht, und damit die
Decode-Qualität — aus einem völlig unabhängigen Grund. Die Satzlogik ist **zusätzlich**.

**Fehltrennungen, die abgefangen werden müssen:**

| Fall | Beispiel | Behandlung |
|---|---|---|
| Ordinalzahl | de `am 3. Januar`, pt `3.º` | `\d{1,4}\.` → keine Trennung |
| Dezimalzahl | `3.14` | fällt schon durch den Letztzeichen-Test |
| Abkürzung | de `z.B.` `bzw.` `usw.`; en `Mr.` `e.g.`; pt `sr.` `p.ex.`; sv `t.ex.` `bl.a.` | Liste, klein geschrieben verglichen |
| Initiale | `J. R. Tolkien` | einzelner Großbuchstabe + Punkt |
| Ellipse | `…` / `...` | keine Trennung |

**Der wichtigste Schutz ist aber nicht die Abkürzungsliste, sondern ein Satzanfangs-Test:** nur
trennen, wenn das nächste Token wie ein Satzanfang aussieht (erster Buchstabe groß, oder Ziffer,
öffnendes Anführungszeichen, Gedankenstrich, oder Beginn eines neuen Absatzes). Alle vier Sprachen
schreiben satzinitial groß — das fängt auch unbekannte Abkürzungen ab, die keine Liste enthält.

> **Der Test muss auf dem Quelltoken laufen, nie auf dem Zieltoken.** `prompts/_default.yaml`
> Regel 7 erlaubt deutschen Ziel-Substantiven ihre kanonische Großschreibung. Auf der deutschen
> Seite würde der Satzanfangs-Test bei **jedem Substantiv mitten im Satz** feuern.
> Satzsegmentierung ist eine Eigenschaft des Quelltexts.

**Bulletpoint-Listen sind teilweise schon gelöst:** `_LIST_MARKER_PATTERNS` (`decoder.py:44-48`)
entfernt `1.` / `a)` / `-` / `*` / `•` / `·` **vor** der Tokenisierung. Der Punkt eines Markers
erreicht den Tokenstrom also nie, eine `1.`-induzierte Fehltrennung ist unmöglich. Es fehlt nur das
Zusammenfassen aufeinanderfolgender Listenzeilen zu einem Satz: ein Block zusammenhängender
Zeilen, die alle einen Marker tragen, teilt sich eine Satznummer.

**`-` und `;` sind konstruktionsbedingt keine Trenner.** Weder Zeichen kommt in der Trennlogik vor.
Das einzige `-` in der Pipeline ist (a) ein führender Listenmarker und (b) der Binnen-Bindestrich in
Zieltokens wie `werden-wir`, der zielseitig und damit irrelevant ist. Trotzdem gehört eine
Regressionszusicherung dazu, damit eine spätere "Verbesserung" das nicht wieder einführt.

### 2.4 Der Monospace-Text wird zum Renderer

`_format_aligned`, `_format_single_block` und `_prepend_marker` wandern aus der Decoder-Klasse in
ein reines Renderer-Modul über Token-Zeilen. Damit gibt es **eine Wahrheit**, und `max_line_length`
betritt das System nur noch an der Darstellungsgrenze — genau was `TODO.md:122` verlangt.

`TokenPair` ist repo-weit privat (nur in `decoder.py` referenziert) und entfällt; die
`column_width`-Eigenschaft wandert auf die neue Zeilenklasse.

**`DecoderResult` wird rein additiv erweitert:** `aligned_text` bleibt das erste, eager gefüllte
Feld. Damit laufen `pages/0_Start.py`, `pages/1_Decode.py`, `utils/ui.py:save_to_library` und
`tests/test_decoder_e2e.py` unverändert weiter.

### 2.5 Ein Datenintegritätsfehler, der vorher zu beheben ist

`domain/decoder.py:306-309` baut die Paare mit `zip(tokens, translated_words)`. Fehlt ein
`line_results`-Eintrag — weil das LLM eine Zeile ausgelassen hat oder die Index-Rückabbildung in
`_decode_chunk` unterfüllt —, ist `translated_words` leer und **die gesamte Zeile verschwindet
stillschweigend aus der Ausgabe**.

Heute ist das kosmetisch. Mit persistierten Tokens wäre es eine Datenintegritätsfrage: Token-Indizes
und Satznummern verschöben sich gegenüber `texts.content`.

**Korrektur:** den Zeilenaufbau von der **Quelle** treiben, `target_token` leer lassen, wo keine
Übersetzung vorliegt. Die Zeilenzahl wird damit eine reine Funktion des Quelltexts — und genau das
macht Token-Indizes stabil und die DB-Zeilen idempotent wiederbeschreibbar.

> Diese Korrektur **ändert `aligned_text` im Fehlerfall** (eine fehlende Zeile erscheint jetzt mit
> Leerstellen statt zu verschwinden). Deshalb: erst den Renderer byte-identisch portieren und das
> beweisen, **dann** diese Korrektur als eigenen, angekündigten Commit.

---

## 3. Enrichment: Wortart und Zeitform

### 3.1 Der Decode-Prompt wird nicht angefasst

[`decoder-prompting-rules.md`](decoder-prompting-rules.md) §4.1 dokumentiert, dass
JSON-Schema-Output **bereits eingeführt und wieder verworfen** wurde: Systemprompt 9000 → 5300
Zeichen, Anweisungstreue 243/246 → 246/246 Tokens. Die dort genannten Gründe:

- Lange Prompts erodieren die Regeltreue bei kleinen Modellen.
- Output-Tokens gehen für JSON-Syntax statt für Übersetzung drauf.
- Schema garantiert **Struktur**, nie **Semantik**.

**Enrichment läuft deshalb als separater Call mit eigener Prompt-Konfiguration, die keinen Text mit
dem Decode-Prompt teilt.** Damit ist die Trennung strukturell garantiert statt nur gut gemeint: ein
Fehlschlag des Enrichments leert Tabellenspalten, er beschädigt nie einen Decode.

### 3.2 Warum keine lokale NLP-Bibliothek

**Apache OpenNLP wurde geprüft und scheidet aus** — nicht wegen Deployment, sondern weil die
geforderte Information dort nicht existiert. `POSTaggerME` gibt **einen flachen Tag pro Token**
zurück und hat **keinen Morphologie-Kanal**. Die 2.x-Modelle emittieren UPOS (17 Werte), worin
Zeitform kein Konzept ist. Deutsch ist der schlechteste Fall in **beiden** Modellgenerationen: das
Legacy-Tagset STTS kodiert nur Finitheit und Verbklasse — **`sagt` und `sagte` sind beide
`VVFIN`**. Dazu: kein gepflegtes Python-Binding, und `default-jre` bricht auf Streamlit Community
Cloud dokumentiert den Boot.

**`stanza` räumt jeden Engineering-Einwand ab** — pure Python, baut auf torch, das `easyocr` schon
installiert, ~18–20 MB pro Sprache, liefert UD-Features **inklusive `Tense=`** für alle vier
Sprachen. Es scheidet aus einem **fachlichen** Grund aus, und der ist der Kern des ganzen Konzepts:

> **langDec modelliert keine Tokens, sondern Konstruktionen.**

`prompts/pt_de.yaml` beweist das — dort steht ein eigener Block für den periphrastischen Futur
(`vou comer → werde-ich essen`) und ein hartes Verbot des Compound-Past-Merges
(`ter mostrado → haben-gezeigt` ist FORBIDDEN). Ein Per-Token-Tagger kann das nicht wissen:

| Konstruktion | Was ein Tagger sagt | Was stimmt |
|---|---|---|
| pt `vou comer` | `vou: Tense=Pres` + `comer: VerbForm=Inf` | periphrastischer **Futur** |
| pt `ter mostrado` | `Inf` + `Part` | zusammengesetzte Vergangenheit |
| de `fing … an` | Partikel als `PTKVZ`, kilometerweit vom Verb | trennbares Verb, ein Lexem |

Der Lernende liest **"Präsens" unter einem Futur**. `stanza` macht aus "keine Antwort" eine
**selbstbewusst falsche Antwort** — und für Birkenbihl, wo das ganze mentale Modell aus dem
entsteht, was unter jedem Wort steht, ist eine falsch beschriftete Zelle schlechter als eine leere.

**Als dokumentierter Plan B für einen späteren Offline-Modus vormerken**, hinter derselben
Service-Schnittstelle wie die bestehenden Backends.

Nebenbefund, der für jede Bibliothek gilt: die Tokenisierung ist `text.split()`, ein Token wie
`noite.` trägt also seine Interpunktion. Jede Bibliothek müsste man auf diese Tokens zwingen
(`tokenize_pretokenized`, `Doc(words=…)`) — und verlöre damit genau die Genauigkeit, für die man
sie geholt hat, weil kein Modell auf `noite.` als ein Token trainiert wurde. Der LLM-Pfad hat dieses
Problem nicht: er bekommt die Tokens vorgegeben und muss N Antworten liefern — derselbe Vertrag,
den `_default.yaml` bereits durchsetzt.

### 3.3 Kein Call pro Token

Die Docstrings von `_pad_or_truncate` (`llm_service.py:125-136`) und `_fallback_all_lines`
dokumentieren, warum der alte per-Wort-Fallback entfernt wurde: **ein API-Call pro Token erzeugte
HTTP-429-Stürme** bei Claude Haiku (50 RPM). Deshalb ist `_retry_single_line` ausdrücklich auf
**einen** Call pro fehlerhafter Zeile begrenzt.

Jedes Design mit einem Call pro Token ist damit disqualifiziert. Ein per-Token-Google-Ansatz
verschiebt das Problem nur: ~480 Tokens bei 40 Zeilen bedeuten ~480 **sequentielle**
HTTP-Roundtrips, weil `deep_translator.translate_batch` intern eine Python-`for`-Schleife über
`translate` ist — kein Batch-Endpoint. Aus 429 würde Latenz und IP-Blocking.

**Ein Call pro Chunk**, der alle Enrichment-Spalten gemeinsam liefert. Bei ~40 Zeilen sind das
4 Chunks, also 4 zusätzliche Requests.

### 3.4 Alignment über echoed Token

Der Decode-Pfad ist fragil, *weil* er positionell über Tokenzahl alignt — daher überhaupt
`_retry_single_line`. Das Enrichment umgeht das: **jede Antwortzeile echot ihr Quelltoken als
Alignment-Schlüssel**, der Parser resynchronisiert daran.

Antwortformat, pipe-getrennt, eine Zeile pro Token:

```
<source_token> | <pos> | <tense> | <context_target> | <comment>
```

```
Eu     | pron | -                          | ich       |
subi   | verb | pretérito perfeito simples | stieg     | unregelmäßig
e      | conj | -                          | und       |
desci  | verb | pretérito perfeito simples | stieg-ab  |
a      | det  | -                          | die       |
Torre  | noun | -                          | Turm      |
dos    | prep | -                          | von-den   | Kontraktion de + os
```

Regeln im Prompt: genau eine Ausgabezeile pro Quelltoken in Quellreihenfolge; Feld 1 ist das
Quelltoken **wörtlich wiederholt**; `pos` aus einer **geschlossenen Menge**; `tense` nur bei Verben,
sonst `-`; `comment` **leer, außer es ist wirklich nicht offensichtlich** (das halbiert die
Ausgabekosten und ergibt zugleich eine bessere Tabelle — ein Hinweis an jedem Token ist Rauschen).

**Der Parser macht nie einen API-Call.** Bei Nichtzuordnung bleiben die Zellen dieses **einen**
Tokens leer, die Nachbarn nicht. Niemals padden, niemals kürzen, niemals nachfordern — eine
verschobene POS-Spalte ist schlimmer als eine fehlende.

**Warum Pipes und nicht JSON:** dieselbe Begründung wie §4.1, eine Ebene tiefer. Keine
Output-Tokens für Klammern und Escaping, und — entscheidend — **eine fehlerhafte Zeile ist isoliert
reparierbar**, statt den ganzen Parse zu killen. Ein Schema garantierte, dass jede Zeile ein
`pos`-Feld *hat*, nicht dass das `pos` *stimmt*; die geschlossene Menge plus eine Prüfung im Parser
liefert denselben Wert zu null Prompt-Kosten.

### 3.5 Lazy, nicht eager

Enrichment darf **nicht** als vierter Future in den Decode-Hotpath:

1. **Es ist fachlich nachgelagert** — Spalte 9 braucht das Decode-Ergebnis. Es wäre kein echter
   Geschwister-Future, sondern müsste im Executor auf das Decode-Future warten und einen Worker
   blockieren.
2. **Rate-Limit-Rechnung:** eager hebt die Spitzenparallelität von 3 auf ~7 gleichzeitige Requests.
   Das Anthropic-SDK wiederholt 429/5xx standardmäßig zweimal — ein Burst, der das Limit reißt,
   **vervielfacht sich selbst**.
3. **`TODO.md:131` und `:133` protokollieren bereits Hotpath-Fragilität** ("decode hat mega lange
   gebraucht", "speichern kann ich den Text jetzt auch nicht"). Ein vierter langer Future in diese
   `as_completed`-Schleife ist fahrlässig, solange das offen ist.
4. **Die meisten Nutzer öffnen die Tabelle nie.** Der zweizeilige Text *ist* das Produkt.

Also: Decode rendern → Enrichment im Hintergrund → Tabellen-Slot nachrendern. Das Ergebnis wird pro
Text persistiert und ist damit **Einmalkosten**, nicht Kosten pro Ansicht.

---

## 4. Die Konzeptschicht

### 4.1 Eine Begriffstrennung, an der das ganze Modell hängt

Umgangssprachlich sind "Wort", "Bedeutung" und "Übersetzung" eine Sache. Im Modell sind es drei:

- **Lemma** (sprachspezifisch): die Wörterbuchform in *einer* Sprache. Deutsch `frei`, deutsch
  `kostenlos`, portugiesisch `saudade`. Ein Lemma hat **eine feste Wortart** und — bei Substantiven
  in Genussprachen — **ein festes Genus**.
- **Lexem / Sense** (sprachspezifisch, bedeutungsdisambiguiert): ein Lemma plus *eine* seiner
  Bedeutungen. `Bank` ist **ein** Lemma, aber **zwei** Lexeme — Sitzbank und Geldinstitut.
- **Konzept** (sprachunabhängig): die Bedeutung selbst. `Bank`(Möbel), `bench` und `banco`(Möbel)
  zeigen auf **dasselbe** Konzept; `Bank`(Geld) auf ein anderes.

**Konsequenz: ein Token verweist auf ein Lexem, und das Lexem trägt das Konzept.**

Niemals `concept_id` direkt auf dem Token. Zwei Gründe:

1. Eine reine Oberflächenform ist bis zur Disambiguierung **mehrdeutig** — das Lexem *ist* dieser
   Schritt.
2. **Konzept-Zusammenführungen bleiben dadurch billig.** Ein Merge berührt einige tausend
   `lexemes`-Zeilen statt Millionen Tokenzeilen (§7.3).

### 4.2 Englisch als Pivot: als Etikett ja, als Logik nein

Echtes Pivotieren über Englisch bricht an genau den Fällen, die in de/en/pt/sv sofort auftreten:

- **Lexikalische Lücke durch Unterteilung:** englisch "free" deckt deutsch `frei` (ungehindert)
  **und** `kostenlos` ab — zwei unverwandte deutsche Konzepte. Ist Englisch der Schlüssel,
  kollabieren sie fälschlich in einen Knoten.
- **Lücke ohne Ziel:** `saudade` hat kein englisches Einwortäquivalent. Durch einen englischen Pivot
  gezwungen wird es verworfen oder auf "longing" gepresst — und verliert genau die Nuance, für die
  man das Wort lernt.
- **Polysemie-Kollaps:** über einen englischen *String* zu pivotieren führt Bedeutungen zusammen,
  die eine echte Sense-Schicht trennt.

**Regel:** `concepts.gloss_en` ist ein **menschenlesbares Etikett** für Entwicklung und Kuration —
nie ein Matching-Schlüssel, nie eine dem Nutzer präsentierte Wahrheit. Die Identität eines Konzepts
ist die **Menge der Lexeme über alle Sprachen**, die darauf zeigen.

### 4.3 Wo welches Attribut hingehört

| Angefragtes Attribut | Ort | Begründung |
|---|---|---|
| Verweis zum Satz | `tokens.sentence_id` | eigene Tabelle, §4.4 |
| Verweis zum Text | `tokens.text_id` **direkt**, nicht nur über den Satz | "alle Tokens eines Texts, geordnet" ist die häufigste Abfrage gegen die größte Tabelle |
| Verweis zur Sprache | **keine Spalte** auf dem Token | durch den Text eindeutig bestimmt; erneut zu speichern ist Redundanz. Auf dem **Lemma** liegt sie sehr wohl (§4.6) |
| Verweis zum Nutzer | `tokens.user_id`, denormalisiert | folgt dem bestehenden Muster: `audio_files.text_id` ist nullable, `user_id` immer direkt (`sql/schema.sql:166-175`) |
| Wortart | Spalte auf dem Token | **vorkommensbezogen** — der Tag dieses Auftretens |
| Zeitform | Spalte auf dem Token, nullable | vorkommensbezogen, nur Verben |
| **Genus** | **auf dem Lemma** | pro Lemma invariant (`Bank` ist immer feminin). Pro Vorkommen gespeichert würde eine Tatsache über jedes Auftreten dupliziert und könnte auseinanderlaufen. **Präzedenz:** `scripts/load_dictcc_to_db.py:15-24` extrahiert `{f}`/`{m}`/`{n}` genau so — einmal pro Eintrag |
| **Übersetzungsvarianten** | **keine eigene Tabelle** | §4.5 |
| Verweis auf Konzept | `source_lexeme_id` + `target_lexeme_id` | §4.1 |
| Zeichenlängen | **nicht gespeichert** | `length(col)` beim Lesen |

### 4.4 Sätze bekommen eine eigene Tabelle

Nicht nur eine `sentence_number`-Spalte, aus drei Gründen:

1. **`TODO.md:158` fragt wörtlich** *"Speichern wir Sätze einzeln und verknüpfen diese mit den
   Wörtern?"* — das braucht eine **stabile, adressierbare** `sentence_id`. Eine Integer-Spalte
   liefert Gruppierung, aber keine Identität, auf die der Vokabeltrainer verweisen kann.
2. **Rekonstruktion ist verlustbehaftet, nicht bloß unbequem.** Tokens mit Leerzeichen wieder
   zusammenzufügen verliert Interpunktionsanbindung, Kontraktionen und exakte Abstände. Genau diese
   Fehlerklasse ist bereits offen — `TODO.md:109`, *"Sonderzeichen ç werden nicht immer
   übernommen"*. Eine zweite Quelle desselben Bugs auf DB-Ebene will man nicht. Den Satzstring
   einmal **verbatim beim Decode** festhalten umgeht das.
3. **Es ist billig:** ~30–40 Satzzeilen gegen ~480 Tokenzeilen pro Text, Verhältnis ~1:12.

Damit braucht `user_dictionary` **keinen** Fremdschlüssel auf "den einen" Beispielsatz. *"Zeig mir
Sätze, in denen ich dieses Wort getroffen habe"* ist ein Join über `tokens` → `sentences`.
`user_dictionary.example_sentence` bleibt als Override für manuelle Einträge.

### 4.5 Übersetzungsvarianten brauchen keine eigene Tabelle

Eine Variante *ist* ein weiteres Lemma derselben Zielsprache, dessen Lexem **dasselbe Konzept**
teilt. Das Konzept "kostenfrei" hat die deutschen Lemmata `kostenlos`, `gratis`, `umsonst` — das
**ist** die Variantenliste:

```sql
SELECT l.lemma_text
FROM lexemes x
JOIN lemmas  l ON l.lemma_id = x.lemma_id
WHERE x.concept_id = %s AND l.language = %s;
```

Auch **Provenienz und Häufigkeit** brauchen keine Tabelle: jede `tokens`-Zeile mit diesem Lexem
*ist* ein Nachweis (welcher Text, welcher Nutzer, wann). Häufigkeit ist `COUNT(*)`, optional
`GROUP BY user_id` für persönlich vs. global. Dasselbe UPSERT-und-Zähl-Idiom, das
`domain/vocabulary.py:38-48` bereits verwendet, nur eine Ebene höher.

Eine materialisierte Häufigkeitstabelle erst, wenn diese Abfrage **gemessen** langsam ist.

### 4.6 Geteilt vs. nutzereigen — ein bewusster Bruch mit der CASCADE-Konvention

| Schicht | Tabellen | Cascade von `users`? |
|---|---|---|
| **Nutzereigen** | `sentences`, `tokens`, `token_overrides`, `user_lexeme_status`, `vocab_review_events`, `user_dictionary`, `vocab_cards` | **ja**, wie heute |
| **Global geteilt** | `concepts`, `lemmas`, `lexemes` | **nein** |

Das bricht bewusst die Regel *"All user data scoped by `user_id`"* aus `CLAUDE.md`. Präzedenz
existiert bereits: `scripts/load_dictcc_to_db.py:107-109` lädt eine globale Referenztabelle, die
nicht nutzergebunden ist.

Löscht man einen Nutzer, verschwinden Texte, Sätze und Tokens wie heute — aber die Lemmata und
Konzepte, zu denen er beigetragen hat, bleiben als geteiltes Wissen erhalten. **Diese Abweichung
muss in `sql/schema.sql` kommentiert werden**, damit sie als Absicht erkennbar ist und nicht als
Versehen.

**Risiko ehrlich benannt:** ein schlechter Decode eines Nutzers kann ein geteiltes Lemma
verschmutzen. Die Gegenmaßnahme ist **prozedural**, nicht strukturell — nie hart löschen, Merge
statt Löschung, und Konzept-Aggregate zunächst **nicht** als Wahrheit an Endnutzer ausspielen.
Strukturelle Isolation pro Nutzer würde den Sinn einer geteilten Konzeptschicht zerstören.

### 4.7 Konzept-IDs selbst erzeugen — mit Retrieval-First

**Empfehlung: eigene Konzept-IDs, LLM-erzeugt, später mergebar.**

| Externe Ressource | Warum nicht jetzt |
|---|---|
| WordNet / Open Multilingual Wordnet | Englisch exzellent, **de/pt/sv deutlich dünner und lückenhaft** — als Rückgrat zu schwach. Mehrere OMW-Sprachwortnetze sind CC BY-SA (Share-alike auf dem abgeleiteten Datensatz) |
| BabelNet | sehr breit, aber **kommerzielle Nutzung kostenpflichtig** — ein Minenfeld für ein Produkt, das vielleicht aufhört, ein freier Prototyp zu sein |
| Wikidata-Lexeme | CC0, saubere Lizenz — echte Option **für später** |

Wichtig: **ein LLM kann eine korrekte Synset-ID nicht zuverlässig aus dem Gedächtnis ausgeben.**
Das ist Halluzinationsrisiko. Es *kann* aus einer per Lookup vorgelegten Kandidatenliste auswählen —
das ist eine andere Architektur (Retrieval + Klassifikation).

Eine nullable `external_ref`-Spalte bleibt als dokumentierte Tür zur späteren Angleichung, leer bis
es einen konkreten Grund gibt.

> **Konzept-Fragmentierung ist Risiko Nummer 1 — und sie ist unsichtbar.** Wird dieselbe Bedeutung
> in zwei Decode-Sitzungen zweimal geprägt, entstehen zwei Konzept-IDs und die sprachübergreifende
> Brücke liefert **stillschweigend nichts**. Ein *False Negative, das niemand meldet.*
>
> **Gegenmaßnahme am ersten Tag: Retrieval-First statt frei prägen.** Vor dem Prägen eines neuen
> Konzepts die Gloss einbetten, die fünf nächsten existierenden Konzepte per Vektorsuche holen und
> dem LLM als *"nimm eins davon, wenn es passt"* vorlegen. Das **verhindert** Fragmentierung, statt
> sie später aufzuräumen — und nachzurüsten, wenn 100.000 Konzepte existieren, ist deutlich
> schwerer. Details in
> [`cross_lingual_similarity_concept.md`](cross_lingual_similarity_concept.md) §6.

### 4.8 `user_dictionary` wird angelagert, nicht absorbiert

`user_dictionary` (`sql/schema.sql:93-109`) hat einen eigenen Lebenszyklus — der Nutzer speichert,
bearbeitet und löscht bewusst — und ein eigenes `UNIQUE (user_id, source_word, source_language,
target_language)`. Das ist fundamental anders als `tokens`, die automatisch erzeugte
Decode-Artefakte sind.

Also: **eine nullable Spalte anhängen**, sonst nichts. Altzeilen bekommen `NULL` und funktionieren
unverändert weiter — kein Backfill, kein Risiko für Produktionsdaten.

`source_word`/`target_word` bleiben erhalten: das persönliche Wörterbuch ist eine **Momentaufnahme**,
die Konzeptschicht ein **bewegliches Ziel**. Ein gespeichertes Wortpaar muss stabil bleiben, auch
wenn darunter Konzepte gemerged werden.

> **Befund aus dem Schema-Review:** die bestehende `UNIQUE`-Bedingung kann **strukturell keine zwei
> Bedeutungen desselben Worts abbilden** — Homographen sind heute unmöglich. Genau das behebt die
> Lexem-Schicht. Die Bedingung jetzt **nicht** anfassen; ihr späterer Wegfall braucht eine
> Dedup-Geschichte.

---

## 5. Korrekturen: Overrides statt Mutation

Dies ist die **zweitwichtigste Entscheidung** des Konzepts, und sie ist praktisch nicht umkehrbar.

### 5.1 Die Spannung

`tokens` ist als **abgeleiteter Cache** definiert. Aber der Nutzer soll darin den
Off-by-one-Versatz korrigieren — damit enthält die Tabelle **Nutzerarbeit**. Ein Re-Decode würde
diese Korrektur stillschweigend wegwerfen.

Schlimmer: sind Korrekturen direkt in den Cache geschrieben, lässt sich **Korrektur nicht mehr von
Decode-Ausgabe unterscheiden** — und dann kann nie wieder gefahrlos neu decodiert werden.

### 5.2 Regel 1: Korrekturen leben in einer eigenen Tabelle

`tokens` bleibt wegwerfbar. Re-Decode heißt: `tokens` neu erzeugen, **dann Overrides abspielen**.
Nichts geht verloren, weil die Korrektur nie in dem lag, was neu erzeugt wurde.

### 5.3 Regel 2: Die Operation speichern, nicht N Werte

Ein Versatz ist **eine Operation** (`insert_before` / `delete` / `shift`), keine Menge von N
Wertänderungen. Speichert man die Shift-Korrektur als 40 einzelne `set_target`-Werte, macht der
nächste Re-Decode **alle 40 auf einmal ungültig**. Speichert man die eine Operation, überlebt sie.

**Deshalb muss `op` von Anfang an existieren** — nachträglich hinzugefügt kann man die bereits
gesammelten Korrekturen nicht mehr interpretieren.

### 5.4 Regel 3: Auf Inhalt ankern, nicht auf Position

Zeile plus Ordinalzahl allein sind fragil: ändert der Nutzer den Quelltext oder tokenisiert ein
neues Modell anders, zeigt die Ordinalzahl woanders hin — und man wendete die Korrektur auf das
**falsche Wort** an, was schlimmer ist als sie zu verlieren.

Also zusätzlich das Quelltoken selbst und einen Kontext-Hash mitführen, und beim Abspielen:

| Befund | Verhalten |
|---|---|
| Quelltoken passt an derselben Ordinalzahl | still anwenden |
| passt an einer nahen Ordinalzahl | anwenden, Drift protokollieren |
| passt nirgends | **nicht anwenden**, als `needs_review` markieren und im UI zeigen: *"deine frühere Korrektur passt nicht mehr — behalten oder verwerfen?"* |

---

## 6. Lernstatus, Vokabeltrainer, Statistiken

### 6.1 Der Status gehört nicht auf das Token

Der Status — *kann ich schon* / *lerne ich gerade* / *kann ich noch nicht* — gilt **pro Nutzer und
pro Lexem**, nicht pro Vorkommen. Ein Token ist ein Ereignis ("hier stand dieses Wort in diesem
Satz") und kann keinen Lernstatus haben. Läge er dort, hätte dasselbe Wort in 40 Texten **40
widersprüchliche Stati**.

### 6.2 Wiederholungshistorie muss append-only sein

**Dies ist die am stärksten unumkehrbare Entscheidung des ganzen Konzepts: Historie, die man nie
aufgezeichnet hat, ist später nicht rekonstruierbar.**

`vocab_cards` ist heute **veränderlicher Zählerstand** (`box_number`, `last_reviewed`,
`next_review`). Sobald es mehrere Geräte gibt, ist Last-Write-Wins darauf echt verlustbehaftet:
Gerät A macht offline 30 Wiederholungen, Gerät B fünf, B synchronisiert zuletzt — **A's 30
Wiederholungen sind spurlos weg.**

Die Lösung ist billig und braucht kein CRDT: **ein append-only Ereignis-Log mit clientgenerierten
IDs.** Append-only-Zeilen mergen per **Mengenvereinigung**, was trivial konvergent ist — keine
Vektoruhren, keine Merge-Funktion. `box_number` und `next_review` werden eine **abgeleitete
Projektion** über das Log.

`vocab_cards` bleibt als Projektion bestehen; `domain/flashcard.py` rechnet künftig aus dem Log.

### 6.3 Status und Wiederholungsmechanik getrennt halten

Der Status ist eine **Nutzeraussage**, `box_number` eine **Algorithmusausgabe**. Beides gehört
nicht in dieselbe Spalte.

Das "Markieren für den Vokabeltrainer" ist dann kein neues Konzept, sondern ein Statuswechsel auf
*lerne ich gerade*, der eine `vocab_cards`-Zeile anlegt. `domain/flashcard.py` und
`pages/5_Vocab_Trainer.py` existieren **fertig** und sind nur in `app.py` auskommentiert — hier
schließt sich der Kreis zum billigsten großen Feature im Bestand.

### 6.4 Statistiken

*"Wie viele Wörter kann ich schon in Sprache X"* ist ein `COUNT` über *(user, status)* gejoint auf
`lemmas.language`. Das ist der Grund, warum `language` **auf dem Lemma** liegt: die Statistik ist
eine Frage über den **Wortschatz**, nicht über die Texte.

Die Sprache wird auf die Statuszeile **denormalisiert** — ein Lexem wechselt nie die Sprache, die
Denormalisierung ist also gerechtfertigt und spart den Join.

> **Diese Zahl ist eine Motivationsanzeige und darf nicht schwanken**, wenn im Hintergrund Konzepte
> gemerged werden. Deshalb zählt sie **Lexeme mit Status**, nicht Konzepte.

Kein Materialized View: `REFRESH MATERIALIZED VIEW` ist in PostgreSQL ein Voll-Neuaufbau
(auch `CONCURRENTLY` scannt neu). Falls die Zahl je zu langsam wird, ist die Antwort eine
**inkrementell per ±1 gepflegte Rollup-Tabelle**, kein periodischer Neuaufbau.

---

## 7. Schema

Alle Objekte folgen den bestehenden Konventionen aus `sql/schema.sql`: UUID-PK via
`gen_random_uuid()`, PK benannt `<tabelle_singular>_id`, `TIMESTAMPTZ`, `set_updated_at()`-Trigger.
Nächste freie Migrationsnummer ist **`sql/007_*.sql`** (`sql/README.md`).

### 7.1 Nutzereigene Schicht

```sql
-- Sätze: ein Satz pro Text
CREATE TABLE IF NOT EXISTS sentences (
    sentence_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    text_id         UUID NOT NULL REFERENCES texts(text_id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    sentence_index  INTEGER NOT NULL,          -- 0-basiert, Reihenfolge im Text
    source_text     TEXT    NOT NULL,          -- verbatim beim Decode festgehalten
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,               -- Tombstone, siehe target_architecture.md
    UNIQUE (text_id, sentence_index)
);
CREATE INDEX IF NOT EXISTS idx_sentences_text ON sentences(text_id, sentence_index);
CREATE INDEX IF NOT EXISTS idx_sentences_user ON sentences(user_id);

-- Tokens: ein ausgerichtetes Quell/Ziel-Paar pro Satz
CREATE TABLE IF NOT EXISTS tokens (
    token_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL REFERENCES users(user_id)     ON DELETE CASCADE,
    text_id           UUID NOT NULL REFERENCES texts(text_id)     ON DELETE CASCADE,
    sentence_id       UUID NOT NULL REFERENCES sentences(sentence_id) ON DELETE CASCADE,
    token_index       INTEGER NOT NULL,        -- 0-basiert innerhalb des Satzes
    line_index        INTEGER NOT NULL,        -- Zeile im Originaltext, für den Renderer
    source_token      VARCHAR(255) NOT NULL,
    target_token      VARCHAR(255),            -- Birkenbihl-Decode, NULL wenn nicht geliefert
    context_target    TEXT,                    -- Spalte 9: Alignment der Gesamtübersetzung
    word_class        VARCHAR(20),             -- vorkommensbezogen
    tense             VARCHAR(32),             -- nur bei Verben
    comment           TEXT,
    source_lexeme_id  UUID REFERENCES lexemes(lexeme_id) ON DELETE SET NULL,  -- Stufe 2
    target_lexeme_id  UUID REFERENCES lexemes(lexeme_id) ON DELETE SET NULL,  -- Stufe 2
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (sentence_id, token_index)
);
CREATE INDEX IF NOT EXISTS idx_tokens_text     ON tokens(text_id, line_index, token_index);
CREATE INDEX IF NOT EXISTS idx_tokens_sentence ON tokens(sentence_id, token_index);
CREATE INDEX IF NOT EXISTS idx_tokens_user     ON tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_tokens_src_lex  ON tokens(source_lexeme_id);
CREATE INDEX IF NOT EXISTS idx_tokens_source   ON tokens(source_token);
```

**Keine Längenspalten.** `length(source_token)` beim Lesen.

**Provenienz des Decodes** gehört auf `texts` (oder in den Decode-Cache, siehe
[`target_architecture.md`](target_architecture.md)): `decoded_by_service`, `decode_model`,
`prompt_version`, `decoded_at`. Ohne `prompt_version` kann man einen Cache nach einer
Prompt-Änderung nicht gezielt invalidieren.

### 7.2 Korrekturen

```sql
CREATE TABLE IF NOT EXISTS token_overrides (
    override_id         UUID PRIMARY KEY,      -- CLIENT-generiert, nicht DEFAULT
    user_id             UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    text_id             UUID NOT NULL REFERENCES texts(text_id) ON DELETE CASCADE,
    anchor_line         INTEGER NOT NULL,      -- Zeilenindex im Text
    anchor_ordinal      INTEGER NOT NULL,      -- Quelltoken-Index in der Zeile
    anchor_surface      TEXT    NOT NULL,      -- das Quelltoken, wie der Nutzer es sah
    anchor_context_hash TEXT    NOT NULL,      -- Hash der umgebenden Quelltokens
    op                  TEXT    NOT NULL,      -- 'set_target'|'insert_before'|'delete'|'shift'
    payload             TEXT,
    base_provenance     TEXT,                  -- Modell/Prompt-Version der korrigierten Ausgabe
    needs_review        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_token_overrides_text ON token_overrides(text_id, anchor_line);
CREATE TRIGGER trg_token_overrides_updated
    BEFORE UPDATE ON token_overrides
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

### 7.3 Geteilte Sprachschicht — **kein `user_id`, kein Cascade von `users`**

```sql
CREATE TABLE IF NOT EXISTS concepts (
    concept_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gloss_en               TEXT NOT NULL,          -- NUR Etikett, nie Matching-Schlüssel
    concept_source         VARCHAR(20) NOT NULL DEFAULT 'llm',  -- llm|manual|merged|wordnet
    external_ref           VARCHAR(100),           -- reserviert, bleibt leer
    merged_into_concept_id UUID REFERENCES concepts(concept_id) ON DELETE SET NULL,  -- Grabstein
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lemmas (
    lemma_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    language          VARCHAR(10)  NOT NULL,   -- 'de'|'en'|'pt'|'sv'
    lemma_text        VARCHAR(255) NOT NULL,   -- kanonische Wörterbuchform
    word_class        VARCHAR(20),             -- Homographen verschiedener Wortart = eigene Zeilen
    grammatical_gender VARCHAR(10),            -- 'masc'|'fem'|'neut'|'utrum', NULL bei en
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (language, lemma_text, word_class)
);
CREATE INDEX IF NOT EXISTS idx_lemmas_lang_text ON lemmas(language, lemma_text);

CREATE TABLE IF NOT EXISTS lexemes (
    lexeme_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lemma_id   UUID NOT NULL REFERENCES lemmas(lemma_id)     ON DELETE CASCADE,
    concept_id UUID NOT NULL REFERENCES concepts(concept_id) ON DELETE CASCADE,
    rank       SMALLINT NOT NULL DEFAULT 1,    -- 1 = Hauptbedeutung dieses Lemmas
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (lemma_id, concept_id)
);
CREATE INDEX IF NOT EXISTS idx_lexemes_lemma   ON lexemes(lemma_id);
CREATE INDEX IF NOT EXISTS idx_lexemes_concept ON lexemes(concept_id);
```

Offline entstandene Wörter dürfen **nicht** direkt in diese Tabellen schreiben — sonst bricht die
Konfliktfreiheit der geteilten Schicht. Stattdessen eine nutzereigene Vorschlagszeile, die der
Server später dedupliziert (siehe [`target_architecture.md`](target_architecture.md)).

### 7.4 Lernstatus und Wiederholungshistorie

```sql
CREATE TABLE IF NOT EXISTS user_lexeme_status (
    user_id    UUID NOT NULL REFERENCES users(user_id)     ON DELETE CASCADE,
    lexeme_id  UUID NOT NULL REFERENCES lexemes(lexeme_id) ON DELETE CASCADE,
    language   VARCHAR(10) NOT NULL,           -- denormalisiert für die Statistik
    status     VARCHAR(16) NOT NULL,           -- 'known'|'learning'|'unknown'
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, lexeme_id)
);
CREATE INDEX IF NOT EXISTS idx_uls_stats ON user_lexeme_status(user_id, language, status);

-- Append-only. NIEMALS UPDATE, NIEMALS DELETE.
CREATE TABLE IF NOT EXISTS vocab_review_events (
    event_id    UUID PRIMARY KEY,              -- CLIENT-generiert
    user_id     UUID NOT NULL REFERENCES users(user_id)     ON DELETE CASCADE,
    lexeme_id   UUID NOT NULL REFERENCES lexemes(lexeme_id) ON DELETE CASCADE,
    reviewed_at TIMESTAMPTZ NOT NULL,
    outcome     VARCHAR(16) NOT NULL,          -- 'correct'|'incorrect'
    device_id   TEXT
);
CREATE INDEX IF NOT EXISTS idx_review_events ON vocab_review_events(user_id, lexeme_id, reviewed_at);
```

### 7.5 Anlagerung an `user_dictionary`

```sql
ALTER TABLE user_dictionary
    ADD COLUMN IF NOT EXISTS source_lexeme_id UUID REFERENCES lexemes(lexeme_id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_user_dictionary_lexeme ON user_dictionary(source_lexeme_id);
```

Rein additiv. Altzeilen `NULL`, kein Backfill, kein Risiko für Produktionsdaten seit 2026-05-15.

---

## 8. Stufenplan

Branches nach `CLAUDE.md`-Konvention, **nie direkt auf `main`**.

### Stufe 0 — die Messlatte reparieren (Voraussetzung, kein Extra)

**Ohne diese Stufe ist der Decoder-Umbau nicht sicher abnehmbar.**

Die 246/246-Metrik ist aus dem Repo **nicht reproduzierbar**: `tests/test_decoder_e2e.py:33-41`
enthält 5 pt→de-Sätze, [`decoder-prompting-rules.md`](decoder-prompting-rules.md) §9 beschreibt 8.

1. Die fehlenden Sätze zurück ins Korpus (`ter mostrado`, `poderá oferecer`, `vai decorrer`,
   `do que`, `se pensava`, die Eigennamenfälle).
2. **Token-Zähl-Assertion** pro Zeile mit laufender `N/246`-Ausgabe. Heute druckt der Harness nur
   Text, ein Mensch muss zählen.
3. **Offline-Modus** mit gestubbtem Service, der `translate_birkenbihl_full` mit konservierten
   Antworten bedient. Die Weiche ist schon `hasattr(...)` (`decoder.py:87`), der Stub braucht
   ~15 Zeilen und keinen API-Key. **Das ist die wertvollste einzelne Ergänzung im ganzen Plan** —
   sie macht aus der Regressionsprüfung einen deterministischen Byte-Vergleich.
4. Einen Online-Lauf als Referenz festhalten.
5. **Prompt-Größen-Wächter:** `assert len(build_system_prompt(cfg)) < 6500`. Der pt→de-Prompt liegt
   heute bei **6158 Zeichen** statt der dokumentierten 5300 — 16 % Drift, die niemand bemerkt hat.

### Stufe 1 — reiner Refactor, byte-identische Ausgabe

Token-Zeilenmodell, Satznummerierung, Renderer-Extraktion, `TokenPair` entfernen, den toten
Parameter `natural_translation` entfernen (**null Aufrufstellen**). `DecoderResult` additiv
erweitern. `pandas` explizit in `requirements.txt` (kommt heute nur transitiv über Streamlit),
Import **lazy** in der Konvertierungsmethode, damit `domain/` ohne Streamlit importierbar bleibt.

**Nachweis:** Offline-Lauf byte-identisch zur Referenz, danach ein Online-Lauf mit 246/246.

### Stufe 1b — der `zip`-Fehler (eigener Commit)

§2.5. Getrennt, weil er `aligned_text` im Fehlerfall bewusst ändert.

### Stufe 2 — Tabelle und Korrektur-UI, ohne jeden neuen LLM-Call

`st.data_editor` mit Shift-Operationen, `token_overrides` **vor** der ersten Auslieferung der UI
(§5). POS-, Zeitform- und Kommentarspalten bleiben **leer** — das beweist die
Ausfallsicherheit, bevor überhaupt Enrichment-Code existiert, und zeigt, dass fünf der neun Spalten
gratis sind.

### Stufe 3 — Persistenz

`sql/007_*.sql` mit §7.1, §7.2, §7.4. **Pflicht dabei:** `DBService.execute_many`.
`services/db_service.py:28` öffnet **pro Aufruf eine frische Verbindung** — bei ~480 Tokenzeilen
wären das ~480 TCP+TLS-Handshakes gegen Neon **pro einzelnem Decode**.

**Re-Decode-Vertrag:** `DELETE FROM sentences WHERE text_id = …` (cascadet auf Tokens) und
Bulk-Reinsert, in **derselben Transaktion** wie das `texts`-Update, danach Overrides abspielen. Das
gibt zugleich einen klaren Vertrag für die offenen Bugs `TODO.md:108` und `:137`.

> **`tokens` darf nie serverautoritativ werden.** 480 Zeilen × 100 Texte × 100.000 Nutzer ≈
> **4,8 Mrd. Zeilen, ~1 TB**. Für den heutigen Streamlit-Prototyp gibt es kein Gerät, also liegt
> `tokens` serverseitig — entscheidend ist, dass es dort als **Cache** gilt. Sobald Clients
> existieren, wandert es auf das Gerät. Diese Festlegung ist heute kostenlos.

### Stufe 4 — Enrichment

Eigene Prompt-Konfiguration (`prompts/_enrichment.yaml` plus optionaler `enrichment:`-Block pro
Sprachpaar), eigener Prompt-Builder, der **keinen Text** mit `build_system_prompt` teilt.
Lazy ausgelöst, opt-in über die Einstellungen.

**Nachweis, dass der Decode nicht regressiert:** `git diff --stat` muss zeigen, dass
`prompts/_default.yaml`, `prompts/pt_de.yaml`, `build_system_prompt`, `build_user_prompt` und
`_parse_birkenbihl_text_response` **unberührt** sind. Diese Prüfung gehört auf die PR-Checkliste.

### Stufe 5 — Konzeptschicht

§7.3 und §7.5, plus Retrieval-First-Prägung (§4.7). Backfill ist lazy und optional — die in
Stufe 3 gesammelten Tokens lassen sich nachträglich auflösen.

### Stufe 6 — Lernstatus, Trainer, Statistiken

§7.4 verdrahten, `pages/4_Dictionary.py` und `pages/5_Vocab_Trainer.py` in `app.py` wieder
aktivieren, `domain/flashcard.py` auf das Ereignis-Log umstellen.

---

## 9. Die Entscheidungen, die jetzt fallen müssen

Nach Umkehrkosten sortiert. Alles andere kann warten.

| # | Entscheidung | Warum jetzt |
|---|---|---|
| 1 | **Wiederholungshistorie append-only** statt veränderlicher Zähler | Historie, die nie aufgezeichnet wurde, ist nicht rekonstruierbar. Kostet heute eine Tabelle |
| 2 | **Korrekturen als Operationen mit Inhaltsankern** | Sobald der Cache direkt korrigiert wurde, ist Korrektur nicht mehr von Decode-Ausgabe unterscheidbar — **dann kann nie wieder gefahrlos neu decodiert werden** |
| 3 | **Lemma / Lexem / Konzept sauber trennen** | Falsch aufgehängt, muss später jede Tokenzeile neu aufgelöst werden |
| 4 | **Clientgenerierbare UUIDs + Tombstones** | Nachrüsten in Zeilen, die schon auf Nutzergeräten liegen, heißt die ganze Flotte anfassen |
| 5 | **`tokens` nie serverautoritativ** | Heute kostenlos festzulegen; später kauft man sich das 1-TB-Problem *und* das Nicht-mehr-decodieren-Problem ein |
| 6 | **Retrieval-First bei der Konzeptprägung** | Fragmentierung ist unsichtbar; nachträglich mergen bei 100.000 Konzepten ist deutlich schwerer |

**Billig aufschiebbar:** welches Sync-Produkt, ob das Backend Python oder etwas anderes wird, ob
Ähnlichkeit über Trigramme oder Embeddings läuft, Rollup-Tabellen, `pgvector`.

---

*Erstellt 2026-08-08 auf Branch `verbiverse-concept`. Alle Datei- und Zeilenverweise gegen den
Stand dieses Branches geprüft.*
