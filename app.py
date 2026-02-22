import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="RAJ GROUP Pricebook", layout="wide")

# -------------------- Helpers --------------------
@st.cache_data(show_spinner=False)
def read_sheet(uploaded_file, sheet_name: str) -> pd.DataFrame:
    return pd.read_excel(uploaded_file, sheet_name=sheet_name)

def norm(s: str) -> str:
    return str(s).strip().lower()

def safe_str_series(s: pd.Series) -> pd.Series:
    return s.astype("string").fillna("")

def find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols = {norm(c): c for c in df.columns}
    for cand in candidates:
        if norm(cand) in cols:
            return cols[norm(cand)]
    return None

def apply_multiselect_filters(df: pd.DataFrame, filters: dict[str, list[str]]) -> pd.DataFrame:
    out = df
    for col, selected in filters.items():
        if not selected or col not in out.columns:
            continue
        out = out[safe_str_series(out[col]).isin([str(x) for x in selected])]
    return out

def apply_contains_search(df: pd.DataFrame, cols: list[str], q: str) -> pd.DataFrame:
    q = (q or "").strip().lower()
    if not q:
        return df
    mask = False
    for c in cols:
        if c in df.columns:
            mask = mask | safe_str_series(df[c]).str.lower().str.contains(q, na=False)
    return df[mask]

def to_whatsapp_lines(df: pd.DataFrame, code_col: str | None, desc_col: str | None, mrp_col: str | None, max_rows=200):
    out = df.head(max_rows)
    lines = []
    for _, r in out.iterrows():
        code = str(r[code_col]) if code_col and code_col in out.columns else ""
        desc = str(r[desc_col]) if desc_col and desc_col in out.columns else ""
        mrp = str(r[mrp_col]) if mrp_col and mrp_col in out.columns else ""
        code = code.strip()
        desc = desc.strip()
        mrp = mrp.strip()
        if mrp:
            lines.append(f"{code} - {desc} | MRP: {mrp}")
        else:
            lines.append(f"{code} - {desc}")
    return "\n".join([ln for ln in lines if ln.strip()])

def copy_to_clipboard_js(text: str):
    # Small HTML/JS snippet to copy text to clipboard
    escaped = text.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
    html = f"""
    <script>
    navigator.clipboard.writeText(`{escaped}`).then(() => {{
      const el = document.getElementById("copystatus");
      if (el) el.innerText = "Copied ✅";
    }});
    </script>
    <div id="copystatus" style="font-family: system-ui; font-size: 13px; opacity: 0.8;"></div>
    """
    components.html(html, height=30)

