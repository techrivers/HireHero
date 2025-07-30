import io
import os
from typing import List, Optional, Tuple
from pdfminer.six.high_level import extract_text
from docx import Document
import re

class DocumentParser:
    """Service for parsing different document formats."""
    
    @staticmethod
    def extract_text_from_pdf(file_content: bytes) -> str:
        """Extract text from PDF file content."""
        try:
            print(f"🔍 PDF extraction: Received {type(file_content)} with length {len(file_content) if file_content else 0}")
            
            if not file_content:
                print("❌ PDF extraction: No file content provided")
                return ""
            
            # Use the proper pdfminer API for BytesIO
            from pdfminer.six.pdfinterp import PDFResourceManager, PDFPageInterpreter
            from pdfminer.six.converter import TextConverter
            from pdfminer.six.layout import LAParams
            from pdfminer.six.pdfpage import PDFPage
            from io import StringIO
            
            print(f"✅ PDF extraction: Using pdfminer components")
            
            # Create resource manager
            rsrcmgr = PDFResourceManager()
            retstr = StringIO()
            laparams = LAParams()
            device = TextConverter(rsrcmgr, retstr, laparams=laparams)
            
            # Create interpreter
            interpreter = PDFPageInterpreter(rsrcmgr, device)
            
            # Convert bytes to BytesIO
            pdf_stream = io.BytesIO(file_content)
            
            # Process pages
            for page in PDFPage.get_pages(pdf_stream, check_extractable=True):
                interpreter.process_page(page)
            
            device.close()
            text = retstr.getvalue()
            retstr.close()
            
            extracted_length = len(text.strip())
            print(f"✅ PDF extraction: Successfully extracted {extracted_length} characters")
            
            if extracted_length == 0:
                print("⚠️ PDF extraction: No text extracted from PDF")
            else:
                # Show first 100 characters as preview
                preview = text.strip()[:100].replace('\n', ' ')
                print(f"📄 PDF extraction preview: {preview}...")
            
            return text.strip()
        except Exception as e:
            print(f"❌ Error extracting text from PDF: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback: try using PyPDF2 or another library
            try:
                print("🔄 Trying fallback PDF extraction with PyPDF2...")
                import pypdf2 as PyPDF2
                
                pdf_stream = io.BytesIO(file_content)
                pdf_reader = PyPDF2.PdfReader(pdf_stream)
                
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                
                print(f"✅ Fallback extraction: Got {len(text.strip())} characters")
                return text.strip()
            except Exception as e2:
                print(f"❌ Fallback also failed: {e2}")
                return ""
    
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
    def extract_text_from_file(file_content: bytes, filename: str) -> str:
        """Extract text from file based on extension."""
        file_extension = os.path.splitext(filename.lower())[1]
        
        if file_extension == '.pdf':
            return DocumentParser.extract_text_from_pdf(file_content)
        elif file_extension == '.docx':
            return DocumentParser.extract_text_from_docx(file_content)
        elif file_extension == '.txt':
            return DocumentParser.extract_text_from_txt(file_content)
        else:
            print(f"Unsupported file format: {file_extension}")
            return ""
    
    @staticmethod
    def extract_candidate_name(text: str) -> Optional[str]:
        """Extract candidate name from Resume text using heuristics."""
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
        
        # Fallback: look for "Name:" pattern
        name_pattern = re.search(r'name\s*:?\s*([a-zA-Z\s\-\']+)', text, re.IGNORECASE)
        if name_pattern:
            return name_pattern.group(1).strip()
        
        return None
    
    @staticmethod
    def extract_candidate_summary(text: str) -> str:
        """Extract a summary from Resume text."""
        # Look for summary/objective sections
        summary_patterns = [
            r'summary\s*:?\s*(.*?)(?=\n\s*[A-Z]|\n\s*\n|$)',
            r'objective\s*:?\s*(.*?)(?=\n\s*[A-Z]|\n\s*\n|$)',
            r'profile\s*:?\s*(.*?)(?=\n\s*[A-Z]|\n\s*\n|$)',
            r'about\s*:?\s*(.*?)(?=\n\s*[A-Z]|\n\s*\n|$)'
        ]
        
        for pattern in summary_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                summary = match.group(1).strip()
                # Clean up and limit length
                summary = re.sub(r'\s+', ' ', summary)
                if len(summary) > 200:
                    summary = summary[:200] + "..."
                return summary
        
        # Fallback: return first 200 characters
        clean_text = re.sub(r'\s+', ' ', text.strip())
        if len(clean_text) > 200:
            return clean_text[:200] + "..."
        return clean_text
    
    @staticmethod
    def extract_complete_summary(text: str) -> str:
        """Extract complete professional summary from Resume."""
        # Enhanced patterns for better summary extraction
        summary_patterns = [
            # Professional Summary with better boundaries
            r'(?:professional\s*)?summary\s*:?\s*\n?\s*(.*?)(?=\n\s*(?:EXPERIENCE|WORK\s*EXPERIENCE|EMPLOYMENT|EDUCATION|SKILLS|TECHNICAL\s*SKILLS|PROJECTS|CERTIFICATIONS|QUALIFICATIONS|[A-Z][A-Z\s]{2,})\s*:?|\n\s*\n\s*[A-Z][A-Z\s]*\s*:?|$)',
            # Objective with better boundaries  
            r'(?:career\s*)?objective\s*:?\s*\n?\s*(.*?)(?=\n\s*(?:EXPERIENCE|WORK\s*EXPERIENCE|EMPLOYMENT|EDUCATION|SKILLS|TECHNICAL\s*SKILLS|PROJECTS|CERTIFICATIONS|QUALIFICATIONS|[A-Z][A-Z\s]{2,})\s*:?|\n\s*\n\s*[A-Z][A-Z\s]*\s*:?|$)',
            # Profile
            r'(?:professional\s*)?profile\s*:?\s*\n?\s*(.*?)(?=\n\s*(?:EXPERIENCE|WORK\s*EXPERIENCE|EMPLOYMENT|EDUCATION|SKILLS|TECHNICAL\s*SKILLS|PROJECTS|CERTIFICATIONS|QUALIFICATIONS|[A-Z][A-Z\s]{2,})\s*:?|\n\s*\n\s*[A-Z][A-Z\s]*\s*:?|$)',
            # About Me
            r'about\s*(?:me)?\s*:?\s*\n?\s*(.*?)(?=\n\s*(?:EXPERIENCE|WORK\s*EXPERIENCE|EMPLOYMENT|EDUCATION|SKILLS|TECHNICAL\s*SKILLS|PROJECTS|CERTIFICATIONS|QUALIFICATIONS|[A-Z][A-Z\s]{2,})\s*:?|\n\s*\n\s*[A-Z][A-Z\s]*\s*:?|$)'
        ]
        
        for pattern in summary_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                summary_text = match.group(1).strip()
                # Clean up while preserving meaning
                summary_text = re.sub(r'\n+', ' ', summary_text)  # Replace newlines with spaces
                summary_text = re.sub(r'\s+', ' ', summary_text)  # Normalize spaces
                summary_text = summary_text.strip()
                
                # Remove common junk
                summary_text = re.sub(r'^[\s•·▪▫\-\*\+\|]+', '', summary_text)
                summary_text = re.sub(r'[\s•·▪▫\-\*\+\|]+$', '', summary_text)
                
                # Return if meaningful and substantial
                if len(summary_text) > 30:
                    return summary_text
        
        # Enhanced fallback: look for first meaningful paragraph after name/contact
        lines = text.split('\n')
        skip_contact_lines = True
        collected_text = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip contact info and headers
            if (any(indicator in line.lower() for indicator in ['email', 'phone', '@', '+', 'linkedin', 'github', 'address', 'city']) or
                re.match(r'^[A-Z\s]+$', line) or  # All caps headers
                len(line) < 10):
                continue
            
            # Check if this looks like start of experience/education section
            if any(section in line.upper() for section in ['EXPERIENCE', 'EDUCATION', 'WORK HISTORY', 'EMPLOYMENT', 'SKILLS', 'PROJECTS']):
                break
            
            # If we find a meaningful line, start collecting
            if len(line) > 20 and not re.match(r'^[\d\s\-\+\(\)]+$', line):
                collected_text.append(line)
                
                # Keep collecting until we have enough content or hit a section
                continue_collecting = True
                for j in range(i+1, min(i+10, len(lines))):
                    next_line = lines[j].strip()
                    if (any(section in next_line.upper() for section in ['EXPERIENCE', 'EDUCATION', 'WORK HISTORY', 'EMPLOYMENT']) or
                        len(next_line) == 0):
                        continue_collecting = False
                        break
                    if len(next_line) > 10:
                        collected_text.append(next_line)
                
                # Join and return if we have substantial content
                if collected_text:
                    summary = ' '.join(collected_text)
                    summary = re.sub(r'\s+', ' ', summary).strip()
                    if len(summary) > 50:
                        return summary[:500]  # Cap at reasonable length
                break
        
        return "Professional background information not found in standard format"
    
    @staticmethod 
    def extract_skills_section(text: str) -> List[str]:
        """Extract skills ONLY from proper skill headings - return empty if no skill section found."""
        
        # Comprehensive skill section patterns - only looking for explicit skill headings
        skill_heading_patterns = [
            # Technical Skills variations
            r'(?:^|\n)\s*technical\s*skills?\s*:?\s*\n?\s*(.*?)(?=\n\s*(?:[A-Z][A-Z\s]{2,}|EXPERIENCE|EDUCATION|WORK|EMPLOYMENT|PROJECTS|CERTIFICATIONS)\s*:?|\n\s*\n\s*[A-Z]|$)',
            # Skills variations  
            r'(?:^|\n)\s*(?:key\s*)?skills?\s*:?\s*\n?\s*(.*?)(?=\n\s*(?:[A-Z][A-Z\s]{2,}|EXPERIENCE|EDUCATION|WORK|EMPLOYMENT|PROJECTS|CERTIFICATIONS)\s*:?|\n\s*\n\s*[A-Z]|$)',
            # Skills Tools - NEW PATTERN
            r'(?:^|\n)\s*skills?\s*(?:and\s*)?tools?\s*:?\s*\n?\s*(.*?)(?=\n\s*(?:[A-Z][A-Z\s]{2,}|EXPERIENCE|EDUCATION|WORK|EMPLOYMENT|PROJECTS|CERTIFICATIONS)\s*:?|\n\s*\n\s*[A-Z]|$)',
            # Tools and Skills - NEW PATTERN  
            r'(?:^|\n)\s*tools?\s*(?:and\s*)?skills?\s*:?\s*\n?\s*(.*?)(?=\n\s*(?:[A-Z][A-Z\s]{2,}|EXPERIENCE|EDUCATION|WORK|EMPLOYMENT|PROJECTS|CERTIFICATIONS)\s*:?|\n\s*\n\s*[A-Z]|$)',
            # Professional Skills
            r'(?:^|\n)\s*professional\s*skills?\s*:?\s*\n?\s*(.*?)(?=\n\s*(?:[A-Z][A-Z\s]{2,}|EXPERIENCE|EDUCATION|WORK|EMPLOYMENT|PROJECTS|CERTIFICATIONS)\s*:?|\n\s*\n\s*[A-Z]|$)',
            # Core Competencies
            r'(?:^|\n)\s*core\s*competencies\s*:?\s*\n?\s*(.*?)(?=\n\s*(?:[A-Z][A-Z\s]{2,}|EXPERIENCE|EDUCATION|WORK|EMPLOYMENT|PROJECTS|CERTIFICATIONS)\s*:?|\n\s*\n\s*[A-Z]|$)',
            # Technical Expertise
            r'(?:^|\n)\s*technical\s*expertise\s*:?\s*\n?\s*(.*?)(?=\n\s*(?:[A-Z][A-Z\s]{2,}|EXPERIENCE|EDUCATION|WORK|EMPLOYMENT|PROJECTS|CERTIFICATIONS)\s*:?|\n\s*\n\s*[A-Z]|$)',
            # Programming Languages
            r'(?:^|\n)\s*programming\s*languages?\s*:?\s*\n?\s*(.*?)(?=\n\s*(?:[A-Z][A-Z\s]{2,}|EXPERIENCE|EDUCATION|WORK|EMPLOYMENT|PROJECTS|CERTIFICATIONS)\s*:?|\n\s*\n\s*[A-Z]|$)',
            # Technologies
            r'(?:^|\n)\s*technologies\s*:?\s*\n?\s*(.*?)(?=\n\s*(?:[A-Z][A-Z\s]{2,}|EXPERIENCE|EDUCATION|WORK|EMPLOYMENT|PROJECTS|CERTIFICATIONS)\s*:?|\n\s*\n\s*[A-Z]|$)',
            # Tools
            r'(?:^|\n)\s*tools?\s*:?\s*\n?\s*(.*?)(?=\n\s*(?:[A-Z][A-Z\s]{2,}|EXPERIENCE|EDUCATION|WORK|EMPLOYMENT|PROJECTS|CERTIFICATIONS)\s*:?|\n\s*\n\s*[A-Z]|$)',
            # Software
            r'(?:^|\n)\s*software\s*:?\s*\n?\s*(.*?)(?=\n\s*(?:[A-Z][A-Z\s]{2,}|EXPERIENCE|EDUCATION|WORK|EMPLOYMENT|PROJECTS|CERTIFICATIONS)\s*:?|\n\s*\n\s*[A-Z]|$)',
            # Technical Stack - NEW PATTERN
            r'(?:^|\n)\s*technical\s*stack\s*:?\s*\n?\s*(.*?)(?=\n\s*(?:[A-Z][A-Z\s]{2,}|EXPERIENCE|EDUCATION|WORK|EMPLOYMENT|PROJECTS|CERTIFICATIONS)\s*:?|\n\s*\n\s*[A-Z]|$)',
            # Competencies - NEW PATTERN
            r'(?:^|\n)\s*competencies\s*:?\s*\n?\s*(.*?)(?=\n\s*(?:[A-Z][A-Z\s]{2,}|EXPERIENCE|EDUCATION|WORK|EMPLOYMENT|PROJECTS|CERTIFICATIONS)\s*:?|\n\s*\n\s*[A-Z]|$)'
        ]
        
        # Try each pattern to find a proper skills section
        for pattern in skill_heading_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                skills_text = match.group(1).strip()
                
                # Clean up the extracted text
                skills_text = re.sub(r'\n+', ' ', skills_text)  # Replace newlines with spaces
                skills_text = re.sub(r'\s+', ' ', skills_text)   # Normalize spaces
                
                # Must have substantial content to be valid
                if len(skills_text) > 15:  # Minimum meaningful content
                    skills = []
                    
                    # Parse skills using multiple delimiters
                    # Split by commas, semicolons, bullets, pipes, newlines
                    skill_items = re.split(r'[,;•·▪▫|\-\n]+', skills_text)
                    
                    for item in skill_items:
                        item = item.strip()
                        
                        # Clean up bullet points and special characters at start/end
                        item = re.sub(r'^[\s•·▪▫\-\*\+\|\(\)]+', '', item)
                        item = re.sub(r'[\s•·▪▫\-\*\+\|\(\)]+$', '', item)
                        item = item.strip()
                        
                        # Valid skill criteria
                        if (len(item) >= 2 and           # Minimum length
                            len(item) <= 50 and          # Maximum length  
                            not item.isdigit() and       # Not just numbers
                            not re.match(r'^[\s\-\*\+]+$', item)):  # Not just symbols
                            skills.append(item)
                    
                    # Return skills if we found meaningful ones
                    if skills:
                        return skills[:12]  # Return max 12 skills
        
        # NO FALLBACK - if no proper skill section found, return empty list
        # This will be handled by the calling code to show "No key skills mentioned"
        return []
    
    @staticmethod
    def extract_experience_years(text: str) -> Optional[int]:
        """Extract years of experience from Resume text."""
        # Look for experience patterns
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

document_parser = DocumentParser()
