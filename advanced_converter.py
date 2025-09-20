 # advanced_converter.py
import camelot
import tabula
from pdfminer.high_level import extract_text
import re
from typing import List, Dict

class AdvancedPDFConverter:
    @staticmethod
    def extract_with_camelot(pdf_bytes: bytes) -> Dict:
        """Extract tables using Camelot"""
        with open("temp.pdf", "wb") as f:
            f.write(pdf_bytes)
        
        tables = camelot.read_pdf("temp.pdf", pages='all')
        return {
            "tables": [table.df.to_dict() for table in tables],
            "table_count": tables.n
        }
    
    @staticmethod
    def extract_with_tabula(pdf_bytes: bytes) -> Dict:
        """Extract tables using Tabula"""
        with open("temp.pdf", "wb") as f:
            f.write(pdf_bytes)
        
        tables = tabula.read_pdf("temp.pdf", pages='all', multiple_tables=True)
        return {
            "tables": [table.to_dict() for table in tables] if tables else [],
            "table_count": len(tables) if tables else 0
        }
    
    @staticmethod
    def extract_structured_data(text: str) -> Dict:
        """Extract structured information using regex patterns"""
        patterns = {
            "emails": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone_numbers": r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
            "urls": r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*\??[/\w\.-=&]*',
            "dates": r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
        }
        
        extracted = {}
        for key, pattern in patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            extracted[key] = list(set(matches))  # Remove duplicates
        
        return extracted

# Add to your main API
@app.post("/convert/advanced")
async def advanced_conversion(file: UploadFile = File(...)):
    """
    Advanced PDF conversion with multiple extraction methods
    """
    contents = await file.read()
    
    # Basic text extraction
    basic_data = extract_pdf_data(contents)
    
    # Advanced processing
    converter = AdvancedPDFConverter()
    structured_data = converter.extract_structured_data(basic_data["text"])
    
    # Combine all data
    result = {
        **basic_data,
        "structured_data": structured_data,
        "advanced_processing": {
            "email_count": len(structured_data.get("emails", [])),
            "phone_count": len(structured_data.get("phone_numbers", [])),
            "url_count": len(structured_data.get("urls", []))
        }
    }
    
    return JSONResponse(content=result)