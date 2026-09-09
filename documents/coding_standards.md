# Coding Standards langDec

**Stand:** 2026-08-08 · **Branch:** `verbiverse-concept` · **Status:** Vorschlag zum Review

Diese Standards sind **aus dem Bestand extrahiert**, nicht von außen aufgesetzt. Der Code hat
bereits starke Konventionen; dieses Dokument macht sie verbindlich und ergänzt sie um das, was der
[Code-Review](code_review_2026-08.md) an Lücken gezeigt hat.

**Leitsatz:** *kurzer, klarer Code mit Kommentaren, die das Warum erklären.*

---

## 1. Die wichtigste Regel: Docstrings erklären das Warum

Der Bestand enthält Docstrings, die deutlich über dem liegen, was man in einem Prototyp erwartet —
und sie sind der Maßstab für alles Weitere. Drei echte Beispiele:

**`services/llm_service.py`, `_pad_or_truncate`:**

> *"Token-count mismatches between source and LLM output used to trigger a per-word fallback (one
> API call per token, per offending line). On rate-limited models like Claude Haiku (50 RPM) that
> easily produced HTTP 429 storms. We now pad with '[]' or truncate instead — the comment log makes
> the imperfection visible without flooding the API."*

**`services/llm_service.py`, `_retry_single_line`:**

> *"Bounded to exactly one call per offending line (not per word), so it can't reproduce the 429
> storm the per-word fallback used to cause."*

**`domain/decoder.py`, `PreprocessedLine`:**

> *"The marker — if any — is preserved here so the renderer can prepend it back onto the aligned
> output, while the decoder itself never sees it."*

Was diese Beispiele richtig machen:

- Sie erklären **warum die Lösung so aussieht**, nicht was der Code tut.
- Sie nennen **die konkrete Havarie**, die zu der Regel geführt hat (429-Sturm, 50 RPM).
- Sie machen die **Grenze explizit** ("genau ein Call pro Zeile, nicht pro Wort") — wer den Code
  später ändert, sieht sofort, welche Zusicherung er dabei bricht.

### Regeln

- **Jede nicht offensichtliche Entscheidung bekommt ihre Begründung im Docstring.** Wenn eine
  Funktion eine bestimmte Grenze, Schwelle oder Reihenfolge einhält, steht dort, was passiert, wenn
  man sie aufhebt.
- **Kein Docstring, der die Signatur wiederholt.** `"""Returns the user id."""` über
  `get_user_id()` ist Rauschen.
- **Zahlenwerte im Code brauchen eine Begründung.** `max_tokens=64`, `_MAX_PARALLEL_CHUNKS = 3`,
  `similarity_threshold = 0.28` sind keine Geschmacksfragen, sondern Ergebnisse — die Quelle gehört
  daneben.
- **Deutsch oder Englisch:** Code, Bezeichner und Docstrings **auf Englisch**. Konzeptdokumente in
  `documents/` dürfen deutsch sein.

---

## 2. Kanon

- **PEP 8** für Layout und Benennung, **PEP 257** für Docstring-Konventionen, **PEP 484** für Typen.
- **`from __future__ import annotations`** am Dateianfang — im Bestand bereits durchgehalten
  (`domain/decoder.py`, `services/prompt_builder.py`), erlaubt moderne Typsyntax ohne
  Laufzeitkosten.
- **Zeilenlänge 100** — der Bestand liegt faktisch dort; PEP 8s 79 ist für diesen Code zu eng.
- **Typannotationen an jeder öffentlichen Funktion.** Private Helfer dürfen sie weglassen, wenn die
  Signatur trivial ist.

---

## 3. Struktur

### 3.1 Die Schichtung ist verbindlich

```
pages/     UI. Streamlit-spezifisch. Keine Geschäftslogik.
domain/    reine Logik. KEIN Streamlit-Import, KEIN DB-Zugriff.
services/  Adapter nach außen: LLM, DB, TTS, OCR, Auth.
utils/     geteilte UI-Bausteine und Konstanten.
prompts/   Daten (YAML), kein Code außer dem Loader.
```

**`domain/` muss ohne Streamlit und ohne Datenbank importierbar bleiben.** Das ist keine Ästhetik:
`tests/test_decoder_e2e.py` importiert `domain.decoder` in einem nackten Python-Prozess, und die
Wiederverwendbarkeit für Variante 2 hängt daran.

**Praktische Konsequenz:** schwere oder UI-gebundene Importe (pandas, Streamlit) in `domain/` **lazy
innerhalb der Funktion**, nie auf Modulebene.

### 3.2 Abstrakte Basisklassen für austauschbare Backends

Der Bestand macht das richtig: `TranslationService`, `LLMService`, `TTSService`, `OCRService` sind
ABCs, neue Implementierungen leiten ab. **Beibehalten.**

**Fähigkeitserkennung über `hasattr` statt Typprüfung**, wo ein optionales Feature vorliegt — so
macht es `domain/decoder.py:87` mit `translate_birkenbihl_full`. Das hält Google und Argos
funktionsfähig, ohne sie zu einer Methode zu zwingen, die sie nicht erbringen können.

