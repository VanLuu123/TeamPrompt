import fitz
from docx import Document
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
import pandas as pd
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Any


class DocumentProcessor:
    def __init__(self, chunk_size=800, overlap=150):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", ". ", "• ", "- ", " "]
        )

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
        doc = fitz.open(file_path)
        text = ""
        for page_num, page in enumerate(doc):
            text += f"\n--- Page {page_num + 1} ---\n"
            text += page.get_text() + "\n"
        doc.close()
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

            if len(body) <= self.splitter._chunk_size:
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
                body_chunks = self.splitter.split_text(body)
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
