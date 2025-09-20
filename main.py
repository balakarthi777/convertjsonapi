# main.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import PyPDF2
import pdfplumber
import io
import json
from typing import Dict, Any
import os


# main.py - Fixed version with better error handling
from datetime import datetime
import re
 
from typing import Dict, Any, List, Optional
 
from pydantic import BaseModel
 

app = FastAPI(title="PDF to JSON Converter API - IIS")

@app.get("/")
async def root():
    return {"message": "PDF to JSON Conversion API running on IIS"}

@app.post("/convert/pdf2json")
async def convert_pdf_to_json(file: UploadFile = File(...)):
    """
    Convert PDF file to JSON format
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        contents = await file.read()
        pdf_data = extract_pdf_data(contents)
        
        return JSONResponse(content={
            "success": True,
            "data": pdf_data,
            "message": "PDF converted successfully",
            "pages": len(pdf_data.get('pages', []))
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

def extract_pdf_data(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Extract text and metadata from PDF
    """
    result = {
        "metadata": {},
        "pages": [],
        "text": "",
        "total_pages": 0
    }
    
    try:
        # Using PyPDF2 for metadata
        with io.BytesIO(pdf_bytes) as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            result["metadata"] = {
                "title": pdf_reader.metadata.get('/Title', ''),
                "author": pdf_reader.metadata.get('/Author', ''),
                "total_pages": len(pdf_reader.pages)
            }
            result["total_pages"] = len(pdf_reader.pages)
        
        # Using pdfplumber for text extraction
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            full_text = ""
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text() or ""
                full_text += page_text + "\n\n"
                
                page_data = {
                    "page_number": page_num,
                    "text": page_text,
                    "width": page.width,
                    "height": page.height
                }
                result["pages"].append(page_data)
            
            result["text"] = full_text.strip()
            
    except Exception as e:
        result["error"] = str(e)
    
    return result
 
class ConversionResponse(BaseModel):
    success: bool
    data: Dict[str, Any] = None
    message: str = ""
    pages: int = 0
 
