import os
import re
import base64
from io import BytesIO
from typing import Optional, List, Dict

import pandas as pd
import streamlit as st

from PIL import Image, ImageEnhance

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm

# ================= CONFIG =================
st.set_page_config(page_title="RAJ GROUP • Catalog", layout="wide")

MAX_CARDS = 240
DEFAULT_DATA_PATH = os.path.join("data", "master.xlsx")
LOGO_PATH = os.path.join("assets", "logo.png")

# THEME COLORS
DARK_BLUE = colors.HexColor("#0B1B3B")
ORANGE = colors.HexColor("#F47C20")
LIGHT_BG = colors.HexColor("#F7F9FF")

# ================= CSS =================
st.markdown(
    """
    <style>
      .block-container { padding-top: 1.0rem; }
      h1, h2, h3 { letter-spacing: 0.2px; }
      .raj-pill {
        display:inline-block; border:1px solid rgba(255,255,255,0.30);
        padding:3px 10px; border-radius:999px; margin-right:6px;
        background: rgba(11,27,59,0.07);
      }
      .raj-hr { border:0; height:1px; background: rgba(255,255,255,0.08); margin: 10px 0; }
      /* Make selectboxes nicer on dark screenshots vibe */
      div[data-baseweb="select"] > div {
        border-radius: 10px !important;
      }
    </style>
    """,
    unsafe_allow_html=True
)

# ================= HELPERS =================
@st.cache_data(show_spinner=False)
def read_sheet(path_or_file, sheet_name: str) -> pd.DataFrame:
    return pd.read_excel(path_or_file, sheet_name=sheet_name)

def safe_str_series(s: pd.Series) -> pd.Series:
    return s.astype("string").fillna("")

def pick_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    cols = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        key = cand.lower()
        if key in cols:
            return cols[key]
    return None

def df_contains_search(df: pd.DataFrame, cols: List[Optional[str]], q: str) -> pd.DataFrame:
    q = (q or "").lower().strip()
    if not q:
        return df
    mask = False
    for c in cols:
        if c and c in df.columns:
            mask = mask | safe_str_series(df[c]).str.lower().str.contains(re.escape(q), na=False)
    return df[mask]

def normalize_filename(name: str) -> str:
    # remove spaces, make lower
    return re.sub(r"\s+", "", (name or "").strip().lower())

def pil_to_bytes(img: Image.Image, fmt="PNG", quality=90) -> bytes:
    buf = BytesIO()
    save_kwargs = {}
    if fmt.upper() in ("JPG", "JPEG"):
        save_kwargs["quality"] = quality
    img.save(buf, format=fmt, **save_kwargs)
    return buf.getvalue()

def load_logo_pil() -> Optional[Image.Image]:
    if os.path.exists(LOGO_PATH):
        return Image.open(LOGO_PATH).convert("RGBA")
    return None

def apply_center_watermark(base_img: Image.Image, logo: Optional[Image.Image], opacity=0.18, scale=0.35) -> Image.Image:
    """
    base_img: RGB/RGBA
    watermark logo will be centered with given opacity and scale relative to base width
    """
    img = base_img.convert("RGBA")
    if logo is None:
        return img

    w, h = img.size
    # scale logo
    target_w = int(w * scale)
    if target_w <= 1:
        return img
    ratio = target_w / logo.size[0]
    target_h = max(1, int(logo.size[1] * ratio))
    wm = logo.resize((target_w, target_h), Image.LANCZOS)

    # apply opacity
    alpha = wm.split()[-1]
    alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
    wm.putalpha(alpha)

    # center paste
    x = (w - wm.size[0]) // 2
    y = (h - wm.size[1]) // 2
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay.paste(wm, (x, y), wm)
    out = Image.alpha_composite(img, overlay)
    return out

def badge(txt: str) -> str:
    return f"<span class='raj-pill'>{txt}</span>"

def guess_image_key(code: str) -> str:
    return normalize_filename(code)

# ================= LOAD DATA =================
with st.sidebar:
    st.header("Data")

uploaded_xl = st.sidebar.file_uploader(
    "Upload Excel (optional)",
    type=["xlsx", "xlsm", "xls"]
)

# NEW: image uploader
uploaded_imgs = st.sidebar.file_uploader(
    "Upload Product Images (optional, multiple)",
    type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True
)

