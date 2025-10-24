# Refrigeration Controller Comparison Tool

## Setup

1. Install dependencies: `pip install pdfplumber sumy numpy google-generativeai`
2. Set Gemini API key in `compare.py` (line 10)

## Usage

1. Place PDF manuals in `EXTERNAL_COMPANIES/CompanyName/` folders
2. Extract text: `python convert_to_json.py`
3. Parse features: `python extract_features.py CompanyName`
4. Compare: `python compare.py CompanyName`

Select device by number, view summarized comparison, and AI analysis.
