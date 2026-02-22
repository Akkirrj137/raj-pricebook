import json
import pandas as pd
import streamlit as st

st.set_page_config(page_title="RAJ GROUP Pricebook", layout="wide")

# ---------- Helpers ----------
@st.cache_data(show_spinner=False)
def load_excel(file, sheet_name: str):
    return pd.read_excel(file, sheet_name=sheet_name)

def safe_str_series(s):
    return s.astype("string").fillna("")

def apply_filters(df, filters: dict):
    out = df
    for col, selected in filters.items():
        if not selected:
            continue
        if col not in out.columns:
            continue
        out = out[safe_str_series(out[col]).isin([str(x) for x in selected])]
    return out

def contains_search(df, cols, q: str):
    if not q.strip():
        return df
    q = q.strip().lower()
    mask = False
    for c in cols:
        if c in df.columns:
            mask = mask | safe_str_series(df[c]).str.lower().str.contains(q, na=False)
    return df[mask]

# ---------- UI ----------
st.title("RAJ GROUP • Pricebook Filter")

with st.sidebar:
    st.header("Data")
    uploaded = st.file_uploader("Upload Excel (.xlsx/.xlsm)", type=["xlsx","xlsm"])

    st.caption("Tip: Upload the latest pricebook anytime. New columns will appear automatically.")

if not uploaded:
    st.info("Upload your Excel file to start.")
    st.stop()

# Sheet selection
xl = pd.ExcelFile(uploaded)
sheet = st.sidebar.selectbox("Sheet", xl.sheet_names, index=0)

df = load_excel(uploaded, sheet)

# Clean columns
df.columns = [str(c).strip() for c in df.columns]

with st.sidebar:
    st.header("View")
    default_filter_cols = [c for c in ["Segment","Vehicle","Model","Category Name","Group"] if c in df.columns]
    filter_cols = st.multiselect(
        "Filter fields (choose which dropdowns you want)",
        options=df.columns.tolist(),
        default=default_filter_cols
    )

    # Visible columns (mobile-friendly)
    default_visible = [c for c in ["Code","Description","MRP","Rate","Disc","GST","Unit","Segment","Vehicle","Model","Category Name"] if c in df.columns]
    visible_cols = st.multiselect(
        "Visible columns (hide/show columns)",
        options=df.columns.tolist(),
        default=default_visible if default_visible else df.columns.tolist()
    )

    st.header("Rename columns (optional)")
    st.caption("Paste JSON mapping, example: {\"MRP\":\"LIST PRICE\",\"Code\":\"PART NO\"}")
    mapping_txt = st.text_area("Column name mapping (JSON)", value="{}", height=110)

    st.header("Search")
    search_q = st.text_input("Search in Code/Description", value="")
    search_cols = [c for c in ["Code","Description"] if c in df.columns]
    if not search_cols:
        search_cols = df.columns.tolist()

# Parse mapping JSON
col_map = {}
try:
    col_map = json.loads(mapping_txt) if mapping_txt.strip() else {}
    if not isinstance(col_map, dict):
        col_map = {}
except Exception:
    st.sidebar.error("Invalid JSON in rename mapping. Using original names.")
    col_map = {}

# Build filters
filters = {}
for col in filter_cols:
    if col not in df.columns:
        continue
    options = sorted(safe_str_series(df[col]).unique().tolist())
    # Remove blanks from options but keep if user wants
    options = [o for o in options if o != ""]
    selected = st.sidebar.multiselect(f"{col}", options=options)
    filters[col] = selected

# Apply filters + search
filtered = apply_filters(df, filters)
filtered = contains_search(filtered, search_cols, search_q)

# Show stats
c1, c2, c3 = st.columns(3)
c1.metric("Rows (total)", f"{len(df):,}")
c2.metric("Rows (filtered)", f"{len(filtered):,}")
c3.metric("Columns", f"{len(df.columns):,}")

# Prepare display
display = filtered.copy()

# Apply rename mapping
rename_ok = {k: v for k, v in col_map.items() if k in display.columns and isinstance(v, str) and v.strip()}
if rename_ok:
    display = display.rename(columns=rename_ok)

# Visible columns (after rename)
final_cols = []
for c in visible_cols:
    if c in rename_ok:
        final_cols.append(rename_ok[c])
    else:
        final_cols.append(c)
final_cols = [c for c in final_cols if c in display.columns]
if not final_cols:
    final_cols = display.columns.tolist()

st.subheader("Filtered Results")
st.dataframe(display[final_cols], use_container_width=True, height=520)

# Download
st.download_button(
    "Download filtered CSV",
    data=display[final_cols].to_csv(index=False).encode("utf-8"),
    file_name="raj_pricebook_filtered.csv",
    mime="text/csv"
)
