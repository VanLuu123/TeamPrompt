import fitz  # PyMuPDF
from docx import Document
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
import pandas as pd
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Any


class DocumentProcessor:
    def __init__(self, chunk_size=800, overlap=150):
        # Smaller chunks with more overlap for better context preservation
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", ". ", "• ", "- ", " "]
        )

    def extract_text(self, file_path: str) -> str:
        """Enhanced text extraction with better structure preservation"""
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
        """Enhanced PDF extraction with better formatting"""
        doc = fitz.open(file_path)
        text = ""
        
        for page_num, page in enumerate(doc):
            page_text = page.get_text()
            # Add page context
            text += f"\n--- Page {page_num + 1} ---\n"
            text += page_text + "\n"
        
        doc.close()
        return self._clean_text(text)

    def _extract_docx_text(self, file_path: str) -> str:
        """Enhanced DOCX extraction preserving structure"""
        doc = Document(file_path)
        text_parts = []
        
        for para in doc.paragraphs:
            if para.text.strip():
                # Preserve paragraph structure
                text_parts.append(para.text.strip())
        
        return self._clean_text("\n\n".join(text_parts))

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text while preserving structure"""
        # Remove excessive whitespace but preserve structure
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Max 2 consecutive newlines
        text = re.sub(r'[ \t]+', ' ', text)  # Normalize spaces and tabs
        text = re.sub(r'\n ', '\n', text)  # Remove spaces after newlines
        return text.strip()

    def _detect_sections(self, text: str) -> List[Dict[str, Any]]:
        """Detect document sections (resume-specific patterns)"""
        sections = []
        
        # Common resume section patterns
        section_patterns = [
            r'(?i)^(education|experience|professional experience|work experience|projects|skills|technical skills|certifications?)$',
            r'(?i)^(summary|objective|profile)$',
            r'(?i)^(contact|personal information)$'
        ]
        
        lines = text.split('\n')
        current_section = None
        current_content = []
        
        for line_num, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Check if this line is a section header
            is_section_header = False
            for pattern in section_patterns:
                if re.match(pattern, line_stripped):
                    is_section_header = True
                    break
            
            # Also check for other potential headers (all caps, short lines)
            if (not is_section_header and 
                len(line_stripped) < 50 and 
                line_stripped.isupper() and 
                len(line_stripped.split()) <= 4):
                is_section_header = True
            
            if is_section_header:
                # Save previous section
                if current_section and current_content:
                    sections.append({
                        'section': current_section,
                        'content': '\n'.join(current_content).strip(),
                        'start_line': getattr(sections[-1] if sections else None, 'end_line', 0),
                        'end_line': line_num
                    })
                
                # Start new section
                current_section = line_stripped
                current_content = []
            else:
                if line_stripped:  # Only add non-empty lines
                    current_content.append(line)
        
        # Add final section
        if current_section and current_content:
            sections.append({
                'section': current_section,
                'content': '\n'.join(current_content).strip(),
                'start_line': sections[-1]['end_line'] if sections else 0,
                'end_line': len(lines)
            })
        
        return sections

    def _detect_projects_and_jobs(self, text: str) -> List[Dict[str, Any]]:
        """Detect individual projects and job experiences"""
        items = []
        
        # Patterns for job titles and project names
        job_patterns = [
            r'(?i)^([^|\n]+)\s+([A-Za-z]+ \d{4})\s*[–-]\s*([A-Za-z]+ \d{4}|Present)',  # Job with dates
            r'(?i)^([^|\n]+)\|\s*([^|]+)\s+([A-Za-z]+ \d{4})',  # Project with tech stack
        ]
        
        lines = text.split('\n')
        current_item = None
        current_content = []
        
        for line_num, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Check if this looks like a job/project header
            is_item_header = False
            for pattern in job_patterns:
                if re.match(pattern, line_stripped):
                    is_item_header = True
                    break
            
            # Check for company names or project titles
            if (not is_item_header and 
                len(line_stripped) > 10 and 
                len(line_stripped) < 100 and
                not line_stripped.startswith('•') and
                not line_stripped.startswith('-') and
                ('Inc' in line_stripped or 'Corp' in line_stripped or 
                 'Company' in line_stripped or 'LLC' in line_stripped or
                 '|' in line_stripped)):
                is_item_header = True
            
            if is_item_header:
                # Save previous item
                if current_item and current_content:
                    items.append({
                        'title': current_item,
                        'content': '\n'.join(current_content).strip(),
                        'start_line': items[-1]['end_line'] if items else 0,
                        'end_line': line_num
                    })
                
                # Start new item
                current_item = line_stripped
                current_content = []
            else:
                if line_stripped:
                    current_content.append(line)
        
        # Add final item
        if current_item and current_content:
            items.append({
                'title': current_item,
                'content': '\n'.join(current_content).strip(),
                'start_line': items[-1]['end_line'] if items else 0,
                'end_line': len(lines)
            })
        
        return items

    def split_text(self, text: str, filename: str) -> List[Dict[str, Any]]:
        """Enhanced text splitting with better context preservation"""
        chunks = []
        
        # Detect document structure
        sections = self._detect_sections(text)
        projects_jobs = self._detect_projects_and_jobs(text)
        
        if sections:
            # Process by sections
            for section in sections:
                section_chunks = self._split_section(section, filename)
                chunks.extend(section_chunks)
        elif projects_jobs:
            # Process by projects/jobs
            for item in projects_jobs:
                item_chunks = self._split_item(item, filename)
                chunks.extend(item_chunks)
        else:
            # Fallback to regular splitting
            regular_chunks = self.splitter.split_text(text)
            chunks = [
                {
                    "content": chunk,
                    "metadata": {
                        "filename": filename,
                        "chunk_index": i,
                        "document_type": "unstructured"
                    }
                }
                for i, chunk in enumerate(regular_chunks) if chunk.strip()
            ]
        
        return chunks

    def _split_section(self, section: Dict[str, Any], filename: str) -> List[Dict[str, Any]]:
        """Split a document section while preserving context"""
        section_name = section['section']
        content = section['content']
        
        # For shorter sections, keep as single chunk
        if len(content) <= self.splitter._chunk_size:
            return [{
                "content": f"[{section_name}]\n{content}",
                "metadata": {
                    "filename": filename,
                    "section": section_name,
                    "chunk_index": 0,
                    "document_type": "section"
                }
            }]
        
        # Split longer sections
        chunks = self.splitter.split_text(content)
        return [
            {
                "content": f"[{section_name}]\n{chunk}",
                "metadata": {
                    "filename": filename,
                    "section": section_name,
                    "chunk_index": i,
                    "document_type": "section"
                }
            }
            for i, chunk in enumerate(chunks) if chunk.strip()
        ]

    def _split_item(self, item: Dict[str, Any], filename: str) -> List[Dict[str, Any]]:
        """Split a project/job item while preserving context"""
        title = item['title']
        content = item['content']
        
        # Keep items together when possible
        full_content = f"{title}\n{content}"
        
        if len(full_content) <= self.splitter._chunk_size:
            return [{
                "content": full_content,
                "metadata": {
                    "filename": filename,
                    "item_title": title,
                    "chunk_index": 0,
                    "document_type": "item"
                }
            }]
        
        # Split if too long, but keep title context
        chunks = self.splitter.split_text(content)
        return [
            {
                "content": f"{title}\n{chunk}",
                "metadata": {
                    "filename": filename,
                    "item_title": title,
                    "chunk_index": i,
                    "document_type": "item"
                }
            }
            for i, chunk in enumerate(chunks) if chunk.strip()
        ]

    def process_document(self, file_path: str) -> List[Dict[str, Any]]:
        """Complete document processing pipeline"""
        filename = Path(file_path).name
        
        try:
            # Extract text
            text = self.extract_text(file_path)
            
            if not text.strip():
                raise ValueError("No text content extracted")
            
            # Split into chunks
            chunks = self.split_text(text, filename)
            
            # Add additional metadata
            for chunk in chunks:
                chunk["metadata"]["file_path"] = file_path
                chunk["metadata"]["total_chunks"] = len(chunks)
                chunk["metadata"]["char_count"] = len(chunk["content"])
            
            return chunks
            
        except Exception as e:
            raise Exception(f"Error processing {filename}: {str(e)}")