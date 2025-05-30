import fitz 
from docx import Document
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
import pandas as pd
from bs4 import BeautifulSoup


class DocumentProcessor:
    def __init__(self, chunk_size=500, overlap=50):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.overlap
        )

    def extract_text(self, file_path: str) -> str:
        file_type = Path(file_path).suffix.lower()

        try:
            if file_type == ".pdf":
                doc = fitz.open(file_path)
                text = "\n".join([page.get_text() for page in doc])
                return text.strip()

            elif file_type == ".docx":
                doc = Document(file_path)
                text = "\n".join([para.text for para in doc.paragraphs])
                return text.strip()

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
            else:
                raise ValueError(f"Unsupported file type: {file_type}")

        except Exception as e:
            raise RuntimeError(f"Failed to extract text: {str(e)}")

    def split_text(self, text: str, file_name: str, file_type: str, page_numbers=None):
        chunks = self.splitter.split_text(text)
        result = []

        for i, chunk in enumerate(chunks):
            metadata = {
                "file_name": file_name,
                "file_type": file_type,
                "chunk_index": i,
            }

            if page_numbers:
                metadata["page_number"] = page_numbers[i] if i < len(page_numbers) else None

            result.append({"content": chunk, "metadata": metadata})

        return result
        

    def process(self, file_path: str):
        text = self.extract_text(file_path)
        chunks = self.splitter.split_text(text)
        return chunks