if uploaded_xl is not None:
    xl = pd.ExcelFile(uploaded_xl)
    sheet = st.sidebar.selectbox("Sheet", xl.sheet_names)
    df = read_sheet(uploaded_xl, sheet)
else:
    if not os.path.exists(DEFAULT_DATA_PATH):
        st.error("❌ data/master.xlsx missing. Please upload or add file.")
        st.stop()
    xl = pd.ExcelFile(DEFAULT_DATA_PATH)
    sheet = xl.sheet_names[0]
    df = read_sheet(DEFAULT_DATA_PATH, sheet)

df.columns = [str(c).strip() for c in df.columns]

# ================= DETECT COLUMNS =================
col_code = pick_col(df, ["code", "part no", "part_no", "item code", "itemcode"])
col_desc = pick_col(df, ["description", "item name", "item", "name"])
col_mrp = pick_col(df, ["mrp", "price", "list price"])
col_rate = pick_col(df, ["rate", "sale rate", "net rate"])
col_unit = pick_col(df, ["unit", "uom"])
col_group = pick_col(df, ["group"])
col_segment = pick_col(df, ["segment", "segment (deduped)", "segment_deduped"])
col_hsn = pick_col(df, ["hsn", "hsn code"])
col_gst = pick_col(df, ["gst", "tax", "gst %", "gst%"])
col_category = pick_col(df, ["category"])

# NEW: vehicle brand/model columns
col_v_brand = pick_col(df, ["vehicle brand", "brand", "veh brand", "vehicle_brand", "veh_brand"])
col_v_model = pick_col(df, ["vehicle model", "model", "veh model", "vehicle_model", "veh_model"])

# NEW: image column (optional)
col_img = pick_col(df, ["image", "img", "photo", "picture", "image file", "image_file", "image path", "image_path", "filename"])

# ================= PREP IMAGE MAP (from uploads) =================
# key: normalized filename without extension, value: bytes of image
uploaded_image_map: Dict[str, bytes] = {}
if uploaded_imgs:
    for uf in uploaded_imgs:
        stem = os.path.splitext(uf.name)[0]
        uploaded_image_map[normalize_filename(stem)] = uf.getvalue()

logo_pil = load_logo_pil()

# ================= HEADER =================
c1, c2 = st.columns([1, 4])

with c1:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH)

with c2:
    st.title("RAJ GROUP • Catalog")
    st.caption("Public searchable product catalog")

# ================= FILTERS =================
st.subheader("Filters")

# Layout similar to SS: Group + Segment on top row
frow1_a, frow1_b = st.columns(2)
frow2_a, frow2_b, frow2_c = st.columns(3)

selected_group = None
selected_segment = None
selected_brand = None
selected_model = None

out = df.copy()

# Group dropdown
if col_group:
    groups = sorted([g for g in df[col_group].dropna().unique().tolist() if str(g).strip() != ""])
    with frow1_a:
        selected_group = st.selectbox("Group (type here to search)", groups, index=0 if groups else None)

# Segment dropdown
if col_segment:
    segs = sorted([s for s in df[col_segment].dropna().unique().tolist() if str(s).strip() != ""])
    with frow1_b:
        # allow "ALL"
        seg_opts = ["ALL"] + segs
        selected_segment = st.selectbox("Segment (deduped)", seg_opts, index=0)

# Vehicle Brand / Model dropdowns
if col_v_brand:
    brands = sorted([b for b in df[col_v_brand].dropna().unique().tolist() if str(b).strip() != ""])
    with frow2_a:
        selected_brand = st.selectbox("Vehicle Brand", ["ALL"] + brands, index=0)

if col_v_model:
    with frow2_b:
        if col_v_brand and selected_brand and selected_brand != "ALL":
            models = sorted([
                m for m in df.loc[safe_str_series(df[col_v_brand]) == str(selected_brand), col_v_model]
                .dropna().unique().tolist()
                if str(m).strip() != ""
            ])
        else:
            models = sorted([m for m in df[col_v_model].dropna().unique().tolist() if str(m).strip() != ""])
        selected_model = st.selectbox("Vehicle Model", ["ALL"] + models, index=0)

with frow2_c:
    search_q = st.text_input("Search (Code / Description)")
    mobile_mode = st.toggle("📱 Mobile compact", value=True)

