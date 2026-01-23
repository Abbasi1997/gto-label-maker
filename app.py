import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from io import BytesIO
from PIL import Image
import os

# --- PRECISE SIZES PROVIDED BY USER ---
LABEL_W = 4.072965 * inch
LABEL_H = 2.56757 * inch
SHEET_SIZE = 10.0 * inch

def generate_pdf(uploaded_file):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(SHEET_SIZE, SHEET_SIZE))
    
    # Calculate Center Alignment
    # 2 columns width = 8.14". Space left = 1.86".
    h_gap = (SHEET_SIZE - (2 * LABEL_W)) / 3
    # 3 rows height = 7.70". Space left = 2.30".
    v_gap = (SHEET_SIZE - (3 * LABEL_H)) / 4

    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    
    temp_path = "temp_print.jpg"
    img.save(temp_path, "JPEG", quality=100)
    
    # Grid: 2 columns, 3 rows
    for row in range(3): 
        for col in range(2):
            x = h_gap + (col * (LABEL_W + h_gap))
            # Positioning from top-down
            y = SHEET_SIZE - ((row + 1) * (LABEL_H + v_gap))
            
            c.drawImage(temp_path, x, y, width=LABEL_W, height=LABEL_H)
            
            # Hairline cutting guide (0.1 pt)
            c.setLineWidth(0.1)
            c.rect(x, y, LABEL_W, LABEL_H, stroke=1, fill=0)

    c.showPage()
    c.save()
    if os.path.exists(temp_path): os.remove(temp_path)
    buffer.seek(0)
    return buffer

# --- MOBILE UI ---
st.set_page_config(page_title="GTO Automator", layout="centered")

st.title("GTO Plate Maker")
st.write(f"Sheet: 10x10\" | Labels: 4.07\" x 2.56\"")

uploaded_file = st.file_uploader("Upload Image", type=['jpg', 'png', 'jpeg'])

if uploaded_file:
    if st.button('🚀 GENERATE PDF FOR CTC', use_container_width=True):
        pdf_data = generate_pdf(uploaded_file)
        st.download_button(
            label="📥 DOWNLOAD PDF",
            data=pdf_data,
            file_name="GTO_Sheet_10x10.pdf",
            mime="application/pdf",
            use_container_width=True
        )
