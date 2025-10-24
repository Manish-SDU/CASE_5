# Refrigeration Controller Comparison Tool

## Setup

1. Install dependencies: `pip install pdfplumber sumy numpy google-generativeai streamlit`
2. Set Gemini API key in `compare.py` and `app.py` (line 10)

## Usage

### Terminal Version

1. Place PDF manuals in `EXTERNAL_COMPANIES/CompanyName/` folders
2. Extract text: `python convert_to_json.py`
3. Parse features: `python extract_features.py CompanyName`
4. Compare: `python compare.py CompanyName`

### Web App Version

Run `streamlit run app.py` and open the browser to use the UI.
