import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from io import BytesIO
from PIL import Image
import os

# --- PRECISE SIZES PROVIDED BY USER ---
LABEL_W_IN = 4.072965
LABEL_H_IN = 2.56757
SHEET_SIZE = 10.0 * inch

# Professional Print Standard (300 DPI)
DPI = 300

def generate_pdf(uploaded_file):
    # 1. OPTIMIZE IMAGE FOR PRESS
    img = Image.open(uploaded_file)
    
    # Convert to RGB to ensure compatibility and smaller size
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    
    # Calculate target pixels for 300 DPI sharpness
    target_w_px = int(LABEL_W_IN * DPI)
    target_h_px = int(LABEL_H_IN * DPI)
    
    # Resize with Lanczos (Best for labels/text quality)
    img = img.resize((target_w_px, target_h_px), Image.Resampling.LANCZOS)
    
    # Save to memory buffer with high optimization
    img_buffer = BytesIO()
    img.save(img_buffer, format="PNG", optimize=True)
    img_buffer.seek(0)
    
    # --- THE FIX ---
    # Wrap the image in ImageReader. This prevents the TypeError.
    # By creating it once here, we ensure the PDF only stores ONE copy of the image.
    reader = ImageReader(img_buffer)

    # 2. CREATE PDF
    pdf_output = BytesIO()
    c = canvas.Canvas(pdf_output, pagesize=(SHEET_SIZE, SHEET_SIZE))
    
    # Convert inches to PDF points
    label_w_pts = LABEL_W_IN * inch
    label_h_pts = LABEL_H_IN * inch
    
    # Precise Centering Math
    h_gap = (SHEET_SIZE - (2 * label_w_pts)) / 3
    v_gap = (SHEET_SIZE - (3 * label_h_pts)) / 4

    # 3. DRAW 6 LABELS
    for row in range(3): 
        for col in range(2):
            x = h_gap + (col * (label_w_pts + h_gap))
            y = SHEET_SIZE - ((row + 1) * (label_h_pts + v_gap))
            
            # Use the 'reader' object we created earlier
            c.drawImage(reader, x, y, width=label_w_pts, height=label_h_pts)
            
            # Hairline border (0.1pt) for the cutter
            c.setLineWidth(0.1)
            c.rect(x, y, label_w_pts, label_h_pts, stroke=1, fill=0)

    c.showPage()
    c.save()
    pdf_output.seek(0)
    return pdf_output

# --- MOBILE UI ---
st.set_page_config(page_title="GTO Automator Pro", layout="centered")

st.title("📸 GTO Plate Maker")
st.write(f"Sheet: 10x10\" | Labels: {LABEL_W_IN}\" x {LABEL_H_IN}\"")

uploaded_file = st.file_uploader("Upload Image", type=['jpg', 'png', 'jpeg'])

if uploaded_file:
    if st.button('🚀 GENERATE OPTIMIZED PDF', use_container_width=True):
        with st.spinner('Fixing errors & compressing...'):
            try:
                pdf_data = generate_pdf(uploaded_file)
                size_kb = len(pdf_data.getvalue()) // 1024
                
                st.success(f"Success! File size: {size_kb} KB")
                st.download_button(
                    label="📥 DOWNLOAD PDF",
                    data=pdf_data,
                    file_name="GTO_Ready_10x10.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"An error occurred: {e}")
