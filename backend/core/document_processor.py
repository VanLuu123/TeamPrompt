import PyPDF2
import json
from docx import Document
from pathlib import Path
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss


class DocumentProcessor:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')  # or your preferred model
        self.index = faiss.IndexFlatL2(384)

    def extract_text(self, file_path: str, file_name: str = None) -> str:
        try:
            if not file_type:
                file_type = Path(file_path).suffix.lower().lstrip('.')

            file_type = file_type.lower()

            if file_type == ".pdf":
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    return text.strip()
            
            elif file_type == ".docx":
                doc = Document(file_path)
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text.strip()
            
            elif file_type == ".txt":
                with open(file_path, 'r', encoding='utf-8') as file:
                    text = file.read()
                return text.strip()
            
            else:
                return "Unsupported file type."

        except Exception as e:
            return f"Error reading file: {str(e)}"
        
    def split_text(self, text: str, chunk_size: int = 500, overlap: int = 50):
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks

    def generate_embeddings(self, chunks):
        return self.model.encode(chunks)

    def store_embeddings(self, embeddings):
        self.index.add(np.array(embeddings))

    def process_file(self, file_path: str, file_type: str = None):
        # 1. Extract text
        text = self.extract_text(file_path, file_type)
        if text.startswith("Error"):
            print(text)
            return

        # 2. Split into chunks
        chunks = self.split_text(text)

        # 3. Generate embeddings
        embeddings = self.generate_embeddings(chunks)

        # 4. Store in vector database (FAISS)
        self.store_embeddings(embeddings)

        print(f"Processed {len(chunks)} chunks from {file_path}")