# Code-Review langDec — August 2026

**Stand:** 2026-08-08 · **Umfang:** `app.py`, `pages/`, `domain/`, `services/`, `utils/`,
`prompts/`, `sql/`, `tests/`

**Dies ist ein Bericht. Es wurde nichts behoben.** Jeder Befund nennt Datei und Zeile und wurde
gegen den damaligen Code geprüft.

Ein gezielter Review hat mehrere Stellen freigelegt, an denen der Code nicht das tut, was die
Dokumentation behauptet — sowie einen Fehler, der harmlos aussieht, aber ohne jede Fehlermeldung
Inhalte verschwinden lässt.

**Einordnung:** die Codebasis ist mit **5.093 Zeilen** klein und in erkennbar gutem Zustand. Die
Schichtung `pages/` → `domain/` → `services/` ist konsequent durchgehalten, `domain/` ist frei von
UI-Kopplung, und die Docstrings gehören zum Besten, was in einem Prototyp dieser Größe zu erwarten
ist. Die Befunde unten sind Detailarbeit, kein struktureller Sanierungsfall.

---

## A. Korrektheit und Datenintegrität

### A1 — `zip()` lässt ganze Zeilen still verschwinden

**`domain/decoder.py:306-309`** · Schweregrad: **niedrig** — kosmetisch, aber ohne jede
Fehlermeldung

```python
pairs = [
    TokenPair(source_token=src, target_token=tgt)
    for src, tgt in zip(tokens, translated_words)
]
```

`zip` kürzt auf die kürzere Seite. Fehlt für eine Zeile ein `line_results`-Eintrag — weil das LLM
sie ausgelassen hat, oder weil die Index-Rückabbildung in `_decode_chunk` (`decoder.py:256-259`)
unterfüllt, wenn `len(local_indices) < len(chunk)` — ist `translated_words` leer und **die gesamte
Zeile verschwindet aus der Ausgabe**. Der Nutzer sieht schlicht eine Zeile weniger im decodierten
Text, ohne jeden Hinweis darauf, dass etwas fehlt.

**Behebung:** den Zeilenaufbau von der **Quelle** treiben, `target_token` leer lassen wo keine
Übersetzung vorliegt. Die Zeilenzahl wird damit eine reine Funktion des Quelltexts.

**Achtung:** die Behebung **ändert `aligned_text` im Fehlerfall** (fehlende Zeile erscheint mit
Leerstellen statt zu verschwinden). Deshalb als **eigener, angekündigter Commit**, nicht mit
anderen Änderungen vermischt.

### A2 — Sprachnamen erreichen den Prompt als ISO-Codes

**`prompts/__init__.py`** in Verbindung mit **`services/llm_service.py`** · Schweregrad:
**mittel**, betrifft **alle Sprachpaare außer pt→de**

`load_prompt_config('en','de')` liefert `source_lang_name == "en"`, weil nur `pt_de.yaml`
`source_lang_name`/`target_lang_name` setzt. `build_system_prompt` (`services/prompt_builder.py:23`)
baut daraus:

> *"You are a strict word-for-word translator using the Birkenbihl decoding method, translating
> from **en** to **de**."*

Das ist eine latente Qualitätsminderung für jedes Paar ohne YAML-Datei — also für alles außer
pt→de. `_LANG_NAMES` in `services/llm_service.py` hätte die Klarnamen, wird vom Loader aber nicht
konsultiert.

**Behebung:** `_LANG_NAMES` nach `prompts/__init__.py` ziehen (oder importieren) und als Default
für `source_lang_name`/`target_lang_name` verwenden. Wenige Zeilen, und es hebt die Qualität aller
künftigen Sprachpaare, bevor sie überhaupt YAML-Regeln haben.

---

## B. Nicht überwachte Regression

### B1 — Die 246/246-Metrik ist aus dem Repo nicht reproduzierbar

**`tests/test_decoder_e2e.py:33-41`** vs. **`documents/decoder-prompting-rules.md:296-311`** ·
Schweregrad: **hoch** — es ist der Qualitätsanker des Produkts

`decoder-prompting-rules.md` §9 beschreibt ein **8-Satz-Korpus** und ein Ziel von **246/246
korrekten Tokens** als stehende Regressionsprüfung. Im Harness stehen **5 Sätze**. Es fehlen unter
anderem die Fälle `ter mostrado` (zusammengesetzte Vergangenheit), `poderá oferecer`
(Modal + Infinitiv), `vai decorrer` (periphrastischer Futur), `do que` (Vergleichsidiom) und
`se pensava` (Reflexiv) sowie Teile der Eigennamenfälle.

Damit ist die Zahl, die den ganzen Prompt-Refactor rechtfertigt, **nicht nachrechenbar**.

Zweitens **prüft der Harness gar nichts** — er druckt Text, und ein Mensch müsste zählen. Es gibt
keine Assertion auf Tokenzahl.