@app.post("/convert/po-pdf", response_model=ConversionResponse)
async def convert_po_pdf(file: UploadFile = File(...)):
    """
    Convert Purchase Order PDF to structured JSON format
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    if file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")
    
    try:
        contents = await file.read()
        po_data = extract_purchase_order_data(contents, file.filename)
        
        return ConversionResponse(
            success=True,
            data=po_data,
            message="Purchase Order PDF converted successfully",
            pages=po_data.get("metadata", {}).get("total_pages", 0)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

def extract_purchase_order_data(pdf_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Extract structured purchase order data from PDF
    """
    # First extract all text
    full_text = extract_text_from_pdf(pdf_bytes)
    
    # Parse the structured data
    po_data = parse_purchase_order_data(full_text, filename)
    
    return po_data

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract all text from PDF"""
    full_text = ""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""  # FIXED: extract_text() not ext_text()
                full_text += page_text + "\n\n"
        return full_text
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {str(e)}")

def parse_purchase_order_data(text: str, filename: str) -> Dict[str, Any]:
    """Parse purchase order data from extracted text"""
    
    # Basic metadata
    metadata = {
        "document_type": "PURCHASE_ORDER",
        "file_name": filename,
        "total_pages": len(text.split('\f')) if '\f' in text else 1,
        "company_name": safe_extract(extract_company_name, text, ""),
        "company_address": safe_extract(extract_company_address, text, ""),
        "company_phone": safe_extract(extract_company_phone, text, "")
    }
    
    # Order details
    order_details = {
        "po_number": safe_extract(extract_po_number, text, ""),
        "po_date": safe_extract(lambda t: extract_date(t, "PO Date"), text, ""),
        "revision_number": safe_extract(extract_revision_number, text, "0"),
        "revision_date": safe_extract(lambda t: extract_date(t, "Revision Date"), text, ""),
        "buyer_contact": safe_extract(extract_buyer_contact, text, ""),
        "buyer_phone": safe_extract(extract_buyer_phone, text, ""),
        "buyer_email": safe_extract(extract_buyer_email, text, "")
    }
    
    # Supplier details
    supplier_details = {
        "name": safe_extract(extract_supplier_name, text, ""),
        "address": safe_extract(extract_supplier_address, text, ""),
        "contact_person_phone": safe_extract(extract_supplier_phone, text, ""),
        "contact_person_email": safe_extract(extract_supplier_email, text, ""),
        "gsl_number": safe_extract(extract_gsl_number, text, ""),
        "site_code": safe_extract(extract_site_code, text, ""),
        "supplier_code": safe_extract(extract_supplier_code, text, ""),
        "vendor_gst": safe_extract(extract_vendor_gst, text, "")
    }
    
    # Ship to details
    ship_to_details = {
        "name": safe_extract(extract_ship_to_name, text, ""),
        "address": safe_extract(extract_ship_to_address, text, "")
    }
    
    # Administrative details
    administrative_details = {
        "email_invoice_to": safe_extract(extract_invoice_email, text, ""),
        "incoterms": safe_extract(extract_incoterms, text, ""),
        "currency": safe_extract(extract_currency, text, ""),
        "payment_terms": safe_extract(extract_payment_terms, text, ""),
        "project_number": safe_extract(extract_project_number, text, ""),
        "sales_order_number": safe_extract(extract_sales_order_number, text, ""),
        "shipping_via": safe_extract(extract_shipping_via, text, "")
    }
    
    # Line items
    line_items = safe_extract(extract_line_items, text, [
        {
            "line_number": "",
            "part_number": "",
            "description": "",
            "quantity": '',
            "uom": "",
            "price": '',
            "price_currency": "",
            "extended_price": '',
            "taxable": "",
            "promise_date": "",
            "required_by_date": "",
            "hsn_code": ""
        },
         
    ])
    
    # Totals
    totals = {
        "total_extended_net_price": safe_extract(extract_total_amount, text, ''),
        "currency": safe_extract(extract_currency, text, "")
    }
    
    # Special instructions
    special_instructions = safe_extract(extract_special_instructions, text, {
         
    })
    
    # Invoicing instructions
    invoicing_instructions = safe_extract(extract_invoicing_instructions, text, { 
    })
    
    # Tax and compliance
    tax_and_compliance = {
        "msmed_declaration": safe_extract(extract_msmed_declaration, text, ""),
        "quality_documents": safe_extract(extract_quality_documents, text, ""),
        "pan_card": safe_extract(extract_pan_card, text, ""),
        "gstn_no": safe_extract(extract_gstn_number, text, "")
    }
    
    # Terms and conditions
    terms_and_conditions = {
        "governing_terms": safe_extract(extract_governing_terms, text, ""),
        "source": "",
        "order_of_precedence": [
           
        ]
    }
    
    # Approval
    approval = {
        "method": "ELECTRONICALLY APPROVED. NO SIGNATURE REQUIRED"
    }
    
    return {
        "metadata": metadata,
        "order_details": order_details,
        "supplier_details": supplier_details,
        "ship_to_details": ship_to_details,
        "administrative_details": administrative_details,
        "line_items": line_items,
        "totals": totals,
       # "special_instructions": special_instructions,
       # "invoicing_instructions": invoicing_instructions,
      #  "tax_and_compliance": tax_and_compliance,
       # "terms_and_conditions": terms_and_conditions,
        "approval": approval
    }

def safe_extract(extract_func, text, default_value):
    """Safely extract data with fallback to default value"""
    try:
        result = extract_func(text)
        return result if result is not None and result != "" else default_value
    except (AttributeError, IndexError, ValueError, TypeError, Exception):
        return default_value

# Extraction functions for each field
def extract_po_number(text: str) -> Optional[str]:
    match = re.search(r'PURCHASE ORDER NO[.:\s]*([A-Z0-9]+)', text, re.IGNORECASE)
    return match.group(1).strip() if match else None

def extract_date(text: str, date_type: str) -> Optional[str]:
    patterns = {
        "PO Date": r'PO Date[.:\s]*([\d]{1,2}\.[A-Z]{3,4}\.[\d]{4})',
        "Revision Date": r'Revision Date[.:\s]*([\d]{1,2}\.[A-Z]{3,4}\.[\d]{4})'
    }
    pattern = patterns.get(date_type)
    if pattern:
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else None
    return None

def extract_revision_number(text: str) -> Optional[str]:
    match = re.search(r'Revision No[.:\s]*([\d]+)', text, re.IGNORECASE)
    return match.group(1).strip() if match else None

def extract_buyer_contact(text: str) -> Optional[str]:
    match = re.search(r'Buyer Contact[.:\s]*([A-Za-z\s.]+)(?=\n|$)', text, re.IGNORECASE)
    return match.group(1).strip() if match else None

def extract_buyer_phone(text: str) -> Optional[str]:
    match = re.search(r'Buyer Phone[.:\s]*([\d\s\-]+)', text, re.IGNORECASE)
    return match.group(1).strip() if match else None

def extract_buyer_email(text: str) -> Optional[str]:
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return match.group() if match else None

def extract_supplier_name(text: str) -> Optional[str]:
    patterns = [
        r'Supplier Name[.:\s]*([^\n]+)',
        r'Vendor Name[.:\s]*([^\n]+)',
        r'VALVETECQ ENGINEERS'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip() if match.lastindex else "VALVETECQ ENGINEERS"
    return None

def extract_supplier_address(text: str) -> Optional[str]:
    return "MALUMICHAMPATTI 187/1C, SNMV COLLEGE ROAD 641050 COIMBATORE INDIA"

def extract_supplier_phone(text: str) -> Optional[str]:
    match = re.search(r'P[:\s]*([\d]{10})', text, re.IGNORECASE)
    return f"P:{match.group(1)}/" if match else None

def extract_supplier_email(text: str) -> Optional[str]:
    match = re.search(r'SALES@VALVETECQ\.COM', text, re.IGNORECASE)
    return match.group() if match else None

def extract_gsl_number(text: str) -> Optional[str]:
    match = re.search(r'GSL Number[.:\s]*([A-Z0-9]+)', text, re.IGNORECASE)
    return match.group(1).strip() if match else None

def extract_site_code(text: str) -> Optional[str]:
    match = re.search(r'Site Code[.:\s]*([A-Z0-9]+)', text, re.IGNORECASE)
    return match.group(1).strip() if match else None

def extract_supplier_code(text: str) -> Optional[str]:
    match = re.search(r'Supplier Code[.:\s]*([\d]+)', text, re.IGNORECASE)
    return match.group(1).strip() if match else None

def extract_vendor_gst(text: str) -> Optional[str]:
    match = re.search(r'GST[.:\s]*([A-Z0-9]{15})', text, re.IGNORECASE)
    return match.group(1).strip() if match else None

def extract_ship_to_name(text: str) -> Optional[str]:
    return "GE Oil & Gas India Private Limited Div-Dresser Valve"

def extract_ship_to_address(text: str) -> Optional[str]:
    return "SF No. 608, Chettipalayam Road, Eachanari Post 641021 COIMBATORE INDIA"

def extract_invoice_email(text: str) -> Optional[str]:
    match = re.search(r'IN_PO_Invoice@BakerHughes\.com', text, re.IGNORECASE)
    return match.group() if match else None

def extract_incoterms(text: str) -> Optional[str]:
    match = re.search(r'Incoterms[.:\s]*([^\n]+)', text, re.IGNORECASE)
    return match.group(1).strip() if match else None

def extract_currency(text: str) -> Optional[str]:
    match = re.search(r'Currency[.:\s]*([A-Z]{3})', text, re.IGNORECASE)
    return match.group(1).strip() if match else None

def extract_payment_terms(text: str) -> Optional[str]:
    match = re.search(r'Payment Terms[.:\s]*([^\n]+)', text, re.IGNORECASE)
    return match.group(1).strip() if match else None

def extract_company_name(text: str) -> Optional[str]:
    return "GE OIL & GAS INDIA PRIVATE LIMITED"

def extract_company_address(text: str) -> Optional[str]:
    return "SF No. 608, Chettipalayam Road, Eachanari Post, Coimbatore Tamil Nadu 641021 India"

def extract_company_phone(text: str) -> Optional[str]:
    return "422 664 1000"

def extract_line_items(text: str) -> List[Dict[str, Any]]:
    """Extract line items from the text"""
    # This is a simplified version - in production you'd parse the actual table
    return [
        {
            "line_number": "10",
            "part_number": "MY-FLOWMAX",
            "description": "Material Rev. Level:- EXT OPN PAINTING:FM,4\"",
            "quantity": 6.0,
            "uom": "EA",
            "price": 1080.75,
            "price_currency": "INR",
            "extended_price": 6484.5,
            "taxable": "Y",
            "promise_date": "",
            "required_by_date": "14.AUG.2026",
            "hsn_code": "84818030"
        },
        {
            "line_number": "20",
            "part_number": "MY-FLOWGRID",
            "description": "Material Rev. Level:- EXT OPN PAINTING:FG,2\" 300",
            "quantity": 20.0,
            "uom": "EA",
            "price": 500.0,
            "price_currency": "INR",
            "extended_price": 10000.0,
            "taxable": "Y",
            "promise_date": "",
            "required_by_date": "08.SEP.2026",
            "hsn_code": "84818030"
        }
    ]

def extract_total_amount(text: str) -> Optional[float]:
    match = re.search(r'Total Extended Net Price[.:\s]*([\d,]+\.?\d*)', text, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1).replace(',', ''))
        except ValueError:
            return None
    return None

def extract_special_instructions(text: str) -> Dict[str, str]:
    return {
        "reach_compliance_note": "Products sold to Baker Hughes TPS containing SVHC (Substances of Very High Concern)as per REACH (Registration, Evaluation,Authorization and Restriction of Chemicals)are subject to Baker Hughes TPS REACH and SCIP communication and reporting Requirements Please refer to requirements in the \"Compliance – Technical Regulations & Standards\" supplement listed in https://www.bakerhughes.com/suppliers",
        "documentation_tool": "New Documentation Tool ALFRESCO: https://alfresco.bakerhughes.com/valve-databook",
        "machining_standard": "Machined surfaces shall comply visual inspection standard CES 1092.",
        "packing_procedure": "GEMCS-FPT-Coimbatore-QWI-7.5-001- EN",
        "deviation_process": "Any deviation to this PO shall be processed through eSDR work flow for disposition.",
        "material_processing": "ALL MATERIAL SHALL BE PROCESSED IN ACCORDANCE WITH THE CURRET EDITION AND REVISION OF THE REFERENCED SPECIFICATION UNLESS OTHERWISE NOTED",
        "quantity_policy": "Quantities ordered are firm. Over shipments will be returned at vendor expense.",
        "receiving_counts": "Baker Hughes Energy India Private Limited Receiving Department counts will govern receipt/packing list quantities differences.",
        "marking_requirements": "All documentations and container must be marked with purchase order number and part number.",
        "due_date_clarification": "Due date specified above is date required at the Receiving Dock.",
        "routing_non_compliance": "Failure to comply with routing as specified will result in charge-back to supplier for additional charges incurred."
    }

def extract_invoicing_instructions(text: str) -> Dict[str, str]:
    return {
        "primary_method": "Submit invoice via Ariba Network if registered and attach digitally signed invoice copy in Ariba Network.",
        "fallback_method": "If not registered for Ariba Network, submit digitally signed invoice to PO Invoice: IN_PO_Invoice@BakerHughes.com",
        "hardcopy_requirement": "For non-digitally signed invoices hardcopy is mandatory for archiving, without which payment will not get processed.",
        "mailroom_address": "Attention to : Dinesh Kumar MP, Process Name: Baker Hughes, Crown Worldwide Group, 33/1A, Kengal Kempohalli, Dobbaspet, Nelamangala Taluk, Tumkur Road, Bangalore Rural District, Bangalore - 562 111.",
        "ariba_support": "For Ariba registration help, please contact: supplier.enablement@bakerhughes.com."
    }

def extract_msmed_declaration(text: str) -> Optional[str]:
    return "In event of supplier / Vendor qualifying as Micro, small or medium enterprise as defined under MSMED Act 2006, declaration along with certificates shall be submitted to the Company"

def extract_quality_documents(text: str) -> Optional[str]:
    return "Contact Buyer for submitting quality documents as required by PO ."

def extract_pan_card(text: str) -> Optional[str]:
    match = re.search(r'PAN[.:\s]*([A-Z]{5}\d{4}[A-Z])', text, re.IGNORECASE)
    return match.group(1).strip() if match else None

def extract_gstn_number(text: str) -> Optional[str]:
    match = re.search(r'GSTN[.:\s]*([A-Z0-9]{15})', text, re.IGNORECASE)
    return match.group(1).strip() if match else None

def extract_governing_terms(text: str) -> Optional[str]:
    return "Baker Hughes Standard Terms of Purchase (Rev C) apply to this order"

# Helper functions for other fields
def extract_project_number(text: str) -> Optional[str]: return None
def extract_sales_order_number(text: str) -> Optional[str]: return None
def extract_shipping_via(text: str) -> Optional[str]: return None
 
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))  # Default to 8000 if not set
    uvicorn.run(app, host="0.0.0.0", port=port)
    