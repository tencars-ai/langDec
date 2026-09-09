# Vokabeluniversum — Übersicht und Leseanleitung

**Produkt:** langDec · **Stand:** 2026-08-08 · **Branch:** `verbiverse-concept`

> **Dieser Branch enthält ausschließlich Dokumente.** Kein Produktionscode, keine Migration, keine
> Schemaänderung wurde ausgeführt. Alles hier ist Vorschlag zum Review.

---

## Worum es geht

Der Decoder gibt heute **vorformatierten Text** zurück — eine zweizeilige Zeichenkette, an
`max_line_length` umgebrochen. Darstellung und Speicherformat sind verschmolzen.

Die Erweiterung dreht das um: **Decodieren erzeugt strukturierte Token-Zeilen**, und der
Monospace-Text wird nur noch eine Darstellung darüber. Aus diesen Tokens wächst über alle Texte
eines Nutzers hinweg ein **Vokabeluniversum** mit einer sprachunabhängigen Konzeptschicht.

**Der eigentliche Auslöser ist aber nicht Analyse, sondern Reparatur:** das LLM verschiebt
regelmäßig um genau ein Token, und dann ist der Rest der Zeile falsch zugeordnet, obwohl jede
einzelne Übersetzung stimmt. In einer Tabelle ist das ein Spaltenversatz — ein Zwei-Klick-Fix statt
einer Neugenerierung.

---

## Lesereihenfolge

| # | Dokument | Umfang | Warum |
|---|---|---|---|
| **1** | [`vokabeluniversum_concept.md`](vokabeluniversum_concept.md) | groß | **Wenn du nur eins liest, dann dieses.** Token-Modell, Korrektur-UI, Klick-Panel, Enrichment, Konzeptschicht, Lernstatus. Enthält die schwer umkehrbaren Entscheidungen — und braucht die Plattformfrage **nicht** |
| **2** | [`code_review_2026-08.md`](code_review_2026-08.md) | kurz | Sofort handlungsfähig. Zwei echte Fehler, eine nicht überwachte Regression, toter Code |
| **3** | [`target_architecture.md`](target_architecture.md) | groß | Plattformen, zentrale DB, Sync, **Clojure/Dart-Bewertung**. Das Dokument für das Gespräch mit deinem Kollegen |
| **4** | [`cross_lingual_similarity_concept.md`](cross_lingual_similarity_concept.md) | groß | Ähnlichkeit, False Friends, das Flaggschiff-Feature. Der Teil mit Forschungscharakter — am wenigsten dringend |
| **5** | [`coding_standards.md`](coding_standards.md) | mittel | Aus dem Bestand extrahiert, nicht von außen aufgesetzt |

---

## Der entlastende Befund

**Die schwer umkehrbaren Entscheidungen sind alle Schema-Entscheidungen — und die hängen nicht an
der Technologiewahl.**

Lemma/Lexem/Konzept-Trennung, Status am Lexem statt am Token, Genus am Lemma, geteilte vs.
duplizierte Sprachschicht: das sind Aussagen über **Bedeutung und Korn**, nicht über
Laufzeitumgebungen. Weder "Clojure oder Python" noch "Flutter oder Expo" berührt sie.

> **Dokument 1 kann also entschieden und umgesetzt werden, während die Plattformfrage offen bleibt.**

Die einzige Stelle, an der sich beides berührt, ist die zentrale Datenbank — und dazu lautet die
Empfehlung: **DB-Wahl und Backend-Sprache entkoppeln.** Clojure spricht problemlos mit PostgreSQL.
Der Fehler wäre die Kopplung *"wir nehmen Clojure, also Datomic"*.

---

## Die sechs Entscheidungen, die dein Review wirklich braucht

Nach Umkehrkosten sortiert. Alles andere kann warten.

| # | Entscheidung | Warum jetzt | Wo |
|---|---|---|---|
| 1 | **Wiederholungshistorie append-only** statt veränderlicher Zähler | Historie, die nie aufgezeichnet wurde, ist **nicht rekonstruierbar**. Kostet heute eine Tabelle | [Konzept §6.2](vokabeluniversum_concept.md) |
| 2 | **Korrekturen als Operationen mit Inhaltsankern**, nicht als Änderung am Cache | Sobald Nutzer den Cache direkt korrigiert haben, ist Korrektur nicht mehr von Decode-Ausgabe unterscheidbar — **dann kann nie wieder gefahrlos neu decodiert werden** | [Konzept §5](vokabeluniversum_concept.md) |
| 3 | **Lemma / Lexem / Konzept sauber trennen** | Falsch aufgehängt, muss später jede Tokenzeile neu aufgelöst werden | [Konzept §4.1](vokabeluniversum_concept.md) |
| 4 | **Clientgenerierbare UUIDs + Tombstones** | Nachrüsten in Zeilen, die schon auf Nutzergeräten liegen, heißt die ganze Flotte anfassen. **Tombstones fehlen heute überall** | [Architektur §3.6](target_architecture.md) |
| 5 | **`tokens` nie serverautoritativ** | Heute kostenlos festzulegen. Später kauft man sich das 1-TB-Problem *und* das Nicht-mehr-decodieren-Problem ein | [Architektur §4.1](target_architecture.md) |
| 6 | **Retrieval-First bei der Konzeptprägung** | Fragmentierung ist **unsichtbar** — ein False Negative, das niemand meldet. Nachträglich mergen bei 100.000 Konzepten ist deutlich schwerer | [Ähnlichkeit §6.2](cross_lingual_similarity_concept.md) |