# -------------------- Styling --------------------
st.markdown(
    """
    <style>
      .raj-banner {
        background: linear-gradient(90deg, #b71c1c, #e53935);
        border-radius: 18px;
        padding: 16px 18px;
        margin-bottom: 14px;
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap: 12px;
      }
      .raj-banner h1 {
        color: white;
        font-size: 30px;
        margin: 0;
        font-weight: 900;
        letter-spacing: 0.4px;
      }
      .raj-banner p {
        color: rgba(255,255,255,0.88);
        margin: 4px 0 0 0;
        font-size: 13px;
      }
      .pill {
        background: rgba(255,255,255,0.16);
        color: white;
        border: 1px solid rgba(255,255,255,0.22);
        padding: 6px 10px;
        border-radius: 999px;
        font-size: 12px;
        white-space:nowrap;
      }

      div.stButton > button {
        border-radius: 14px !important;
        font-weight: 800 !important;
        padding: 0.6rem 0.9rem !important;
      }

      /* Red button look */
      .redbtn div.stButton > button {
        background: #e53935 !important;
        color: white !important;
        border: 1px solid #e53935 !important;
      }
      .redbtn div.stButton > button:hover {
        background: #c62828 !important;
        border: 1px solid #c62828 !important;
      }

      /* Neutral button look */
      .neutralbtn div.stButton > button {
        background: transparent !important;
        color: inherit !important;
        border: 1px solid rgba(255,255,255,0.18) !important;
      }
      .neutralbtn div.stButton > button:hover {
        border: 1px solid rgba(255,255,255,0.32) !important;
      }

      @media (max-width: 768px) {
        .raj-banner h1 { font-size: 22px; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------- Sidebar: Data --------------------
with st.sidebar:
    st.header("Data")
    uploaded = st.file_uploader("Upload Excel (.xlsx/.xlsm)", type=["xlsx", "xlsm"])
    st.caption("Tip: Aap naya Excel upload karoge to new columns automatically aa jayenge.")

if not uploaded:
    st.info("Upload your Excel file to start.")
    st.stop()

xl = pd.ExcelFile(uploaded)

with st.sidebar:
    sheet = st.selectbox("Sheet", xl.sheet_names, index=0)

df = read_sheet(uploaded, sheet)
df.columns = [str(c).strip() for c in df.columns]

# Auto-detect columns
col_segment = find_col(df, ["SEGMENT", "Segment"])
col_code = find_col(df, ["CODE", "Code", "PART NO", "PARTNO", "PART_NO"])
col_desc = find_col(df, ["DESCRIPTION", "Description", "ITEM", "ITEM NAME"])
col_mrp = find_col(df, ["MRP", "LIST", "LIST PRICE", "PRICE"])
col_brand = find_col(df, ["VEHICLE BRAND", "BRAND", "Vehicle Brand"])
col_vehicle = find_col(df, ["VEHICLE", "Vehicle"])
col_model = find_col(df, ["MODEL", "Model"])
col_category = find_col(df, ["CATEGORY NAME", "CATEGORY", "Category Name", "Category"])
col_group = find_col(df, ["GROUP", "Group"])
col_gst = find_col(df, ["GST", "TAX"])
col_disc = find_col(df, ["DISC", "DISCOUNT"])

# -------------------- Top Banner + Logo --------------------
left_banner, right_banner = st.columns([3.2, 1.2])

with left_banner:
    st.markdown(
        f"""
        <div class="raj-banner">
          <div>
            <h1>RAJ GROUP • Pricebook</h1>
            <p>One-tap Segment • Advanced filters • Mobile view • WhatsApp export</p>
          </div>
          <div class="pill">Rows: {len(df):,}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with right_banner:
    # Optional logo: upload OR keep blank
    logo = st.file_uploader("Logo (optional)", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
    if logo:
        st.image(logo, use_container_width=True)

# -------------------- Top Controls --------------------
top_a, top_b, top_c = st.columns([2.2, 2.0, 1.2])

with top_a:
    search_cols = [c for c in [col_code, col_desc] if c]
    if not search_cols:
        search_cols = df.columns.tolist()
    q = st.text_input("Search (Code/Description)", value="", placeholder="Type part no / description...")

with top_c:
    mobile_mode = st.toggle("📱 Mobile mode", value=True)

# Segment quick buttons
if "segment_quick" not in st.session_state:
    st.session_state.segment_quick = None

def set_segment(val):
    st.session_state.segment_quick = val

if col_segment:
    seg_vals = sorted([x for x in safe_str_series(df[col_segment]).unique().tolist() if x != ""])
    prefer = ["CAR", "HCV", "LCV"]
    ordered = [p for p in prefer if p in seg_vals] + [x for x in seg_vals if x not in prefer]

    with top_b:
        st.write("Quick Segment")
        b1, b2, b3, b4 = st.columns([1, 1, 1, 1])
        active = st.session_state.segment_quick

        def btn(label, container):
            klass = "redbtn" if active == label else "neutralbtn"
            with container:
                st.markdown(f'<div class="{klass}">', unsafe_allow_html=True)
                if st.button(label, use_container_width=True):
                    set_segment(label)
                st.markdown("</div>", unsafe_allow_html=True)

        shown = ordered[:3]
        if len(shown) >= 1: btn(shown[0], b1)
        if len(shown) >= 2: btn(shown[1], b2)
        if len(shown) >= 3: btn(shown[2], b3)

        with b4:
            st.markdown('<div class="neutralbtn">', unsafe_allow_html=True)
            if st.button("Clear", use_container_width=True):
                set_segment(None)
            st.markdown("</div>", unsafe_allow_html=True)

# -------------------- Sidebar: Filters + Columns --------------------
with st.sidebar:
    st.header("Filters")

    default_filters = [c for c in [col_segment, col_vehicle, col_model, col_brand, col_category, col_group] if c]
    filter_cols = st.multiselect(
        "Filter fields (choose dropdowns)",
        options=df.columns.tolist(),
        default=default_filters
    )

    filters = {}
    for col in filter_cols:
        if col not in df.columns:
            continue
        options = [x for x in safe_str_series(df[col]).unique().tolist() if x != ""]
        options = sorted(options)
        filters[col] = st.multiselect(col, options=options)

    st.header("Columns")
    default_visible = [c for c in [col_code, col_desc, col_mrp, col_disc, col_gst, col_segment, col_vehicle, col_brand, col_model, col_category] if c]
    visible_cols = st.multiselect(
        "Visible columns (hide/show)",
        options=df.columns.tolist(),
        default=default_visible if default_visible else df.columns.tolist()
    )

    st.header("Rename columns (optional)")
    st.caption('Paste JSON mapping, e.g. {"MRP":"LIST PRICE","Code":"PART NO"}')
    mapping_txt = st.text_area("Column name mapping (JSON)", value="{}", height=110)

# Parse rename mapping
col_map = {}
try:
    col_map = json.loads(mapping_txt) if mapping_txt.strip() else {}
    if not isinstance(col_map, dict):
        col_map = {}
except Exception:
    st.sidebar.error("Invalid JSON in rename mapping. Using original names.")
    col_map = {}

# -------------------- Apply Filters --------------------
filtered = df.copy()

if col_segment and st.session_state.segment_quick:
    filtered = filtered[safe_str_series(filtered[col_segment]) == st.session_state.segment_quick]

filtered = apply_multiselect_filters(filtered, filters)
filtered = apply_contains_search(filtered, search_cols, q)

# -------------------- KPIs --------------------
k1, k2, k3 = st.columns(3)
k1.metric("Rows (total)", f"{len(df):,}")
k2.metric("Rows (filtered)", f"{len(filtered):,}")
k3.metric("Columns", f"{len(df.columns):,}")

# -------------------- Prepare Display --------------------
display = filtered.copy()
rename_ok = {k: v for k, v in col_map.items() if k in display.columns and isinstance(v, str) and v.strip()}
if rename_ok:
    display = display.rename(columns=rename_ok)

# Visible columns after rename
final_cols = [rename_ok.get(c, c) for c in visible_cols]
final_cols = [c for c in final_cols if c in display.columns]
if not final_cols:
    final_cols = display.columns.tolist()

# Mobile compact: keep essentials
if mobile_mode:
    priority = [rename_ok.get(x, x) for x in [col_code, col_desc, col_mrp, col_disc, col_gst, col_segment, col_vehicle, col_brand, col_model] if x]
    pr = [c for c in priority if c in display.columns]
    if pr:
        final_cols = pr

# -------------------- Copy Code + WhatsApp Export --------------------
st.subheader("Quick Actions")

act1, act2 = st.columns([1.4, 2.6])

with act1:
    # Pick a row to copy its code (first 500 to keep UI fast)
    st.caption("Copy Code")
    if col_code and len(filtered) > 0:
        sample = filtered.head(500).copy()
        sample_codes = safe_str_series(sample[col_code]).tolist()
        selected_code = st.selectbox("Select code", options=sample_codes, index=0)
        cbtn1, cbtn2 = st.columns([1,1])
        with cbtn1:
            if st.button("Copy selected code"):
                copy_to_clipboard_js(selected_code)
        with cbtn2:
            st.code(selected_code, language=None)
    else:
        st.info("Code column not found or no data.")

with act2:
    st.caption("WhatsApp share format")
    wa_text = to_whatsapp_lines(filtered, col_code, col_desc, col_mrp, max_rows=200)
    st.text_area("Copy/paste to WhatsApp (first 200 rows)", value=wa_text, height=140)
    wa_cols = st.columns([1,1,1])
    with wa_cols[0]:
        if st.button("Copy WhatsApp text"):
            copy_to_clipboard_js(wa_text)
    with wa_cols[1]:
        st.download_button(
            "Download .txt",
            data=wa_text.encode("utf-8"),
            file_name="raj_pricebook_whatsapp.txt",
            mime="text/plain"
        )
    with wa_cols[2]:
        st.download_button(
            "Download filtered CSV",
            data=display[final_cols].to_csv(index=False).encode("utf-8"),
            file_name="raj_pricebook_filtered.csv",
            mime="text/csv"
        )

# -------------------- Styled Table (Row highlight + MRP bold) --------------------
st.subheader("Filtered Results")

# For styling, keep it reasonable in size for speed (large datasets can be heavy with styler)
MAX_STYLE_ROWS = 1500
show_df = display[final_cols].copy().head(MAX_STYLE_ROWS)

mrp_show_col = rename_ok.get(col_mrp, col_mrp) if col_mrp else None
seg_show_col = rename_ok.get(col_segment, col_segment) if col_segment else None

def style_rows(row):
    styles = [""] * len(row)

    # Row highlighting by Segment (subtle)
    if seg_show_col and seg_show_col in row.index:
        val = str(row[seg_show_col]).upper()
        if val == "LCV":
            styles = ["background-color: rgba(229,57,53,0.10);"] * len(row)
        elif val == "HCV":
            styles = ["background-color: rgba(255,193,7,0.10);"] * len(row)
        elif val == "CAR":
            styles = ["background-color: rgba(76,175,80,0.10);"] * len(row)

    return styles

styler = show_df.style.apply(style_rows, axis=1)

# Bold MRP column
if mrp_show_col and mrp_show_col in show_df.columns:
    styler = styler.set_properties(subset=[mrp_show_col], **{"font-weight": "800"})

# Tight font for mobile
styler = styler.set_table_styles([
    {"selector": "th", "props": [("font-weight", "800")]},
    {"selector": "td", "props": [("font-size", "13px")]},
])

st.dataframe(styler, use_container_width=True, height=520)

st.caption(f"Showing styled preview: first {min(len(display), MAX_STYLE_ROWS):,} rows (styling large data can be heavy).")