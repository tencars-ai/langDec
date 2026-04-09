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
    def extract_text(self, image: Image.Image, lang: str = 'eng', line_height_threshold: int = 30) -> str:
        """Extract text from an image.
        
        Args:
            image: PIL Image object
            lang: Language code for OCR (e.g., 'eng', 'deu', 'por')
            line_height_threshold: Vertical distance threshold for line breaks (pixels)
            
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
    
    def extract_text(self, image: Image.Image, lang: str = 'eng', line_height_threshold: int = 30) -> str:
        """Extract text from an image using Tesseract.
        
        Args:
            image: PIL Image object
            lang: Language code for OCR
                  - 'eng' for English
                  - 'deu' for German
                  - 'por' for Portuguese
                  - 'eng+deu' for multiple languages
            line_height_threshold: Not used in Tesseract (for compatibility)
            
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
    
    def extract_text(self, image: Image.Image, lang: str = 'eng', line_height_threshold: int = 30) -> str:
        """Extract text from an image using EasyOCR.
        
        Args:
            image: PIL Image object
            lang: Language code for OCR
                  - 'eng' for English
                  - 'deu' for German (will be converted to 'de')
                  - 'por' for Portuguese (will be converted to 'pt')
            line_height_threshold: Vertical distance in pixels to detect line breaks
                                 Higher values = fewer line breaks (only major gaps)
                                 Lower values = more line breaks (detect smaller gaps)
            
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
            
            # Smart joining: use bounding boxes to determine line breaks
            full_text = self._smart_join_text(results, line_height_threshold)
            
            # Clean up the text
            text = self._clean_text(full_text)
            
            return text
            
        except ImportError:
            return "[Error: easyocr not installed. Install with: pip install easyocr]"
        except Exception as e:
            return f"[OCR Error: {str(e)}]"
    
    def _smart_join_text(self, results, line_height_threshold: int = 30) -> str:
        """Intelligently join OCR results based on bounding box positions.
        
        Args:
            results: List of (bbox, text, confidence) tuples from EasyOCR
            line_height_threshold: Vertical distance in pixels to detect line breaks
            
        Returns:
            Text with smart line breaks preserved
        """
        if not results:
            return ""
        
        # Extract text and vertical positions
        text_blocks = []
        for result in results:
            # EasyOCR returns (bbox, text, confidence) - handle flexible unpacking
            try:
                if len(result) >= 2:
                    bbox = result[0]
                    text = result[1]
                    # bbox is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    # Get average Y position (vertical position)
                    # Ensure bbox is a list of points
                    if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                        # Check if points are in correct format
                        if all(isinstance(point, (list, tuple)) and len(point) >= 2 for point in bbox):
                            avg_y = sum(point[1] for point in bbox) / len(bbox)
                            text_blocks.append((avg_y, text))
            except Exception:
                continue  # Skip malformed results
        
        # Sort by vertical position (top to bottom)
        text_blocks.sort(key=lambda x: x[0])
        
        # Join text with smart line breaks
        result_parts = []
        prev_y = None
        
        for y_pos, text in text_blocks:
            if prev_y is None:
                # First line
                result_parts.append(text)
            else:
                # Calculate vertical distance to previous line
                y_distance = y_pos - prev_y
                
                # Use configured threshold to determine line breaks
                if y_distance > line_height_threshold:
                    # Large gap → new line/paragraph
                    result_parts.append('\n' + text)
                else:
                    # Small gap → same line, add space
                    result_parts.append(' ' + text)
            
            prev_y = y_pos
        
        return ''.join(result_parts)
    
    def _clean_text(self, text: str) -> str:
        """Clean up extracted text by removing excessive whitespace.
        
        Args:
            text: Raw OCR text
            
        Returns:
            Cleaned text with normalized whitespace
        """
        import re
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        
        # Replace multiple consecutive newlines with max 2 (paragraph separator)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove spaces at start/end of lines
        text = re.sub(r' *\n *', '\n', text)
        
        return text
    
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
