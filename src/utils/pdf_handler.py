import base64
import streamlit as st
import fitz
from datetime import datetime
import io

def displayPDF(upl_file, width):
    bytes_data = upl_file.getvalue()
    base64_pdf = base64.b64encode(bytes_data).decode("utf-8", 'ignore')
    
    # Handle percentage-based width
    width_style = f'width="{width}"' if isinstance(width, str) else f'width={str(width)}'
    height = 'height="600"'  # Fixed height for better display in sidebar
    
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" {width_style} {height} type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def displayPDFpage(upl_file, page_nr):
    bytes_data = upl_file.getvalue()
    base64_pdf = base64.b64encode(bytes_data).decode("utf-8")
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}#page={page_nr}" width="700" height="1000" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def extract_text_from_pdf(file_bytes):
    """Extract text from PDF using PyMuPDF"""
    text = ""
    try:
        # Create a file-like object from bytes
        pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
        
        # Extract text from each page
        for page in pdf_document:
            text += page.get_text()
        
        pdf_document.close()
        return text
    except Exception as e:
        return f"Error extracting text: {str(e)}"

def handle_pdf_upload(file, user_id, logger):
    start_time = datetime.now()
    file_info = {
        "filename": file.name,
        "size": file.size,
        "type": file.type
    }
    
    # Process the file
    bytes_data = file.getvalue()
    
    # Extract text
    extracted_text = extract_text_from_pdf(bytes_data)
    
    # Calculate processing duration
    end_time = datetime.now()
    processing_duration = (end_time - start_time).total_seconds()
    
    # Log the PDF upload interaction
    logger(
        user_id,
        "PDF_UPLOAD",
        user_prompt=f"Uploaded file: {file.name}",
        model_output=str(file_info),
        duration={"processing": processing_duration}
    )
    
    return bytes_data, extracted_text
