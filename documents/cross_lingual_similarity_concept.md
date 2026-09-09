# Cross-linguale Ähnlichkeit — Fachkonzept

**Produkt:** langDec · **Stand:** 2026-08-08 · **Branch:** `verbiverse-concept`
**Status:** Konzept zum Review. Der Teil mit Forschungscharakter — am wenigsten dringend.

Dieses Dokument beschreibt vier zusammenhängende Funktionen:

1. *"Was heißt dieses Wort in anderen Sprachen?"*
2. Ähnlichkeit nach **Schreibweise**
3. Ähnlichkeit nach **Aussprache**
4. **False Friends und True Friends** — und darauf aufbauend das **Flaggschiff-Feature**:
   *"welche Wörter der neuen Sprache kannst du eigentlich schon?"*

Grundlage ist die Lemma/Lexem/Konzept-Schicht aus
[`vokabeluniversum_concept.md`](vokabeluniversum_concept.md) §4. Ohne sie funktioniert nichts
davon, und §4 dieses Dokuments erklärt warum.

---

## 1. Was heißt das Wort in anderen Sprachen?

Konzeptvermittelte Auffächerung — eine Abfrage, drei Index-Sprünge:

```sql
WITH src AS (
    SELECT x.concept_id
    FROM lemmas l
    JOIN lexemes x ON x.lemma_id = l.lemma_id
    WHERE l.language = 'de' AND l.norm_form = :eingabe
)
SELECT l2.language, l2.lemma_text, l2.word_class, l2.grammatical_gender,
       c.gloss_en, x2.rank, l2.ipa
FROM src
JOIN lexemes  x2 ON x2.concept_id = src.concept_id
JOIN lemmas   l2 ON l2.lemma_id   = x2.lemma_id AND l2.language <> 'de'
JOIN concepts c  ON c.concept_id  = src.concept_id
ORDER BY l2.language, x2.rank;
```

### Qualitätsrisiken bei LLM-geprägten Konzepten

| # | Risiko | Wirkung |
|---|---|---|
| 1 | **Fragmentierung** — dieselbe Bedeutung zweimal geprägt | Die Brücke liefert **stillschweigend nichts**. Ein *False Negative, das niemand meldet* — **Risiko Nummer 1** |
| 2 | **Kollision** — `Bank`(Geld) und `Bank`(Möbel) in einem Konzept | Zerstört die False-Friend-Logik. **Schlimmer als Fragmentierung**, weil das Ergebnis *selbstbewusst falsch* ist |
| 3 | **Keine Richtungssymmetrie** | Ein de→pt-Decode prägt X, ein sv→de-Decode prägt Y für dieselbe Bedeutung |
| 4 | **Ungleiche Granularität** | de `du`/`Sie` vs. en `you`; pt `ser`/`estar` vs. de `sein`. Die Liste wirkt kaputt, wenn `rank` und Register nicht angezeigt werden |
| 5 | **Identitätsinstabilität** | Da die Identität eines Konzepts *seine Lexemmenge ist*, ändern Merges die Identität — und alles Vorberechnete referenziert `concept_id` |
| 6 | **Muttersprachen-Bias** | Aus deutschen Glossen geprägte Konzepte ergeben einen deutsch geformten Bestand; portugiesische Unterscheidungen fallen flach |

**Gegen Risiko 1 und 3 hilft nur eine Maßnahme, und sie muss am ersten Tag eingebaut werden:
Retrieval-First-Prägung** (§6.2). Nachzurüsten, wenn 100.000 Konzepte existieren, ist deutlich
schwerer.

Gegen Risiko 5: `concepts.merged_into_concept_id` als Grabstein plus ein Umleitungsmechanismus. Und
**`concept_id` steht bewusst nicht auf dem Token** — ein Merge berührt dadurch einige tausend
`lexemes`-Zeilen statt Millionen Tokenzeilen.

---

## 2. Ähnlichkeit nach Schreibweise

### 2.1 Der Befund, der die Architektur festlegt

**`pg_trgm` allein verpasst genau die wertvollsten Paare.** Nachgerechnet an echten Trigrammmengen
(pg_trgm polstert jedes Wort mit zwei führenden und einem abschließenden Leerzeichen):

| Paar | Trigramm | Levenshtein (norm.) | Jaro-Winkler |
|---|---|---|---|
| de `bank` / pt `banco` | 0,375 — knapp über der Standardschwelle 0,3 | — | — |
| **de `bekommen` / en `become`** | **0,154 — unter der Schwelle, komplett verpasst** | 0,50 | ≈0,79 |
| **sv `rolig` / de `ruhig`** | **0,20 — auch verpasst** | 0,60 | ≈0,78 |

Die beiden verpassten sind unter den **wertvollsten Paaren des ganzen Produkts** — `bekommen`/
`become` ist der klassische Fehler deutscher Englischlerner.

### 2.2 Nur eine Metrik ist indexierbar

| Verfahren | Ort | **Indexierbar?** | Rolle |
|---|---|---|---|
| Trigramm `similarity()` | `pg_trgm`, in der DB | **JA** — GIN/GiST über `%`, `<%`, `<->` | **Blocker** |
| Levenshtein | `fuzzystrmatch`, multibyte-sicher | nein, aber `levenshtein_less_equal` bricht früh ab | Scorer |
| Damerau-Levenshtein | Python: `rapidfuzz` (MIT) | nein | Scorer, +ε bei Metathese |
| Jaro-Winkler | Python: `rapidfuzz` | nein | **bester Einzelranker für kurze Wörter** — präfixgewichtet, und Präfixgleichheit *ist* das Kognatensignal. **Braucht zwingend eine Längenstrafe**, sonst `Bank`/`Banane` |
| Soundex / Metaphone | `fuzzystrmatch` | — | **nicht verwenden** (§3.3) |
| Daitch-Mokotoff | `fuzzystrmatch`, gibt `text[]` | GIN auf dem Array möglich | allenfalls dritter billiger Blocker |

> **Die architektonische Konsequenz:** nur **Mengenüberlappungs-Metriken** haben eine
> invertierte Indexform — `pg_trgm` ist die eine. Jede **Editierdistanz ist von Natur aus paarweise
> und nicht indexierbar**. Deshalb steht die Pipeline fest:
> **Trigramm (oder ein gespeicherter Schlüssel) blockt, Editierdistanz scort innerhalb der Blöcke.
> Diese Reihenfolge nie umdrehen.**

### 2.3 Blocken auf der Vereinigung billiger Schlüssel

Weil ein Blocker nachweislich nicht reicht (§2.1):

- `norm_form % :andere` — GIN-Trigramm, Schwelle 0,25–0,30
- `left(norm_form, 3)` — B-Tree. **Fängt `bekommen`/`become`**
- `left(phon_class, 4)` — B-Tree. **Fängt `rolig`/`ruhig`**
- immer UND-verknüpft mit `abs(len_a − len_b) ≤ 3`

**Mitschreiben, welcher Blocker gefeuert hat** (`blockers text[]`), um die Ausbeute jedes Blockers zu
messen und nutzlose später abzuschalten.

