# Anforderungsdokument – Sprachlernsoftware (Prototyp)

## 1. Ziel des Projekts
Ziel ist die Entwicklung eines Software‑Prototyps zum effektiven Erlernen von Fremdsprachen nach dem **Dekodier‑Prinzip (angelehnt an die Birkenbiel‑Methode)**. Die Software soll Lernenden ermöglichen, Texte sowohl **sinngemäß** als auch **1:1 wörtlich (dekodiert)** zu übersetzen und diese auditiv sowie visuell zu verarbeiten.

Der Prototyp startet mit den Sprachen **Deutsch (Muttersprache)**, **Englisch** und **Portugiesisch**, soll jedoch **sprachenagnostisch** konzipiert werden, sodass später weitere Sprachen einfach ergänzt werden können.

---

## 2. Zielgruppe
- Erwachsene Selbstlerner
- Sprachinteressierte
- Nutzer der Birkenbiel‑Methode oder ähnlicher Dekodier‑Ansätze
- Autodidakten mit Fokus auf Lesen & Hören

---

## 3. Unterstützte Sprachen (Startphase)
- Deutsch (Ausgangs‑/Muttersprache)
- Englisch
- Portugiesisch

> Architektur muss so gestaltet sein, dass jede Sprache sowohl **Quell‑** als auch **Zielsprache** sein kann.

---

## 4. Kernfunktionen

### 4.1 Textverwaltung
- Texte können:
  - per **Copy & Paste** eingefügt werden
  - über einen **OCR‑Scanner** aus Bildern / PDFs eingelesen werden
- Texte werden:
  - in **Ordnern** organisiert
  - lokal gespeichert (Struktur: Ordner → Texte)
  - mit Metadaten versehen (Sprache, Titel, Datum, Notizen)

---

### 4.2 Übersetzungsmodule

#### 4.2.1 Sinngemäße Übersetzung
- Klassische, natürliche Übersetzung
- Satzweise oder absatzweise Darstellung

#### 4.2.2 Dekodier‑Übersetzung (Birkenbiel‑Prinzip)
- **1:1 Wort‑für‑Wort‑Übersetzung**
- Beibehaltung der Original‑Wortreihenfolge
- Ziel: Transparenz der fremden Sprachstruktur

**Darstellungsoptionen:**
- Originaltext
- Dekodierte Übersetzung direkt darunter oder inline
- Optionale Hervorhebung einzelner Wörter

---

### 4.3 Einzelwort‑Nachschlagen
- Wörter können:
  - im Text markiert werden
  - einzeln nachgeschlagen werden
- Anzeige von:
  - Grundbedeutung
  - ggf. Wortart
- Wörter können direkt:
  - als **Vokabelkarte** gespeichert werden

---

### 4.4 Audio‑ & Hörfunktionen (Text‑to‑Speech)
- Texte können vorgelesen werden:
  - Originalsprache
  - optional auch Übersetzung
- Steuerung:
  - Abspielgeschwindigkeit
  - Wiederholung einzelner Abschnitte

#### Playlists
- Texte können zu **Hör‑Playlists** zusammengestellt werden
- Playlists können:
  - innerhalb der App abgespielt werden
  - als **MP3‑Dateien exportiert** werden (z. B. für externe Player)

---

### 4.5 Vokabeltrainer (Karteikartenprinzip)
- Integrierter Vokabeltrainer nach dem **Karteikasten‑Prinzip**
- Jede Vokabelkarte enthält:
  - Wort (Fremdsprache)
  - Übersetzung (Muttersprache)
  - optional Beispielsatz

#### Lernlogik
- Mehrere Lernboxen (z. B. neu → gelernt)
- Wiederholungslogik (manuell oder später automatisierbar)

#### Import / Export
- **CSV‑Import** von Vokabeln
- **CSV‑Export** der eigenen Vokabelsammlung

---

## 5. Datenorganisation
- Ordnerstruktur für Texte
- Separate Speicherung von:
  - Texten
  - Audiodateien
  - Vokabeln
  - Playlists

---

## 6. Nicht‑funktionale Anforderungen
- Modularer Aufbau (Übersetzung, Audio, Vokabeln getrennt)
- Erweiterbarkeit auf weitere Sprachen
- Plattformunabhängiges Design (für spätere Desktop / Web / Mobile Umsetzungen)
- Fokus auf **Lern‑Usability**, nicht auf perfekte KI‑Übersetzung

---

## 7. Abgrenzung (Prototyp‑Phase)
Nicht Teil des ersten Prototyps:
- Benutzerkonten / Cloud‑Sync
- Gamification (Punkte, Abzeichen etc.)
- Automatische Spracherkennung

---

## 8. Vision (Langfristig)
- Vollständig sprachenagnostisches Lernsystem
- Erweiterte Analyse grammatischer Strukturen
- Kombination aus Lesen, Hören und aktiver Wortarbeit

---

**Dokumentstatus:** Prototyp‑Anforderungsdefinition

