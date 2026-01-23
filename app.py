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

# --- HARD-CODED PRECISION SIZES ---
LABEL_W_IN = 4.072965
LABEL_H_IN = 2.56757
SHEET_SIZE = 9.0 * inch  # CHANGED TO 9x9 INCHES
DPI = 450 

def smart_crop_to_border(img):
    gray = img.convert("L")
    gray = ImageOps.autocontrast(gray, cutoff=2)
    threshold = 80 
    bw = gray.point(lambda x: 255 if x < threshold else 0)
    bbox = bw.getbbox()
    if bbox:
        return img.crop(bbox)
    return img

def send_email_to_ctc(pdf_buffer):
    try:
        SENDER_EMAIL = st.secrets["email_user"]
        SENDER_PASSWORD = st.secrets["email_password"]
        SMTP_SERVER = st.secrets.get("smtp_server", "smtp.gmail.com")
        SMTP_PORT = st.secrets.get("smtp_port", 465)
        
        RECEIVER_EMAIL = "colorxctp@yahoo.com"
        SUBJECT = "Rabnawaz Plate GTO"

        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = SUBJECT

        part = MIMEBase('application', 'octet-stream')
        part.set_payload(pdf_buffer.getvalue())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="Rabnawaz_9x9_GTO.pdf"')
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
    
    # EXACT DIMENSIONS IN POINTS
    l_pts = LABEL_W_IN * inch
    h_pts = LABEL_H_IN * inch
    gap_pts = 10 * mm         # 10mm Gap as requested
    top_gripper_pts = 10 * mm # 10mm Top Gripper as requested
    
    # AUTO-CENTERING ON X-AXIS
    total_labels_w = (2 * l_pts) + gap_pts
    left_margin_pts = (SHEET_SIZE - total_labels_w) / 2

    for row in range(3): # 3 Rows
        for col in range(2): # 2 Columns
            # X Calculation
            x = left_margin_pts + (col * (l_pts + gap_pts))
            
            # Y Calculation (Top-Down)
            # Starts from top, subtracts gripper, then subtracts label heights and gaps
            y = SHEET_SIZE - top_gripper_pts - h_pts - (row * (h_pts + gap_pts))
            
            c.drawImage(reader, x, y, width=l_pts, height=h_pts)
            
            # Precision Cutting Guide (0.1pt)
            c.setLineWidth(0.1)
            c.rect(x, y, l_pts, h_pts, stroke=1, fill=0)

    c.showPage()
    c.save()
    pdf_output.seek(0)
    return pdf_output

# --- UI ---
st.set_page_config(page_title="GTO 9x9 Precision", layout="centered")
st.title("🎯 GTO 9x9 Smart Plate Maker")

st.info("Configured for 9x9\" Sheet | 10mm Gripper | 10mm Gaps")

with st.expander("✨ Smart Options", expanded=True):
    col_a, col_b = st.columns(2)
    with col_a:
        auto_crop = st.toggle("Auto-Crop to Black Box", value=True)
    with col_b:
        black_only = st.toggle("Black Plate Optimization", value=True)

uploaded_file = st.file_uploader("Upload Image from Canva", type=['jpg', 'png', 'jpeg'])

if uploaded_file:
    st.image(uploaded_file, caption="Ready for Layout", width=250)
    
    if st.button('🚀 GENERATE 9x9 PDF', use_container_width=True):
        st.session_state.pdf_data = generate_pdf(uploaded_file, auto_crop, black_only)
        size_kb = len(st.session_state.pdf_data.getvalue()) // 1024
        st.success(f"9x9 PDF Generated! Size: {size_kb} KB")

    if "pdf_data" in st.session_state:
        st.download_button("📥 DOWNLOAD PDF", data=st.session_state.pdf_data, file_name="Rabnawaz_9x9_GTO.pdf", mime="application/pdf", use_container_width=True)
        
        if st.button('📧 SEND TO CTC (colorxctp@yahoo.com)', use_container_width=True):
            with st.spinner('Sending to CTC Plant...'):
                if send_email_to_ctc(st.session_state.pdf_data):
                    st.balloons()
                    st.success("Sent! Plate will be exactly 9x9 with 10mm margins.")
