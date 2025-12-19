# Technisches Konzept – Prototyp-Stack & Tooling

## 1. Ziel
Festlegung eines pragmatischen Technologie‑Stacks für den **ersten Prototypen** der Sprachlernsoftware (mobile-fähige Web-App) mit Fokus auf schnelle Umsetzung, Open-Source-Komponenten und späterer Erweiterbarkeit.

---

## 2. Leitprinzipien
- **Schnell lauffähiger Prototyp** (Feature-Fluss demonstrierbar)
- **Open Source** (Frameworks/Komponenten, Self-Hosting prinzipiell möglich)
- **Saubere Datenbasis** (Postgres als langfristige Persistenz)
- **Architektur so wählen**, dass später ein Wechsel auf „App-näheren“ Stack möglich ist (Variante 2)

---

## 3. Entscheidung: Variante 1 (Start)
### 3.1 Frontend/UI
- **Streamlit** als UI‑Framework für den Prototyp
- Begründung:
  - Sehr schneller Aufbau klickbarer Oberflächen in Python
  - Ideal für frühe Validierung der Kernfunktionen (OCR → Textverwaltung → Übersetzung/Decoder → Audio/Playlist → Vokabeln)

### 3.2 Datenbank
- **PostgreSQL** als primäre Datenbank
- Begründung:
  - Stabil, Open Source, gut geeignet für relationale Daten (Texte, Ordner, Vokabelkarten, Playlists, Metadaten)

### 3.3 Hosting (Prototyp)
- **Streamlit Community Cloud** für schnelle Bereitstellung der App
- **Supabase (Postgres)** als gehostete Postgres-Instanz (für schnellen Start)

> Hinweis: Später ist ein Wechsel zu eigenem Postgres (z. B. auf VPS/Managed DB) möglich.

---

## 4. AI-gestütztes Entwickeln (Tooling-Entscheidung)
### 4.1 Direkt im Code/IDE
- **GitHub Copilot + Copilot Chat** für:
  - Implementierung einzelner Module
  - Boilerplate, CRUD, Tests, Refactoring im Projektkontext

### 4.2 Übergreifend (Planung/Architektur)
- **ChatGPT** für:
  - System-/Modularchitektur und Schnittstellen
  - Datenmodellierung (Tabellen/Entities)
  - Spezifikation Decoder-Logik (Birkenbiel)
  - Review, Debugging-Strategien, technische Entscheidungen

---

## 5. Option für spätere Ausbaustufe: Variante 2
Variante 1 ist bewusst prototypisch. Für eine „echte App“ mit besserer Mobile-UX und langfristiger Struktur ist später vorgesehen:

### 5.1 Möglicher Ziel-Stack (Variante 2)
- Backend: **FastAPI (Python)**
- Datenbank: **PostgreSQL** (weiterhin)
- UI:
  - entweder Python-first: **Reflex**
  - oder separates Web-Frontend (z. B. React/Next.js) und später Mobile (React Native/Expo)

### 5.2 Migrationsidee
- Datenbank (Postgres) bleibt gleich
- Business-Logik (Decoder/Übersetzung/Vokabeltrainer) möglichst als Python‑Module kapseln
- Streamlit dient als frühe UI-Schicht; später UI austauschen, Kernlogik wiederverwenden

---

## 6. Nächste Schritte (konkret)
1) Minimales Datenmodell definieren (Tabellen/Beziehungen)
2) Modul-Schnittstellen festlegen:
   - Textverwaltung + Ordner
   - OCR Import
   - Übersetzung (sinngemäß) + Decoder
   - TTS + Playlists/Export
   - Vokabeltrainer + CSV Import/Export
3) Streamlit App-Skelett erstellen (Navigation + Grundseiten)

---

**Status:** Stack-Entscheidung für Prototyp (Variante 1) dokumentiert; Variante 2 als spätere Option festgehalten.