### 2.4 Normalisierung: in Python, nicht in der Abfrage

**`unaccent` ist STABLE, nicht IMMUTABLE** — es kann ohne handgeschriebenen IMMUTABLE-Wrapper
**nicht in einen Index**
([PG-Diskussion](https://www.postgresql.org/message-id/CABRT9RAxL5nL-34WeigFiGHWi+P-kpgbGO=iK70o6us1Jr4rfw@mail.gmail.com)).
Es ist zudem sprachblind. Also: **die Faltung beim Schreiben in Python erledigen und als Spalte
ablegen.**

| Sprache | Faltung |
|---|---|
| de | `ß→ss`, `ä→a`, `ö→o`, `ü→u` — plus eine **Variantenzeile** für die `ae/oe/ue`-Schreibung, die eine echte deutsche Alternative ist |
| sv | `å→a`, `ä→a`, `ö→o` |
| pt | `ç→c`, `ã→a`, `õ→o`, `á à â→a`, `é ê→e`, `í→i`, `ó ô→o`, `ú→u` |
| en | keine |

> **Eine bewusste Ungenauigkeit, die man kennen muss:** schwedisch `å` ist /oː/. `å→a` zu falten ist
> **richtig für die Schreibweise und falsch für die Aussprache**. Genau deshalb müssen Schreibweise
> und Aussprache **zwei unabhängige Kanäle mit getrennten Schlüsseln** sein und niemals zu einer
> einzigen "Ähnlichkeit" verschmelzen.

---

## 3. Ähnlichkeit nach Aussprache

### 3.1 IPA-Erzeugung — die Lizenzlage entscheidet die Werkzeugwahl

| Werkzeug | Lizenz | de | en | pt | sv | Bewertung |
|---|---|---|---|---|---|---|
| **epitran** | **MIT** | ✓ | ✓* | ✓ | ✓ | **Das einzige permissiv lizenzierte Werkzeug für alle vier Sprachen.** Regeltabellen-basiert: gut für pt/sv (transparente Orthographie), schwächer für Deutsch (Auslautverhärtung, `-ig`→[ɪç], `st/sp`, Kompositagrenzen). *Englisch braucht das CMU-`flite`-Binary |
| **espeak-ng** (via `phonemizer`) | **GPL-3.0-or-later** | sehr gut | gut | gut | gut | Beste Genauigkeit pro Byte — **aber die GPL ist der Blocker für eine kommerzielle App** (§3.2) |
| **g2p-en** | Apache-2.0 | – | gut | – | – | Schließt die Englischlücke ohne GPL. ARPAbet → IPA-Abbildung nötig |
| **WikiPron** | Werkzeug Apache-2.0, **Daten CC BY-SA** | ✓ | ✓ | ✓ | ✓ | 1,7 Mio. Aussprachen. **Share-alike steckt die Lemma-Tabelle an**, wenn sie ausgeliefert wird. Serverseitig nutzbar, im Offline-App-Paket nicht |
| **ipa-dict** | **gemischt**: de CC BY-SA, sv CC BY-SA 2.5, en_US MIT, en_UK GPL-3.0 | ✓ | ✓ | **✗ kein Portugiesisch** | ✓ | Vier Lizenzen in einem Repo **und keine Portugiesisch-Daten** — disqualifiziert als einzige Quelle |

**Empfohlener Stack, durchgehend permissiv:**
**epitran (MIT)** für de/pt/sv → **g2p-en (Apache-2.0)** für Englisch → **LLM-Batch für den harten
Rest** (Komposita, Lehnwörter, Eigennamen), gespeichert mit niedriger Konfidenz.

Ein LLM-Batch "gib IPA für diese 200 Lemmata" kostet Cent und deckt genau die Fälle ab, an denen die
Regelmaschinen scheitern.

### 3.2 Die espeak-ng-Lizenzfrage, präzise

Zwei getrennte Fragen:

- **Einbinden/Ausliefern:** `libespeak-ng` per ctypes aufzurufen und in einer verteilten App
  mitzuliefern stellt die App nach FSF-Lesart unter GPL-3.0. Kommerziell fast sicher inakzeptabel.
- **Offline laufen lassen und nur die Ausgabe ausliefern:** Programmausgabe ist im Allgemeinen kein
  abgeleitetes Werk — **außer** das Programm kopiert Teile seiner selbst in die Ausgabe (der
  Bison-Parser-Fall in der [GPL-FAQ](http://gnu.ist.utl.pt/copyleft/gpl-faq.html)). eSpeak-ng
  erzeugt IPA aus **GPL-lizenzierten Regel- und Lexikondateien**, eine Massenextraktion für 200.000
  Lemmata ist also womöglich eine Extraktion dieser Daten. **Echte Grauzone — Anwaltsfrage, keine
  Ingenieursfrage.**

**Designseitige Absicherung:** die IPA-Quelle hinter **eine Schnittstelle** legen und pro Zeile
`ipa_src` mitschreiben. Die IPA-Spalte ist dann **vollständig aus einer anderen Engine
regenerierbar**, ohne dass irgendetwas Nachgelagertes angefasst werden muss. epitran/g2p-en/LLM
ausliefern; espeak-ng und WikiPron als **Bewertungsbaseline** behalten, gegen die man misst, aber
nie verteilen.

### 3.3 Warum Soundex, Metaphone und Kölner Phonetik scheitern

Nicht als Behauptung, sondern mit Mechanismus — denn der bestimmt, was kaputtgeht:

**Soundex** (1918, US-Volkszählung, Namen) behält den **ersten Buchstaben wörtlich**, bildet die
übrigen Konsonanten auf sechs Zifferngruppen ab, die aus **englischen** Konsonantenverwechslungen
abgeleitet sind, wirft Vokale weg und kürzt auf vier Zeichen. Folgen:

- Die **4-Zeichen-Kappung vernichtet jedes deutsche Kompositum** — alle langen Wörter kollabieren
  auf denselben Code.
- Den Anfangsbuchstaben wörtlich zu behalten heißt: deutsch `Vater` [ˈfaːtɐ] und `Fahrer` [ˈfaːʁɐ]
  bekommen **verschiedene Codes trotz identischem Anlaut**.
- Es arbeitet auf **Buchstaben, nicht Lauten**, und unterstellt damit stillschweigend englische
  Schreib-Laut-Konventionen. Portugiesisch `ç`, Nasalvokale, `lh`/`nh` und schwedisch
  `sj/skj/stj/tj/kj` (alle als [ɧ]/[ç] realisiert) kommen im Regelwerk schlicht nicht vor.

**Metaphone / Double Metaphone** erweitern das um **echte englische Schreib-Laut-Regeln** — `GH`,
`TH`, `PH`, stummes `E`, `-TION`. Anderswo sind die aktiv schädlich: Double Metaphone behandelt
deutsch `sch` und schwedisch `sj` als unverwandt, obwohl beide [ʃ]/[ɧ] sind.

**PostgreSQL dokumentiert die Grenze selbst:** soundex/metaphone/dmetaphone "funktionieren nicht gut
mit Multibyte-Kodierungen (wie UTF-8). Verwenden Sie `daitch_mokotoff` oder `levenshtein` mit solchen
Daten." ([Doku](https://www.postgresql.org/docs/current/fuzzystrmatch.html))

**Kölner Phonetik** (Postel 1969) ist das exakte deutsche Spiegelbild: unbegrenzt langer Zifferncode,
Klassen 0–8, Regeln auf deutsche Orthographie getunt (`sch`, `ch`, `-ig`, `ß`, Umlaute, die
`Meier/Mayer/Mayr/Maier`-Familie). Auf Portugiesisch behandelt sie Nasale und `ç` falsch, auf
Schwedisch `sj/tj/rs`.

> **Konsequenz für ein Vier-Sprachen-System:** jedes dieser Verfahren ist eine
> **Orthographie→Code-Abbildung, fest verdrahtet auf die Rechtschreibung einer Sprache**. Den
> Kölner Code eines deutschen Worts mit dem eines portugiesischen zu vergleichen ist bedeutungslos;
> ihre Soundex-Codes zu vergleichen ist auf andere Weise bedeutungslos.
>
> **Das einzige tragfähige Design führt über eine sprachunabhängige Lautrepräsentation — IPA — und
> rechnet dort. Es gibt keinen Shortcut, und jeder sprachspezifische Lautcode ist für
> sprachübergreifende Arbeit konstruktionsbedingt eine Sackgasse.**

*(Eine Teilausnahme: **Daitch-Mokotoff** wurde für sprachübergreifende germanisch/slawische
Namensvarianz entworfen, ist multibyte-sicher und liefert ein Array von Alternativcodes. Trotzdem
orthographiebasiert und namenorientiert — allenfalls als dritter billiger Blocker, nie als Beleg.)*

### 3.4 Distanzmaß und Blocking-Schlüssel

- **`PanPhon` (MIT)** als **primäres Distanzmaß**: bildet IPA-Segmente auf artikulatorische
  Merkmalsvektoren ab und liefert eine gewichtete Merkmals-Editierdistanz
  ([COLING 2016](https://aclanthology.org/C16-1328.pdf)). Es weiß, dass /b/~/p/ nah und /b/~/ʃ/ fern
  ist — **das kann keine Zeichenmetrik**. Und es ist bereits eine epitran-Abhängigkeit, also
  kostenlos. Einschränkungen: phonologisch (merkmalszählend), nicht perzeptuell; Vokaldistanzen
  grob; in Python langsam.
- **Reine Levenshtein-Distanz über den IPA-String ist die falsche Einheit.** IPA hat mehrere
  Codepoints pro Segment (Aspiration `ʰ`, Länge `ː`, Nasalierung `̃`, Affrikatenbogen `t͡ʃ`) —
  zeichenweise Editierdistanz zählt Diakritika als ganze Segmente. Wenn überhaupt, dann **erst mit
  PanPhons `ipa_segs()` segmentieren** und über die Segmentliste rechnen. Das ist eine brauchbare,
  schnelle 80-%-Metrik als Rückfall.
- **Dolgopolsky-Reduktion (10 Lautklassen) als Blocking-Schlüssel.** Sie ist bewusst so konstruiert,
  dass Entsprechungen *innerhalb* einer Klasse regelmäßiger sind als *zwischen* ihnen. Damit wird
  Aussprache zu einem kurzen ASCII-String, den man b-tree- oder trigrammindexieren kann — genau das,
  was Kognaten-Pipelines in der historischen Linguistik tun. LingPy liefert die Konverter.

### 3.5 Vorberechnen, nicht zur Laufzeit

**Eindeutig vorberechnen und speichern:**

1. G2P ist eine **deterministische reine Funktion** von `(lemma, sprache)` — stabile Daten.
2. **Der Blocking-Schlüssel muss gespeichert sein, um überhaupt indexierbar zu sein.**
3. **Streamlit führt das Skript bei jeder Widget-Interaktion neu aus** — laufzeitiges G2P würde bei
   jedem Klick neu berechnet.
4. epitran/PanPhon sind Python-Geschwindigkeit, Größenordnungen langsamer als ein B-Tree-Lookup.
5. Der Speicher ist vernachlässigbar: ~30 B IPA + ~12 B Lautklasse × 200.000 Lemmata ≈ **10 MB**.

Zur Laufzeit rechnen **nur** für ein gerade eingetipptes Wort, das nicht in `lemmas` steht — und
dann einfügen.

---

## 4. False Friends und True Friends

### 4.1 Formalisierung

Für ein sprachübergreifendes Lemmapaar `(a ∈ L1, b ∈ L2)` mit `C(a)` als Konzeptmenge von `a`:

- `S_form(a,b) ∈ [0,1]` — kombinierte orthographische und phonetische Ähnlichkeit
- `overlap = |C(a) ∩ C(b)|`
- `J = |C(a) ∩ C(b)| / |C(a) ∪ C(b)|` — Jaccard über die Bedeutungsmengen

| | `overlap ≥ 1`, `J ≥ 0,6` | `overlap ≥ 1`, `J` niedrig | `overlap = 0` |
|---|---|---|---|
| **`S_form` hoch** | **TRUE FRIEND** — als Geschenk zeigen | **PARTIAL FRIEND** — mit Einschränkung zeigen | **FALSE FRIEND** — warnen, nie als Geschenk |
| **`S_form` niedrig** | verstecktes Kognat / normale Übersetzung — korrekt, aber kein Formbonus | dito | unverwandt |

> **Ohne die sprachunabhängige Konzeptschicht ist diese Unterscheidung unmöglich**, weil
> Formähnlichkeit allein beide Fälle gleich aussehen lässt. `Gift`/`gift` und `Bank`/`bank` sind
> formidentisch — **nur das Konzept trennt sie**. Das ist die stärkste inhaltliche Rechtfertigung
> dafür, die Konzeptschicht überhaupt zu bauen.

### 4.2 Durchgerechnete Beispiele

**de `Gift` (n., "Gift") / en `gift` ("Geschenk")**
Nach Faltung schreibidentisch; IPA de [ɡɪft] / en [ɡɪft] praktisch gleich → `S_form ≈ 1,0`.
Konzepte {GIFT} vs. {GESCHENK, TALENT} → `overlap = 0`. **False Friend, höchster Schweregrad.**
Sie *sind* etymologisch verwandt (germanisch \*giftiz "Gabe"; das Deutsche verengte euphemistisch) —
und genau deshalb muss der Schweregrad aus `S_form × (1 − J)` kommen, also daraus **wie
wahrscheinlich der Lernende hereinfällt**, und **nicht** aus der Etymologie.

**de `bekommen` / en `become`**
Trigramm **0,154 — unter der Standardschwelle, `pg_trgm` allein verpasst es.** Levenshtein 0,50,
Jaro-Winkler ≈0,79, Dolgo-Klassen fast identisch. Konzepte {ERHALTEN} vs. {WERDEN} →
**False Friend**, und eine der wertvollsten Warnungen für deutsche Englischlerner überhaupt.
**Dieses Paar ist der konkrete Beweis, dass Präfix- und Phonetik-Blocker nicht optional sind.**

**pt `embaraçada` / en `embarrassed` — Korrektur eines verbreiteten Irrtums**
Das ist **kein** False Friend, sondern ein **True/Partial Friend**. Der klassische False Friend ist
**spanisch `embarazada`** = "schwanger" — und **Spanisch ist in langDec nicht dabei**.
Portugiesisch `embaraçada` heißt "verlegen / verwickelt"; sowohl englisch `embarrass` als auch
spanisch `embarazada` stammen von portugiesisch `embaraçar` "verwickeln, behindern" ab, wobei das
Spanische euphemistisch zu "schwanger" driftete. Im Sprachsatz von langDec: Konzeptüberlappung auf
{VERLEGEN}, portugiesisch zusätzlich {VERWICKELT} → `J ≈ 0,5` → **PARTIAL FRIEND**, gezeigt als
Gewinn mit dem Hinweis *"im Portugiesischen heißt es auch 'verheddert'"*.

> **Dieses Beispiel gehört wörtlich ins Konzept**, als stehende Erinnerung daran, dass
> **volkstümliche False-Friend-Listen Fehler enthalten** und die Klassifikation aus den eigenen
> Daten abgeleitet werden muss, nie hartcodiert.

**sv `rolig` ("lustig") / de `ruhig`**
Trigramm **0,20 — wieder verpasst**; Levenshtein 0,60; JW ≈0,78; IPA sv [ˈruːlɪɡ] / de [ˈruːɪç] →
kleine PanPhon-Distanz. **Gefunden vom Phonetik- und Präfixkanal, nicht vom Trigrammkanal** — ein
zweites unabhängiges Argument für die Blockervereinigung und dafür, Aussprache überhaupt zu haben.
Konzepte {LUSTIG} vs. {RUHIG} → False Friend. Etymologisch verwandt (schwedisch `ro` "Ruhe";
dänisch/norwegisch `rolig` heißt **noch immer** "ruhig", das Schwedische driftete).

> **Struktureller Kernpunkt: dasselbe Paar wäre ein *True* Friend, wenn die beherrschte Sprache
> Dänisch wäre.** Deshalb muss die Relation am **Paar** `(lemma_a, lemma_b)` hängen — **niemals an
> einem einzelnen Lemma.**

**de `Chef` ("Vorgesetzter") / en `chef` ("Koch")**
Nach Faltung identisch, IPA beide [ʃɛf]. Beide von französisch `chef (de cuisine)` "Kopf".
Konzeptüberlappung unter strenger Identität null — **doch die ehrliche Beschriftung ist
"verschoben", nicht "unverwandt"**: beides ist "die Person, die X leitet". Hier bricht reine
Mengenüberlappung, weil `J` eine Stufenfunktion ist, die **Nachbarschaft nicht ausdrücken kann**.

Zwei Auswege: (a) eine `concept_relation`-Kantentabelle (`narrower|broader|adjacent`), die `J`
weicher macht; oder (b) billiger und ehrlicher: eine **Embedding-Kosinus zwischen den beiden
Konzept-Glossen**, **ausschließlich** um harte von weichen Warnungen zu trennen. `Gift`/`gift`:
Kosinus niedrig → harte Warnung. `Chef`/`chef`: Kosinus hoch, Überlappung null → weiches *"Vorsicht,
die Bedeutung hat sich verschoben"* — die pädagogisch korrekte Botschaft.

### 4.3 Zufällige Doppelgänger — und warum Etymologie nicht gebraucht wird

de `Rat` "Ratschlag" / en `rat`; sv `bra` "gut" / en `bra`; de `Bad` / en `bad`.

**Aus Sicht des Lernenden verhalten sie sich exakt wie False Friends** — und das ist die tragende
Einsicht:

> **Das Produkt muss nicht unterscheiden zwischen "False Friend durch Bedeutungswandel aus
> gemeinsamem Ursprung" und "zufälliger Doppelgänger". Beides sind Fallen derselben Art und
> bekommen dieselbe Warnung.**

Damit entfällt der Bedarf an Etymologiedaten im Kern. Jede lernerseitige Entscheidung ist eine von
dreien — (i) darf ich das als fast geschenkt bezeichnen? (ii) muss ich warnen? (iii) schweigen — und
alle drei bestimmt `S_form` × Bedeutungsüberlappung. Die Beispiele in §4.2 zeigen, dass echte
Kognatie und Fallenhaftigkeit **orthogonal** sind.

Praktische Blocker, falls man es doch wollte: **CogNet** (3,1 Mio. Kognatenpaare, 338 Sprachen —
[ACL 2019](https://aclanthology.org/P19-1302.pdf)) — **die Lizenzseite war nicht abrufbar (TLS-Fehler),
kommerzielle Nutzung also unverifiziert und vorsorglich klärungsbedürftig.** Etymological WordNet ist
Wiktionary-abgeleitet → CC-BY-SA-Abstammung. Und **beide bauen auf WordNet auf** — genau der
Ressource, die für de/pt/sv wegen Dünne bereits ausgeschlossen wurde; sie erben diese Dünne.

**Billiger Ersatz:** das LLM um eine einzeilige Etymologienotiz bitten **pro Paar, das tatsächlich
angezeigt wird**, zwischenspeichern und im UI als *"Hintergrund, kann ungenau sein"* kennzeichnen.
Die Kosten sind dann durch die Anzeigemenge begrenzt, nicht durch den Bestand.

---

## 5. Das Flaggschiff-Feature

Arbeitsname: **Brücke** — von der beherrschten Sprache in die Zielsprache.

### 5.1 Was als "kannst du fast schon" zählt

Ein Ziel-Lexem `t` in Sprache `T` ist Brückenkandidat für Nutzer `u`, wenn es ein Lemma `s` in der
**beherrschten** Sprache `M` gibt mit **allen** folgenden Eigenschaften:

1. `u` hat Status **`known`** auf einem Lexem von `s` — *nicht* bloß "gesehen". Für eine
   Muttersprache den Status aus einer **Frequenzliste vorbelegen**, statt zu warten, bis der Nutzer
   5.000 Wörter markiert hat.
2. `S_form(s, t) ≥ θ_form` — nah genug, um wiedererkennbar zu sein.
3. **`∃ c : lexem(s,c) ∧ lexem(t,c)`** — sie teilen mindestens ein Konzept.
   **Das ist die eine Bedingung, die ein Geschenk von einer Falle trennt.**
4. `u` kennt `t` noch nicht — sonst ist es keine Neuigkeit.
5. Wortart passt oder ist verträglich. Formgleichheit über Wortartgrenzen hinweg ist häufiger Zufall
   als Kognatie.
6. **`J(s,t) ≥ θ_sense` ODER das geteilte Konzept ist für `t` Rang 1.**

> **Regel 6 ist die wichtigste Qualitätsregel des ganzen Features.** Sie verhindert "technisch
> ähnlich, aber nutzlos". de `Bank` / pt `banco`: das geteilte Konzept BANK_FINANZ ist für beide
> Rang 1 — *und* beide bedeuten zusätzlich SITZBANK, die Überlappung ist also fast vollständig. Eine
> großartige Brücke. Ist das geteilte Konzept dagegen Bedeutung Nummer 7 des Zielworts, "kennt" der
> Lernende eine Bedeutung, der er praktisch nie begegnen wird. **Dann schweigen.**

### 5.2 Bewertungsfunktion

```python
# ---- Formähnlichkeit: eine SPRACHTATSACHE, völlig nutzerunabhängig ----
orth = (0.50 * norm_lev(a.norm_form, b.norm_form)      # 1 - lev/max(len)
      + 0.30 * jaro_winkler(a.norm_form, b.norm_form)
      + 0.20 * trigram_sim(a.norm_form, b.norm_form))

phon = 1 - panphon_weighted_feature_edit(a.ipa, b.ipa) / max_nsegs

len_pen = 1 - min(1, abs(len(a) - len(b)) / max(len(a), len(b)))   # killt Bank/Banane

S_form = (0.45*orth + 0.40*phon + 0.15*bigram_dice) * len_pen**0.5

# ---- Bedeutungsübereinstimmung ----
S_sense = (0.60 * min(1, overlap)
         + 0.25 * jaccard(C(a), C(b))
         + 0.15 * (geteiltes_konzept_ist_rang1_fuer_beide))

# ---- Anzeigewürdigkeit: der EINZIGE Ort, an dem kollektive Daten eingehen ----
S_util  = (0.60 * korpus_frequenz_perzentil(t)
         + 0.20 * nutzer_breite(t)
         + 0.20 * niveau_passung(t))

BridgeScore = S_form**1.5 * S_sense * (0.7 + 0.3 * S_util)
```

Die **Form** der Funktion ist wichtiger als die Konstanten:

- **`orth` und `phon` fast gleich gewichtet**, weil die beiden Kanäle **disjunkte** Paare fangen —
  `rolig`/`ruhig` ist nur phonetisch, `embaraçada`/`embarrassed` nur orthographisch stark. `orth`
  bekommt eine Spur mehr, weil langDec ein Lesewerkzeug ist.
- **`len_pen` multiplikativ, wurzelgedämpft** — dämpfen statt vernichten.
- **`S_form**1.5` superlinear**, weil **Überzeugungskraft superlinear in der Ähnlichkeit** ist: ein
  Paar mit 0,95 ("schau mal — `banco`!") ist mehr wert als drei mit 0,7.
- **`S_sense` strikt multiplikativ** — stimmen die Konzepte nicht überein, ist das Produkt **null**.
  Keine Formähnlichkeit kann das kompensieren. **Das ist die strukturelle Sicherung, die verhindert,
  dass das Motivationsfeature zu einem False-Friend-Generator degeneriert.**
- **`S_util` moduliert nur 0,7×–1,0×** — Nützlichkeit **rerankt**, sie filtert nie. Eine wirklich
  gute Brücke für ein seltenes Wort erscheint trotzdem. **Genau das hält das Feature bei einem
  einzigen Nutzer voll funktionsfähig.**
- **Fehlt IPA oder ist die Konfidenz niedrig:** `phon` fallen lassen, restliche Gewichte
  renormalisieren, **`S_form` auf 0,85 deckeln**, damit so ein Paar nie Rang 1 belegt.

### 5.3 Ranking, damit die Liste überzeugt statt nur zu stimmen

Billige Nachbearbeitung mit überproportionaler Wirkung:

1. **Harte Untergrenzen.** Acht gute Zeilen schlagen vierzig gemischte.
2. **Höchstens eine Brücke pro bekanntem Quelllemma** — nicht `Bank` → `banco`, `banca`, `bancário`,
   `bancada`.
3. **Nach Anfangsbuchstabe und Sachfeld streuen.** Sechs Zeilen hintereinander mit `k` liest sich wie
   ein Bug.
4. **Mit dem Fast-Identischen beginnen** (`S_form ≥ 0,9`): de `Hotel`/pt `hotel`, de `Musik`/pt
   `música`, de `Problem`/sv `problem`. **Die erste Zeile bestimmt das Vertrauen in das ganze
   Feature.**
5. **Triviale Internationalismen abwerten.** `Hotel`, `Taxi`, `Internet` sind *technisch* perfekte
   Brücken, aber sie zu lesen ist **beleidigend statt motivierend**. Erkennbar als "in ≥3 von 4
   Sprachen identisch". **Nicht löschen** — sie sind großartig für einen einmaligen
   Onboarding-Schirm ("10 Wörter geschenkt") und schlecht in der Tagesliste.
6. **Auf 10–20 begrenzen** und eine Behauptung formulieren, die man halten kann: *"20 portugiesische
   Wörter, die du wahrscheinlich schon lesen kannst"*.
7. **Den Beleg mitanzeigen** — das deutsche Wort, das portugiesische, die geteilte Bedeutung, beide
   IPA. Wer *sieht warum*, verzeiht einen Fehltreffer; eine bloße Behauptung übersteht keinen
   einzigen.

### 5.4 Vorberechnung, Blocking, Mengen

```sql
CREATE TABLE IF NOT EXISTS lemma_similarity (
    lemma_a_id        UUID NOT NULL REFERENCES lemmas(lemma_id) ON DELETE CASCADE,
    lemma_b_id        UUID NOT NULL REFERENCES lemmas(lemma_id) ON DELETE CASCADE,
    lang_a            VARCHAR(10) NOT NULL,
    lang_b            VARCHAR(10) NOT NULL,      -- immer lang_a <> lang_b
    orth_score        REAL NOT NULL,
    phon_score        REAL,                      -- NULL wenn IPA fehlt/unsicher
    form_score        REAL NOT NULL,             -- S_form
    sense_overlap     SMALLINT NOT NULL,
    sense_jaccard     REAL NOT NULL,
    relation          TEXT NOT NULL,             -- true_friend|partial|false_friend|form_only
    blockers          TEXT[] NOT NULL,           -- welcher Blocker fand es: Tuning/Audit
    etymology_note    TEXT,                      -- lazy gefüllt, nur Anzeige
    form_computed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sense_computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    algo_version      SMALLINT NOT NULL,
    PRIMARY KEY (lemma_a_id, lemma_b_id)         -- kanonisch mit a_id < b_id
);
CREATE INDEX ON lemma_similarity (lemma_a_id, form_score DESC) WHERE form_score >= 0.6;
CREATE INDEX ON lemma_similarity (lemma_b_id, form_score DESC) WHERE form_score >= 0.6;
CREATE INDEX ON lemma_similarity (relation) WHERE relation = 'false_friend';
```

**Zwei getrennte `*_computed_at` sind Absicht:** Formwerte sind teuer und ändern sich nie;
Bedeutungswerte sind billig und ändern sich bei jedem neuen Lexem und jedem Konzept-Merge.
Unabhängig auffrischbar halten.

**Mengenrechnung** bei N = 50.000 Lemmata je Sprache, 4 Sprachen, 6 ungeordnete Paare:

| Stufe | Zeilen | Anmerkung |
|---|---|---|
| Naiv, ein Sprachpaar | **2,5 × 10⁹** | ≈4 CPU-Stunden bei 1 µs/Paar |
| Naiv, alle sechs Paare | **1,5 × 10¹⁰** | undurchführbar, und bei jedem Insert erneut |
| **Geblockt, ein Paar** | 50.000 × ~30 ≈ **1,5 × 10⁶** | Trigramm ∪ Präfix-3 ∪ Dolgo-4, ∧ Längenfilter |
| **Geblockt, alle sechs** | **~9 × 10⁶** | Minuten Arbeit, ein Offline-Lauf |
| Über Schwelle `form_score ≥ 0,6` | ~5–8 % → **~600.000 Zeilen** | **~50 MB** plus Indizes |
| `true_friend` + `partial` | **~70.000** | der eigentliche Brückenbestand |
| `false_friend` | **~20.000–40.000** | der Warnbestand |

**Reduktionsfaktor ~1.700×**, und die Abfrage pro Nutzer wird ein B-Tree-Join.

> **Die operative Falle, die darüber entscheidet, ob das in der Praxis funktioniert:** über
> `lemma_a_id`-Bereiche von **~2.000** batchen. Bei einem Bulk-Join wählt der Planner sonst
> fröhlich Hash-/Seq-Scan und **ignoriert den GIN-Index komplett** — das Ganze degradiert
> stillschweigend zu quadratisch. **Mit `EXPLAIN` prüfen, nicht vertrauen.**
> Und `%` liest `pg_trgm.similarity_threshold` aus der Session-GUC — die also explizit setzen.

**Scoring in Python** (rapidfuzz + PanPhon), Rückschreiben in Batches. Offline-Job, nie im
Anfragepfad. Idempotent und über `algo_version` versioniert, damit Neubewertung nie ein Neublocken
erfordert.

**Inkrementelle Pflege:** ein neues Lemma wird eingereiht, ein Hintergrundjob blockt **dieses eine**
Lemma gegen die anderen drei Sprachen (3 × ~30 ≈ 90 Kandidatenpaare) und fügt ein. **O(1) pro neuem
Wort.** Ein Konzept-Merge berührt nur die Bedeutungsspalten — die teuren Formspalten bleiben
unangetastet.

**Die Abfrage pro Nutzer** ist ein einziger Join; entscheidend ist diese Zeile:

```sql
JOIN lexemes tlx ON tlx.lemma_id = tl.lemma_id
                AND tlx.concept_id = slx.concept_id    -- Bedingung (3), in SQL
```

**Damit kann kein Kandidat ohne geteiltes Konzept den Nutzer physisch erreichen.** Die Regel steht
in der Datenbank, nicht im Anwendungscode.

Optional in einen Cache pro Nutzer materialisieren (Streamlit rechnet bei jeder Interaktion neu) —
**aber bei jedem Schreibvorgang auf den Lernstatus invalidieren**. Ein Cache, der eine
Statusänderung überlebt, behauptet dem Nutzer, er kenne ein Wort nicht, das er gerade als bekannt
markiert hat.

### 5.5 Was wirklich kollektive Daten braucht — die ehrliche Abrechnung

Das ist der am leichtesten falsch dimensionierte Teil des ganzen Konzepts.

**Funktioniert ab Nutzer 1, ganz ohne kollektive Daten:**

- `norm_form`, `ipa`, `phon_class`
- die **gesamte** `lemma_similarity`-Tabelle: Blocking, orthographische und phonetische Werte,
  `form_score`
- **die vollständige False-Friend-Erkennung**
- der Join gegen die eigene Wissensmenge des Nutzers

> Dass de `Bank` an pt `banco` erinnert, ist wahr bei einem Nutzer wie bei einer Million.
> **Die Ähnlichkeitstabelle ist ein Wörterbuch-Artefakt, kein soziales Artefakt.** Sie lässt sich
> aus öffentlichen Frequenzlisten vorbefüllen, und das Feature kann ausgeliefert werden, **bevor
> sich ein einziger Nutzer registriert hat.** Wer behauptet, dieses Feature brauche Netzwerkeffekte,
> irrt über seinen Kern.

**Wird echt besser durch das kollektive Korpus — und nur das:**

1. **Der Lemma- und Konzeptbestand selbst.** `lemma_similarity` kann nur Paare unter existierenden
   Lemmata finden, und `S_sense` ist der **multiplikative** Term — ein dünner Konzeptgraph bewertet
   gute Paare mit null und sie bleiben stumm. **Das ist der echte Netzwerkeffekt: nicht die
   Ähnlichkeit, sondern die Sinnverknüpfung.** Gegen den Kaltstart: Lemmata und Sinne aus
   Frequenzlisten plus einem LLM-Batch vorbefüllen, damit man nie *abhängig* davon ist.
2. **Welche Kandidaten anzeigewürdig sind (`S_util`).** Häufigkeit **im Material, das langDec-Nutzer
   tatsächlich lesen**, schlägt eine generische Frequenzliste, weil eure Nutzer ein bestimmtes
   Register lesen. Fällt sauber auf eine öffentliche Liste zurück.
3. **Empirische Validierung und Gewichtsanpassung.** Eine Rückmeldetabelle ("ja, erkannt" / "nein")
   erlaubt, die Gewichte zu **fitten** statt zu raten — und die **Falsch-Positiv-Rate zu messen**,
   die das Vertrauen tatsächlich steuert. Mit einem Nutzer unmöglich.
4. **Fragmentierungserkennung.** Viele Nutzer, die dieselben Wörter decodieren, legen doppelte
   Konzepte offen — eine kostenlose kollektive Konsistenzprüfung.
5. **Verhaltensbasierte False-Friend-Entdeckung.** Wenn viele deutsche Muttersprachler `become` über
   eine Brücke "gelernt" haben und es im Vokabeltrainer wiederholt falsch beantworten, ist das ein
   datengetriebenes False-Friend-Signal unabhängig vom Konzeptgraphen. Braucht wirklich Skalierung.

> **Designvorgabe: als Einzelnutzer-Feature bauen und ausliefern. Das Schema so formen, dass
> kollektive Daten später in `S_util` und die Gewichtsanpassung einhaken. Den Launch nicht an
> Skalierung binden.**

### 5.6 False-Friend-Warnungen in derselben Ansicht

Dieselbe Tabelle, `relation = 'false_friend'`, derselbe Join, umgekehrte Darstellung:

- **Zwei Bereiche auf einem Schirm:** "Geschenkt" (`true_friend`/`partial`) und "Vorsicht"
  (`false_friend`). Der zweite gefiltert auf False Friends, **deren L1-Seite dieser Nutzer
  tatsächlich kennt** — genau die Fallen, denen er persönlich ausgesetzt ist. **Das kann keine
  statische False-Friend-Liste**, und es kostet nichts extra.
- **Umgekehrte Sortierung für Warnungen:** nach `S_form × (1 − J)`, also **das Trügerischste zuerst**.
  `Gift`/`gift` steht oben.
- **Die Bereiche niemals zu einer Liste mit grünen und roten Abzeichen verschmelzen.** Ein falsch
  gelesenes Abzeichen auf dem Handy ist exakt der Fehlermodus, den man sich nicht leisten kann.

---

## 6. Embeddings als Ergänzung

### 6.1 Wofür sie **nicht** da sind

Nicht als primäre Bedeutungsrepräsentation. Die Konzepte sind **diskret, prüfbar und an Tokens
anheftbar**; Embeddings sind Fließkommazahlen und lassen sich dem Nutzer nicht als Begründung
zeigen. **Konzepte bleiben primär.**

### 6.2 Wofür schon — vier konkrete Aufgaben

1. **Retrieval-First-Prägung — der höchste Hebel.** Vor dem Prägen eines neuen Konzepts die
   vorgeschlagene Gloss einbetten, die fünf nächsten existierenden Konzepte per Vektorsuche holen
   und dem LLM als *"nimm eines davon, wenn es passt"* vorlegen. Das **verhindert** Fragmentierung
   (Risiko 1 in §1), statt sie später aufzuräumen. Ein Embedding plus eine Vektorabfrage pro neuer
   Bedeutung.
2. **Fragmentierungs-Durchlauf.** Nächste-Nachbarn über die Konzept-Glossen bei Kosinus ≥ ~0,92
   markiert Merge-Kandidaten. Batch, offline.
3. **Versteckte Synonyme ohne Formähnlichkeit** — das genaue Komplement des Flaggschiffs. sv `mjölk`
   / pt `leite` stehen nie in `lemma_similarity`; der Konzeptgraph sollte sie halten, und Embeddings
   können die Verknüpfung vorschlagen, wenn der Graph dünn ist.
4. **Schweregrad-Abstufung bei False Friends** — der `Chef`/`chef`-Fall aus §4.2.

### 6.3 Modellwahl und Betrieb

| Modell | Lizenz | Dim | Bewertung |
|---|---|---|---|
| `intfloat/multilingual-e5-small` | **MIT** | 384 | **Empfohlener Start.** Passt in den Speicher, 384 Dimensionen halten pgvector billig, Lizenz eindeutig |
| `sentence-transformers/LaBSE` | Apache-2.0 | 768 | Eigens für *Bitext-Mining* gebaut — wörtlich "ist das dieselbe Bedeutung in einer anderen Sprache". Beste Qualität, schwer |
| `multilingual-e5-base` / `-large` | MIT | 768 / 1024 | Ausbauweg |

> **Betriebsregel: das Modell nicht im Streamlit-Prozess laufen lassen.** Streamlit führt das Skript
> bei jeder Interaktion neu aus; ein 470-MB-Modell hat dort nichts zu suchen. Embedding läuft im
> **selben Offline-Batch** wie die Ähnlichkeitsvorberechnung, die Vektoren werden gespeichert, und
> die App stellt nur noch **Vektorabfragen** — die kosten nichts. Für eine brandneue Gloss zur
> Laufzeit eine gehostete Embedding-API nutzen.
>
> **Einen 50.000-Konzepte-Bestand einmal einzubetten sind Minuten CPU, und es gibt nirgends
> Inferenzkosten pro Anfrage.** Genau deshalb sind Embeddings hier bezahlbar: sie sind
> **ausschließlich Batch**.

`torch` ist über `easyocr` bereits im Baum, die schwerste Abhängigkeit ist also bezahlt. `pgvector`
ist auf Neon verifiziert verfügbar (HNSW und IVFFlat, `<->` L2, `<=>` Kosinus). Bei 50.000–200.000
Zeilen kann man den Index anfangs ehrlicherweise weglassen — ein Seq-Scan ist schnell, der
HNSW-Aufbau ist der langsame Teil.

---

## 7. Stufenplan

| Stufe | Inhalt | Neue Abhängigkeiten |
|---|---|---|
| **0 — Grundlagen** (Tage) | `pg_trgm`, `unaccent`, `fuzzystrmatch`, `vector` anlegen. `norm_form` + Faltung in Python, Backfill, GIN-Trigramm-Index + B-Tree auf `left(norm_form,3)`. Konzept-Umleitungstabellen. **§1 ist damit fertig** — reines SQL über das bestehende Modell. Und: **Retrieval-First-Prägung jetzt einbauen**, bevor der Konzeptbestand wächst | **keine** |
| **1 — Brücke nur über Schreibweise** (1–2 Wochen) | `lemma_similarity` nur mit orthographischen Werten; Blocker = Trigramm ∪ Präfix-3 ∪ Länge. Flaggschiff live mit `phon_score` NULL und der 0,85-Deckelung. **False-Friend-Bereich live.** Rückmeldung ab Tag 1 sammeln | `rapidfuzz` (MIT) |
| **2 — Aussprache** (2–4 Wochen) | `ipa`, `ipa_src`, `ipa_confidence`, `phon_class`. Backfill de/pt/sv über epitran, en über g2p-en, LLM-Batch für den Rest. Phonetik-Blocker und `phon_score`, Deckelung aufheben. **Vorher bewerten:** 200 handgeprüfte Paare je Sprachpaar, Precision@10 messen, *bevor* Schwellen geändert werden | `epitran` (MIT), `panphon` (MIT) |
| **3 — Kollektives Signal** (braucht Nutzer) | Korpusstatistik aus `tokens`, `S_util` verdrahten, Gewichte auf gesammelter Rückmeldung fitten, **gemessene** Falsch-Positiv-Rate berichten | keine |
| **4 — Embeddings** (nach der Stufe-2-Bewertung) | `multilingual-e5-small` im Batch, Glossen-Vektoren, Retrieval-First härten, Fragmentierungs-Durchlauf, Schweregrad-Abstufung | `sentence-transformers` |
| **5 — Zurückgestellt** | LLM-Etymologienotizen (gecacht, als ungefähr gekennzeichnet). CogNet nur bei geklärter Lizenz. espeak-ng/WikiPron **nur als Offline-Baseline**, nie als ausgelieferte Abhängigkeit, und nur nach rechtlicher Prüfung | — |

> **Stufe 1 allein ist grob 80 % des sichtbaren Nutzens** — ohne GPL, ohne torch, ohne
> Modellgewichte, ohne Forschungsrisiko.

---

## 8. Wo das System schweigen muss

Eine falsche *"das kennst du schon"*-Behauptung beschädigt das Vertrauen mehr als gar keine Anzeige.
Deshalb ist Schweigen **erzwungene Politik, keine Ermessensfrage**:

1. **Kein geteiltes Konzept → schweigen.** Ein reiner Formtreffer ist nie eine Brücke; er gehört in
   den False-Friend-Bereich oder nirgendwohin. **Erzwungen als SQL-Join-Prädikat** (§5.4), nicht in
   Anwendungscode.
2. **IPA fehlt oder Konfidenz < 0,5 →** Phonetik-Term fallen lassen, renormalisieren, `S_form` auf
   0,85 deckeln. Solche Paare belegen **nie Rang 1**.
3. **LLM-erzeugtes IPA darf ranken, aber nie angezeigt werden.** Falsches IPA auf dem Schirm ist ein
   eigener, hochsichtbarer Fehlermodus.
4. **Geteiltes Konzept ist für das Ziel nicht Rang 1 und `J < 0,4` → schweigen.** "Teilt technisch
   Bedeutung Nummer 6" heißt nicht, ein Wort zu kennen.
5. **`sense_computed_at < form_computed_at`, oder Konzept nach dem Scoring gemerged → Zeile als
   veraltet behandeln und ausschließen**, bis neu bewertet. **Veraltete Bedeutungsdaten sind genau
   der Weg, auf dem eine Brücke stillschweigend zu einem False Friend wird.**
6. **Wortart-Missverhältnis bei `S_form ≥ 0,9` → abwerten oder unterdrücken.**
7. **Weniger als ~5 Zeilen über der Schwelle → nichts zeigen**, mit ehrlichem Leerzustand
   (*"noch keine überzeugenden Überschneidungen — decodiere ein paar Texte mehr"*). Eine
   Zweierliste liest sich wie ein Bug, ein ehrlicher Leerzustand wie Sorgfalt.
8. **Niemals den Wortschatz quantifizieren.** *"Du kennst schon 4.312 portugiesische Wörter"* ist
   unfalsifizierbar, wird falsch sein, und **ein einziges Gegenbeispiel zerstört die
   Glaubwürdigkeit**. Stattdessen eine begrenzte, prüfbare Liste.
9. **Asymmetrische Schwellen nach Fehlerkosten.** Brücken (positive Behauptungen) brauchen hohe
   Schwellen; False-Friend-**Warnungen** dürfen lockerer laufen. Eine überflüssige Warnung kostet
   einen Moment Aufmerksamkeit, eine falsche "das kennst du" kostet Vertrauen.
10. **Jede angezeigte Zeile trägt ihren Beleg und ein "das stimmt nicht" mit einem Tipp.**

---

## 9. Zwei Risiken, die an euren Sprachen hängen

**Deutsche Komposita.** `Bankkonto` / pt `conta bancária` werden nie matchen — und schlimmer, das
Trigramm-Blocking erzeugt Rauschen zwischen kurzen und langen deutschen Formen. `lang_a <> lang_b`
erzwingen und eine **Längenverhältnis-Untergrenze**, damit ein kurzes Lemma nie zu einem viel
längeren brückt.

**Schwedische agglutinierte Definitheit — und das trifft direkt euer eigenes Material.**
`rules-swedish-german.md` notiert: *"Im Schwedischen ist der bestimmte Artikel des Nomens hinten
konkateniert: `pojken` → `Junge-der`"*. Speichert `lemmas` **flektierte Oberflächenformen** statt
echter Lemmata (bei schwedischen Substantiven: unbestimmter Singular), berechnet man Ähnlichkeit
zwischen einer flektierten schwedischen Form und einem deutschen Lemma und nennt das Rauschen ein
Ergebnis.

> **Lemmatisierungsqualität ist eine harte Obergrenze für die Brückenqualität.** Das braucht einen
> Validierungsdurchgang, **bevor Stufe 1 ausgeliefert wird.**

---

## Quellen

- [PostgreSQL — pg_trgm](https://www.postgresql.org/docs/current/pgtrgm.html) ·
  [fuzzystrmatch](https://www.postgresql.org/docs/current/fuzzystrmatch.html) ·
  [unaccent/IMMUTABLE-Diskussion](https://www.postgresql.org/message-id/CABRT9RAxL5nL-34WeigFiGHWi+P-kpgbGO=iK70o6us1Jr4rfw@mail.gmail.com)
- [Neon — pgvector](https://neon.com/docs/extensions/pgvector) ·
  [pg_trgm](https://neon.com/docs/extensions/pg_trgm) ·
  [fuzzystrmatch](https://neon.com/docs/extensions/fuzzystrmatch)
- [epitran (MIT)](https://github.com/dmort27/epitran) ·
  [Epitran, LREC 2018](https://aclanthology.org/L18-1429.pdf)
- [panphon (MIT)](https://github.com/dmort27/panphon) ·
  [PanPhon, COLING 2016](https://aclanthology.org/C16-1328.pdf)
- [espeak-ng (GPL-3.0+)](https://github.com/espeak-ng/espeak-ng) ·
  [phonemizer (GPL-3.0)](https://github.com/bootphon/phonemizer) ·
  [GNU GPL-FAQ zur Programmausgabe](http://gnu.ist.utl.pt/copyleft/gpl-faq.html)
- [WikiPron](https://github.com/CUNY-CL/wikipron) ·
  [LREC 2020](https://aclanthology.org/2020.lrec-1.521.pdf) ·
  [ipa-dict (gemischte Lizenzen, kein Portugiesisch)](https://github.com/open-dict-data/ipa-dict)
- [LingPy — Lautklassenmodelle (dolgo/asjp/sca)](https://lingpy.org/docu/data/model.html) ·
  [ASJP](https://clts.clld.org/contributions/asjp)
- [Kölner Phonetik](https://en.wikipedia.org/wiki/Cologne_phonetics) ·
  [Vergleich mit Soundex](https://www.assono.de/en/blog/koelner-phonetik-better-than-soundex)
- [RapidFuzz (MIT)](https://github.com/rapidfuzz/RapidFuzz)
- [multilingual-e5-small (MIT)](https://huggingface.co/intfloat/multilingual-e5-small) ·
  [LaBSE (Apache-2.0)](https://huggingface.co/sentence-transformers/LaBSE)
- [CogNet, ACL 2019](https://aclanthology.org/P19-1302.pdf) — **Lizenz unverifiziert (TLS-Fehler)**
- [False friend — Überblick](https://en.wikipedia.org/wiki/False_friend) ·
  [embarazada/embaraçada](https://www.babbel.com/learn-spanish/cognates/embarrassed)

**Ausdrücklich unverifiziert:** CogNets Lizenz und kommerzielle Bedingungen; die
`query:`/`passage:`-Präfixkonvention bei E5; ob die Massenextraktion von IPA aus espeak-ng
GPL-gedeckte Datenextraktion darstellt (Anwaltsfrage); **sämtliche Mengenangaben in §5.4** — sie sind
parametrisch auf 50.000 Lemmata je Sprache und angenommene Blockgrößen. **Am echten Bestand
nachmessen, bevor irgendetwas darauf dimensioniert wird.**

---

*Erstellt 2026-08-08 auf Branch `verbiverse-concept`.*
