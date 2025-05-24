import PyPDF2
import json
from docx import Document
from pathlib import Path


class DocumentProcessor:
    def __init__(self):
        self.processed_docs = {}

    def extract_text_from_pdf(self, file_path: str) -> str:
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        except Exception as e:
            return f"Error reading PDF: {str(e)}"
        
    def extract_text_from_docx(self, file_path:str) -> str:
        try:
            
        
        except Exception as e:
            return f"Error reading Docx: {str(e)}"