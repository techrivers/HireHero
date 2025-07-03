import io
import os
from typing import List, Optional
from docx import Document
import re

class SimpleDocumentParser:
    """Simplified document parser that works without pdfminer."""
    
    @staticmethod
    def extract_text_from_docx(file_content: bytes) -> str:
        """Extract text from DOCX file content."""
        try:
            doc = Document(io.BytesIO(file_content))
            text = []
            for paragraph in doc.paragraphs:
                text.append(paragraph.text)
            return '\n'.join(text)
        except Exception as e:
            print(f"Error extracting text from DOCX: {e}")
            return ""
    
    @staticmethod
    def extract_text_from_txt(file_content: bytes) -> str:
        """Extract text from TXT file content."""
        try:
            return file_content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                return file_content.decode('latin-1')
            except Exception as e:
                print(f"Error extracting text from TXT: {e}")
                return ""
    
    @staticmethod
    def extract_text_from_pdf(file_content: bytes) -> str:
        """Simplified PDF text extraction - basic fallback for now."""
        try:
            # Try to import and use PyPDF2 if available
            try:
                import PyPDF2
                pdf_stream = io.BytesIO(file_content)
                pdf_reader = PyPDF2.PdfReader(pdf_stream)
                
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                
                return text.strip()
            except ImportError:
                print("PyPDF2 not available, returning placeholder text for PDF")
                # Return a basic placeholder that indicates we found a PDF but couldn't extract text
                return "PDF document detected - text extraction requires additional setup. Please ensure this CV contains relevant experience and skills for the position."
                
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return "PDF processing error - manual review recommended."
    
    @staticmethod
    def extract_text_from_file(file_content: bytes, filename: str) -> str:
        """Extract text from file based on extension."""
        file_extension = os.path.splitext(filename.lower())[1]
        
        if file_extension == '.pdf':
            return SimpleDocumentParser.extract_text_from_pdf(file_content)
        elif file_extension == '.docx':
            return SimpleDocumentParser.extract_text_from_docx(file_content)
        elif file_extension == '.txt':
            return SimpleDocumentParser.extract_text_from_txt(file_content)
        else:
            print(f"Unsupported file format: {file_extension}")
            return ""
    
    @staticmethod
    def extract_candidate_name(text: str) -> Optional[str]:
        """Extract candidate name from CV text using heuristics."""
        lines = text.split('\n')
        
        # Look for name in first few lines
        for i, line in enumerate(lines[:5]):
            line = line.strip()
            if not line:
                continue
            
            # Skip common headers
            if any(header in line.lower() for header in ['curriculum vitae', 'resume', 'cv', 'profile']):
                continue
            
            # Check if line looks like a name (2-4 words, mostly alphabetic)
            words = line.split()
            if 2 <= len(words) <= 4:
                if all(word.replace('-', '').replace("'", '').isalpha() for word in words):
                    return line
        
        return None
    
    @staticmethod
    def extract_complete_summary(text: str) -> str:
        """Extract complete professional summary from CV."""
        # Look for summary/objective sections
        summary_patterns = [
            r'(?:professional\s*)?summary\s*:?\s*\n?\s*(.*?)(?=\n\s*(?:EXPERIENCE|WORK\s*EXPERIENCE|EMPLOYMENT|EDUCATION|SKILLS)\s*:?|\n\s*\n\s*[A-Z]|$)',
            r'(?:career\s*)?objective\s*:?\s*\n?\s*(.*?)(?=\n\s*(?:EXPERIENCE|WORK\s*EXPERIENCE|EMPLOYMENT|EDUCATION|SKILLS)\s*:?|\n\s*\n\s*[A-Z]|$)',
            r'(?:professional\s*)?profile\s*:?\s*\n?\s*(.*?)(?=\n\s*(?:EXPERIENCE|WORK\s*EXPERIENCE|EMPLOYMENT|EDUCATION|SKILLS)\s*:?|\n\s*\n\s*[A-Z]|$)',
        ]
        
        for pattern in summary_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                summary_text = match.group(1).strip()
                summary_text = re.sub(r'\n+', ' ', summary_text)
                summary_text = re.sub(r'\s+', ' ', summary_text)
                if len(summary_text) > 30:
                    return summary_text[:500]
        
        # Fallback: return first 200 characters
        clean_text = re.sub(r'\s+', ' ', text.strip())
        if len(clean_text) > 200:
            return clean_text[:200] + "..."
        return clean_text
    
    @staticmethod
    def extract_skills_section(text: str) -> List[str]:
        """Extract skills from proper skill headings."""
        skill_heading_patterns = [
            r'(?:^|\n)\s*technical\s*skills?\s*:?\s*\n?\s*(.*?)(?=\n\s*(?:[A-Z][A-Z\s]{2,}|EXPERIENCE|EDUCATION)\s*:?|\n\s*\n\s*[A-Z]|$)',
            r'(?:^|\n)\s*(?:key\s*)?skills?\s*:?\s*\n?\s*(.*?)(?=\n\s*(?:[A-Z][A-Z\s]{2,}|EXPERIENCE|EDUCATION)\s*:?|\n\s*\n\s*[A-Z]|$)',
        ]
        
        for pattern in skill_heading_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                skills_text = match.group(1).strip()
                skills_text = re.sub(r'\n+', ' ', skills_text)
                skills_text = re.sub(r'\s+', ' ', skills_text)
                
                if len(skills_text) > 15:
                    skills = []
                    skill_items = re.split(r'[,;•·▪▫|\-\n]+', skills_text)
                    
                    for item in skill_items:
                        item = item.strip()
                        item = re.sub(r'^[\s•·▪▫\-\*\+\|\(\)]+', '', item)
                        item = re.sub(r'[\s•·▪▫\-\*\+\|\(\)]+$', '', item)
                        item = item.strip()
                        
                        if (len(item) >= 2 and len(item) <= 50 and 
                            not item.isdigit() and 
                            not re.match(r'^[\s\-\*\+]+$', item)):
                            skills.append(item)
                    
                    if skills:
                        return skills[:12]
        
        return []
    
    @staticmethod
    def extract_experience_years(text: str) -> Optional[int]:
        """Extract years of experience from CV text."""
        experience_patterns = [
            r'(\d+)\+?\s*years?\s*of\s*experience',
            r'(\d+)\+?\s*years?\s*experience',
            r'experience\s*:?\s*(\d+)\+?\s*years?'
        ]
        
        for pattern in experience_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return None

# Create a simple document parser instance
simple_document_parser = SimpleDocumentParser()