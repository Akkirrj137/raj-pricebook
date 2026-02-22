import json
import pandas as pd
import streamlit as st

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

# -------------------- Styling --------------------
st.markdown(
    """
    <style>
      .raj-title { font-size: 40px; font-weight: 800; letter-spacing: 0.5px; margin-bottom: 0.25rem; }
      .raj-sub { opacity: 0.8; margin-top: 0; }
      div.stButton > button {
        border-radius: 14px !important;
        font-weight: 700 !important;
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
      /* Make sidebar a bit tighter on mobile */
      @media (max-width: 768px) {
        .raj-title { font-size: 30px; }
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
    st.markdown('<div class="raj-title">RAJ GROUP • Pricebook Filter</div>', unsafe_allow_html=True)
    st.info("Upload your Excel file to start.")
    st.stop()

xl = pd.ExcelFile(uploaded)

with st.sidebar:
    sheet = st.selectbox("Sheet", xl.sheet_names, index=0)

df = read_sheet(uploaded, sheet)
df.columns = [str(c).strip() for c in df.columns]

# Auto-detect common columns (case/space safe)
col_segment = find_col(df, ["SEGMENT", "Segment"])
col_code = find_col(df, ["CODE", "Code", "PART NO", "PARTNO", "PART_NO"])
col_desc = find_col(df, ["DESCRIPTION", "Description", "ITEM", "ITEM NAME"])
col_mrp = find_col(df, ["MRP", "LIST", "LIST PRICE", "PRICE"])
col_brand = find_col(df, ["VEHICLE BRAND", "BRAND", "Vehicle Brand"])
col_vehicle = find_col(df, ["VEHICLE", "Vehicle"])
col_model = find_col(df, ["MODEL", "Model"])
col_category = find_col(df, ["CATEGORY NAME", "CATEGORY", "Category Name", "Category"])
col_group = find_col(df, ["GROUP", "Group"])

# -------------------- Header --------------------
st.markdown('<div class="raj-title">RAJ GROUP • Pricebook Filter</div>', unsafe_allow_html=True)
st.markdown('<p class="raj-sub">One-tap Segment buttons + mobile clean view + advanced filters</p>', unsafe_allow_html=True)

# -------------------- Top Controls Row --------------------
top_left, top_mid, top_right = st.columns([2.2, 2.2, 1.2])

# Search (top)
with top_left:
    search_cols = [c for c in [col_code, col_desc] if c]
    if not search_cols:
        search_cols = df.columns.tolist()
    q = st.text_input("Search (Code/Description)", value="", placeholder="Type part no / description...")

# Mobile mode
with top_right:
    mobile_mode = st.toggle("📱 Mobile mode", value=True)

# Segment buttons
if "segment_quick" not in st.session_state:
    st.session_state.segment_quick = None  # None = no quick filter

def set_segment(val):
    st.session_state.segment_quick = val

if col_segment:
    # Options (prefer standard order)
    seg_vals = sorted([x for x in safe_str_series(df[col_segment]).unique().tolist() if x != ""])
    prefer = ["CAR", "HCV", "LCV"]
    ordered = [p for p in prefer if p in seg_vals] + [x for x in seg_vals if x not in prefer]

    with top_mid:
        st.write("Quick Segment")
        b1, b2, b3, b4 = st.columns([1, 1, 1, 1])
        active = st.session_state.segment_quick

        # Button style: active red, else neutral
        def btn(label, container):
            klass = "redbtn" if active == label else "neutralbtn"
            with container:
                st.markdown(f'<div class="{klass}">', unsafe_allow_html=True)
                if st.button(label, use_container_width=True):
                    set_segment(label)
                st.markdown("</div>", unsafe_allow_html=True)

        # Show 3 buttons if available
        shown = ordered[:3]
        # If less than 3 segments exist, still show what exists
        if len(shown) >= 1: btn(shown[0], b1)
        if len(shown) >= 2: btn(shown[1], b2)
        if len(shown) >= 3: btn(shown[2], b3)

        # Clear button
        with b4:
            st.markdown('<div class="neutralbtn">', unsafe_allow_html=True)
            if st.button("Clear", use_container_width=True):
                set_segment(None)
            st.markdown("</div>", unsafe_allow_html=True)

# -------------------- Sidebar: Advanced Filters + Columns --------------------
with st.sidebar:
    st.header("Filters")

    # Default filter fields (if exist)
    default_filters = [c for c in [col_segment, col_vehicle, col_model, col_brand, col_category, col_group] if c]
    filter_cols = st.multiselect(
        "Filter fields (choose dropdowns)",
        options=df.columns.tolist(),
        default=default_filters
    )

    # Build multiselect filters
    filters = {}
    for col in filter_cols:
        if col not in df.columns:
            continue
        options = [x for x in safe_str_series(df[col]).unique().tolist() if x != ""]
        options = sorted(options)
        filters[col] = st.multiselect(col, options=options)

    st.header("Columns")
    # Default visible columns (mobile friendly)
    default_visible = [c for c in [col_code, col_desc, col_mrp, col_segment, col_vehicle, col_brand, col_model, col_category] if c]
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

# Quick segment button filter (top)
if col_segment and st.session_state.segment_quick:
    filtered = filtered[safe_str_series(filtered[col_segment]) == st.session_state.segment_quick]

# Sidebar multiselect filters
filtered = apply_multiselect_filters(filtered, filters)

# Search
filtered = apply_contains_search(filtered, search_cols, q)

# -------------------- KPIs --------------------
c1, c2, c3 = st.columns(3)
c1.metric("Rows (total)", f"{len(df):,}")
c2.metric("Rows (filtered)", f"{len(filtered):,}")
c3.metric("Columns", f"{len(df.columns):,}")

# -------------------- Prepare Display --------------------
display = filtered.copy()

# Apply rename mapping
rename_ok = {k: v for k, v in col_map.items() if k in display.columns and isinstance(v, str) and v.strip()}
if rename_ok:
    display = display.rename(columns=rename_ok)

# Visible columns after rename
final_cols = []
for c in visible_cols:
    final_cols.append(rename_ok.get(c, c))
final_cols = [c for c in final_cols if c in display.columns]
if not final_cols:
    final_cols = display.columns.tolist()

# Mobile compact suggestion: keep fewer columns
if mobile_mode:
    # Prioritize key columns if they exist
    priority = [rename_ok.get(x, x) for x in [col_code, col_desc, col_mrp, col_segment, col_vehicle, col_brand, col_model] if x]
    pr = [c for c in priority if c in display.columns]
    if pr:
        final_cols = pr

st.subheader("Filtered Results")
height = 480 if mobile_mode else 620
st.dataframe(display[final_cols], use_container_width=True, height=height)

st.download_button(
    "Download filtered CSV",
    data=display[final_cols].to_csv(index=False).encode("utf-8"),
    file_name="raj_pricebook_filtered.csv",
    mime="text/csv"
)