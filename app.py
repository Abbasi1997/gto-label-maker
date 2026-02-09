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
import re

# --- HARD-CODED PRECISION SIZES ---
LABEL_W_IN = 4.072965
LABEL_H_IN = 2.56757
SHEET_SIZE = 9.0 * inch 
DPI = 450 

# --- PREMIUM UI CSS ---
def local_css():
    st.markdown("""
    <style>
        /* Main background */
        .stApp {
            background: linear-gradient(135deg, #0e1117 0%, #1c202a 100%);
        }
        
        /* Glassmorphism Cards */
        div[data-testid="stExpander"], .stAlert, .css-1r6slb0, .e1tzayqy2 {
            background: rgba(255, 255, 255, 0.05) !important;
            border-radius: 15px !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            backdrop-filter: blur(10px);
            padding: 20px;
        }

        /* Titles and Headers */
        h1 {
            font-family: 'Inter', sans-serif;
            font-weight: 800;
            letter-spacing: -1px;
            color: #ffffff;
            text-align: center;
            margin-bottom: 30px;
        }
        
        /* Custom Button Styling */
        .stButton>button {
            border-radius: 10px;
            height: 3em;
            transition: all 0.3s ease;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            border: none !important;
        }
        
        /* Specific Button Colors */
        div.stButton > button:first-child { /* Generate Button */
            background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
            color: black;
        }
        
        /* Hide Streamlit Branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Success Message Styling */
        .stSuccess {
            background-color: rgba(40, 167, 69, 0.2) !important;
            color: #28a745 !important;
            border: 1px solid #28a745 !important;
        }
    </style>
    """, unsafe_allow_html=True)

# --- CORE FUNCTIONS (Unchanged as per instructions) ---
def extract_file_info(img):
    try:
        import pytesseract
        img_for_ocr = img.convert("L")
        img_for_ocr = ImageOps.autocontrast(img_for_ocr, cutoff=2)
        text = pytesseract.image_to_string(img_for_ocr)
        text_raw = text.replace('\n', ' ')
        text_up = text_raw.upper()
        
        importer = "Unknown_Importer"
        imp_match = re.search(r"IMPORTED BY\s+([^0-9]+)", text_up)
        if imp_match: importer = imp_match.group(1).split("LOT")[0].strip()[:25]

        exporter = "LGC" if "LUCKY GLOBAL" in text_up else "Pacific" if "PACIFIC" in text_up else "Unknown_Exporter"
        
        weight = "NoWeight"
        w_match = re.search(r"(\d+)\s?KG", text_up)
        if w_match: weight = f"{w_match.group(1)}KG"

        product = "Onion" if any(x in text_up for x in ["ONION", "BAWANG"]) else "Potato" if any(x in text_up for x in ["POTATO", "KENTANG"]) else "Product"
        
        grade = "Grade_1" if "GRADE : 1" in text_up or "GRED : 1" in text_up else "Grade_Unknown"
        
        size = "M" if " M " in text_up or "/M" in text_up else "S" if " S " in text_up else "L" if " L " in text_up else "NoSize"

        importer = re.sub(r'[^A-Z0-9]', '_', importer.upper())
        return f"{importer}, {exporter}, {weight}, {product}, {size}, {grade}"
    except: return "GTO_Plate_Output"

def smart_crop_to_border(img):
    gray = img.convert("L")
    gray = ImageOps.autocontrast(gray, cutoff=2)
    threshold = 80 
    bw = gray.point(lambda x: 255 if x < threshold else 0)
    bbox = bw.getbbox()
    if bbox: return img.crop(bbox)
    return img

def send_email_to_ctc(pdf_buffer, filename):
    try:
        S_EMAIL = st.secrets["email_user"]
        S_PASS = st.secrets["email_password"]
        msg = MIMEMultipart()
        msg['From'] = S_EMAIL
        msg['To'] = "colorxctp@yahoo.com"
        msg['Subject'] = f"New Plate Order: {filename}"
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(pdf_buffer.getvalue())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{filename}.pdf"')
        msg.attach(part)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(S_EMAIL, S_PASS)
            server.sendmail(S_EMAIL, "colorxctp@yahoo.com", msg.as_string())
        return True
    except: return False

