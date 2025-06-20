import PyPDF2
from docx import Document
from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Any


class DocumentProcessor:
    def __init__(self, chunk_size=800, overlap=150):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def extract_text(self, file_path: str) -> str:
        file_type = Path(file_path).suffix.lower()
        
        if file_type == ".pdf":
            return self._extract_pdf_text(file_path)
        elif file_type == ".docx":
            return self._extract_docx_text(file_path)
        elif file_type == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        elif file_type == ".csv":
            df = pd.read_csv(file_path)
            return df.to_string(index=False)
        elif file_type == ".html":
            with open(file_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, "html.parser")
                return soup.get_text(separator="\n", strip=True)
        
        raise ValueError(f"Unsupported file type: {file_type}")

    def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text using PyPDF2 instead of PyMuPDF"""
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num, page in enumerate(pdf_reader.pages):
                text += f"\n--- Page {page_num + 1} ---\n"
                text += page.extract_text() + "\n"
        return self._clean_text(text)

    def _extract_docx_text(self, file_path: str) -> str:
        doc = Document(file_path)
        text_parts = [para.text.strip() for para in doc.paragraphs if para.text.strip()]
        return self._clean_text("\n\n".join(text_parts))

    def _clean_text(self, text: str) -> str:
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n ', '\n', text)
        return text.strip()

    def _simple_text_splitter(self, text: str) -> List[str]:
        """Simple text splitter without LangChain dependency"""
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            if end >= len(text):
                chunks.append(text[start:])
                break
            
            # Try to break at sentence or paragraph boundary
            chunk = text[start:end]
            for sep in ['\n\n', '\n', '. ', '! ', '? ']:
                last_sep = chunk.rfind(sep)
                if last_sep > self.chunk_size // 2:  # Don't break too early
                    end = start + last_sep + len(sep)
                    break
            
            chunks.append(text[start:end])
            start = end - self.overlap
            
        return [chunk.strip() for chunk in chunks if chunk.strip()]

    def _group_by_headings(self, text: str) -> List[Dict[str, str]]:
        """Group text into sections based on heading heuristics"""
        lines = text.splitlines()
        blocks = []
        current_heading = "Introduction"
        current_body = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Heading heuristics
            is_heading = (
                len(stripped) < 60 and
                (
                    stripped.isupper() or  # ALL CAPS
                    stripped.istitle() or  # Title Case
                    (len(stripped.split()) <= 5 and not stripped.endswith('.'))  # short + not sentence
                )
            )

            if is_heading:
                # Save previous block
                if current_body:
                    blocks.append({
                        "heading": current_heading,
                        "body": "\n".join(current_body).strip()
                    })
                    current_body = []
                current_heading = stripped
            else:
                current_body.append(line)

        # Final block
        if current_body:
            blocks.append({
                "heading": current_heading,
                "body": "\n".join(current_body).strip()
            })

        return blocks

    def split_text(self, text: str, filename: str) -> List[Dict[str, Any]]:
        """Split text while preserving heading context"""
        chunks = []
        blocks = self._group_by_headings(text)

        for block_index, block in enumerate(blocks):
            heading = block["heading"]
            body = block["body"]

            if len(body) <= self.chunk_size:
                chunks.append({
                    "content": f"[{heading}]\n{body}",
                    "metadata": {
                        "filename": filename,
                        "heading": heading,
                        "chunk_index": 0,
                        "block_index": block_index,
                        "document_type": "structured",
                        "char_count": len(body)
                    }
                })
            else:
                body_chunks = self._simple_text_splitter(body)
                for i, chunk in enumerate(body_chunks):
                    chunks.append({
                        "content": f"[{heading}]\n{chunk}",
                        "metadata": {
                            "filename": filename,
                            "heading": heading,
                            "chunk_index": i,
                            "block_index": block_index,
                            "document_type": "structured",
                            "char_count": len(chunk)
                        }
                    })

        return chunks

    def process_document(self, file_path: str) -> List[Dict[str, Any]]:
        filename = Path(file_path).name
        try:
            text = self.extract_text(file_path)
            if not text.strip():
                raise ValueError("No text content extracted")
            return self.split_text(text, filename)
        except Exception as e:
            raise Exception(f"Error processing {filename}: {str(e)}")