### 3.3 Unveränderliche Datenklassen für Werte

`@dataclass(frozen=True)` für alles, was ein Wert und kein Zustand ist — `DecoderResult`,
`TokenPair`, `PreprocessedLine`, `PromptConfig` machen es vor. Abgeleitete Größen als
`@property`, nicht als Feld.

---

## 4. Regeln, die aus dem Review entstanden sind

Jede dieser Regeln hat einen konkreten Befund als Anlass; die Nummer verweist auf
[`code_review_2026-08.md`](code_review_2026-08.md).

### 4.1 Keine Konstante zweimal (C3)

`pages/4_Dictionary.py:24` hält eine eigene `LANGUAGES`-Kopie, wortgleich mit
`utils/ui.py:LANGUAGES_WITH_ALL`. Eine neue Sprache müsste an beiden Stellen nachgetragen werden.

> **Regel:** Konstanten, die mehr als eine Datei betreffen, leben in `utils/`. Kopieren ist ein
> Review-Blocker.

### 4.2 Keine dritte hartcodierte Liste (D1)

Die Provider-Liste steht an drei Stellen (`build_llm_service`, `pages/8_Settings.py:144`,
`app.py:_decode_default()`), ohne dass etwas den Zusammenhang erzwingt.

> **Regel:** Was erweiterbar sein soll, bekommt **eine** Registry-Struktur, aus der alle Stellen
> lesen. Wer eine zweite Aufzählung derselben Sache anlegt, muss begründen warum.

### 4.3 Abgeleitete Werte nicht speichern

Zeichenlängen sind `len()`, Häufigkeiten sind `COUNT(*)`, `box_number` ist eine Projektion über das
Wiederholungs-Log.

> **Regel:** Ein Wert, der aus anderen Werten berechenbar ist, wird berechnet — es sei denn, es gibt
> eine **gemessene** Performancebegründung. Gespeicherte Ableitungen erzeugen eine zweite Wahrheit,
> die bei jeder Änderung mitgepflegt werden muss.

### 4.4 Darstellung von Datenmodell trennen

`aligned_text` mischt heute beides: `max_line_length` ist im gespeicherten Ergebnis eingebrannt.

> **Regel:** Formatierungsparameter betreten das System **an der Darstellungsgrenze**, nie im
> Speicherformat. Renderer sind reine Funktionen über Datenzeilen.

### 4.5 Toter Code wird entfernt, nicht kommentiert (C1, C2, C4, C5)

Der Bestand enthält einen Parameter mit null Aufrufstellen, eine ungenutzte Abhängigkeit, zwei tote
CSS-Selektoren und ein Skript, das eine entfernte Bibliothek importiert. Alle sehen aus, als
funktionierten sie.

> **Regel:** Was nicht läuft, kommt raus. Git erinnert sich. Ein auskommentierter Block braucht
> einen Kommentar, der sagt **wann er zurückkommt** — sonst ist er tot.

**Ausnahme mit Begründungspflicht:** die in `app.py:PAGES` auskommentierten Seiten sind bewusst
geparkt (MVP-01-Entscheidung, `TODO.md`). Solche Fälle brauchen einen Verweis auf die Entscheidung,
die sie geparkt hat.

### 4.6 Reservierte Felder kennzeichnen oder entfernen (C7)

`line_results[idx]["comments"]` ist immer `""`. Ein Leser kann nicht wissen, ob das ein Bug oder
Absicht ist.

> **Regel:** Ein Feld, das absichtlich leer bleibt, sagt im Docstring **wofür es reserviert ist**
> und **wer es füllen wird**.

### 4.7 Handgeführte Indizes vermeiden (D2)

`pages/3_Texts.py:141-167` zählt einen `idx` von Hand über bedingt angelegte Tabs hoch.

> **Regel:** Wo eine Liste und ihre Indizes parallel gepflegt werden, stattdessen Paare aus
> (Bezeichner, Funktion) bilden und zippen. Handgeführte Zähler sind Bugs in Wartestellung.

---

## 5. Umgang mit LLM-Aufrufen

Dieser Abschnitt ist projektspezifisch und wichtiger als alles andere, weil hier die teuersten
Fehler entstanden sind.

### 5.1 Nie ein API-Call pro Token

Der per-Wort-Fallback erzeugte 429-Stürme bei 50 RPM. Die Gegenmaßnahme steht seither in zwei
Docstrings.

> **Regel:** Aufrufmengen müssen **deterministisch begrenzt** sein und dürfen nicht mit der
> Tokenzahl skalieren. Jede Wiederholungslogik nennt ihre Obergrenze im Docstring.

### 5.2 Parser machen keine API-Calls

> **Regel:** Ein Parser resynchronisiert aus dem, was er hat, oder gibt auf. Er fordert nie nach.
> Ein Parser, der bei Fehlern nachfordert, ist ein unbegrenzter Aufrufmultiplikator.

### 5.3 Prompt-Länge ist ein überwachtes Budget