def generate_pdf(uploaded_file, auto_crop, black_only):
    img = Image.open(uploaded_file)
    ext_name = extract_file_info(img)
    if auto_crop: img = smart_crop_to_border(img)
    img = img.convert("L") if black_only else img.convert("RGB")
    target_w_px, target_h_px = int(LABEL_W_IN * DPI), int(LABEL_H_IN * DPI)
    img = img.resize((target_w_px, target_h_px), Image.Resampling.LANCZOS)
    img_buf = BytesIO()
    img.save(img_buf, format="JPEG", quality=85)
    img_buf.seek(0)
    reader = ImageReader(img_buf)
    pdf_output = BytesIO()
    c = canvas.Canvas(pdf_output, pagesize=(SHEET_SIZE, SHEET_SIZE))
    l_pts, h_pts = LABEL_W_IN * inch, LABEL_H_IN * inch
    inner_gap, gripper = 8 * mm, 10 * mm
    total_w = (2 * l_pts) + inner_gap
    left_m = (SHEET_SIZE - total_w) / 2
    for row in range(3): 
        for col in range(2):
            x = left_m + (col * (l_pts + inner_gap))
            y = SHEET_SIZE - gripper - h_pts - (row * (h_pts + inner_gap))
            c.drawImage(reader, x, y, width=l_pts, height=h_pts)
            c.setLineWidth(0.1)
            c.rect(x, y, l_pts, h_pts, stroke=1, fill=0)
    c.showPage()
    c.save()
    pdf_output.seek(0)
    return pdf_output, ext_name

# --- PREMIUM UI LAYOUT ---
st.set_page_config(page_title="GTO Precision | Pro", layout="centered")
local_css()

st.markdown("<h1>🎯 GTO 9×9 PRO PLATE</h1>", unsafe_allow_html=True)

# Main Dashboard Container
with st.container():
    # Setup Information Header
    st.markdown("""
        <div style='text-align: center; color: #888; margin-bottom: 20px;'>
            9.0" Plate Format &nbsp; | &nbsp; 10mm Gripper &nbsp; | &nbsp; 8mm Gutter
        </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader("", type=['jpg', 'png', 'jpeg'])

if uploaded_file:
    # Option Card
    with st.expander("🛠️ PLATE CONFIGURATION", expanded=True):
        col1, col2 = st.columns(2)
        with col1: auto_crop = st.toggle("Smart Border Crop", value=True)
        with col2: black_only = st.toggle("K-Plate Only (Grayscale)", value=True)

    if st.button('🚀 GENERATE PRODUCTION PDF', use_container_width=True):
        with st.spinner('Processing Pre-Press...'):
            pdf_data, auto_name = generate_pdf(uploaded_file, auto_crop, black_only)
            st.session_state.pdf_data = pdf_data
            st.session_state.auto_name = auto_name

    # Result Card (Only shows if data exists)
    if "pdf_data" in st.session_state:
        st.markdown("---")
        st.markdown(f"### 📋 Plate Details")
        st.info(f"**Detected Filename:** {st.session_state.auto_name}")
        
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                label="📥 DOWNLOAD PDF", 
                data=st.session_state.pdf_data, 
                file_name=f"{st.session_state.auto_name}.pdf", 
                mime="application/pdf", 
                use_container_width=True
            )
        with c2:
            if st.button('📧 SEND TO CTC PLANT', use_container_width=True):
                if send_email_to_ctc(st.session_state.pdf_data, st.session_state.auto_name):
                    st.balloons()
                    st.success("SUCCESS: File dispatched to CTC.")
                else:
                    st.error("Error connecting to email server.")

else:
    # Empty State
    st.markdown("""
        <div style='border: 2px dashed rgba(255,255,255,0.1); border-radius: 15px; padding: 50px; text-align: center; color: #555;'>
            Upload a Canva export to begin plate imposition.
        </div>
    """, unsafe_allow_html=True)
