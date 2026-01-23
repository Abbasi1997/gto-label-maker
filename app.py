import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from io import BytesIO
from PIL import Image
import os

# --- PRECISE SIZES ---
LABEL_W_IN = 4.072965
LABEL_H_IN = 2.56757
SHEET_SIZE = 10.0 * inch

# Print quality standard (300 DPI)
DPI = 300

def generate_pdf(uploaded_file):
    # 1. Process and Optimize Image
    img = Image.open(uploaded_file)
    
    # Convert to RGB (Removes unnecessary transparency data that bloats PNGs)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    
    # Calculate target pixels for 300 DPI
    target_w_px = int(LABEL_W_IN * DPI)
    target_h_px = int(LABEL_H_IN * DPI)
    
    # Resize using Lanczos (Highest quality scaling for text and graphics)
    img = img.resize((target_w_px, target_h_px), Image.Resampling.LANCZOS)
    
    # Save optimized image to memory
    img_buffer = BytesIO()
    img.save(img_buffer, format="PNG", optimize=True)
    img_buffer.seek(0)

    # 2. Create PDF
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=(SHEET_SIZE, SHEET_SIZE))
    
    # Math for centering
    label_w_pts = LABEL_W_IN * inch
    label_h_pts = LABEL_H_IN * inch
    h_gap = (SHEET_SIZE - (2 * label_w_pts)) / 3
    v_gap = (SHEET_SIZE - (3 * label_h_pts)) / 4

    # 3. Use "Template" logic (embed image once, draw 6 times)
    # This is the secret to tiny file sizes
    c.setLineWidth(0.1)
    
    for row in range(3): 
        for col in range(2):
            x = h_gap + (col * (label_w_pts + h_gap))
            y = SHEET_SIZE - ((row + 1) * (label_h_pts + v_gap))
            
            # Draw the image from the buffer
            # ReportLab is smart: if you pass the same Image object, it only embeds it once
            c.drawImage(Image.open(img_buffer), x, y, width=label_w_pts, height=label_h_pts)
            
            # Thin cutting guide
            c.rect(x, y, label_w_pts, label_h_pts, stroke=1, fill=0)

    c.showPage()
    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer

# --- UI ---
st.set_page_config(page_title="GTO Automator Pro", layout="centered")

st.title("GTO Plate Maker (Lite)")
st.write(f"Sheet: 10x10\" | Quality: {DPI} DPI | Format: Optimized PDF")

uploaded_file = st.file_uploader("Upload Image", type=['jpg', 'png', 'jpeg'])

if uploaded_file:
    if st.button('🚀 GENERATE LITE PDF', use_container_width=True):
        with st.spinner('Compressing without quality loss...'):
            pdf_data = generate_pdf(uploaded_file)
            st.success(f"Done! File size is roughly {len(pdf_data.getvalue())//1024} KB")
            st.download_button(
                label="📥 DOWNLOAD PDF",
                data=pdf_data,
                file_name="GTO_Sheet_Lite.pdf",
                mime="application/pdf",
                use_container_width=True
            )