**Behebung (Voraussetzung für jeden Decoder-Umbau, kein Extra):**
1. Die fehlenden Sätze zurück ins Korpus.
2. Assertion pro Zeile: `len(src.split()) == len(tgt.split())`, mit laufender `N/246`-Ausgabe.
3. **Ein Offline-Modus** mit gestubbtem Service, der `translate_birkenbihl_full` mit konservierten
   Antworten bedient. Die Weiche ist bereits `hasattr(...)` (`domain/decoder.py:87`), der Stub
   braucht ~15 Zeilen und keinen API-Key. Damit wird aus der Regressionsprüfung ein
   **deterministischer Byte-Vergleich** statt eines LLM-abhängigen Augenmaßes.

### B2 — Das Prompt-Budget ist unbemerkt um 16 % gewachsen

**`prompts/_default.yaml` + `prompts/pt_de.yaml`** · Schweregrad: **mittel**

`decoder-prompting-rules.md` §4.1 nennt **5300 Zeichen** als Ergebnis des JSON→Plain-Text-Refactors
und begründet ausführlich, warum Prompt-Kürze die Anweisungstreue trägt.

Gemessen rendert `build_system_prompt(load_prompt_config('pt','de'))` heute **6158 Zeichen** — der
Block zu trennbaren Verben kam dazu. **Niemand überwacht das.**

**Behebung:** eine Größen-Assertion in den Harness (`assert len(...) < 6500`) und die Zahl in §4.1
korrigieren. Der Wert der Assertion liegt nicht in der konkreten Schranke, sondern darin, dass
Wachstum künftig **sichtbar** wird.

---

## C. Toter Code und Duplikate

| # | Befund | Ort | Anmerkung |
|---|---|---|---|
| C1 | **`natural_translation` hat null Aufrufstellen** | `domain/decoder.py:72-80` | Der Parameter wird entgegengenommen und laut Kommentar absichtlich ignoriert. Verifiziert: die einzigen Vorkommen im Repo sind die Signatur und ihr Kommentar. Ersatzlos streichen |
| C2 | **`streamlit-authenticator` ist ungenutzt** | `requirements.txt` | Verifiziert: null Importe im ganzen Repo. `app.py` macht eigenes bcrypt-Login mit `st.navigation()`. Die Abhängigkeit entfernen — und die Behauptung in `technical_concept_prototype_stack_tooling.md` §7.2 gleich mit |
| C3 | **Eigene `LANGUAGES`-Kopie** | `pages/4_Dictionary.py:24` | Wortgleich mit `utils/ui.py:LANGUAGES_WITH_ALL`. Zwei Wahrheiten für dieselbe Liste — eine neue Sprache müsste an beiden Stellen nachgetragen werden |
| C4 | **Tote CSS-Selektoren** | `utils/styles.py:14,20` | Die Selektoren erwarten `aria-label="Decoded text (word-by-word)"`. `pages/0_Start.py:190-193` labelt das Textarea `"Decoded"` mit `label_visibility="collapsed"`. **Die Farbtönung ist auf der aktiven Seite wirkungslos** — das Feature sieht implementiert aus und ist es nicht |
| C5 | **`psycopg2` in einem Skript** | `scripts/load_dictcc_to_db.py:8,9,104` | psycopg2 wurde projektweit durch psycopg v3 ersetzt und steht nicht mehr in `requirements.txt`. Das Skript ist damit **nicht lauffähig** |
| C6 | **Reservierter, nie gefüllter Slot** | `services/llm_service.py:226,245,273` | `line_results[idx]["comments"]` ist immer `""`. Entweder befüllen oder im Docstring als das kennzeichnen, was er ist: ein reservierter **Diagnose**-Slot |

---

## D. Struktur

### D1 — Die Provider-Liste steht an drei Stellen

`services/llm_service.py:build_llm_service` · `pages/8_Settings.py:144` · `app.py:_decode_default()`

`pages/8_Settings.py:144` ist wörtlich `[("openai", "OpenAI"), ("anthropic", "Anthropic (Claude)")]`.
Ein vierter Provider bedeutet drei Änderungen an drei Stellen, ohne dass irgendetwas den
Zusammenhang erzwingt. `user_api_keys.provider` hat zudem **keinen CHECK** (`sql/schema.sql`) — die
Liste ist also nur ein weiches Register.

**Vorschlag:** eine einzige Registry-Struktur (Provider-Kennung, Anzeigename, Factory), aus der
alle drei Stellen lesen.

### D2 — Handgeführter Tab-Zähler

**`pages/3_Texts.py:141-167`**

Die Tabs werden über bedingtes `append` gebaut, und der Zugriff läuft über einen von Hand
mitgeführten `idx`, der bei jedem optionalen Tab hochgezählt wird. Bei vier Tabs geht das noch
gut; ein **fünfter bedingter Tab** ist ein Bug in Wartestellung.

**Vorschlag:** vor der Erweiterung auf eine Liste aus `(Label, Renderfunktion)` umstellen und mit
`st.tabs` zippen. Dann verschwindet der Zähler.

### D3 — `user_preferences` ist ein festes Spaltenset

`sql/schema.sql` · `services/preferences_service.py` · `app.py:_init_preferences` ·
`utils/services_ui.py` · `pages/8_Settings.py`

