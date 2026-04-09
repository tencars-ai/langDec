# Birkenbihl LLM Vergleich — PT→DE
*Benchmark: 10 Modelle, 5 Testsätze, März 2026*

---

## Legende
- ✅ Korrekt / Birkenbihl-konform
- ⚠️ Leichte Abweichung / akzeptabel
- ❌ Fehler / glättet zu stark
- 🌟 Beste Lösung im Vergleich

---

## Tabelle 1: Detailbewertung pro Satz

| Kriterium | GPT-5 mini | Claude Haiku | Gemini 3 Flash | Grok Fast | Sonnet 4.5 | Gemini 2.5 Pro | GPT-5.2 | GPT-4.1 | Opus 4.5 | GPT-4o |
|---|---|---|---|---|---|---|---|---|---|---|
| **1. saudade** | ✅ | ⚠️ | ✅ | ⚠️ | ✅ | ✅ | 🌟 original | ✅ | 🌟 Kompositum | ✅ |
| **2. com fome** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ Klammer falsch |
| **3. vamos / à noite** | ❌ "am Abend" | ✅ | ✅ | ⚠️ kein Artikel | ✅ | ⚠️ | ✅ | ❌ "werden" | ⚠️ | ❌ "werden" |
| **4. do meu vizinho** | ⚠️ geglättet | ✅ | ✅ | ⚠️ inkonsistent | ✅ | ✅ | ✅ | ❌ geglättet | ✅ | ⚠️ |
| **5. quanto mais** | ⚠️ | ⚠️ | ❌ Mischfehler | ✅ | ⚠️ | ⚠️ | 🌟 "desto" | ⚠️ "Wie mehr" | ⚠️ | 🌟 "desto" |
| **Klammer-Logik** | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ falsch verstanden |
| **Spontane Hinweise** | ❌ | ❌ | ❌ | ❌ | 🌟 | ❌ | 🌟 | ❌ | ✅ | ❌ |
| **Instruktionstreue** | ❌ Todos! | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ rechnet erst | ✅ |

---

## Tabelle 2: Gesamtranking

| Platz | Modell | Qualität | Speed | API-Kosten | Urteil |
|---|---|---|---|---|---|
| 🥇 | **Sonnet 4.5** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | mittel (~$3/$15 MTok) | Bestes Gesamtpaket, konsistentestes |
| 🥈 | **GPT-5.2** | ⭐⭐⭐⭐⭐ | ⭐⭐ | teuer | Kreativste Einzellösungen, langsam |
| 🥉 | **Claude Haiku** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | günstig (~$1/$5 MTok) | Effizienz-Champion |
| 4. | **Gemini 2.5 Pro** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | mittel | Solide, keine Ausreißer |
| 5. | **Gemini 3 Flash** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | günstig (~$0,50/$3 MTok) | Schnell, kleiner Mischfehler Satz 5 |
| 6. | **Opus 4.5** | ⭐⭐⭐⭐ | ⭐⭐⭐ | sehr teuer | Kreativ aber oversized für den Use Case |
| 7. | **GPT-4o** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | günstig | Klammer-Logik systematisch falsch |
| 8. | **GPT-4.1** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | günstig | Glättet zu stark ("werden" statt "gehen") |
| 9. | **Grok Fast** | ⭐⭐⭐ | ⭐⭐⭐⭐ | mittel | Kasusproblem ("von du") |
| 10. | **GPT-5 mini** | ⭐⭐ | ⭐⭐⭐ | günstig (~$0,25/$2 MTok) | K.O.: erstellt eigenständig Todos per API |

---

## Empfehlung für Birkenbihl-App

### Zwei-Modell-Strategie

| Anwendungsfall | Modell | Begründung |
|---|---|---|
| Standard-Übersetzungen | **Claude Haiku** | Schnell, günstig, instruktionstreue, 90% der Fälle |
| Erklärungen / Idiome | **Claude Sonnet 4.5** | Spontane Grammatikhinweise, präziseste Gesamtlösung |

**UI-Idee:** "Erklären"-Button pro Satz triggert Sonnet nur on-demand → Sonnet-Kosten nur wenn User aktiv will.

---

## Testsätze (PT→DE)

```
1. Eu tenho saudade de você.
2. Ela está com fome agora.
3. Nós vamos chegar tarde hoje à noite.
4. O menino que eu vi ontem é o filho do meu vizinho.
5. Quanto mais eu estudo, menos eu entendo.
```

### Musterlösungen

| # | Original | Wort-f-Wort | Anmerkung |
|---|---|---|---|
| 1 | Eu tenho saudade de você. | Ich habe Sehnsucht von dir. | saudade = tiefe Sehnsucht, kein deutsches Äquivalent |
| 2 | Ela está com fome agora. | Sie ist mit Hunger jetzt. | PT sagt "mit Hunger sein" statt "Hunger haben" |
| 3 | Nós vamos chegar tarde hoje à noite. | Wir gehen ankommen spät heute zu-der Nacht. | vamos = Futur, wörtlich "gehen"; à = a+a Kontraktion |
| 4 | O menino que eu vi ontem é o filho do meu vizinho. | Der Junge den ich sah gestern ist der Sohn von-dem mein Nachbar. | do = de+o = von+dem |
| 5 | Quanto mais eu estudo, menos eu entendo. | Je mehr ich studiere, desto weniger ich verstehe. | Quanto mais... menos... = Je mehr... desto weniger... |

---

# Birkenbihl LLM Vergleich — EN→DE
*Benchmark: 10 Modelle, 5 Testsätze, März 2026*

---

## Tabelle 3: Detailbewertung EN→DE pro Satz

