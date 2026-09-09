# Zielarchitektur langDec — Plattformen, Datenhaltung, Technologiewahl

**Stand:** 2026-08-08 · **Branch:** `verbiverse-concept` · **Status:** Konzept zum Review

Dieses Dokument beantwortet drei Fragen:

1. Ist **Clojure + Dart** — der Vorschlag des Kollegen — für langDec sinnvoll?
2. Welche Technologie trägt die **zentrale Universum-Datenbank**?
3. Wie funktioniert **"eigenes Universum lokal, großes Universum auf dem Server"** über Android,
   iOS, Web und Desktop?

Der Prototyp läuft dabei **weiter in Python**. Ziel ist eine Richtungsentscheidung, damit das
Datenmodell nicht gegen die Zukunft gebaut wird.

Verwandt: [`vokabeluniversum_concept.md`](vokabeluniversum_concept.md) (das Datenmodell),
[`cross_lingual_similarity_concept.md`](cross_lingual_similarity_concept.md) (die
Ähnlichkeitsschicht).

---

## 0. Zusammenfassung

| Frage | Antwort |
|---|---|
| Clojure + Dart? | **Die Dart-Hälfte ja, die Clojure-Hälfte nein.** Flutter für die Clients, Python im Backend |
| Flutter Web? | **In Phase 1 nicht nötig** — Streamlit *ist* schon eine DOM-Web-App |
| Zentrale DB? | **PostgreSQL auf Neon** + `pg_trgm` + `unaccent` + später `pgvector` |
| Datalog-Familie? | Absage bleibt — aber **aus anderen Gründen als bisher behauptet** (§2.3) |
| Sync? | **Selbst gebaut für v1**, PowerSync als benannter Ausbauweg |
| CRDT? | **Nein** — mit einer Korrektur, die zählt (§3.2) |
| DB an Sprache koppeln? | **Nein**, mit genau einer Ausnahme (§2.5) |

**Der entlastende Befund:** die schwer umkehrbaren Entscheidungen sind **Schema-Entscheidungen**,
und die hängen nicht an der Sprachwahl. Das Datenmodell aus
[`vokabeluniversum_concept.md`](vokabeluniversum_concept.md) kann entschieden und umgesetzt werden,
**während die Plattformfrage offen bleibt**.

---

## 1. Clojure + Dart

### 1.1 Was der Vorschlag überhaupt bedeutet

Clojure und Dart teilen **keine Laufzeit**. Die möglichen Lesarten:

| Lesart | Bewertung |
|---|---|
| (a) Clojure-Backend + Flutter-Clients über HTTP/JSON | **kohärent** — aber **null Code-Sharing** zwischen beiden |
| (b) ClojureScript-Frontend + Dart irgendwo | zwei vollständige UI-Codebasen — das Gegenteil des Ziels |
| (c) Clojure-Backend + Dart-Backend-for-Frontend | zusätzliche Schicht ohne erkennbaren Nutzen |
| (d) **ClojureDart** — Clojure, das nach Dart kompiliert und Flutter treibt | **real**: Roam Research hat damit seine Mobile-Apps ausgeliefert. Aber von einer Zwei-Personen-Beratung nebenbei gepflegt, und **hilft beim Web nicht** |

Nur (a) und (d) sind ernsthaft diskutabel. (d) ist für ein Zwei-Personen-Team eine zu große Wette
auf ein Nebenbei-Projekt.

**Also ist die Frage: Clojure-Backend, ja oder nein — und Flutter-Clients, ja oder nein.** Zwei
unabhängige Entscheidungen.

### 1.2 Flutter für die Clients: ja, mit einer wichtigen Einschränkung

Für Android, iOS und Desktop ist Flutter aus einer Codebasis ein starkes Argument.