# ================= APPLY FILTERS =================
if selected_group and col_group:
    out = out[safe_str_series(out[col_group]) == str(selected_group)]

if col_segment and selected_segment and selected_segment != "ALL":
    out = out[safe_str_series(out[col_segment]) == str(selected_segment)]

if col_v_brand and selected_brand and selected_brand != "ALL":
    out = out[safe_str_series(out[col_v_brand]) == str(selected_brand)]

if col_v_model and selected_model and selected_model != "ALL":
    out = out[safe_str_series(out[col_v_model]) == str(selected_model)]

out = df_contains_search(out, [col_code, col_desc], search_q)

# ================= KPI =================
k1, k2, k3 = st.columns(3)
k1.metric("Total Rows", f"{len(df):,}")
k2.metric("Filtered Rows", f"{len(out):,}")
k3.metric("Showing Cards", f"{min(len(out), MAX_CARDS):,}")

# ================= PDF EXPORT 1: A4 TABLE =================
st.subheader("Print / Export")

def build_a4_table_pdf(df_in: pd.DataFrame, title: str, group_name: str = "") -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14, rightMargin=14, topMargin=18, bottomMargin=18)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "rajTitle",
        parent=styles["Title"],
        textColor=DARK_BLUE,
        fontSize=18,
        spaceAfter=8
    )
    sub_style = ParagraphStyle(
        "rajSub",
        parent=styles["Normal"],
        textColor=colors.HexColor("#333333"),
        fontSize=10,
        spaceAfter=10
    )

    story = []

    # Logo
    if os.path.exists(LOGO_PATH):
        try:
            story.append(RLImage(LOGO_PATH, width=40*mm, height=18*mm))
            story.append(Spacer(1, 6))
        except:
            pass

    head = title
    if group_name:
        head = f"{title} — {group_name}"
    story.append(Paragraph(head, title_style))
    story.append(Paragraph("Generated from RAJ GROUP catalog", sub_style))
    story.append(Spacer(1, 8))

    # Limit columns for readability (still includes "all" present in df_in)
    data = [df_in.columns.tolist()] + df_in.astype(str).values.tolist()
    table = Table(data, repeatRows=1)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),

        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B9C3D6")),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))

    story.append(table)
    doc.build(story)
    return buf.getvalue()

# build small table for quick A4
pdf_a4_bytes = build_a4_table_pdf(out.head(120), "RAJ GROUP — A4 Catalog Table", group_name=str(selected_group or ""))

st.download_button("⬇️ Download A4 PDF (Table)", data=pdf_a4_bytes, file_name="catalog_a4_table.pdf")

# ================= PDF EXPORT 2: PRICE BOOK / CATALOG WITH IMAGES =================
st.caption("⬇️ नीचे वाला PDF: Images + full product info (Price Book / Catalog)")

def resolve_image_bytes(row) -> Optional[bytes]:
    """
    Try resolve image from:
    1) Excel image column: value = filename (match uploaded map)
    2) Excel image column: value = path on server (if exists)
    3) Uploaded images by CODE filename
    """
    code = str(row[col_code]) if col_code else ""
    code_key = guess_image_key(code)

    # 3) match by code
    if code_key in uploaded_image_map:
        return uploaded_image_map[code_key]

    # 1/2) if excel has image column
    if col_img and col_img in row.index:
        raw = str(row[col_img] or "").strip()
        if raw and raw.lower() != "nan":
            stem = os.path.splitext(os.path.basename(raw))[0]
            key = normalize_filename(stem)
            if key in uploaded_image_map:
                return uploaded_image_map[key]
            # if it's a local path on server
            if os.path.exists(raw):
                try:
                    with open(raw, "rb") as f:
                        return f.read()
                except:
                    pass

    return None

