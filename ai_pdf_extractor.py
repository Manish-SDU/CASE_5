import json
import os
import re
import pdfplumber
import google.generativeai as genai
from pathlib import Path

# Configure Gemini API
genai.configure(api_key="AIzaSyA8A6aAqKdUi-HvKXSPNPZV0D8B3EgVZCg")

def extract_text_from_pdf(pdf_path):
    """Extract clean text from PDF using pdfplumber"""
    text = ''
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + '\n'
    except Exception as e:
        print(f"Error extracting {pdf_path}: {e}")
        return None
    return text

def clean_extracted_text(text):
    """Clean and preprocess extracted text"""
    if not text:
        return ""
    
    # Remove excessive whitespace and normalize
    text = re.sub(r'\s+', ' ', text)
    
    # Remove common PDF artifacts
    text = re.sub(r'\.{3,}', '', text)  # Remove excessive dots
    text = re.sub(r'-{3,}', '', text)   # Remove excessive dashes
    
    # Fix common word breaks
    text = re.sub(r'(\w)-\s+(\w)', r'\1\2', text)  # Fix hyphenated words
    
    return text.strip()

def extract_features_with_ai(text, device_type="refrigeration controller"):
    """Use Gemini AI to extract structured features from technical text"""
    
    if not text or len(text.strip()) < 100:
        return create_empty_features_dict()
    
    prompt = f"""
    You are a technical documentation analyst specializing in {device_type} specifications.
    
    Extract and organize the following information from this technical document into exactly these 8 categories:
    
    1. Hardware features and specifications
    2. Functions  
    3. Core features
    4. Additional features
    5. User experience
    6. Connectivity
    7. Standards compliance
    8. Notes
    
    Technical Document:
    {text[:8000]}  # Limit text to avoid token limits
    
    For each category, provide:
    - Clear, concise bullet points
    - Specific technical values (voltages, temperatures, dimensions, etc.)
    - Remove any marketing language or redundant information
    - If no relevant information is found for a category, write "Information not available"
    
    Format your response as JSON with the exact category names as keys.
    
    Example output format:
    {{
        "1. Hardware features and specifications": "• Power supply: 100-240V AC\\n• Operating temperature: -10 to +50°C\\n• Protection: IP65",
        "2. Functions": "• Temperature control\\n• Defrost management\\n• Alarm handling",
        ...
    }}
    
    Important: Only include factual technical information. Exclude installation instructions, warranty information, and marketing content.
    """
    
    try:
        model = genai.GenerativeModel("gemini-pro-latest")
        response = model.generate_content(prompt)
        
        # Try to parse JSON response
        response_text = response.text.strip()
        
        # Clean up response if it has markdown formatting
        if response_text.startswith('```json'):
            response_text = response_text.replace('```json', '').replace('```', '').strip()
        elif response_text.startswith('```'):
            response_text = response_text.replace('```', '').strip()
        
        try:
            features = json.loads(response_text)
            
            # Validate that we have the expected structure
            expected_keys = [
                "1. Hardware features and specifications",
                "2. Functions",
                "3. Core features", 
                "4. Additional features",
                "5. User experience",
                "6. Connectivity",
                "7. Standards compliance",
                "8. Notes"
            ]
            
            # Ensure all expected keys exist
            for key in expected_keys:
                if key not in features:
                    features[key] = "Information not available"
            
            return features
            
        except json.JSONDecodeError:
            print("AI response was not valid JSON, using fallback extraction")
            return extract_features_fallback(response_text)
            
    except Exception as e:
        print(f"AI extraction failed: {e}")
        return extract_features_fallback(text)

