# RAJ GROUP Pricebook (Streamlit)

This app lets you:
- Upload your Excel pricebook anytime (works even if new columns are added)
- Choose which **filter dropdowns** to show (e.g., Segment/Vehicle/Model/Category/Group)
- Hide/show columns for a **mobile-friendly view**
- Optional column renaming using a JSON mapping
- Search in Code/Description
- Download filtered results as CSV

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Community Cloud
1. Create a GitHub repo (public): e.g. `pricebook-app`
2. Upload these files: `app.py`, `requirements.txt`, `README.md`
3. Go to Streamlit Community Cloud → **New app**
4. Fill:
   - Repository: `yourusername/pricebook-app`
   - Branch: `main` (or `master`)
   - Main file path: `app.py`
5. Deploy

## Notes
- Keep the Excel file private by NOT committing it to GitHub. Use the upload box inside the app.