def build_pricebook_pdf(df_in: pd.DataFrame, title: str, group_name: str = "") -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14, rightMargin=14, topMargin=16, bottomMargin=16)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "pbTitle",
        parent=styles["Title"],
        textColor=DARK_BLUE,
        fontSize=18,
        spaceAfter=6
    )
    meta_style = ParagraphStyle(
        "pbMeta",
        parent=styles["Normal"],
        textColor=colors.HexColor("#333333"),
        fontSize=10,
        spaceAfter=10
    )

    story = []

    # Header row: logo + title + group
    if os.path.exists(LOGO_PATH):
        try:
            story.append(RLImage(LOGO_PATH, width=42*mm, height=19*mm))
            story.append(Spacer(1, 6))
        except:
            pass

    head = title
    if group_name:
        head = f"{title} — {group_name}"
    story.append(Paragraph(head, title_style))
    story.append(Paragraph("RAJ GROUP • Price Book / Catalog (with images)", meta_style))
    story.append(Spacer(1, 8))

    # Build rows as cards in PDF
    # We'll create a table per product: [image | details]
    for _, r in df_in.iterrows():
        code = str(r[col_code]) if col_code else ""
        desc = str(r[col_desc]) if col_desc else ""
        rate = str(r[col_rate]) if col_rate else ""
        mrp = str(r[col_mrp]) if col_mrp else ""
        unit = str(r[col_unit]) if col_unit else ""
        hsn = str(r[col_hsn]) if col_hsn else ""
        gst = str(r[col_gst]) if col_gst else ""
        grp = str(r[col_group]) if col_group else ""
        seg = str(r[col_segment]) if col_segment else ""
        vbr = str(r[col_v_brand]) if col_v_brand else ""
        vmo = str(r[col_v_model]) if col_v_model else ""

        # Image
        img_bytes = resolve_image_bytes(r)
        img_flow = None
        if img_bytes:
            try:
                pil = Image.open(BytesIO(img_bytes)).convert("RGBA")
                pil = apply_center_watermark(pil, logo_pil, opacity=0.18, scale=0.42)
                # convert to png for reportlab
                png_bytes = pil_to_bytes(pil, fmt="PNG")
                img_flow = RLImage(BytesIO(png_bytes), width=34*mm, height=34*mm)
            except:
                img_flow = None

        details_lines = []
        if code: details_lines.append(f"<b>CODE:</b> {code}")
        if desc and desc.lower() != "nan": details_lines.append(f"<b>DESC:</b> {desc}")
        if unit and unit.lower() != "nan": details_lines.append(f"<b>UNIT:</b> {unit}")
        if rate and rate.lower() != "nan": details_lines.append(f"<b>RATE:</b> {rate}")
        if mrp and mrp.lower() != "nan": details_lines.append(f"<b>MRP:</b> {mrp}")
        if hsn and hsn.lower() != "nan": details_lines.append(f"<b>HSN:</b> {hsn}")
        if gst and gst.lower() != "nan": details_lines.append(f"<b>GST:</b> {gst}")
        if grp and grp.lower() != "nan": details_lines.append(f"<b>GROUP:</b> {grp}")
        if seg and seg.lower() != "nan": details_lines.append(f"<b>SEGMENT:</b> {seg}")
        if vbr and vbr.lower() != "nan": details_lines.append(f"<b>VEH BRAND:</b> {vbr}")
        if vmo and vmo.lower() != "nan": details_lines.append(f"<b>VEH MODEL:</b> {vmo}")

        details_html = "<br/>".join(details_lines) if details_lines else ""

        left_cell = img_flow if img_flow else Paragraph("<font color='#999999'>No Image</font>", styles["Normal"])
        right_cell = Paragraph(details_html, styles["Normal"])

        row_tbl = Table([[left_cell, right_cell]], colWidths=[40*mm, 150*mm])
        row_tbl.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.7, ORANGE),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
            ("VALIGN", (1, 0), (1, 0), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))

        story.append(row_tbl)
        story.append(Spacer(1, 8))

    doc.build(story)
    return buf.getvalue()

# Limit pricebook size to keep performance ok (you can increase)
pricebook_limit = min(len(out), 300)
pricebook_pdf = build_pricebook_pdf(out.head(pricebook_limit), "RAJ GROUP Price Book", group_name=str(selected_group or ""))

st.download_button(
    "⬇️ Download Price Book / Catalog PDF (with images)",
    data=pricebook_pdf,
    file_name="raj_group_price_book.pdf"
)

# ================= PRODUCTS GRID =================
st.subheader("Products")

N = min(len(out), MAX_CARDS)
data = out.head(N)

grid_cols = st.columns(2 if mobile_mode else 3)

