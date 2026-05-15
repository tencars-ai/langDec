# TODO – langDec

## Refactoring (completed 2026-03-07)

- [x] **psycopg version conflict fixed**
  - `dictcc_translation_service.py` migrated from `psycopg2` to `psycopg` v3
  - `psycopg-pool` added to requirements.txt

- [x] **`DictCcTranslationService` – lazy DB init**
  - `__post_init__` no longer raises on missing `DATABASE_URL`
  - Connection opened lazily in `_get_connection()` with graceful fallback in `translate_word()`

- [x] **`argostranslate` added to `requirements.txt`**

- [x] **dict.cc removed from default AVAILABLE_SERVICES in Decoder page**
  - Code retained, not surfaced in UI by default

---

## Implementation Phases

### Phase 1 – Foundation
- [x] `sql/schema.sql` — full DB schema
- [x] `services/db_service.py` — connection pool, base queries
- [x] `services/auth_service.py` — password hash, API key encryption
- [x] Auth gate in `app.py` (login + register)
- [ ] Run `sql/schema.sql` against Neon (neon.tech) / local PostgreSQL instance / in Prod?
- [ ] Set `DATABASE_URL` and `SECRET_KEY` in `.streamlit/secrets.toml`

### Phase 2 – LLM Integration
- [x] `services/llm_service.py` — OpenAI + Claude implementations
- [x] `pages/7_Settings.py` — API key management UI
- [x] LLM service wired into Decoder via `TranslationService` interface

### Phase 3 – Persistence
- [x] `pages/2_Texts.py` — text library with folders
- [x] Auto-save decoded words to `user_dictionary` (in `pages/1_Decoder.py`)
- [x] `domain/vocabulary.py` — deduplication + frequency

### Phase 4 – Dictionary & Vocab Trainer
- [x] `pages/3_Dictionary.py` — browse/search personal dictionary
- [x] `domain/flashcard.py` — flashcard box logic
- [x] `pages/4_Vocab_Trainer.py` — trainer UI

### Phase 5 – Audio
- [x] `services/tts_service.py` — gTTS implementation
- [x] `services/audio_storage_service.py` — BYTEA store/retrieve
- [x] `pages/5_Audio.py` — playback + MP3 save per user

### Phase 6 – LLM Generation
- [x] `pages/6_Generate.py` — dialogue/text generation UI

---

## MVP-01 Phase

### Branch MVP-01 Database
-[x] DB-Migration ausführen (Neon SQL Editor):
  ALTER TABLE texts ADD COLUMN IF NOT EXISTS notes TEXT;
  (Die anderen 3 Spalten aus Migration 003 solltest du bereits ausgeführt
  haben.)
-[ ]! Datenmodell ggf. anpassen. Pro Trabelle sprechende ID. email als unique identifier und mandatory.
-[ ] Data Modeler Agent das Modell prüfen lassen schauen lassen


## Branch MVP-01 Bugs 
### Texfelder
-[x] wenn möglich: Spellcorrection ausschalen oder entsprechen der sprache durchfüreh (rote kringellinien), wahrscheinlich ist das die vom Brownser, kann man gar nicht in der app auschalten, oder? Oder kann man dem browser übermitteln welche sprache es haben soll.
--> workaround erstmal im browsesr richte spell correction wählen

### Bugs Prio 1

-[ ] ! abfangen wenn der input Text leer ist  und auf "Decode & Translate" geklickt wird nicht sagen es sei komplett, sondern meldung: Please insert text
-[ ] wenn ich mich gerade ausgeloggt habe, hat die aktuelle seite keinen login button
-[ ] login mit einer eindeutigen emailadressse als user


## Branch Folder & Menu MVP-01
### Folder
-[ ] !! keine Rückmeldung wenn Folder angelegt wurde, und sieht man irgendwo die folder?
-[x] Save in Folder im Decode & Translate direct
-[ ] "Save to text library" nicht zuklappbar sondern immer offen wie die anderen abschnitte

