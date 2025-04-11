import base64
import streamlit as st
from datetime import datetime

def displayPDF(upl_file, width):
    bytes_data = upl_file.getvalue()
    base64_pdf = base64.b64encode(bytes_data).decode("utf-8", 'ignore')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width={str(width)} height={str(width*4/3)} type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def displayPDFpage(upl_file, page_nr):
    bytes_data = upl_file.getvalue()
    base64_pdf = base64.b64encode(bytes_data).decode("utf-8")
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}#page={page_nr}" width="700" height="1000" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def handle_pdf_upload(file, user_id, logger):
    start_time = datetime.now()
    file_info = {
        "filename": file.name,
        "size": file.size,
        "type": file.type
    }
    
    # Process the file
    bytes_data = file.getvalue()
    
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
    
    return bytes_data
