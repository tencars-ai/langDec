# Anleitung: Weitere Übersetzungsdienste hinzufügen

## Überblick
Das Language Decoder Projekt wurde so konzipiert, dass neue Übersetzungsdienste einfach hinzugefügt werden können. Diese Anleitung erklärt Schritt für Schritt, wie ein neuer Service integriert wird.

## Architektur

### Translation Service Interface
Alle Übersetzungsdienste erben von der abstrakten Basisklasse `TranslationService` in `services/translation_service.py`.

Die Basisklasse definiert drei erforderliche Methoden:
- `translate_word(word, source_lang, target_lang)` - Übersetzt einzelne Wörter
- `translate_text(text, source_lang, target_lang)` - Übersetzt vollständige Texte
- `name` (Property) - Gibt den Anzeigenamen des Services zurück

## Schritt-für-Schritt Anleitung

### 1. Neue Service-Klasse erstellen

Erstellen Sie eine neue Klasse in `services/translation_service.py`:

```python
@dataclass
class MeinNeuerService(TranslationService):
    """Beschreibung des neuen Übersetzungsdienstes."""
    
    source_default: Optional[str] = None
    target_default: Optional[str] = None
    
    @property
    def name(self) -> str:
        """Return the display name of this service."""
        return "Mein Neuer Service"
    
    def translate_word(self, word: str, source_lang: str, target_lang: str) -> str:
        """Translates a single word."""
        source = self.source_default or source_lang
        target = self.target_default or target_lang
        
        # Ihre Implementierung hier
        # z.B. API-Aufruf, lokale Bibliothek, etc.
        translated = ihre_übersetzungs_funktion(word, source, target)
        return translated
    
    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translates complete text."""
        source = self.source_default or source_lang
        target = self.target_default or target_lang
        
        # Ihre Implementierung hier
        translated = ihre_übersetzungs_funktion(text, source, target)
        return translated
```

### 2. Service in app.py registrieren

Öffnen Sie `app.py` und fügen Sie den neuen Service zum `AVAILABLE_SERVICES` Dictionary hinzu:

```python
# Import hinzufügen
from services.translation_service import (
    TranslationService,
    GoogleDeepTranslatorService,
    ArgosTranslateService,
    MeinNeuerService,  # NEU
)

# Im Dictionary registrieren
AVAILABLE_SERVICES = {
    "Google Translate": GoogleDeepTranslatorService(),
    "Argos Translate": ArgosTranslateService(),
    "Mein Neuer Service": MeinNeuerService(),  # NEU
}
```

**Das war's!** Der neue Service erscheint automatisch als Option in den Radio Buttons.

## Beispiele vorhandener Services

### Google Translate (GoogleDeepTranslatorService)
- Nutzt die `deep_translator` Bibliothek
- Online-Service (benötigt Internetverbindung)
- Kostenlos, aber mit Rate Limits

### Argos Translate (ArgosTranslateService)
- Nutzt die `argostranslate` Bibliothek
- Offline-Service (nach Download der Sprachmodelle)
- Gut für Datenschutz und ohne API-Limits

## Best Practices

### Error Handling
Implementieren Sie robustes Error Handling:

```python
try:
    # Übersetzungslogik
    translated = translation_api.translate(text)
    return translated
except ImportError:
    return f"[Service not installed: {text}]"
except Exception as e:
    return f"[Translation Error: {e}]"
```

### Dependencies
Wenn Ihr Service externe Bibliotheken benötigt:
1. Fügen Sie diese zu `requirements.txt` hinzu (optional, mit Kommentar)
2. Behandeln Sie `ImportError` graceful im Code
3. Geben Sie hilfreiche Fehlermeldungen

### Sprachcodes
Stellen Sie sicher, dass Ihr Service die gleichen Sprachcodes versteht wie die anderen Services:
- `de` - Deutsch
- `en` - Englisch
- `pt` - Portugiesisch

Falls Ihr Service andere Codes nutzt, implementieren Sie eine Konvertierungsfunktion.

## Testen

Nach dem Hinzufügen eines neuen Services:

1. Starten Sie die App: `streamlit run app.py`
2. Öffnen Sie die "Decoder configuration"
3. Wählen Sie Ihren neuen Service aus den Radio Buttons
4. Testen Sie sowohl "Decode" als auch "Translate"
5. Überprüfen Sie Edge Cases (leere Eingabe, Sonderzeichen, etc.)

## Weitere Informationen

- Hauptdokumentation: `documents/requirements_document_language_learning_software_prototype.md`
- Technisches Konzept: `documents/technisches_konzept_prototyp_stack_tooling.md`
