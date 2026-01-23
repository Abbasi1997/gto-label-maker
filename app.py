import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from io import BytesIO
from PIL import Image
import os

# --- PRECISE SIZES ---
LABEL_W_IN = 4.072965
LABEL_H_IN = 2.56757
SHEET_SIZE = 10.0 * inch

# INCREASED TO 600 DPI FOR BARCODE SHARPNESS
# This ensures the CTC laser sees perfectly sharp edges on tiny numbers.
DPI = 600 

def generate_pdf(uploaded_file):
    # 1. HIGH-DEFINITION IMAGE PROCESSING
    img = Image.open(uploaded_file)
    
    # Ensure RGB mode for best print color reproduction
    if img.mode != "RGB":
        img = img.convert("RGB")
    
    # Calculate target pixels for 600 DPI (Higher resolution = Sharper text)
    target_w_px = int(LABEL_W_IN * DPI)
    target_h_px = int(LABEL_H_IN * DPI)
    
    # Use Image.Resampling.LANCZOS - the highest quality scaling available
    img = img.resize((target_w_px, target_h_px), Image.Resampling.LANCZOS)
    
    # Save optimized image to memory
    # We use JPEG with Quality 95: It's much sharper than compressed PNG 
    # and keeps file size tiny in the PDF container.
    img_buffer = BytesIO()
    img.save(img_buffer, format="JPEG", quality=95, subsampling=0)
    img_buffer.seek(0)
    
    reader = ImageReader(img_buffer)

    # 2. CREATE PDF
    pdf_output = BytesIO()
    c = canvas.Canvas(pdf_output, pagesize=(SHEET_SIZE, SHEET_SIZE))
    
    # Convert inches to points
    label_w_pts = LABEL_W_IN * inch
    label_h_pts = LABEL_H_IN * inch
    h_gap = (SHEET_SIZE - (2 * label_w_pts)) / 3
    v_gap = (SHEET_SIZE - (3 * label_h_pts)) / 4

    # 3. DRAW 6 LABELS
    for row in range(3): 
        for col in range(2):
            x = h_gap + (col * (label_w_pts + h_gap))
            y = SHEET_SIZE - ((row + 1) * (label_h_pts + v_gap))
            
            # Embed image
            c.drawImage(reader, x, y, width=label_w_pts, height=label_h_pts)
            
            # Ultra-thin cutting guide
            c.setLineWidth(0.1)
            c.rect(x, y, label_w_pts, label_h_pts, stroke=1, fill=0)

    c.showPage()
    c.save()
    pdf_output.seek(0)
    return pdf_output

# --- UI ---
st.set_page_config(page_title="GTO HD Automator", layout="centered")

st.title("📸 GTO Plate Maker (HD Mode)")
st.info(f"Target: 600 DPI Sharpness | Sheet: 10x10\"")

uploaded_file = st.file_uploader("Upload Image", type=['jpg', 'png', 'jpeg'])

if uploaded_file:
    if st.button('🚀 GENERATE HD PDF', use_container_width=True):
        with st.spinner('Enhancing edges for barcode clarity...'):
            try:
                pdf_data = generate_pdf(uploaded_file)
                size_kb = len(pdf_data.getvalue()) // 1024
                
                st.success(f"HD PDF Ready! Size: {size_kb} KB")
                st.download_button(
                    label="📥 DOWNLOAD PDF",
                    data=pdf_data,
                    file_name="GTO_HD_Print.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error: {e}")
