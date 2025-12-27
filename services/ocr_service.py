# Enable modern type hints
from __future__ import annotations

# ABC: Abstract Base Class for defining interfaces
from abc import ABC, abstractmethod
# dataclass: A decorator that automatically generates __init__, __repr__ and other methods
from dataclasses import dataclass
# Type hints
from typing import Optional
# For image processing
from PIL import Image
import io
import numpy as np


class OCRService(ABC):
    """Abstract interface for OCR (Optical Character Recognition) providers.
    
    This defines what methods an OCR service MUST have.
    Think of it as a contract: any OCR service must have these methods.
    """

    @abstractmethod
    def extract_text(self, image: Image.Image, lang: str = 'eng') -> str:
        """Extract text from an image.
        
        Args:
            image: PIL Image object
            lang: Language code for OCR (e.g., 'eng', 'deu', 'por')
            
        Returns:
            Extracted text as string
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the display name of this OCR service."""
        pass


@dataclass
class TesseractOCRService(OCRService):
    """OCR service using Tesseract OCR engine.
    
    Tesseract is a powerful open-source OCR engine that supports
    100+ languages. It requires the tesseract binary to be installed
    on the system.
    
    Installation:
    - Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
    - Linux: sudo apt-get install tesseract-ocr
    - Mac: brew install tesseract
    
    Python package: pip install pytesseract pillow
    
    Language data files:
    - English (eng) - usually included
    - German (deu) - download from https://github.com/tesseract-ocr/tessdata
    - Portuguese (por) - download from https://github.com/tesseract-ocr/tessdata
    """
    
    # Optional path to tesseract executable (if not in PATH)
    tesseract_cmd: Optional[str] = None
    
    @property
    def name(self) -> str:
        """Return the display name of this service."""
        return "Tesseract OCR"
    
    def extract_text(self, image: Image.Image, lang: str = 'eng') -> str:
        """Extract text from an image using Tesseract.
        
        Args:
            image: PIL Image object
            lang: Language code for OCR
                  - 'eng' for English
                  - 'deu' for German
                  - 'por' for Portuguese
                  - 'eng+deu' for multiple languages
            
        Returns:
            Extracted text as string, with cleaned up whitespace
        """
        try:
            import pytesseract
            
            # Set custom tesseract path if provided
            if self.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            
            # Perform OCR
            # config options:
            # --psm 3: Fully automatic page segmentation (default)
            # --oem 3: Use both legacy and LSTM OCR engines
            text = pytesseract.image_to_string(
                image,
                lang=lang,
                config='--psm 3 --oem 3'
            )
            
            # Clean up the text
            text = self._clean_text(text)
            
            return text
            
        except ImportError:
            return "[Error: pytesseract not installed. Install with: pip install pytesseract]"
        except Exception as e:
            return f"[OCR Error: {str(e)}]"
    
    def _clean_text(self, text: str) -> str:
        """Clean up extracted text by removing excessive whitespace.
        
        Args:
            text: Raw OCR text
            
        Returns:
            Cleaned text with:
            - Removed leading/trailing whitespace
            - Removed multiple consecutive spaces
            - Preserved line breaks
        """
        # Split into lines to preserve line breaks
        lines = text.split('\n')
        
        # Clean each line
        cleaned_lines = []
        for line in lines:
            # Remove leading/trailing whitespace
            line = line.strip()
            # Replace multiple spaces with single space
            import re
            line = re.sub(r' +', ' ', line)
            cleaned_lines.append(line)
        
        # Join lines back together
        return '\n'.join(cleaned_lines)
    
    @staticmethod
    def get_language_code(language_label: str) -> str:
        """Convert language display name to Tesseract language code.
        
        Args:
            language_label: Language display name (e.g., "German (de)")
            
        Returns:
            Tesseract language code (e.g., "deu")
        """
        # Mapping from our language codes to Tesseract codes
        lang_mapping = {
            'de': 'deu',
            'en': 'eng',
            'pt': 'por',
        }
        
        # Extract code from label like "German (de)"
        if '(' in language_label and ')' in language_label:
            code = language_label.split('(')[1].split(')')[0]
            return lang_mapping.get(code, 'eng')
        
        return 'eng'  # Default to English


