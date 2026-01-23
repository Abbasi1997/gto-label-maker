import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from io import BytesIO
from PIL import Image, ImageOps
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# --- PRECISE SIZES (UNCHANGED) ---
LABEL_W_IN = 4.072965
LABEL_H_IN = 2.56757
SHEET_SIZE = 10.0 * inch
DPI = 600 

def send_email_to_ctc(pdf_buffer):
    """Function to send the generated PDF via email"""
    try:
        # Fetching credentials from Streamlit Secrets
        SENDER_EMAIL = st.secrets["email_user"]
        SENDER_PASSWORD = st.secrets["email_password"]
        SMTP_SERVER = st.secrets.get("smtp_server", "smtp.gmail.com")
        SMTP_PORT = st.secrets.get("smtp_port", 465)
        
        RECEIVER_EMAIL = "colorxctp@yahoo.com"
        SUBJECT = "Rabnawaz Plate GTO"

        # Create email container
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = SUBJECT

        # Attach PDF
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(pdf_buffer.getvalue())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="GTO_Precision_Sheet.pdf"')
        msg.attach(part)

        # Connect and Send
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Email Error: {e}")
        return False

def generate_pdf(uploaded_file, trim_mm, use_cmyk, left_m, top_m, h_gap, v_gap):
    # --- LOGIC UNTOUCHED AS REQUESTED ---
    img = Image.open(uploaded_file)
    if trim_mm > 0:
        w, h = img.size
        t_px_h = (trim_mm / (LABEL_W_IN * 25.4)) * w
        t_px_v = (trim_mm / (LABEL_H_IN * 25.4)) * h
        img = ImageOps.crop(img, (int(t_px_h), int(t_px_v), int(t_px_h), int(t_px_v)))

    if use_cmyk: img = img.convert("CMYK")
    elif img.mode != "RGB": img = img.convert("RGB")
    
    target_w_px, target_h_px = int(LABEL_W_IN * DPI), int(LABEL_H_IN * DPI)
    img = img.resize((target_w_px, target_h_px), Image.Resampling.LANCZOS)
    
    img_buffer = BytesIO()
    img.save(img_buffer, format="JPEG", quality=95, subsampling=0)
    img_buffer.seek(0)
    reader = ImageReader(img_buffer)

    pdf_output = BytesIO()
    c = canvas.Canvas(pdf_output, pagesize=(SHEET_SIZE, SHEET_SIZE))
    l_pts, h_pts = LABEL_W_IN * inch, LABEL_H_IN * inch
    
    for row in range(3):
        for col in range(2):
            x = (left_m * inch) + (col * (l_pts + (h_gap * inch)))
            y = SHEET_SIZE - (top_m * inch) - h_pts - (row * (h_pts + (v_gap * inch)))
            c.drawImage(reader, x, y, width=l_pts, height=h_pts)
            c.setLineWidth(0.1)
            c.rect(x, y, l_pts, h_pts, stroke=1, fill=0)

    c.showPage()
    c.save()
    pdf_output.seek(0)
    return pdf_output

# --- UI (ADDED EMAIL BUTTON ONLY) ---
st.set_page_config(page_title="GTO Precision Automator", layout="centered")
st.title("🎯 GTO Precision Plate Maker")

with st.expander("📏 Placement & Nudge Settings", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        left_margin = st.slider("Left Margin (in)", 0.0, 2.0, 0.65, 0.01)
        h_gap = st.slider("Horizontal Gap (in)", 0.0, 1.5, 0.55, 0.01)
    with c2:
        top_margin = st.slider("Top Margin (in)", 0.0, 2.0, 0.40, 0.01)
        v_gap = st.slider("Vertical Gap (in)", 0.0, 1.5, 0.65, 0.01)

with st.expander("🎨 Advanced Print Quality"):
    col_a, col_b = st.columns(2)
    with col_a: use_cmyk = st.toggle("CMYK Mode", value=True)
    with col_b: trim_val = st.slider("Edge Trim (mm)", 0.0, 5.0, 0.0, 0.5)

uploaded_file = st.file_uploader("Upload Image", type=['jpg', 'png', 'jpeg'])

if uploaded_file:
    if st.button('🚀 GENERATE PRECISION PDF', use_container_width=True):
        st.session_state.pdf_data = generate_pdf(uploaded_file, trim_val, use_cmyk, left_margin, top_margin, h_gap, v_gap)
        st.success("PDF Ready!")

    if "pdf_data" in st.session_state:
        # Download Button
        st.download_button("📥 DOWNLOAD PDF", data=st.session_state.pdf_data, file_name="GTO_Sheet.pdf", mime="application/pdf", use_container_width=True)
        
        # New Email Button
        if st.button('📧 SEND TO CTC (colorxctp@yahoo.com)', use_container_width=True):
            with st.spinner('Sending email to CTC plant...'):
                if send_email_to_ctc(st.session_state.pdf_data):
                    st.balloons()
                    st.success("Email sent to colorxctp@yahoo.com!")
