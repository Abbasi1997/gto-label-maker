import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch, mm
from reportlab.lib.utils import ImageReader
from io import BytesIO
from PIL import Image, ImageOps
import os

# --- PRECISE SIZES ---
LABEL_W_IN = 4.072965
LABEL_H_IN = 2.56757
SHEET_SIZE = 10.0 * inch
DPI = 600 

def generate_pdf(uploaded_file, trim_mm, use_cmyk):
    # 1. INITIAL IMAGE LOAD
    img = Image.open(uploaded_file)
    
    # 2. BASIC TRIMMING (Manual Crop)
    if trim_mm > 0:
        # Calculate pixels to trim based on image's current resolution
        # We trim the same amount from all 4 sides
        w, h = img.size
        # Estimate pixels per mm of the uploaded file
        # We use a proportional approach to ensure it works on any photo size
        trim_p_h = (trim_mm / (LABEL_W_IN * 25.4)) * w
        trim_p_v = (trim_mm / (LABEL_H_IN * 25.4)) * h
        
        border = (int(trim_p_h), int(trim_p_v), int(trim_p_h), int(trim_p_v)) # left, top, right, bottom
        img = ImageOps.crop(img, border)

    # 3. CONVERT TO CMYK
    if use_cmyk:
        img = img.convert("CMYK")
    else:
        if img.mode != "RGB":
            img = img.convert("RGB")
    
    # 4. HD RESIZING (600 DPI)
    target_w_px = int(LABEL_W_IN * DPI)
    target_h_px = int(LABEL_H_IN * DPI)
    img = img.resize((target_w_px, target_h_px), Image.Resampling.LANCZOS)
    
    # 5. SAVE TO BUFFER
    img_buffer = BytesIO()
    # Note: JPEG supports CMYK. PNG does not. 
    # If CMYK is selected, we must use JPEG or TIFF.
    img.save(img_buffer, format="JPEG", quality=95, subsampling=0)
    img_buffer.seek(0)
    
    reader = ImageReader(img_buffer)

    # 6. CREATE PDF
    pdf_output = BytesIO()
    c = canvas.Canvas(pdf_output, pagesize=(SHEET_SIZE, SHEET_SIZE))
    
    label_w_pts = LABEL_W_IN * inch
    label_h_pts = LABEL_H_IN * inch
    h_gap = (SHEET_SIZE - (2 * label_w_pts)) / 3
    v_gap = (SHEET_SIZE - (3 * label_h_pts)) / 4

    for row in range(3): 
        for col in range(2):
            x = h_gap + (col * (label_w_pts + h_gap))
            y = SHEET_SIZE - ((row + 1) * (label_h_pts + v_gap))
            
            c.drawImage(reader, x, y, width=label_w_pts, height=label_h_pts)
            
            # Hairline border (0.1pt)
            c.setLineWidth(0.1)
            c.rect(x, y, label_w_pts, label_h_pts, stroke=1, fill=0)

    c.showPage()
    c.save()
    pdf_output.seek(0)
    return pdf_output

# --- MOBILE UI ---
st.set_page_config(page_title="GTO Pro Automator", layout="centered")

st.title("📸 GTO Plate Maker Pro")

with st.expander("🛠️ Advanced Print Settings", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        use_cmyk = st.toggle("Convert to CMYK", value=True, help="Standard for Printing Presses")
    with col2:
        trim_val = st.slider("Trim Edges (mm)", 0.0, 5.0, 0.0, 0.5, help="Remove white edges from original image")

uploaded_file = st.file_uploader("Upload Label Image", type=['jpg', 'png', 'jpeg'])

if uploaded_file:
    if st.button('🚀 GENERATE HD PDF', use_container_width=True):
        with st.spinner('Applying CMYK & Trimming...'):
            try:
                pdf_data = generate_pdf(uploaded_file, trim_val, use_cmyk)
                size_kb = len(pdf_data.getvalue()) // 1024
                
                st.success(f"PDF Generated! ({size_kb} KB)")
                st.download_button(
                    label="📥 DOWNLOAD PDF",
                    data=pdf_data,
                    file_name="GTO_Pro_Sheet.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error: {e}")

st.divider()
st.caption(f"Fixed Label Size: {LABEL_W_IN} x {LABEL_H_IN} inches")