### Menu
-[x] die zwei separaten Menüpunkte Decode, Translate auskommentieren, und zunächst nur die Combinierte Variante machen.
-[x] vocabel dictonary feature erstmal auskommentieren, im menu "Dictonary" und auch im decode&translate. reaktivieren und verfeinern wir später
-[x] genauso wie vokab Trainer auch, auskommenieren und später weiterentwickeln.
-[x] audio auch, aber das feature ist be Decode& Translate schon eingebaut. Dort sollte man aber das audio auch absoielen können.
-[x] der Start Menu Punkt soll "Decode Text" heißen
-[x] der Menüpunkt Texts soll "Text Library" heißen. hier sollten alle texte angezeigt werden können, originalcode. decodiert, translated, notes und auch das audio abspielbar
- [x] generate erstzmal auskommenieren.
- [x] settings und help bleiben-
 

 ## deployment auf prod:
 Damit das morgen glatt läuft, hier eine Pre-Deployment-Checklist — ich gehe das gerne mit dir vorher durch, jetzt nur als Vorschau,
  was wir prüfen sollten:

  1. Code & Git

  - Auf welchem Branch sind wir gerade? (mvp-01 laut Git-Status zu Beginn) — soll der direkt auf main gemergt werden oder via PR?
  - Viele geänderte Files aus dem Refactor — wir sollten die in sinnvolle Commits gruppieren statt einen Riesen-Commit zu machen (z. B.
   "Refactor decoder to plain-text format", "Add prompt config system", "Add debug mode", "Fix logout").
  - .streamlit/secrets.toml ist in .gitignore ✅ (aus MEMORY.md schon bekannt)
  - Temp-Dateien im Repo (utils/*.tmp.*) — die sollten weg.

  2. Datenbank

  - Migration sql/005_pk_rename_and_consistency.sql auf der Prod-DB ausführen — das hatten wir frühere in dieser Session schon mal
  bemerkt (User hatte den column "id" Fehler). Wenn Prod schon migriert ist, OK; wenn nicht, vorher migrieren.
  - Prod-Connection-String für Neon (separater von dev?).

  3. Streamlit Cloud

  - App-Setup auf share.streamlit.io oder cloud.streamlit.io
  - Secrets in der Cloud-UI eintragen (nicht im Repo):
    - DATABASE_URL = Prod-Neon-String
    - SECRET_KEY = ≥32-Zeichen-Fernet-Key (muss derselbe sein wie zuvor, sonst können bestehende verschlüsselte API-Keys nicht mehr
  decryptet werden!)
  - Python-Version in requirements.txt ggf. ergänzen (Streamlit Cloud nimmt sonst Default).
  - requirements.txt ist aktuell — PyYAML ist drin ✅.

  4. Lokaler Smoke-Test vor Commit

  - App lokal starten → Login → Decode mit pt-Sätzen → check Output (das, was wir gerade fertig haben)
  - Logout testen (sollte mit dem st.rerun()-Fix laufen)
  - Settings testen (Debug-Toggle, API-Key-Save)

  Vorschlag für die Reihenfolge morgen

  1. Vorher (jetzt/abends): App lokal nochmal komplett durchklicken.
  2. Morgen:
    - Commits gruppieren (ich kann dir die Diffs auflisten und vorschlagen, welche Files in welchen Commit).
    - Migrations-Schritt auf Prod-DB explizit ausführen (oder verifizieren, dass schon gemacht).
    - Streamlit Cloud Secrets setzen.
    - Push auf main (oder PR-merge je nach Branch-Strategie).
    - App-Deployment auf Cloud, dann End-to-End-Test in der Cloud.

  Soll ich dir morgen früh helfen, die Commits sinnvoll zu gruppieren? Dann gibst du mir nur das "Go", und ich liste dir die Files pro
  Commit auf, du verifizierst, und dann committen wir nacheinander.

## Branch: Decoding Bugs
-[ ] Großschreibung von "Und" und "In" mittem im Satz, "No" wird häufig als "Knoten" übersetzt, dabei ist es eine präposition 
-[ ] sollte schon erledigt sein. Aber bitte vom Architekten Agent nochmal überprüfen lassen. Decoding ist noch recht langsam: decoder algorithmus ggf. anpassen, dass zunächst der Ganze Text im Konext übersetzt wird und dann die einzelnen wörter 1:1 übersetzt zugeordnet werden. 


## neue bugs
- [ ] ich würde gern die linebreaks vom input auch in der tranlation Behalten
- [x] die leiste mit der audiowiedergabe sollte direkT UNter das decoding (word-by-word). und ohne die Überschrift Audio.
- [ ] die Überschrift "Decoding (word-by-word)" sollte "Decoded Text (word-by-word)" sein.
- [ ] à wir Die übersetzt, erstens glaub ich das es falsch ist und es müsste im Satz ja klein geschrieben werden "die" für "a" aber "à" "a+a" heißt ja "in die" oder sowas
- [ ] bug bei Text library. hab ein folder angelegt aber es erscheint nicht
- [ ] "Add test manually" brauchen wir nicht, bitte diese box ausbauen

- [ ] audio lässt sich nicht als brauchbare datei runterladen

- [ ] erneute Decode Generierung zeigt dann den Text nicht mehr an
- [ ] Sonderzeichen ç werden nicht immer vom originaltext zum decoded text übernommen
- [ ] vor dem login ist das ganze Menü zu sehen, welches es dann später gar nicht mehr gibt. Ist das doppelt definiert. kann dort nicht einfach das gleiche oder gar kein menu angezeigt werden?
- [ ] die preferences gehen verloren
- [ ] braucht es den word für word fallback im decoder, ich will den eigentlich loswerden



## MVP-02 Phase
- [ ] gibt es eine bessere Darstellungsversion für die Folder in der Text-Library? Bitte erst Vorschlag vor Änderung
- [ ] wir bräuchten beim vorlesen eine Markierung im Text wo wir uns gerade befinden. Mindestens die Zeile besser die Worter einfach fett hervorheben. geht das irgendwie?

if promt improvement did not work we can do that:
For improving decoding quality (capitalization, 'No'→'Knoten' bug): should we start with prompt-only improvements, or also  
implement the two-pass architecture (translate full text first, then use that context for word-by-word mapping)?  
## Prompt + two-pass architecture
-[ ]     Also add a pre-pass that translates the full text contextually, then feeds that as disambiguation context to the 
     word-by-word step. More complex but potentially better quality.

### Dictionary und Vokabeltrainer
-[ ] dictionary füllt sich automatisch mit dem was man je übersetzt hat. konzept wie es sich füllt, welche infos stehen denn dann drin?
-[ ] vokabeltrainer übernimmt man wöter die man lernen will, oder es werden einem wörter aus dem häufig verwendeten übersetzungen vorgeschlagen. so bekommt man auch immer mehr beispielsätze / kontext in dem man das wort schon verwendet hat. sind das dann nur markierungen der wörter im dictonary? werden die texte dann mit den wörtern verknüpft um beispieltexte zu haben, oder wie machen wir das? Speichern wir sätze einzelnt und verknüpfen diese mit den Wötern? konzept bzw. ausprobieren.

## Remaining / Future

## Design
- [ ] Designvorgaben zentral und z.B. alle Buttons blau
- [ ] als MD und als Text anzeigen
- [ ] verspiele Icons oder schlichtes Design, beides testen oder umschaltbar
 

## übergreifende Features
- [ ] Immer als Text speichern und als MD anzeigen, bzw. Modus switchen können
- [ ] immer den Ordner beim Speichern wählen könnnen


## User Story Map / Requirements
-[ ] !! erklärungen, naming, vision, help editieren und birkenbihl nicht zu prominent platzieren. all in one, from zero to hero, build your own Wortschatz.
- [ ] Was will der Nutzer eingentlich mindestens
- [ ] translator und decoder in 2 verschiedene menüpunkte unterteilen, ggf. braucht es doch nur den einen kompinieten modus
- [ ] beim output des translators bitte auch markdown nutzen. beim generate text auch immer den prompt mitspeicher. und auch immer den urspünglichen text speichern. Wahrscheinlich sollte jeder Text mehrere spalten in der datenbank baben. urspung, decode, translate, ...


## UX
-[ ] man braucht ne schaltfläche für die sonderzeichen


## Config
- [ ] Modelle für einzelne Module konfigurierbar machen

### Near-term
- [ ] CSV import/export for vocabulary
- [ ] Clickable word-by-word output (single-word lookup)
- [ ] Playlist management UI (tables in DB are ready)
- [ ] Streamlit Cloud deployment with Neon (neon.tech) secrets configured

### Vocabulary card extensions (planned)
- [ ] Link similar words (similar meaning, similar sounding)
- [ ] Link antonyms and synonyms
- [ ] Verb conjugation tables: store and practice tenses per verb card
- [ ] DB: `vocab_relations` table (word_id, related_word_id, relation_type)
- [ ] DB: `verb_conjugations` table (dictionary_entry_id, tense, person, form)
- [ ] UI: conjugation view in Dictionary and Vocab Trainer

### Long-term
- [ ] Variant 2: FastAPI + Reflex/React
- [ ] Multi-Language Support of GUI, alle Sprachen für die Bedieung und Doku anbieten, die wir auch in der APP anbieten. Prototype aber nur auf Englsisch
- [ ] Spell-Correction für alle unterstützten Sprachen anbieten (auch damit das Audio richtig wird)
- [ ] email-bestätigung