**Im Web ist die Lage ungünstig, und ausgerechnet für diese App.** Der HTML-Renderer ist
**entfernt**; es bleiben CanvasKit und skwasm, die beide in ein `<canvas>` malen
([flutter#145954](https://github.com/flutter/flutter/issues/145954)). Folgen:

- **Kein DOM-Text**, also funktioniert **das Ctrl+F des Browsers nicht**
  ([#65504](https://github.com/flutter/flutter/issues/65504),
  [#79578](https://github.com/flutter/flutter/issues/79578))
- **Barrierefreiheit** ist ein paralleler Semantik-Baum, der **aktiv eingeschaltet werden muss**
  ([Doku](https://docs.flutter.dev/ui/accessibility/web-accessibility))
- Kein Browser-Übersetzen, kein Lesemodus, kein Nachschlagen auf eurem Text

Für eine **Lese- und Textmarkierungs-App** ist das kein Randthema.

*Nuance:* **innerhalb** des eigenen Readers ist `SelectionArea` in Ordnung — die Auswahl will man
ohnehin abfangen. Verloren geht alles, was der Browser dem Leser **gratis** gäbe.

*Zum Vergleich:* **Compose Multiplatform ist im Web schlechter** — dort funktioniert
`SelectionContainer` in Kotlin/Wasm gar nicht
([#4103](https://github.com/JetBrains/compose-multiplatform/issues/4103)).

> **Und daran löst sich das Problem auf: Flutter Web wird in Phase 1 nicht gebraucht.**
> Streamlit *ist* bereits eine DOM-Web-App. Web bleibt auf DOM, Flutter übernimmt
> Android/iOS/Desktop.

### 1.3 Clojure im Backend: nein — und der Grund ist nicht Geschmack

**Die Rewrite-Kosten, quantifiziert.** Die gesamte App ist **5.093 LOC**. Die getunte Prompt-Logik
sind **~1.100 LOC plus 143 Zeilen YAML** — und YAML ist **portierbare Daten**, kein Code. Der
**mechanische** Port ist damit 1–2 Wochen in jeder Sprache.

**Das ist nicht das Risiko.** Das Risiko ist, dass **246/246 empirisch und nicht herleitbar** ist.
Jede Regel in [`decoder-prompting-rules.md`](decoder-prompting-rules.md) §4 ist die **Narbe eines
beobachteten Fehlers**:

- `max_tokens=64`, weil Haiku Eigennamen erklärte statt sie zu übersetzen
- `[L1]`-Label statt `1.`, weil Haiku die Nummerierung als Token behandelte und zu "eins" übersetzte
- Retry-vor-Padding, weil Padding **jedes spätere Token verschiebt**

**Ein Rewrite, der korrekt aussieht, kann still bei 240/246 landen.** Und niemand merkt es, solange
die Messung nicht existiert (siehe [`code_review_2026-08.md`](code_review_2026-08.md) B1).

**Bleibt das Backend Python, ist diese Kosten exakt null.** Diese Asymmetrie entscheidet die Frage.

**Clojures reale Lücken für diesen Anwendungsfall:**

| Bedarf | Lage in Clojure |
|---|---|
| Anthropic-Client | **kein gepflegter** — `nsadeh/clojure-anthropic` ist selbsterklärt pre-alpha |
| OpenAI-Client | `wkok/openai-clojure` existiert, aber nur OpenAI |
| OCR | **kein EasyOCR-Äquivalent** auf der JVM |
| TTS, YAML, HTTP | unproblematisch |

**Was Clojure ehrlicherweise besser könnte:** über Java-Interop bekäme man das **offizielle
`anthropic-java`-SDK** und **PDFBox (Apache-2.0)** — also eine **bessere Lizenzhygiene als der
heutige Python-Stack** (§1.5). JVM-RAM und Kaltstart sind auf dieser Größe irrelevant.

**Das entscheidende Argument steht im eigenen Konzept.**
[`technical_concept_prototype_stack_tooling.md`](technical_concept_prototype_stack_tooling.md) §4
hält fest, dass dieses Projekt **AI-gestützt** entwickelt wird. KI-Unterstützung ist bei Clojure
deutlich schwächer als bei Python oder Dart. Bei zwei Personen, von denen *eine* Clojure vorschlägt
und die andere es erben würde, wiegt das schwerer als jedes Argument über theoretische Passung.

> Der Fehlermodus eines 5.000-Zeilen-Projekts ist nie "suboptimale Laufzeitumgebung".
> Er ist: **"der Rewrite ist bei 70 % steckengeblieben."**

### 1.4 Ein Kompromiss, der den Vorschlag ernst nimmt

Clojure dort hineinlassen, wo es **nichts kostet**: als **eigenständiger Batch-EPUB-Vorverarbeiter**
(PDFBox + `next.jdbc`), der nachts den Decode-Cache vorwärmt.

- Genuin Clojure-förmig (Batch, Datenverarbeitung, JVM-Bibliotheken)
- Unabhängig deploybar
- Jederzeit löschbar, ohne dass die App stehenbleibt
- Löst nebenbei das AGPL-Problem (§1.5), weil PDFBox Apache-2.0 ist

**Das ist ein viel besserer Test der Frage "passt Clojure zu uns" als den Decoder darauf zu wetten.**

### 1.5 Zwei Befunde, die unabhängig von jeder Technologiewahl gelten

**A. Es besteht heute eine Lizenz-Haftung.**

**PyMuPDF ist AGPL-3.0-oder-kommerziell**, und AGPL §13 lässt **Netzwerknutzung als Verbreitung**
zählen — laut Hersteller ausdrücklich "auch als Microservice hinter einer API"
([Artifex](https://artifex.com/licensing)). Die naheliegende Python-EPUB-Bibliothek **EbookLib ist
ebenfalls AGPL**. Der natürliche Python-Dokumentenstack ist damit **zwei AGPL-Abhängigkeiten tief**.

Für einen privaten Prototyp unkritisch, **vor einer Kommerzialisierung zu klären**. EPUB/PDF
clientseitig in Dart (`pdfrx`, MIT auf PDFium-BSD) beseitigt es vollständig — ein echtes Argument
für Flutter, das nichts mit UI zu tun hat.

**B. iOS-Share-Extensions brauchen natives Swift — in jedem Stack.**

Flutter dokumentiert `FlutterViewController` in Extensions, warnt aber nur für ≥100 MB; das
Share-Limit liegt bei 120 MB, und
[flutter#135243](https://github.com/flutter/flutter/issues/135243) berichtet, dass eine **minimale
Flutter-Extension es bereits überschreitet**. Also ~150–300 Zeilen Swift, **unvermeidbar** — React
Native läuft in dieselbe Wand.

Dazu, produktrelevant: **iOS hat kein Äquivalent zu Androids `ACTION_PROCESS_TEXT`.** Das
Flaggschiff *"irgendwo Text markieren → Decode"* ist damit **Android-first aus Plattformgründen,
nicht aus Framework-Gründen.** Das ist eine Produkterwartung, die man früh geradeziehen sollte.

### 1.6 Textaufnahme, verifiziert pro Plattform

| Weg | Lage |
|---|---|
| **Android Share-Target** | `receive_sharing_intent` gesund (aktiv gepflegt, hohe Nutzung) |
| **Android `ACTION_PROCESS_TEXT`** | Plugins klein/community, aber die Registrierung ist ~50 Zeilen Kotlin — Plugin-Gesundheit also kein Risiko |
| **iOS Share/Action Extension** | ~150–300 Zeilen Swift, unvermeidbar (§1.5 B) |
| **Web Share Target** | MDN: *"Limited availability"*, **nicht Baseline**, erfordert PWA-Installation, Firefox hat keine Pläne. **Darauf lässt sich nicht planen** |
| **PDF in Dart** | **positive Überraschung:** `pdfrx`, MIT, aktiv, **alle sechs Zielplattformen inkl. Web/WASM**, Textauswahl standardmäßig an |
| **EPUB in Dart** | **dünn:** `epubx` drei Jahre alt; `epub_pro` beschreibt sich selbst als *"a fork of a fork, of a fork"*; `epub3` zwei Jahre alt. **Empfehlung: selbst schreiben** auf `archive` + `xml`, ~200–400 Zeilen — ihr braucht ohnehin Spine/Offset-Anker, die keine Bibliothek liefert |

### 1.7 Vergleich der Gesamtoptionen

| Kriterium | Clojure + Flutter | **Python + Flutter** | FastAPI + React/Expo | Compose Multiplatform |
|---|---|---|---|---|
| Wiederverwendung der getunten Decode-Logik | **null** (Rewrite) | **vollständig** | vollständig | null |
| Android / iOS | gut | gut | gut | gut |
| Web | Flutter-Web-Probleme | **Streamlit/DOM in Phase 1** | **nativ DOM** | **schlechter als Flutter** |
| Desktop | gut | gut | Tauri/Electron nötig | gut |
| Share-Sheet / markierter Text | Swift nötig | Swift nötig | Swift nötig | Swift nötig |
| EPUB/PDF ohne AGPL | ja (PDFBox) | **ja (`pdfrx` clientseitig)** | teils | ja |
| Offline-fähig | ja | ja | ja (PWA/RN) | ja |
| Realismus für 2 Personen | **schwach** (KI-Unterstützung, Erben) | **stark** | stark | mittel |
| Hosting | JVM | schlank | schlank | JVM/nativ |

**Empfehlung: Python-Backend + Flutter-Clients**, Web zunächst über die bestehende DOM-App.

### 1.8 Der Weg ohne Big Bang

1. **FastAPI vor das unveränderte `domain/`** — 600–900 LOC. Streamlit läuft weiter, weil es
   dieselben Python-Module aufruft.
2. **Token-Auth** — 2–4 Tage.
3. **Erster Flutter-Client ~2–3 Wochen später**, Android zuerst.

Kein Zeitpunkt, an dem der Prototyp stillsteht oder Tester ausgesperrt werden.

---

## 2. Die zentrale Universum-Datenbank

### 2.1 Empfehlung: PostgreSQL auf Neon

Nicht weil "relational sicher ist", sondern weil die zwei Abfragen, auf die es ankommt —
**approximative Nächste-Nachbarn-Suche** und **begrenztes Zählen** — genau das sind, worin jeder
Datalog- und Graph-Kandidat am schwächsten ist.

**Verifizierte Extension-Unterstützung auf Neon:**

| Extension | Neon | Nutzen hier |
|---|---|---|
| `pg_trgm` | **ja** (1.6) | Schreibweisen-Ähnlichkeit, GIN/GiST-Index |
| `pgvector` | **ja** (0.8.x) | Embeddings, HNSW |
| `fuzzystrmatch` | **ja** | `levenshtein`, `daitch_mokotoff` |
| `unaccent` | **ja** | Diakritika-Normalisierung |
| **Apache AGE** | **nein** | bestätigt den früheren Befund |

Quelle: [Neon — Supported Postgres extensions](https://neon.com/docs/extensions/pg-extensions)

> **Warnung zu `fuzzystrmatch`:** dessen `soundex` und `metaphone` sind englisch getunt und liefern
> für de/pt/sv Unsinn. Postgres dokumentiert selbst, dass sie "nicht gut mit Multibyte-Kodierungen
> wie UTF-8 funktionieren". Nur `levenshtein` und `daitch_mokotoff` sind mehrsprachig brauchbar.

### 2.2 Die Ähnlichkeitsanforderung schränkt die DB-Wahl nicht ein

Wichtig zur Entlastung der Diskussion: die cross-linguale Ähnlichkeit wird **von einem Batch-Job in
Kanten vorberechnet**, nicht zur Abfragezeit gerechnet (Details in
[`cross_lingual_similarity_concept.md`](cross_lingual_similarity_concept.md)). Die Datenbank macht
danach nur noch **indizierte Lookups auf eine gewöhnliche Tabelle**.

Der Ähnlichkeits-Job ist damit ein Python-(oder Clojure-)Batch, jederzeit neu berechenbar und
wegwerfbar. Er erzeugt **null Lock-in** und stellt **null Anforderungen** an den Store.

**Daraus folgt: "wir brauchen Ähnlichkeitssuche" darf kein Argument für eine exotische Datenbank
sein.**

### 2.3 Die Datalog-Familie — ehrliche Neubewertung

**Das frühere Argument war schlecht und wird zurückgezogen.** *"Clojure passt nicht zum
Python-Stack"* war nie ein guter Grund, Datalog abzulehnen. Wenn das Backend Clojure würde, wären
Datomic/XTDB/Datalevin ergonomisch ausgezeichnet.

**Die Absage bleibt trotzdem — aus drei Gründen, die von den Daten handeln:**

1. **Datalogs Stärke liegt quer zum Engpass.** Datalog gewinnt bei **rekursiven Regeln über Daten
   unbekannter Form**. Der Engpass hier ist **approximatives Matching** — Trigramm- und phonetische
   Nächste-Nachbarn-Suche. Datomic und XTDB haben darauf keine Antwort; man betriebe Postgres
   *daneben* und hätte zwei Stores plus ein Konsistenzproblem.

2. **Bitemporalität ist hier zufällig, nicht nützlich.** Die zeitliche Frage, die interessiert, ist
   *"wann hat dieser Nutzer dieses Wort gelernt"* — **Domänenzeit**, die man als indizierte Spalte
   will, um zu gruppieren und zu aggregieren. XTDB und Datomic liefern **Systemzeit** ("was
   glaubten wir am Tag X"), ein Audit-Feature. Bitemporalität ist ein echter Grund für XTDB — bei
   einer Bank.

3. **Betrieb dominiert auf dieser Größe.** Datomic ist seit 2023
   [lizenzkostenfrei](https://blog.datomic.com/2023/04/datomic-is-free.html) und wird von Nubank
   gepflegt — aber man betreibt einen JVM-Transactor plus Storage. **XTDB v2** ist GA und MPL-2.0,
   braucht produktiv aber VM + S3 + Kafka für HA und hat **kein Managed-Angebot**. Für ein Projekt,
   dessen Infrarechnung heute aus einem Neon-Free-Tier besteht, ist das der dominierende Posten.

| Kandidat | Traversierung | Ähnlichkeit/ANN | Betrieb | Lizenz | Verdikt |
|---|---|---|---|---|---|
| **PostgreSQL (Neon)** | 1–4 Index-Joins — genau die nötige Form | **nativ** | **null** (läuft schon) | frei | **Empfohlen** |
| Datomic | exzellentes Datalog | **keine** | JVM-Transactor + Storage | Apache-2.0, keine Lizenzgebühr | nein |
| XTDB v2 | gut, SQL + XTQL, bitemporal | **nicht dokumentiert** | VM + S3 (+ Kafka), **kein Managed** | MPL-2.0 | nein, **aber der Hedge** (§2.4) |
| **Datahike** | Datomic-kompatibel | keine | eingebettet, einfach | EPL | **nein — letztes Release Aug 2024** |
| Datalevin | Datalog + Volltext + **Vektorsuche in einer Datei** | **ja** | eingebettet | EPL-2.0 | **nein** (§2.4), aber der interessanteste Clojure-Kandidat |
| Neo4j / Memgraph | Stärke bei variabler Tiefe | Vektorindex, kein Trigramm | zweiter Store | kommerziell/GPL | nein — die Last ist nicht graphförmig |
| Qdrant / LanceDB daneben | — | exzellent | Extra-Dienst bzw. Datei | Apache-2.0 | verfrüht |

**Ist die Last graphförmig? Nein.** Die Struktur ist graph-*ähnlich*
(`token → lexem → konzept ← lexem ← lemma` plus Ähnlichkeitskanten), aber **jede Abfrage hat feste
Tiefe und feste Form**. Die tiefste — *"gib mir deutsche Lemmata mit demselben Konzept wie dieses
schwedische Lemma"* — sind vier Joins. Graphdatenbanken zahlen sich bei **variabler Tiefe** und
Pfadsuche aus. Nichts in der Anforderungsliste braucht das.

**Datalevin verdient eine faire Erwähnung und dann eine präzise Absage:** es macht Datalog +
Volltext + Vektorsuche in *einer* eingebetteten Datei, ist EPL-lizenziert und hat veröffentlichte
PyPI-Bindings. Es wäre ein attraktiver Store **auf dem Gerät** für eine Clojure-Zukunft. Aber es ist
JVM/native-image und hat **keine Dart-FFI-Bindung** — es kann also genau das nicht sein, wofür man
es bräuchte: der lokale Store eines Flutter-Clients. *Richtige Idee, falsche Plattform.*

> **Das Gespräch mit dem Kollegen sollte nicht über Clojure gehen.** Die zwei Fragen, die es
> entscheiden:
> **"Zeig mir die Abfrage, die Postgres nicht beantworten kann"** und **"wer betreibt den
> Transactor?"**

### 2.4 Der Hedge ist ungewöhnlich gut

**XTDB v2 spricht das Postgres-Wire-Protokoll** ([xtdb/xtdb](https://github.com/xtdb/xtdb)). Sollte
Bitemporalität je wirklich wichtig werden, ist die Migration ein **Connection-String-Wechsel plus
Dialekt-Audit**, kein Rewrite. Wenige Datenbankentscheidungen kommen mit einem so billigen
Notausgang — den sollte man mitnehmen.

### 2.5 DB-Wahl und Backend-Sprache entkoppeln

**Kopplung nur bei einer eingebetteten, In-Process-Datenbank** — dann ist die DB eine *Bibliothek*,
und Bibliotheken sind sprachgebunden. Datomic Local, Datalevin und XTDB in-process sind
JVM-Artefakte: sie zu wählen *ist* die JVM zu wählen. SQLite auf dem Gerät ist das Spiegelbild — es
wird von der Client-Plattform gewählt.

Bei einer **vernetzten** DB soll die Kopplung null sein. DB nach Lastform, Betriebsaufwand und
Datenlebensdauer wählen; Sprache danach, wer sie pflegt.

**Die gefährliche Richtung ist nicht "Postgres, also Python"** — das behauptet niemand. Sie ist
**"wir schreiben Clojure, also Datomic"**. Das Gegenargument:

> **Die Daten überleben den Code.** Dieses Schema übersteht mehrere Backend-Generationen —
> Streamlit heute, FastAPI oder Clojure morgen, in fünf Jahren etwas anderes. Der Store soll deshalb
> die **am wenigsten sprachmeinungsstarke** Komponente im Stack sein, gerade weil er die einzige
> ist, die man nicht billig ersetzen kann.

### 2.6 Geteilte und nutzereigene Daten physisch trennen? Später

**Logisch nein, physisch zunächst zusammen** — aber den kleinen Preis zahlen, der sie trennbar hält:

1. **Kein Fremdschlüssel von geteilten auf Nutzertabellen** (es gibt ohnehin keinen Grund dafür).
2. **Nutzerzeilen referenzieren geteilte Entitäten nur über eine global stabile UUID**, und die App
   muss eine **nicht auflösbare Referenz vertragen**. Dann kann das Gerät ein `lexeme_id` halten,
   ohne die ganze Lexem-Tabelle zu haben.
3. **Keine Abfrage joint eine geteilte auf eine Nutzertabelle, wenn das Ergebnis transaktional
   konsistent sein muss.** Jeder solche Join ist ein künftiger Migrationsblocker.

Mit diesen drei Regeln wird "ein Store oder zwei" zu einem Deployment-Detail, das man jahrelang
aufschieben kann.

---

## 3. Local-First und Synchronisation

### 3.1 Die Datenkategorien — daran hängt alles

| Kategorie | Menge | Schreiber | Autorität | Sync-Bedarf |
|---|---|---|---|---|
| Texte, Ordner | ~100/Nutzer | Nutzer | Gerät des Nutzers | echt, winzig, LWW |
| **`tokens`, `sentences`** | ~480 + ~35 pro Text | Decode-Job | **abgeleiteter Cache** | **keiner** |
| Token-Korrekturen | selten, einzelne | Nutzer | **Nutzer, Quelle der Wahrheit** | echt, winzig, LWW |
| Lernstatus | ~5.000/Nutzer | Nutzer | Nutzer | echt, winzig, LWW |
| **Wiederholungshistorie** | 10⁴–10⁵/Nutzer | Nutzer | Nutzer | echt, **muss append-only sein** |
| Konzepte, Lemmata, Lexeme | 10⁵–10⁶ gesamt | Server | **nur Server** | read-only Replikation |
| Ähnlichkeitskanten + Zähler | ~10⁷, durch Lexikon begrenzt | Server-Batch | nur Server | read-only Replikation |

**Die gesamte Menge steckt in den Kategorien 2 und 6/7 — und keine davon braucht bidirektionalen
Sync.** Deshalb ist dieses Problem viel kleiner, als es aussieht.

### 3.2 Kein CRDT nötig — mit einer Korrektur, die zählt

**`tokens`/`sentences` brauchen keinen Sync** — Einzelschreiber, nie konkurrent bearbeitet, aus
`texts.content` plus Decode-Service ableitbar.

*Wrinkle:* "ableitbar" gilt nur **online und zu LLM-Kosten**. Ein Decode ist Sekunden und Cent, nicht
Mikrosekunden. Also **Cache-Semantik: man braucht Haltbarkeit, nicht Konvergenz** — und einen
Provenienz-Stempel (`decoded_by_service`, `model`, `prompt_version`, `decoded_at`).

**Lernstatus als Enum:** LWW pro Zeile genügt. Schlimmstenfalls widersprechen sich zwei eigene
Geräte und eines verliert — Kosten: eine Wiederholung.

**Und hier war die ursprüngliche Annahme falsch:** `vocab_cards` ist heute **veränderlicher
Zählerstand** (`box_number`, `last_reviewed`, `next_review`). LWW auf Zählern ist **echt
verlustbehaftet**: Gerät A macht offline 30 Wiederholungen, Gerät B fünf, B synchronisiert zuletzt —
**A's 30 Wiederholungen sind spurlos weg.** Genau hier greifen Leute zum CRDT.

**Nötig ist es nicht.** Wiederholungshistorie **append-only** machen (siehe
[`vokabeluniversum_concept.md`](vokabeluniversum_concept.md) §6.2 und §7.4):
Append-only-Zeilen mit clientgenerierten IDs mergen per **Mengenvereinigung** — trivial konvergent,
keine Vektoruhren, keine Merge-Funktion. `box_number` wird eine abgeleitete Projektion.

**Damit: kein CRDT.**

1. **Es gibt nirgends kollaboratives Editieren.** Die kanonische CRDT-Begründung — mehrere
   *verschiedene* Nutzer verändern gleichzeitig dasselbe Objekt — kommt nicht vor. Jeder Konflikt
   ist zwischen den eigenen Geräten eines Nutzers.
2. **Jede Schreibkategorie reduziert auf Mengenvereinigung oder LWW-pro-Zeile.**
3. **Die Kosten wären in diesem Stack hoch:** Loro, Automerge und Yjs sind alle MIT und aktiv, aber
   liefern **keine herstellergepflegten Dart/Flutter-Bindings**. Man pflegte eine FFI-Schicht für
   ein Problem, das man nicht hat.

**Drei Dinge würden das kippen — also bewachen:**

- veränderliche Wiederholungszähler statt Ereignis-Log
- ein **langes Freitextfeld** von zwei Geräten offline bearbeitet (`texts.notes`) → dann **Feld-LWW**,
  nicht Modell-CRDT
- **geteilte/kollaborative Texte** (Lehrer und Schüler an einem Decode). Das ist eine
  Produktentscheidung, aber die einzige, die diese ganze Analyse ungültig machen würde — **früh
  flaggen, falls sie auf der Roadmap steht**

### 3.3 Die Ausnahme bei der geteilten Schicht

Ein Gerät trifft offline auf ein Wort ohne Lexem. Es darf **nicht** in die geteilten Tabellen
schreiben — das ist das Einzige, was die Konfliktfreiheit brechen könnte.

Stattdessen eine **nutzereigene Vorschlagszeile** mit clientgenerierter ID, die wie alle
Nutzerdaten synchronisiert; der Server dedupliziert später und setzt eine Umleitung auf das
kanonische Lexem. Das Gerät hält einen lokalen Redirect. **Die geteilte Schicht bleibt strikt
serverautoritativ.**

### 3.4 Korrekturen an einem abgeleiteten Cache

Der interessante Sonderfall: `tokens` ist ein Cache, aber der Nutzer korrigiert darin den
Off-by-one-Versatz. Ein Re-Decode würde diese Arbeit wegwerfen.

**Lösung: Overrides statt Mutation, Operationen statt Werte, Anker auf Inhalt statt Position.**
Vollständig ausgeführt in [`vokabeluniversum_concept.md`](vokabeluniversum_concept.md) §5 — dort
liegt auch die DDL.

Das ist die **am wenigsten umkehrbare Entscheidung des ganzen Systems**: sobald Nutzer den Cache
direkt korrigiert haben, lässt sich Korrektur nicht mehr von Decode-Ausgabe unterscheiden, und dann
kann **nie wieder gefahrlos neu decodiert werden**.

### 3.5 Sync-Werkzeug: v1 selbst bauen

Der Markt ist enger, als man denkt:

| Option | Dart-Client | Modell | Postgres-Kopplung | Verdikt |
|---|---|---|---|---|
| **Selbst gebaut** | trivial (HTTP + Drift) | selbst bestimmt | keine | **Empfohlen für v1** |
| **PowerSync** | **erstklassig, herstellergepflegt** | SQLite ↔ Postgres, bidirektional | **logische Replikation nötig** | **benannter Ausbauweg** |
| ElectricSQL | Dart-Paket **veraltet** (vor dem 2024-Rewrite) — unverifiziert | **nur Lesepfad** | logische Replikation | gut für den geteilten Read-Only-Ausschnitt |
| Zero (Rocicorp) | **keiner — TypeScript only** | — | — | raus |
| Triplit | **keiner — TypeScript only** | — | eigener Store | raus |
| Turso / libSQL Embedded Replicas | vorhanden | SQLite ↔ SQLite | **verdrängt Postgres** | raus — Altlast, Engine im Rewrite |
| **Realm / Atlas Device Sync** | hatte einen | — | — | **tot — Sync am 30.09.2025 abgeschaltet** |
| CouchDB / PouchDB | schwach | JSON-Dokumente | keine | raus — erzwingt Dokumente auf ein relationales Modell |
| Ditto | ja | P2P-Mesh-CRDT | keine | überdimensioniert — kein P2P-Bedarf |

**Warum selbst bauen für v1 gewinnt:** Sync-Engines lohnen sich, wenn die Daten **groß** *und* das
Konfliktmodell **schwer** ist. Hier ist beides nicht der Fall — ein Nutzer-Delta aus ein paar
tausend winzigen Zeilen mit LWW oder Mengenvereinigung, plus ein Read-Only-Ausschnitt. Konkret:

- `GET /shared?pair=de-sv&since=<version>` → Deltas des geteilten Ausschnitts (cachebar, keine
  Autorisierung pro Zeile, kein Replikationsslot)
- `GET /changes?since=<server_seq>` und `POST /changes` → Nutzerzeilen mit LWW auf `updated_at` und
  Tombstones

Wenige hundert Zeilen, kein Anbieter, und **volle Kontrolle über das Replay der Korrekturen** —
genau der Teil, den eine generische Engine unbequem machen würde.

> **Die Kostenfalle, die das entscheidet:** PowerSync *und* Electric brauchen einen **logischen
> Replikationsslot**. Neon dokumentiert, dass Replikation die **Compute dauerhaft aktiv hält — kein
> Scale-to-Zero** — und dass das Einschalten **nicht rückgängig zu machen ist** und alle Computes
> neu startet. Aus einer fast kostenlosen Datenbank wird eine immer laufende.
> **Diesen Schalter erst umlegen, wenn PowerSync wirklich eingeführt wird.**
> ([Neon — Logical replication](https://neon.com/docs/guides/logical-replication-postgres))

### 3.6 Sync-Disziplin, die jetzt ins Schema muss

Alle fünf braucht **jedes** Verfahren, auch das selbstgebaute. Nachrüsten in Zeilen, die schon auf
Nutzergeräten liegen, heißt die ganze Flotte anfassen:

1. **Clientgenerierbare Primärschlüssel** (UUID), nicht DB-Sequenzen. Ist vorhanden — der Client muss
   sie nur erzeugen dürfen.
2. **`updated_at`** auf jeder syncfähigen Tabelle. Größtenteils per Trigger vorhanden.
3. **Tombstones: `deleted_at`, Soft Delete. Fehlt heute überall.** Ohne sie kann ein Löschen nicht
   propagieren und jedes Gerät sammelt für immer Zombie-Zeilen an. **Der billigste und wertvollste
   Zusatz im ganzen Plan.**
4. **Monotone `server_seq`**, damit `?since=` ein Range-Scan ist und kein Zeitstempelvergleich über
   Uhrendrift hinweg.
5. **Namensraum für geteilte Entitäten mit provisorisch→kanonisch-Umleitung** (§3.3).

---

## 4. Mengen, Statistiken, Datenschutz

### 4.1 Mengenrechnung

Pro Nutzer bei 480 Tokens/Text und 100 Texten: **48.000 Tokenzeilen**, ~3.500 Satzzeilen, ~5.000
Wissenszeilen.

| Größe | Tokenzeilen **falls zentral** | Geschätzt | Verdikt |
|---|---|---|---|
| 10 Nutzer | 480.000 | ~100 MB | passt in Neon Free (0,5 GB) |
| **~50 Nutzer** | 2,4 Mio. | **~0,5 GB** | **Neon-Free-Decke** |
| 1.000 Nutzer | 48 Mio. | ~10 GB | in Ordnung auf einem Bezahltarif |
| 100.000 Nutzer | **4,8 Mrd.** | **~1 TB** | **bricht** |

> **`tokens` darf deshalb nie serverautoritativ werden.** Für den heutigen Streamlit-Prototyp gibt
> es kein Gerät, also liegt es serverseitig — als **Cache**. Sobald Clients existieren, wandert es
> auf das Gerät; serverseitig bleibt höchstens ein kurzlebiger Cache für Web-Clients ohne lokalen
> Store. Die Festlegung ist heute kostenlos und macht den 100.000-Nutzer-Fall zum Nichtereignis.

**Und das Flaggschiff-Feature skaliert gratis:** die Ähnlichkeitskanten und ihre Zähler sind **durch
das Lexikon begrenzt, nicht durch die Nutzerzahl**. Beide Tabellen sind bei 100 Nutzern genauso
groß wie bei 100.000.

### 4.2 Statistiken ohne Materialized View

*"Wie viele Wörter kann ich in Sprache X"* ist ein Index-Only-Scan über ~5.000 Zeilen, wenn
`language` auf die Statuszeile denormalisiert wird. **Kein Materialized View, keine Rollup-Tabelle,
kein Analytics-Store** — bis 100.000 Nutzer.

Danach eine **inkrementell per ±1 gepflegte** Rollup-Tabelle. Nicht periodisch neu berechnen:
`REFRESH MATERIALIZED VIEW` ist in PostgreSQL ein Voll-Neuaufbau (auch `CONCURRENTLY` scannt neu),
was bei 500 Mio. Zeilen ein nächtlicher Ausfall wäre.

Ein separater Analytics-Store (DuckDB, ClickHouse) wird unter diesem Design **nie nötig**, weil die
einzigen nutzerübergreifenden Daten bereits voraggregierte Zähler sind.

### 4.3 Datenschutz

Das Aggregat entsteht aus dem **persönlichen Lesestoff** der Nutzer auf EU-Hosting.

**Darf nie aggregiert werden:** `texts.content`, `decoded_text`, `notes`, `explanation`,
`example_sentence`. Nutzertexte können alles enthalten — einen Arztbrief, eine private Mail, einen
Vertrag. Das heißt potenziell **Art.-9-Daten in einer Tabelle, deren Inhalt ihr nicht kontrolliert**.
Nicht verhandelbar: Rohtext betritt keine nutzerübergreifende Tabelle.

**Darf aggregiert werden:** nur **lexikalische Tatsachen**, losgelöst vom Quelltext — "N Nutzer
kennen Lexem X", "N Nutzer haben bestätigt, dass X an Y erinnert". Das sind Aussagen über ein
Wörterbuch, nicht über eine Person.

> **Die entscheidende Designregel: die Zählertabelle darf kein `user_id` enthalten.** Nach `user_id`
> geschlüsselte Zähler sind lediglich **pseudonymisiert** und damit weiterhin personenbezogene Daten
> (EDPB [Leitlinien 01/2025 zur Pseudonymisierung](https://www.edpb.europa.eu/system/files/2025-01/edpb_guidelines_202501_pseudonymisation_en.pdf))
> — mitsamt Löschpflichten nach Art. 17. Ohne `user_id` fällt das Aggregat aus dem Anwendungsbereich
> (Erwägungsgrund 26).

**k-Anonymität:** ein Zählerstand von 1 ist eine Aussage über den Wortschatz **einer identifizierbaren
Person**. Aggregate unterhalb k (üblich: 5) unterdrücken, bevor sie in UI oder API erscheinen.

**Löschpfad:** das heutige `ON DELETE CASCADE` von `users` deckt alles ab — diese Eigenschaft
erhalten. Da die Zähler kein `user_id` tragen, veralten sie beim Löschen leicht. Zwei ehrliche
Optionen: die Drift dokumentieren und periodisch neu berechnen, oder im Löschpfad dekrementieren
(dann muss der Zähler neu berechenbar bleiben). Eine wählen und in die Datenschutzerklärung
schreiben.

**Local-First ist ein Datenschutz-Argument, nicht nur Architektur:** das persönliche Universum auf
dem Gerät zu halten ist lehrbuchmäßige **Datenminimierung** (Art. 5 Abs. 1 lit. c). Nutzen.

> **Bestehende Lücke, größer als alles hier:** Nutzertexte gehen bereits an OpenAI/Anthropic
> (US-Auftragsverarbeiter). Das braucht einen AVV, Zero-Retention-Konfiguration, eine
> Datenschutzerklärung, die den Auftragsverarbeiter benennt, und eine Bewertung des
> Drittlandtransfers. Ebenso: Neon ist in eu-central-1 gehostet, Neon Inc. aber US-amerikanisch.
> **Beides besteht heute schon, wird nicht durch dieses Konzept verursacht, und ist dringlicher.**

---

## 5. Stufenplan

| Stufe | Inhalt | Umkehrbar? |
|---|---|---|
| **0** | Schema-Grundlagen (siehe §6), rein additiv | additiv — aber siehe §6 |
| **1** | `token_overrides` mit Operationen und Inhaltsankern. **Vor jeder Korrektur-UI** | nur *vor* der ersten Nutzerkorrektur |
| **2** | Ähnlichkeits-Pipeline → Kantentabelle. Read-only, neu berechenbar | vollständig |
| **3** | Rollup für Statistiken, inkrementell | vollständig |
| **4** | **HTTP-API vor die DB** (Python oder anders — schemairrelevant). *Sobald ein zweiter Client existiert, darf die DB nicht mehr die API sein.* Hier weicht auch `DBService`' Verbindung-pro-Aufruf einem Pool | vollständig |
| **5** | SQLite auf dem Gerät (Drift) + selbstgebauter Delta-Sync über die Stufe-4-API | weitgehend |
| **6** | Nur falls Stufe 5 schmerzt: PowerSync. **Hier wird Neons logische Replikation eingeschaltet — laut Neon irreversibel** | **der Schalter nicht** |

---

## 6. Was jetzt entschieden werden muss

Stackneutral, alles ohne Plattform- oder Sprachentscheidung machbar:

1. **Decode-Cache mit Schlüssel `(source_lang, target_lang, line_hash, prompt_version)`** — die
   **wertvollste einzelne Änderung**. Macht Offline-Lesen möglich, senkt LLM-Kosten, und
   `prompt_version` erlaubt gezieltes Invalidieren nach Prompt-Änderungen.
2. **Positionsanker** für Textquellen: EPUB Spine + Offset (oder CFI), PDF Seite + Bereich. Ohne die
   findet man eine Markierung nicht wieder — und man braucht sie ohnehin selbst, weil keine
   EPUB-Bibliothek sie liefert.
3. **Provenienz** auf dem Decode-Ergebnis.
4. **Sync-Metadaten, insbesondere Tombstones** (§3.6).
5. **Audio aus `BYTEA` in Objektspeicher** — der tatsächliche Speicherengpass heute.
6. **`token_overrides`** vor der Korrektur-UI (§3.4).
7. **Wiederholungshistorie append-only** (§3.2).
8. **App-eigener LLM-Schlüssel plus serverseitige Kontingentierung** statt nutzereigener API-Keys
   (siehe [`code_review_2026-08.md`](code_review_2026-08.md) E2).

**Billig aufschiebbar:** welches Sync-Produkt (Stufe 6), ob die API Python oder Clojure spricht
(Stufe 4), ob Ähnlichkeit über Trigramme oder Embeddings läuft (Stufe 2, neu berechenbar),
`pgvector`, Rollup-Tabellen, ob die geteilte Schicht physisch umzieht (§2.6), eine Graphdatenbank
(nie nötig, aber jederzeit danebenstellbar).

---

## Quellen

- [Flutter — HTML-Renderer entfernt (#145954)](https://github.com/flutter/flutter/issues/145954) ·
  [Ctrl+F (#65504](https://github.com/flutter/flutter/issues/65504),
  [#79578)](https://github.com/flutter/flutter/issues/79578) ·
  [Web-Barrierefreiheit](https://docs.flutter.dev/ui/accessibility/web-accessibility)
- [Flutter — Extension-Größe (#135243)](https://github.com/flutter/flutter/issues/135243)
- [Compose Multiplatform — SelectionContainer im Web (#4103)](https://github.com/JetBrains/compose-multiplatform/issues/4103)
- [Artifex — PyMuPDF-Lizenzierung](https://artifex.com/licensing)
- [Neon — Supported extensions](https://neon.com/docs/extensions/pg-extensions) ·
  [Logical replication](https://neon.com/docs/guides/logical-replication-postgres) ·
  [Free-Plan-Limits](https://neon.com/faqs/free-plan-limits-and-quotas)
- [Datomic ist lizenzkostenfrei](https://blog.datomic.com/2023/04/datomic-is-free.html) ·
  [Datomic Local Apache-2.0](https://blog.datomic.com/2023/08/datomic-local-is-released.html)
- [XTDB v2 (MPL-2.0, Postgres-Wire-Protokoll)](https://github.com/xtdb/xtdb) ·
  [Konfiguration](https://docs.xtdb.com/ops/config)
- [Datalevin](https://github.com/juji-io/datalevin) ·
  [Datahike Releases](https://github.com/replikativ/datahike/releases)
- [PowerSync — Flutter-SDK](https://docs.powersync.com/client-sdks/reference/flutter) ·
  [Preise](https://www.powersync.com/pricing) ·
  [Quell-DB-Setup](https://docs.powersync.com/configuration/source-db/setup)
- [ElectricSQL — Postgres Sync](https://electric-sql.com/primitives/postgres-sync)
- [Zero 1.0 (InfoQ)](https://www.infoq.com/news/2026/06/zero-version-1/) ·
  [Triplit 1.0](https://www.triplit.dev/blog/triplit-1.0)
- [Turso — Embedded Replicas (Legacy-Status)](https://docs.turso.tech/features/embedded-replicas/introduction)
- [MongoDB — Atlas Device Sync EOL 30.09.2025](https://www.mongodb.com/community/forums/t/atlas-device-sync-end-of-life-and-deprecation/296687)
- [EDPB — Leitlinien 01/2025 zur Pseudonymisierung](https://www.edpb.europa.eu/system/files/2025-01/edpb_guidelines_202501_pseudonymisation_en.pdf)

**Ausdrücklich unverifiziert:** der aktuelle Dart-Client von ElectricSQL (das pub.dev-Paket scheint
vor dem 2024-Rewrite zu liegen); die Produktionsreife Dart-nativer CRDT-Pakete; XTDB v2s fehlende
Trigramm/ANN-Unterstützung (Abwesenheit von Dokumentation, nicht dokumentierte Abwesenheit);
GPL-3.0 vs. Apple App Store (Branchenpraxis, kein Rechtsurteil); die endgültige Fassung der
EDPB-Leitlinien 01/2025; JRE-Imagegröße und Kaltstart auf Streamlit Community Cloud.

---

*Erstellt 2026-08-08 auf Branch `verbiverse-concept`.*