Eine einzige neue Einstellung berührt **fünf Stellen plus eine Migration**, weil `save()`
keyword-only mit fester Signatur arbeitet. Das ist heute vertretbar (fünf Einstellungen), wird aber
zum Bremsklotz, sobald weitere Einstellungen dazukommen.

**Vorschlag:** beim nächsten Einstellungsschub auf ein Key/Value- oder JSONB-Modell wechseln, nicht
vorher. Kein akuter Handlungsbedarf, aber bewusst zu entscheiden statt zu erleiden.

### D4 — Der eigentliche Speicherengpass ist Audio, nicht Text

**`sql/schema.sql:166-175`**, `audio_files.data BYTEA`

Eine Handvoll MP3s erschöpft ein 0,5-GB-Neon-Free-Projekt sehr schnell — deutlich schneller als
jede reine Textmenge im Schema. Die Auslagerung in Objektspeicher ist schon heute fällig,
unabhängig von jeder künftigen Erweiterung.

### D5 — `user_dictionary` kann keine Homographen abbilden

**`sql/schema.sql:93-109`**

`UNIQUE (user_id, source_word, source_language, target_language)` macht es **strukturell
unmöglich**, zwei Bedeutungen desselben Worts zu speichern — `Bank`(Möbel) und `Bank`(Geld)
schließen einander aus.

**Vorschlag:** die Eindeutigkeit um eine Sinn-/Homograph-Kennung erweitern (z.B. eine zusätzliche
Spalte oder ein Disambiguierungsfeld). Die Bedingung **jetzt nicht anfassen**; ihr späterer
Wegfall braucht eine Dedup-Geschichte für Bestandsdaten.

---

## E. Lizenz und Betrieb

Kein Codefehler, aber im Review aufgefallen und wichtiger als die meisten Punkte oben.

### E1 — AGPL-Haftung im Dokumentenstack

**`requirements.txt`**: `PyMuPDF` ist **AGPL-3.0 oder kommerziell**, und AGPL §13 lässt
**Netzwerknutzung als Verbreitung zählen** — nach Auskunft des Herstellers ausdrücklich auch als
Microservice hinter einer API. Die naheliegende Python-EPUB-Bibliothek (EbookLib) ist **ebenfalls
AGPL**.

Für einen privaten Prototyp unkritisch. **Vor einer Kommerzialisierung zu klären.**

### E2 — Nutzereigene API-Keys tragen kein Consumer-Produkt

`sql/schema.sql` `user_api_keys` · `pages/8_Settings.py`

Das heutige Modell — jeder Nutzer hinterlegt seinen eigenen, Fernet-verschlüsselten
OpenAI/Anthropic-Schlüssel — ist für Tester genau richtig und für eine App im Store unbrauchbar:
kein Endnutzer legt sich einen Anthropic-Account an. Nötig wäre ein **app-eigener Schlüssel plus
serverseitige Kontingentierung pro Nutzer**, und das ist eine Schemaänderung, die man besser vor
dem ersten Release einplant als danach.

### E3 — Datenschutz: Texte gehen bereits an US-Auftragsverarbeiter

Nutzertexte werden zum Decodieren an OpenAI/Anthropic gesendet. Das braucht einen
Auftragsverarbeitungsvertrag, eine Zero-Retention-Konfiguration und eine Datenschutzerklärung, die
den Auftragsverarbeiter benennt — plus eine Bewertung des Drittlandtransfers. Ebenso ist Neon zwar
in eu-central-1 gehostet, die Neon Inc. aber US-amerikanisch.

**Beides besteht schon heute**, wird nicht durch das neue Konzept verursacht und ist dringlicher
als alles, was das Konzept an Datenschutzfragen aufwirft.

---

## F. Reihenfolge

Nach Verhältnis von Nutzen zu Aufwand:

| Rang | Maßnahme | Aufwand |
|---|---|---|
| 1 | **B1** — Korpus, Assertion, Offline-Modus | ~einen halben Tag; **Voraussetzung für alles Weitere am Decoder** |
| 2 | **A2** — `_LANG_NAMES` als Fallback | wenige Zeilen, hebt alle künftigen Sprachpaare |
| 3 | **B2** — Größen-Assertion | wenige Zeilen |
| 4 | **C1, C2, C4, C5** — toter Code | trivial, macht das Repo ehrlich |
| 5 | **A1** — `zip`-Kürzung | überschaubar, behebt eine stille Fehlerquelle |
| 6 | **C3, D2** — Duplikat und Tab-Zähler | klein |
| 7 | **D4** — Audio in Objektspeicher | eigener Branch, unabhängig |
| 8 | **E1, E2, E3** — Lizenz und Datenschutz | keine Codearbeit, aber Entscheidungen |

Nicht angefasst werden sollten: **D3** (erst beim nächsten Einstellungsschub), **D5** (erst wenn
Homograph-Support gebraucht wird), **D1** (erst wenn ein dritter Provider ansteht).

---

*Erstellt 2026-08-08. Alle Befunde gegen den damaligen Code verifiziert.*