Der pt→de-Systemprompt ist unbemerkt von 5300 auf 6158 Zeichen gewachsen (B2), obwohl
[`decoder-prompting-rules.md`](decoder-prompting-rules.md) §4.1 ausführlich begründet, warum Kürze
die Anweisungstreue trägt.

> **Regel:** Prompt-Größe wird per Assertion überwacht. Wächst sie, ist das eine bewusste
> Entscheidung mit Messung, kein Nebeneffekt.

### 5.4 Zusätzliche Aufgaben bekommen einen eigenen Call

> **Regel:** Ein bewährter Prompt wird nicht um Zusatzaufgaben erweitert. Neue Aufgaben laufen als
> **separater Call mit eigener Prompt-Konfiguration, die keinen Text mit dem bewährten teilt.** So
> ist die Trennung strukturell garantiert statt gut gemeint, und ein Fehlschlag bleibt lokal.

### 5.5 Sprachwissen gehört in YAML, nicht in Code

`prompts/*.yaml` ist **Daten**: ein neues Sprachpaar ist eine Datei, kein Codeeingriff. Das ist eine
der besten Eigenschaften des Projekts.

> **Regel:** Linguistische Regeln, Beispiele und Disambiguierungen leben in YAML, in prüfbarer Prosa.
> Code interpretiert sie, enthält sie aber nicht.

### 5.6 Graceful Degradation ist Pflicht, nicht Kür

> **Regel:** Ein fehlgeschlagener Anreicherungsschritt leert Felder — er bricht nie den Hauptpfad.
> Jeder optionale LLM-Aufruf beschreibt in seinem Docstring, wie sein Fehlschlag aussieht.

---

## 6. Datenbank

- **psycopg v3** durchgehend. `psycopg2` ist entfernt (siehe C5 für die verbliebene Ausnahme).
- **Migrationen** nach `sql/README.md`: eine `BEGIN; … COMMIT;`-Datei pro Änderung, idempotent wo
  möglich (`IF NOT EXISTS`), `schema.sql` synchron halten, Commit-Nachricht
  `DB migration 0NN: <was und warum>`.
- **Konventionen:** UUID-PK via `gen_random_uuid()`, PK heißt `<tabelle_singular>_id`,
  `TIMESTAMPTZ`, `set_updated_at()`-Trigger, Nutzerdaten cascaden von `users`.
- **Bewusste Abweichungen werden im Schema kommentiert.** Die geteilte Sprachschicht cascadet
  absichtlich *nicht* von `users` — ohne Kommentar liest sich das wie ein Versehen.
- **Massenschreibvorgänge in einer Verbindung.** `DBService` öffnet pro Aufruf eine frische
  Verbindung; N Einzelinserts sind N TCP+TLS-Handshakes gegen Neon.

---

## 7. Tests

Der Bestand hat einen Harness (`tests/test_decoder_e2e.py`), aber keine Prüfungen — er druckt Text,
und ein Mensch müsste zählen (B1).

- **Ein Test, der nichts behauptet, ist kein Test.** Assertions statt Ausgabe.
- **Offline-Pfad für alles, was ein LLM aufruft.** Ein gestubbter Service, der konservierte
  Antworten liefert, macht aus einer nichtdeterministischen Prüfung einen Byte-Vergleich. Die Weiche
  dafür existiert bereits (`hasattr`-Fähigkeitserkennung).
- **Reine Logik wird offline getestet** — Satzsegmentierung, Normalisierung, Renderer brauchen
  keinen API-Key.
- **Der Stil bleibt beim Bestand:** ausführbare Skripte mit `assert`, kein pytest-Zwang.

---

## 8. Git

Aus `CLAUDE.md`, hier nur zusammengefasst:

- **Nie direkt auf `main`.** `main` wird auto-deployed und hat echte Testerdaten.
- Branch-Präfixe: `feature/`, `fix/`, `refactor/`.
- Schemaänderungen bringen ihre Migration **im selben Branch** mit.
- Vor dem Merge: lokaler Smoke-Test des geänderten Flows **plus Login/Logout**.
- **Verhaltensändernde Korrekturen bekommen einen eigenen Commit** mit ausdrücklichem Hinweis —
  nicht in einen Refactor eingemischt, der byte-identisch bleiben soll.

---

## 9. Was diese Standards nicht vorschreiben

Bewusst offen gelassen, um keine Scheingenauigkeit zu erzeugen:

- **Kein Formatter-Zwang.** Der Bestand ist konsistent genug; ein Formatter über 5.000 Zeilen
  erzeugt einen Diff, der jede Codehistorie unlesbar macht. Falls doch, dann in einem eigenen,
  ausschließlich formatierenden Commit.
- **Keine Testabdeckungsquote.** Für einen Prototyp ist die falsche Metrik; die richtige ist, ob die
  246/246-Messung reproduzierbar läuft.
- **Kein Typprüfer im CI** — vorerst. Typannotationen dienen hier der Lesbarkeit.

---

*Erstellt 2026-08-08 auf Branch `verbiverse-concept`. Die Beispiele in §1 sind wörtliche Zitate aus
dem Bestand.*
