# Database Migrations

## Baseline (2026-05-15)

Prod-DB (Neon) wurde am 2026-05-15 komplett gewiped und aus `schema.sql` neu erzeugt.
**Ab diesem Datum gilt:**

- `schema.sql` ist die kanonische Definition des Schemas (Endzustand nach allen bisherigen Migrationen).
- Migrationen `002_*.sql` – `006_*.sql` sind **historisch** und wurden in die Baseline gefaltet. Sie sind **nicht mehr auszuführen**, weder auf Prod noch auf neuen Dev-DBs. Files bleiben im Repo als Audit-Trail.
- `001_init.sql` wurde gelöscht (war eine Supabase-Test-Tabelle, hatte nie zum echten Schema gehört).

## Prod hat ab jetzt echte Daten

Seit dem MVP-01 Release liegen Tester-Daten in Prod. Konsequenz:

- **Niemals `schema.sql` auf Prod erneut ausführen** — die `CREATE TABLE IF NOT EXISTS`-Statements lassen bestehende Tabellen unangetastet, würden aber neue Tabellen anlegen falls jemand das Schema in einer ungesteuerten Weise ändert. Vor allem: ein "alles platt machen und neu" ist nicht mehr erlaubt, da Daten verloren gingen.
- **Schema-Änderungen ab jetzt nur als Delta-Migrationen.** Pro Änderung ein neues File `00N_<beschreibung>.sql`, das die nötigen `ALTER TABLE` / `CREATE …` / Backfill-Statements als eine Transaktion enthält.

## Workflow für neue Schema-Änderungen

1. **Migration-File anlegen**
   - Nächste freie Nummer (aktuell `007_*` wenn was Neues kommt)
   - Komplette `BEGIN; … COMMIT;`-Transaktion
   - Idempotent wo möglich (`IF NOT EXISTS`, `IF EXISTS`)
   - Falls Daten-Backfill nötig: separat im File, klar kommentiert
2. **`schema.sql` synchron updaten** — Endzustand muss exakt dem entsprechen, was rauskommt wenn man alle Migrationen vom Anfang an fährt. Das ist nur noch für Dokumentations- und Fresh-Install-Zwecke relevant, aber muss stimmig bleiben.
3. **Lokal testen**: Migration gegen Dev-DB fahren, App smoke-testen.
4. **Prod-Migration**: nach Code-Push einmal die Migration im Neon SQL-Editor laufen lassen.
5. **Commit-Message**: `DB migration 0NN: <was und warum>`.

## Fresh dev-DB aufsetzen

Für eine neue Dev-Umgebung von Null:

```sql
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO CURRENT_USER;
GRANT USAGE ON SCHEMA public TO PUBLIC;
```

Danach `schema.sql` einmal komplett. Fertig — keine alten Migrationen mehr fahren.

## Migration-Historie (Referenz)

| File | Stand | Inhalt |
|---|---|---|
| ~~`001_init.sql`~~ | gelöscht | nur eine `hello`-Tabelle aus der Supabase-Anfangsphase |
| `002_vocab_decoded_explanation.sql` | superseded by baseline | `user_dictionary`: `word_target_decoded`, `explanation` |
| `003_decoded_translated_columns.sql` | superseded by baseline | `texts`: `target_language`, `decoded_text`, `translated_text` |
| `004_texts_notes.sql` | superseded by baseline | `texts`: `notes` |
| `005_pk_rename_and_consistency.sql` | superseded by baseline | PK-Renames, Spalten-Renames in `user_dictionary`, TIMESTAMPTZ, `updated_at`+Triggers, CHECK, Indexes |
| `006_user_preferences.sql` | superseded by baseline | `user_preferences`-Tabelle + Trigger |