| Satz | GPT-5 mini | Claude Haiku | Gemini 3 Flash | Grok Fast | Sonnet 4.5 | Gemini 2.5 Pro | GPT-5.2 | GPT-4.1 | Opus 4.5 | GPT-4o |
|---|---|---|---|---|---|---|---|---|---|---|
| **1. going to** | ⚠️ "bin gehe" | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **2. has been waiting** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **3. book I borrowed** | ⚠️ "lieh" | ⚠️ "borgte" | ⚠️ "geliehen" | ⚠️ "lieh" | ⚠️ "lieh" | ⚠️ "lieh" | ⚠️ "lieh" | ⚠️ "geliehen" | ⚠️ "lieh" | ⚠️ "geliehen" |
| **4. cats and dogs** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **5. the older... the more** | ✅ | 🌟 beide Varianten | ✅ | ✅ | ✅ | ✅ | 🤔 "bekommt" | ✅ | 🤔 "bekommt" | ✅ |
| **Instruktionstreue** | ❌ Todos! | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Speed** | ❌ ~30 Sek | ✅ 7 Sek | 🌟 5 Sek | ✅ 5 Sek | ⚠️ 10 Sek | 🌟 4 Sek | ⚠️ 12 Sek | 🌟 3 Sek | ✅ 4 Sek | ✅ 4-5 Sek |

---

## Tabelle 4: Gesamtranking EN→DE

| Platz | Modell | Qualität | Speed | Besonderheit |
|---|---|---|---|---|
| 🥇 | **Claude Haiku** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Einziges Modell mit beiden Varianten bei Satz 5 |
| 🥈 | **Gemini 2.5 Pro** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Schnellstes Pro-Modell (4 Sek), fehlerfrei |
| 🥈 | **GPT-4.1** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Schnellstes Modell gesamt (3 Sek), sauber |
| 4. | **Gemini 3 Flash** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Solide, "geliehen" besser als "lieh" |
| 4. | **GPT-4o** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Rehabilitiert sich vs. PT→DE |
| 4. | **Grok Fast** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Rehabilitiert sich vs. PT→DE |
| 4. | **Sonnet 4.5** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Solide, kein Vorsprung ggü. Haiku |
| 8. | **GPT-5.2** | ⭐⭐⭐ | ⭐⭐⭐ | "bekommt" pädagogisch vertretbar, aber langsam |
| 8. | **Opus 4.5** | ⭐⭐⭐ | ⭐⭐⭐⭐ | "bekommt" wie GPT-5.2, oversized |
| 10. | **GPT-5 mini** | ⭐⭐ | ⭐ | K.O.: Todos + 30 Sek + "bin gehe" |

---

## Testsätze (EN→DE)

```
1. I am going to visit my grandmother tomorrow.
2. She has been waiting for three hours already.
3. The book I borrowed from you was really interesting.
4. It's raining cats and dogs outside.
5. The older he gets, the more stubborn he becomes.
```

### Musterlösungen

| # | Original | Wort-f-Wort | Anmerkung |
|---|---|---|---|
| 1 | I am going to visit my grandmother tomorrow. | Ich bin gehend zu besuchen meine Großmutter morgen. | "going to" = EN-Futur, wörtlich "bin gehend zu" |
| 2 | She has been waiting for three hours already. | Sie hat gewesen wartend für drei Stunden bereits. | Progressive "has been waiting" hat kein DE-Äquivalent |
| 3 | The book I borrowed from you was really interesting. | Das Buch [das] ich lieh/geliehen von dir war wirklich interessant. | EN lässt Relativpronomen weg — [das] einfügen! |
| 4 | It's raining cats and dogs outside. | Es ist regnend Katzen und Hunde draußen. (Idiom — bedeutet: es schüttet) | Wörtliche Übersetzung zeigt Absurdität von Idiomen |
| 5 | The older he gets, the more stubborn he becomes. | [Je] älter er wird/bekommt, [desto] mehr stur er wird. | "gets" = "wird" oder pädagogisch "bekommt" |

---

## Wichtigste Erkenntnis: Blinder Fleck aller Modelle

**Satz 3** — kein einziges Modell markiert das unsichtbare Relativpronomen `[das/which]`.
Empfehlung für System-Prompt:

```
Bei englischen Relativsätzen ohne explizites Relativpronomen
(z.B. "The book I borrowed") füge [das] oder [which] ein:
→ "Das Buch [das] ich lieh von dir..."
```

---

## Gesamtfazit: Beide Benchmarks kombiniert

| Modell | PT→DE | EN→DE | Gesamt | API-Empfehlung |
|---|---|---|---|---|
| **Claude Haiku** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ Produktion |
| **Sonnet 4.5** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ Erklärungen |
| **Gemini 2.5 Pro** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⚠️ Google-Stack |
| **GPT-5.2** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⚠️ teuer + langsam |
| **Gemini 3 Flash** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⚠️ Alternative |
| **GPT-4.1** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ PT→DE schwach |
| **GPT-4o** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ Klammer-Logik |
| **Grok Fast** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ PT→DE Kasus |
| **Opus 4.5** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ❌ oversized |
| **GPT-5 mini** | ⭐⭐ | ⭐⭐ | ⭐⭐ | ❌ Todos-K.O. |

### Finale Zwei-Modell-Strategie
| Anwendungsfall | Modell | Begründung |
|---|---|---|
| Standard-Übersetzungen | **Claude Haiku** | Schnell, günstig, konsistent in beiden Sprachen |
| Erklärungen / Idiome | **Claude Sonnet 4.5** | Spontane Grammatikhinweise, stärkste PT→DE Leistung |