def extract_features_fallback(text):
    """Fallback feature extraction using keyword matching"""
    features = create_empty_features_dict()
    
    # Enhanced keyword mapping
    keyword_patterns = {
        "1. Hardware features and specifications": [
            r'power supply.*?(?:\n|voltage|current)',
            r'voltage.*?(?:\n|power|supply)',
            r'temperature.*?range.*?(?:\n|°C|°F)',
            r'dimensions.*?(?:\n|mm|cm|inches)',
            r'protection.*?(?:\n|IP\d+)',
            r'relay.*?(?:\n|SPDT|SPST)',
            r'input.*?(?:\n|analog|digital)'
        ],
        "2. Functions": [
            r'control.*?(?:\n|temperature|defrost)',
            r'defrost.*?(?:\n|cycle|timer)',
            r'alarm.*?(?:\n|management|handling)',
            r'monitoring.*?(?:\n|remote|local)',
            r'valve.*?(?:\n|control|operation)'
        ],
        "3. Core features": [
            r'controller.*?(?:\n|temperature|refrigeration)',
            r'regulation.*?(?:\n|temperature|pressure)',
            r'wizard.*?(?:\n|setup|configuration)'
        ],
        "4. Additional features": [
            r'modbus.*?(?:\n|communication|integration)',
            r'remote.*?(?:\n|monitoring|access)',
            r'datalogger.*?(?:\n|option|feature)',
            r'cloud.*?(?:\n|connectivity|service)'
        ],
        "5. User experience": [
            r'display.*?(?:\n|menu|interface)',
            r'button.*?(?:\n|navigation|control)',
            r'menu.*?(?:\n|intuitive|clear)',
            r'keypad.*?(?:\n|navigation|settings)'
        ],
        "6. Connectivity": [
            r'modbus.*?(?:\n|RS-485|communication)',
            r'communication.*?(?:\n|protocol|interface)',
            r'ethernet.*?(?:\n|TCP|IP)',
            r'wireless.*?(?:\n|WiFi|connectivity)'
        ],
        "7. Standards compliance": [
            r'IP\d+.*?(?:\n|protection|rating)',
            r'EN\d+.*?(?:\n|standard|compliance)',
            r'standard.*?(?:\n|compliance|certification)',
            r'certification.*?(?:\n|approval|rating)'
        ],
        "8. Notes": [
            r'warning.*?(?:\n|caution|important)',
            r'caution.*?(?:\n|warning|note)',
            r'important.*?(?:\n|note|warning)',
            r'note.*?(?:\n|important|warning)'
        ]
    }
    
    # Extract based on patterns
    for category, patterns in keyword_patterns.items():
        extracted_info = []
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                info = match.group(0).strip()
                if len(info) > 10 and len(info) < 200:  # Reasonable length
                    extracted_info.append(f"• {info}")
        
        if extracted_info:
            features[category] = '\n'.join(extracted_info[:5])  # Limit to 5 items
    
    return features

def create_empty_features_dict():
    """Create empty features dictionary with standard categories"""
    return {
        "1. Hardware features and specifications": "Information not available",
        "2. Functions": "Information not available", 
        "3. Core features": "Information not available",
        "4. Additional features": "Information not available",
        "5. User experience": "Information not available",
        "6. Connectivity": "Information not available",
        "7. Standards compliance": "Information not available",
        "8. Notes": "Information not available"
    }

def process_company_pdfs(company_dir, output_dir):
    """Process all PDFs for a company using AI extraction"""
    
    if not os.path.exists(company_dir):
        print(f"Company directory {company_dir} not found.")
        return False
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Find PDF files
    pdf_files = [f for f in os.listdir(company_dir) if f.endswith('.pdf')]
    
    if not pdf_files:
        print(f"No PDF files found in {company_dir}")
        return False
    
    company_data = {}
    
    for pdf_file in pdf_files:
        print(f"Processing {pdf_file}...")
        
        pdf_path = os.path.join(company_dir, pdf_file)
        
        # Extract text from PDF
        raw_text = extract_text_from_pdf(pdf_path)
        if not raw_text:
            print(f"Failed to extract text from {pdf_file}")
            continue
        
        # Clean the text
        cleaned_text = clean_extracted_text(raw_text)
        
        # Save cleaned text for reference
        txt_filename = pdf_file.replace('.pdf', '.txt')
        txt_path = os.path.join(output_dir, txt_filename)
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_text)
        
        # Extract features using AI
        device_name = pdf_file.replace('.pdf', '').replace('-', ' ').replace('_', ' ')
        print(f"Extracting features for {device_name} using AI...")
        
        features = extract_features_with_ai(cleaned_text)
        
        # Store in company data
        company_data[device_name] = features
        
        print(f"✅ Completed {device_name}")
    
    # Save combined JSON
    json_filename = f"{os.path.basename(company_dir)}_features.json"
    json_path = os.path.join(output_dir, json_filename)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(company_data, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Saved features to {json_path}")
    return True

def main():
    """Main function to process all external companies"""
    
    external_companies_dir = 'EXTERNAL_COMPANIES'
    compared_data_dir = 'Compared_Data/External'
    
    # Create output directory
    os.makedirs(compared_data_dir, exist_ok=True)
    
    if not os.path.exists(external_companies_dir):
        print(f"External companies directory {external_companies_dir} not found.")
        return
    
    # Process each company
    companies = [d for d in os.listdir(external_companies_dir) 
                if os.path.isdir(os.path.join(external_companies_dir, d))]
    
    if not companies:
        print("No companies found.")
        return
    
    print(f"Found {len(companies)} companies: {companies}")
    
    for company in companies:
        print(f"\n🔄 Processing {company}...")
        
        company_input_dir = os.path.join(external_companies_dir, company)
        company_output_dir = os.path.join(compared_data_dir, company)
        
        success = process_company_pdfs(company_input_dir, company_output_dir)
        
        if success:
            print(f"✅ {company} processing completed")
        else:
            print(f"❌ {company} processing failed")
    
    print(f"\n🎉 All processing completed! Check {compared_data_dir} for results.")

if __name__ == "__main__":
    main()