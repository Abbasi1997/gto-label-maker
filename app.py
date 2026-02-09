import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch, mm
from reportlab.lib.utils import ImageReader
from io import BytesIO
from PIL import Image, ImageOps
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import pytesseract  # Requires Tesseract OCR installed
import re

# --- HARD-CODED PRECISION SIZES ---
LABEL_W_IN = 4.072965
LABEL_H_IN = 2.56757
SHEET_SIZE = 9.0 * inch 
DPI = 450 

def extract_file_info(img):
    """Extracts text from image to generate a smart filename."""
    try:
        # Pre-process image for better OCR
        gray = img.convert("L")
        text = pytesseract.image_to_string(gray)
        
        # Default values
        importer = "Unknown Importer"
        exporter = "LGC" if "LGC" in text.upper() else "Pacific" if "PACIFIC" in text.upper() else "Unknown Exporter"
        weight = "No Weight"
        size = "No Size"
        grade = "No Grade"

        # Simple Regex to find patterns (adjust based on your typical label layout)
        weight_match = re.search(r'(\d+\s?KG)', text, re.IGNORECASE)
        if weight_match: weight = weight_match.group(1)

        size_match = re.search(r'(\d+[\s?xX]\d+\s?mm)', text, re.IGNORECASE)
        if size_match: size = size_match.group(1)

        grade_match = re.search(r'(Grade[:\s]+)([A-Za-z0-9\s]+)', text, re.IGNORECASE)
        if grade_match: grade = grade_match.group(2).strip().split('\n')[0]

        # Attempt to get first line as Importer if not found
        lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 3]
        if lines: importer = lines[0]

        return f"{importer}, {exporter}, {weight}, {size}, {grade}"
    except Exception:
        return "GTO_9x9_Plate_Output"

def smart_crop_to_border(img):
    gray = img.convert("L")
    gray = ImageOps.autocontrast(gray, cutoff=2)
    threshold = 80 
    bw = gray.point(lambda x: 255 if x < threshold else 0)
    bbox = bw.getbbox()
    if bbox:
        return img.crop(bbox)
    return img

def send_email_to_ctc(pdf_buffer, filename):
    try:
        SENDER_EMAIL = st.secrets["email_user"]
        SENDER_PASSWORD = st.secrets["email_password"]
        SMTP_SERVER = st.secrets.get("smtp_server", "smtp.gmail.com")
        SMTP_PORT = st.secrets.get("smtp_port", 465)
        
        RECEIVER_EMAIL = "colorxctp@yahoo.com"
        SUBJECT = f"Plate Order: {filename}"

        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = SUBJECT

        part = MIMEBase('application', 'octet-stream')
        part.set_payload(pdf_buffer.getvalue())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{filename}.pdf"')
        msg.attach(part)

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Email Error: {e}")
        return False

def generate_pdf(uploaded_file, auto_crop, black_only):
    img = Image.open(uploaded_file)
    
    # Generate Smart Filename
    extracted_name = extract_file_info(img)
    
    if auto_crop:
        img = smart_crop_to_border(img)

    if black_only:
        img = img.convert("L")
    else:
        img = img.convert("RGB")
    
    target_w_px = int(LABEL_W_IN * DPI)
    target_h_px = int(LABEL_H_IN * DPI)
    img = img.resize((target_w_px, target_h_px), Image.Resampling.LANCZOS)
    
    img_buffer = BytesIO()
    img.save(img_buffer, format="JPEG", quality=85, optimize=True)
    img_buffer.seek(0)
    reader = ImageReader(img_buffer)

    # PDF SETUP
    pdf_output = BytesIO()
    c = canvas.Canvas(pdf_output, pagesize=(SHEET_SIZE, SHEET_SIZE))
    
    # DIMENSIONS IN POINTS
    l_pts = LABEL_W_IN * inch
    h_pts = LABEL_H_IN * inch
    inner_gap_pts = 8 * mm         
    top_gripper_pts = 10 * mm 
    
    # AUTO-CENTERING ON X-AXIS
    total_labels_w = (2 * l_pts) + inner_gap_pts
    left_margin_pts = (SHEET_SIZE - total_labels_w) / 2

    # DRAW 6 LABELS
    for row in range(3): 
        for col in range(2):
            x = left_margin_pts + (col * (l_pts + inner_gap_pts))
            y = SHEET_SIZE - top_gripper_pts - h_pts - (row * (h_pts + inner_gap_pts))
            
            c.drawImage(reader, x, y, width=l_pts, height=h_pts)
            
            # Precision Cutting Guide
            c.setLineWidth(0.1)
            c.rect(x, y, l_pts, h_pts, stroke=1, fill=0)

    c.showPage()
    c.save()
    pdf_output.seek(0)
    return pdf_output, extracted_name

# --- UI ---
st.set_page_config(page_title="GTO 9x9 Precision", layout="centered")
st.title("🎯 GTO 9x9 Smart Plate Maker")

st.info("Configured: 9x9\" Sheet | 10mm Gripper | 8mm Gaps")

with st.expander("✨ Smart Options", expanded=True):
    col_a, col_b = st.columns(2)
    with col_a:
        auto_crop = st.toggle("Auto-Crop to Black Box", value=True)
    with col_b:
        black_only = st.toggle("Black Plate Optimization", value=True)

uploaded_file = st.file_uploader("Upload Image from Canva", type=['jpg', 'png', 'jpeg'])

if uploaded_file:
    if st.button('🚀 GENERATE 9x9 PDF', use_container_width=True):
        pdf_data, auto_name = generate_pdf(uploaded_file, auto_crop, black_only)
        st.session_state.pdf_data = pdf_data
        st.session_state.auto_name = auto_name
        st.success(f"Generated: {auto_name}")

    if "pdf_data" in st.session_state:
        final_filename = f"{st.session_state.auto_name}.pdf"
        
        st.download_button(
            label="📥 DOWNLOAD PDF", 
            data=st.session_state.pdf_data, 
            file_name=final_filename, 
            mime="application/pdf", 
            use_container_width=True
        )
        
        if st.button('📧 SEND TO CTC (colorxctp@yahoo.com)', use_container_width=True):
            with st.spinner('Sending...'):
                if send_email_to_ctc(st.session_state.pdf_data, st.session_state.auto_name):
                    st.balloons()
                    st.success("Sent to CTC plant!")