def render_zoomable_image(img_bytes: bytes, caption: str = ""):
    """
    HTML Lightbox zoom. Streamlit native click-zoom is limited,
    so we use a small HTML/JS overlay.
    """
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    html = f"""
    <style>
      .raj-img-wrap {{
        position: relative;
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid rgba(11,27,59,0.10);
        cursor: zoom-in;
      }}
      .raj-img {{
        width: 100%;
        display: block;
      }}
      .raj-modal {{
        display:none;
        position: fixed;
        z-index: 999999;
        left: 0; top: 0;
        width: 100%; height: 100%;
        background: rgba(0,0,0,0.75);
      }}
      .raj-modal-content {{
        position: absolute;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        max-width: 92%;
        max-height: 92%;
        border-radius: 14px;
        overflow: hidden;
        box-shadow: 0 10px 40px rgba(0,0,0,0.45);
      }}
      .raj-modal-content img {{
        width: 100%;
        height: auto;
        display: block;
      }}
      .raj-close {{
        position: absolute;
        right: 18px; top: 12px;
        font-size: 28px;
        color: white;
        cursor: pointer;
        user-select: none;
      }}
      .raj-cap {{
        color: rgba(255,255,255,0.85);
        text-align:center;
        margin-top: 10px;
        font-size: 13px;
      }}
    </style>

    <div class="raj-img-wrap" onclick="document.getElementById('rajModal_{caption}').style.display='block'">
      <img class="raj-img" src="data:image/png;base64,{b64}" />
    </div>

    <div id="rajModal_{caption}" class="raj-modal" onclick="this.style.display='none'">
      <div class="raj-close" onclick="document.getElementById('rajModal_{caption}').style.display='none'">&times;</div>
      <div class="raj-modal-content">
        <img src="data:image/png;base64,{b64}" />
      </div>
      <div class="raj-cap">{caption}</div>
    </div>
    """
    st.components.v1.html(html, height=260, scrolling=False)

for i, (_, r) in enumerate(data.iterrows()):
    with grid_cols[i % len(grid_cols)]:
        st.markdown("<div class='raj-hr'></div>", unsafe_allow_html=True)

        code = str(r[col_code]) if col_code else ""
        desc = str(r[col_desc]) if col_desc else ""
        rate = str(r[col_rate]) if col_rate else ""
        mrp = str(r[col_mrp]) if col_mrp else ""
        unit = str(r[col_unit]) if col_unit else ""
        hsn = str(r[col_hsn]) if col_hsn else ""
        gst = str(r[col_gst]) if col_gst else ""
        grp = str(r[col_group]) if col_group else ""
        seg = str(r[col_segment]) if col_segment else ""
        vbr = str(r[col_v_brand]) if col_v_brand else ""
        vmo = str(r[col_v_model]) if col_v_model else ""

        st.markdown(f"### {code}" if code else "### Item")
        if desc and desc.lower() != "nan":
            st.write(desc)

        # IMAGE (with watermark + zoom)
        img_bytes = resolve_image_bytes(r)
        if img_bytes:
            try:
                pil = Image.open(BytesIO(img_bytes)).convert("RGBA")
                pil = apply_center_watermark(pil, logo_pil, opacity=0.18, scale=0.42)
                disp_bytes = pil_to_bytes(pil, fmt="PNG")
                render_zoomable_image(disp_bytes, caption=code or "Product")
            except:
                st.image(img_bytes, caption=code or "")
        else:
            st.info("No image (upload image named like CODE.jpg or give image column).")

        badges = []
        if rate and rate.lower() != "nan":
            badges.append(badge(f"RATE: {rate}"))
        if mrp and mrp.lower() != "nan":
            badges.append(badge(f"MRP: {mrp}"))
        if unit and unit.lower() != "nan":
            badges.append(badge(f"UNIT: {unit}"))
        if hsn and hsn.lower() != "nan":
            badges.append(badge(f"HSN: {hsn}"))
        if gst and gst.lower() != "nan":
            badges.append(badge(f"GST: {gst}"))
        if grp and grp.lower() != "nan":
            badges.append(badge(f"GROUP: {grp}"))
        if seg and seg.lower() != "nan":
            badges.append(badge(f"SEG: {seg}"))
        if vbr and vbr.lower() != "nan":
            badges.append(badge(f"BRAND: {vbr}"))
        if vmo and vmo.lower() != "nan":
            badges.append(badge(f"MODEL: {vmo}"))

        if badges:
            st.markdown(" ".join(badges), unsafe_allow_html=True)

st.caption(f"Showing {N} products")