**Billig aufschiebbar:** welches Sync-Produkt, ob das Backend Python oder etwas anderes wird, ob
Ähnlichkeit über Trigramme oder Embeddings läuft, Rollup-Tabellen, `pgvector`.

---

## Zwei Dinge, die unabhängig vom ganzen Konzept dringend sind

**1. Es besteht heute eine Lizenz-Haftung.** **PyMuPDF ist AGPL-3.0-oder-kommerziell**, und AGPL §13
lässt Netzwerknutzung als Verbreitung zählen — laut Hersteller ausdrücklich auch als Microservice
hinter einer API. Die naheliegende Python-EPUB-Bibliothek ist ebenfalls AGPL. Betrifft dich, sobald
das Produkt kommerziell wird, **unabhängig von jeder Technologiewahl**.

**2. Nutzereigene LLM-API-Keys tragen kein Produkt im Store.** Kein Endnutzer legt sich einen
Anthropic-Account an. Nötig wäre ein app-eigener Schlüssel plus serverseitige Kontingentierung —
eine Schemaänderung, die man **vor** dem ersten Release einplant.

Dazu, schon bestehend und dringlicher als alles, was dieses Konzept an Datenschutzfragen aufwirft:
Nutzertexte gehen bereits an US-Auftragsverarbeiter (OpenAI/Anthropic). Das braucht AVV,
Zero-Retention und eine Datenschutzerklärung.

---

## Die wichtigste einzelne Maßnahme, falls du sofort etwas tun willst

**Die 246/246-Metrik reproduzierbar machen.**

`tests/test_decoder_e2e.py` enthält 5 pt→de-Sätze; `decoder-prompting-rules.md` §9 beschreibt 8. Der
Qualitätsanker des Produkts **existiert als Messung nicht**. Und der Harness prüft nichts — er
druckt Text, ein Mensch müsste zählen.

Konkret: fehlende Sätze zurück ins Korpus, eine Token-Zähl-Assertion, und ein **Offline-Modus** mit
gestubbtem Service (die Weiche dafür ist schon da, der Stub braucht ~15 Zeilen). Damit wird aus der
Regressionsprüfung ein deterministischer Byte-Vergleich.

**Ohne diese Messung ist der Decoder-Umbau nicht sicher abnehmbar.** Sie ist die Voraussetzung für
alles andere, kein Extra.

---

## Was noch offen ist

- [ ] Review dieser fünf Dokumente
- [ ] Die acht bestehenden Dokumente in `documents/` auf den Ist-Stand korrigieren — mehrere
      beschreiben Dinge, die der Code nicht mehr tut (`software-architecture.md` beschreibt einen
      JSON-Decoder, den es nicht mehr gibt; `adding_translation_services.md` verweist auf ein
      `AVAILABLE_SERVICES`, das nicht existiert)
- [ ] `CLAUDE.md` korrigieren — die dortige Projektstruktur nennt Dateien, die es nicht gibt
- [ ] Namensvereinheitlichung: im Repo konkurrieren fünf Produktnamen, es soll überall **langDec**
      heißen
- [ ] Entscheidung zu den sechs Punkten oben

**Ausdrücklich unverifiziert** und vor einer Entscheidung zu klären: CogNets Lizenz (Seite nicht
abrufbar), GPL-3.0 vs. Apple App Store (Branchenpraxis, kein Rechtsurteil), ob die Massenextraktion
von IPA aus espeak-ng GPL-gedeckte Datenextraktion ist (Anwaltsfrage), der aktuelle Dart-Client von
ElectricSQL, und **sämtliche Mengenangaben zur Ähnlichkeit** — die sind parametrisch auf 50.000
Lemmata je Sprache und müssen am echten Bestand nachgemessen werden.

---

*Erstellt 2026-08-08 auf Branch `verbiverse-concept`.*
