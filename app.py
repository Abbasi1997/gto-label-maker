import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from io import BytesIO
from PIL import Image, ImageOps, ImageFilter
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# --- PRECISE SIZES (UNCHANGED) ---
LABEL_W_IN = 4.072965
LABEL_H_IN = 2.56757
SHEET_SIZE = 10.0 * inch
DPI = 450 

def smart_crop_to_border(img):
    """Automatically detects the black border and crops the image to it"""
    # 1. Convert to grayscale and enhance contrast to find the border easily
    gray = img.convert("L")
    gray = ImageOps.autocontrast(gray, cutoff=2)
    
    # 2. Threshold the image: Everything dark (the border) becomes white, everything else black
    # This helps getbbox find the true 'content'
    threshold = 80 # Adjusting for dark borders
    bw = gray.point(lambda x: 255 if x < threshold else 0)
    
    # 3. Find the bounding box of the non-zero (white) pixels
    bbox = bw.getbbox()
    
    if bbox:
        # Add a tiny 1-pixel padding to ensure we don't cut into the black line itself
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
        part.add_header('Content-Disposition', 'attachment; filename="GTO_Plate_Precision.pdf"')
        msg.attach(part)

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Email Error: {e}")
        return False

def generate_pdf(uploaded_file, auto_crop, black_only, left_m, top_m, h_gap, v_gap):
    img = Image.open(uploaded_file)
    
    # 1. SMART CROP (Replaced manual trim)
    if auto_crop:
        img = smart_crop_to_border(img)

    # 2. BLACK ONLY OPTIMIZATION
    if black_only:
        img = img.convert("L")
    else:
        img = img.convert("RGB")
    
    # 3. RESIZING TO PRECISE PRINT SIZE
    target_w_px = int(LABEL_W_IN * DPI)
    target_h_px = int(LABEL_H_IN * DPI)
    img = img.resize((target_w_px, target_h_px), Image.Resampling.LANCZOS)
    
    # 4. MEMORY OPTIMIZATION
    img_buffer = BytesIO()
    img.save(img_buffer, format="JPEG", quality=85, optimize=True)
    img_buffer.seek(0)
    reader = ImageReader(img_buffer)

    # 5. PDF CONSTRUCTION
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

# --- UI ---
st.set_page_config(page_title="GTO Precision Automator", layout="centered")
st.title("🎯 GTO Smart Plate Maker")

with st.expander("📏 Machine Alignment (Nudge)"):
    c1, c2 = st.columns(2)
    with c1:
        left_margin = st.slider("Left Margin (in)", 0.0, 2.0, 0.65, 0.01)
        h_gap = st.slider("Horizontal Gap (in)", 0.0, 1.5, 0.55, 0.01)
    with c2:
        top_margin = st.slider("Top Margin (in)", 0.0, 2.0, 0.40, 0.01)
        v_gap = st.slider("Vertical Gap (in)", 0.0, 1.5, 0.65, 0.01)

with st.expander("✨ Smart Features", expanded=True):
    col_a, col_b = st.columns(2)
    with col_a:
        auto_crop = st.toggle("Auto-Crop to Label Border", value=True, help="Finds the black box and removes background")
    with col_b:
        black_only = st.toggle("Black Plate Only", value=True)

uploaded_file = st.file_uploader("Upload Image", type=['jpg', 'png', 'jpeg'])

if uploaded_file:
    # Preview
    st.image(uploaded_file, caption="Uploaded Image", width=250)
    
    if st.button('🚀 GENERATE SMART PDF', use_container_width=True):
        st.session_state.pdf_data = generate_pdf(uploaded_file, auto_crop, black_only, left_margin, top_margin, h_gap, v_gap)
        size_kb = len(st.session_state.pdf_data.getvalue()) // 1024
        st.success(f"Perfectly Cropped! Size: {size_kb} KB")

    if "pdf_data" in st.session_state:
        st.download_button("📥 DOWNLOAD PDF", data=st.session_state.pdf_data, file_name="Rabnawaz_GTO_Plate.pdf", mime="application/pdf", use_container_width=True)
        
        if st.button('📧 SEND TO CTC (colorxctp@yahoo.com)', use_container_width=True):
            with st.spinner('Sending...'):
                if send_email_to_ctc(st.session_state.pdf_data):
                    st.balloons()
                    st.success("Email sent to CTC plant!")
