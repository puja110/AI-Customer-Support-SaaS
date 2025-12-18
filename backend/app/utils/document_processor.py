"""
Document Text Extraction Utility
Supports: PDF, DOCX, TXT, Images (OCR)
"""

import PyPDF2
import pdfplumber
from docx import Document
from PIL import Image
import pytesseract
import os
from typing import Optional

class DocumentProcessor:
    """Extract text from various document formats"""
    
    @staticmethod
    def extract_text(file_path: str) -> str:
        """
        Extract text from document based on file extension
        
        Args:
            file_path: Path to the document
            
        Returns:
            Extracted text content
        """
        ext = file_path.lower().split('.')[-1]
        
        try:
            if ext == 'pdf':
                return DocumentProcessor._extract_from_pdf(file_path)
            elif ext in ['docx', 'doc']:
                return DocumentProcessor._extract_from_docx(file_path)
            elif ext == 'txt':
                return DocumentProcessor._extract_from_txt(file_path)
            elif ext in ['png', 'jpg', 'jpeg']:
                return DocumentProcessor._extract_from_image(file_path)
            else:
                raise ValueError(f"Unsupported file type: {ext}")
                
        except Exception as e:
            print(f"Error extracting text from {file_path}: {e}")
            raise
    
    @staticmethod
    def _extract_from_pdf(file_path: str) -> str:
        """Extract text from PDF using pdfplumber (better than PyPDF2)"""
        text = ""
        
        try:
            # Try pdfplumber first (better for most PDFs)
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
        except Exception as e:
            print(f"pdfplumber failed, trying PyPDF2: {e}")
            
            # Fallback to PyPDF2
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n\n"
            except Exception as e2:
                raise Exception(f"Failed to extract PDF text: {e2}")
        
        return text.strip()
    
    @staticmethod
    def _extract_from_docx(file_path: str) -> str:
        """Extract text from DOCX"""
        doc = Document(file_path)
        text = "\n\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    
    @staticmethod
    def _extract_from_txt(file_path: str) -> str:
        """Extract text from TXT"""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    
    @staticmethod
    def _extract_from_image(file_path: str) -> str:
        """Extract text from image using OCR"""
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            raise Exception(f"OCR failed: {e}. Make sure tesseract is installed.")