@dataclass
class EasyOCRService(OCRService):
    """OCR service using EasyOCR engine.
    
    EasyOCR is a pure Python OCR library that requires no external
    binary installation. It downloads language models automatically
    on first use (~100MB per language).
    
    Perfect for:
    - Streamlit Cloud deployment
    - Docker containers
    - Systems where you can't install system packages
    
    Installation:
    - Python package only: pip install easyocr
    
    Supported languages are downloaded automatically:
    - English (en)
    - German (de)
    - Portuguese (pt)
    """
    
    # Cache the reader instance to avoid reloading models
    _reader = None
    
    @property
    def name(self) -> str:
        """Return the display name of this service."""
        return "EasyOCR"
    
    def _get_reader(self, languages: list):
        """Get or create an EasyOCR reader instance.
        
        Args:
            languages: List of language codes (e.g., ['en', 'de'])
            
        Returns:
            EasyOCR Reader instance
        """
        try:
            import easyocr
            
            # Create reader if not exists or languages changed
            if self._reader is None:
                self._reader = easyocr.Reader(
                    languages,
                    gpu=False,  # Use CPU (GPU might not be available)
                    verbose=False,  # Less console output
                )
            
            return self._reader
            
        except ImportError:
            return None
    
    def extract_text(self, image: Image.Image, lang: str = 'eng') -> str:
        """Extract text from an image using EasyOCR.
        
        Args:
            image: PIL Image object
            lang: Language code for OCR
                  - 'eng' for English
                  - 'deu' for German (will be converted to 'de')
                  - 'por' for Portuguese (will be converted to 'pt')
            
        Returns:
            Extracted text as string, with cleaned up whitespace
        """
        try:
            # Convert Tesseract codes to EasyOCR codes
            lang_mapping = {
                'eng': 'en',
                'deu': 'de',
                'por': 'pt',
            }
            easyocr_lang = lang_mapping.get(lang, 'en')
            
            # Get reader instance
            reader = self._get_reader([easyocr_lang])
            
            if reader is None:
                return "[Error: easyocr not installed. Install with: pip install easyocr]"
            
            # Convert PIL Image to numpy array
            image_array = np.array(image)
            
            # Perform OCR
            # readtext returns list of tuples: (bbox, text, confidence)
            results = reader.readtext(image_array)
            
            # Extract just the text from results
            texts = [text for (bbox, text, confidence) in results]
            
            # Join all text pieces with newlines
            full_text = '\n'.join(texts)
            
            # Clean up the text
            text = self._clean_text(full_text)
            
            return text
            
        except ImportError:
            return "[Error: easyocr not installed. Install with: pip install easyocr]"
        except Exception as e:
            return f"[OCR Error: {str(e)}]"
    
    def _clean_text(self, text: str) -> str:
        """Clean up extracted text by removing excessive whitespace.
        
        Args:
            text: Raw OCR text
            
        Returns:
            Cleaned text with:
            - Removed leading/trailing whitespace
            - Removed multiple consecutive spaces
            - Preserved line breaks
        """
        # Split into lines to preserve line breaks
        lines = text.split('\n')
        
        # Clean each line
        cleaned_lines = []
        for line in lines:
            # Remove leading/trailing whitespace
            line = line.strip()
            # Replace multiple spaces with single space
            import re
            line = re.sub(r' +', ' ', line)
            cleaned_lines.append(line)
        
        # Join lines back together
        return '\n'.join(cleaned_lines)
    
    @staticmethod
    def get_language_code(language_label: str) -> str:
        """Convert language display name to EasyOCR language code.
        
        Args:
            language_label: Language display name (e.g., "German (de)")
            
        Returns:
            Language code in Tesseract format (for compatibility)
        """
        # Use Tesseract format, will be converted in extract_text
        return TesseractOCRService.get_language_code(language_label)
