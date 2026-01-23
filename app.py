import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from io import BytesIO
from PIL import Image, ImageOps
import os

# --- HARD-CODED DIMENSIONS ---
LABEL_W_IN = 4.072965
LABEL_H_IN = 2.56757
SHEET_SIZE = 10.0 * inch
DPI = 600 # HD Print Quality

def generate_pdf(uploaded_file, trim_mm, use_cmyk, left_m, top_m, h_gap, v_gap):
    # 1. Image Processing
    img = Image.open(uploaded_file)
    
    # Apply Trimming
    if trim_mm > 0:
        w, h = img.size
        t_px_h = (trim_mm / (LABEL_W_IN * 25.4)) * w
        t_px_v = (trim_mm / (LABEL_H_IN * 25.4)) * h
        img = ImageOps.crop(img, (int(t_px_h), int(t_px_v), int(t_px_h), int(t_px_v)))

    # CMYK Conversion
    if use_cmyk:
        img = img.convert("CMYK")
    elif img.mode != "RGB":
        img = img.convert("RGB")
    
    # HD Resize
    target_w_px = int(LABEL_W_IN * DPI)
    target_h_px = int(LABEL_H_IN * DPI)
    img = img.resize((target_w_px, target_h_px), Image.Resampling.LANCZOS)
    
    # Save optimized buffer
    img_buffer = BytesIO()
    img.save(img_buffer, format="JPEG", quality=95, subsampling=0)
    img_buffer.seek(0)
    reader = ImageReader(img_buffer)

    # 2. PDF Construction
    pdf_output = BytesIO()
    c = canvas.Canvas(pdf_output, pagesize=(SHEET_SIZE, SHEET_SIZE))
    
    # Convert settings to PDF Points
    l_pts = LABEL_W_IN * inch
    h_pts = LABEL_H_IN * inch
    
    # Loop through columns and rows using specific offsets
    for row in range(3): # 3 Rows
        for col in range(2): # 2 Columns
            # X Calculation: Left Margin + (Column * (Width + Horizontal Gap))
            x = (left_m * inch) + (col * (l_pts + (h_gap * inch)))
            
            # Y Calculation: Top down from 10" sheet
            # 10 - TopMargin - Height - (Row * (Height + Vertical Gap))
            y = SHEET_SIZE - (top_m * inch) - h_pts - (row * (h_pts + (v_gap * inch)))
            
            # Place Label
            c.drawImage(reader, x, y, width=l_pts, height=h_pts)
            
            # Hairline border (0.1pt)
            c.setLineWidth(0.1)
            c.rect(x, y, l_pts, h_pts, stroke=1, fill=0)

    c.showPage()
    c.save()
    pdf_output.seek(0)
    return pdf_output

# --- MOBILE UI ---
st.set_page_config(page_title="GTO Precision Automator", layout="centered")

st.title("🎯 GTO Precision Plate Maker")

with st.expander("📏 Placement & Nudge Settings", expanded=True):
    st.write("Adjust these to match your Freehand layout perfectly:")
    c1, c2 = st.columns(2)
    with c1:
        left_margin = st.slider("Left Margin (in)", 0.0, 2.0, 0.65, 0.01)
        h_gap = st.slider("Horizontal Gap (in)", 0.0, 1.5, 0.55, 0.01)
    with c2:
        top_margin = st.slider("Top Margin (in)", 0.0, 2.0, 0.40, 0.01)
        v_gap = st.slider("Vertical Gap (in)", 0.0, 1.5, 0.65, 0.01)

with st.expander("🎨 Advanced Print Quality"):
    col_a, col_b = st.columns(2)
    with col_a:
        use_cmyk = st.toggle("CMYK Mode", value=True)
    with col_b:
        trim_val = st.slider("Edge Trim (mm)", 0.0, 5.0, 0.0, 0.5)

uploaded_file = st.file_uploader("Upload Image", type=['jpg', 'png', 'jpeg'])

if uploaded_file:
    if st.button('🚀 GENERATE PRECISION PDF', use_container_width=True):
        try:
            pdf_data = generate_pdf(uploaded_file, trim_val, use_cmyk, left_margin, top_margin, h_gap, v_gap)
            st.success(f"PDF Generated ({len(pdf_data.getvalue())//1024} KB)")
            st.download_button("📥 DOWNLOAD PDF", data=pdf_data, file_name="GTO_Precision_Sheet.pdf", mime="application/pdf", use_container_width=True)
        except Exception as e:
            st.error(f"Error: {e}")
