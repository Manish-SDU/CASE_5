import streamlit as st
import json
import os
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
import google.generativeai as genai

# Configure Gemini API
genai.configure(api_key="AIzaSyA8A6aAqKdUi-HvKXSPNPZV0D8B3EgVZCg")

# Load external templates and styles
def load_template(template_name):
    """Load HTML template from templates folder"""
    template_path = os.path.join('templates', template_name)
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

def load_css():
    """Load CSS from static folder"""
    css_path = os.path.join('static', 'style.css')
    if os.path.exists(css_path):
        with open(css_path, 'r', encoding='utf-8') as f:
            return f"<style>{f.read()}</style>"
    return ""

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def summarize_text(text, max_length=200):
    if len(text) <= max_length:
        return text
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = LsaSummarizer()
        summary = summarizer(parser.document, 3)
        summarized = ' '.join(str(sentence) for sentence in summary)
        if len(summarized) > max_length:
            return summarized[:max_length] + "..."
        return summarized
    except:
        return text[:max_length] + "..."

def resolve_references(text, all_data, current_device):
    """Resolve 'Same as...' references to actual data"""
    if not text or text.strip().lower() in ['', 'not available', 'n/a']:
        return "ℹ️ **Information not available**"
    
    text = text.strip()
    
    # Check for "Same as" references
    if text.lower().startswith("same as"):
        # Extract the referenced device name
        if "except:" in text.lower():
            # Handle "Same as X except: Y" format
            parts = text.split("except:", 1)
            if len(parts) == 2:
                ref_device = parts[0].replace("Same as", "").replace("same as", "").strip()
                exceptions = parts[1].strip()
                
                # Try to find the referenced device data
                for device_name in all_data:
                    if ref_device.lower() in device_name.lower() or device_name.lower() in ref_device.lower():
                        base_data = all_data[device_name].get(current_device, "")
                        if base_data and base_data != text:
                            return f"{base_data}\n\n**Additional notes:** {exceptions}"
                
                return f"**Base reference not found.** Additional info: {exceptions}"
            else:
                return text
        else:
            # Handle simple "Same as X" format
            ref_device = text.replace("Same as", "").replace("same as", "").strip()
            
            # Try to find the referenced device data
            for device_name in all_data:
                if ref_device.lower() in device_name.lower() or device_name.lower() in ref_device.lower():
                    base_data = all_data[device_name].get(current_device, "")
                    if base_data and base_data != text:
                        return base_data
            
            return "ℹ️ **Reference data not found**"
    
    return text

def clean_and_format_text(text, allow_full=False):
    """Clean and format text for better readability"""
    if not text or text.strip().lower() in ['', 'not available', 'n/a']:
        return "ℹ️ **Information not available.**"
    
    # Remove HTML tags like <br>
    import re
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # Remove excessive whitespace and newlines
    text = ' '.join(text.split())
    
    # Ensure text ends with proper punctuation
    text = text.strip()
    if text and not text.endswith(('.', '!', '?', ':')):
        text += '.'
    
    # Don't truncate if allow_full is True
    if allow_full:
        return text
    
    # If text is too long, truncate intelligently but provide option to expand
    if len(text) > 250:
        # Try to find a good breaking point
        if '. ' in text[:250]:
            cutoff = text[:250].rfind('. ') + 1
            truncated = text[:cutoff]
            return truncated
        else:
            return text[:250] + "..."
    
    return text

def extract_key_specs(text, feature_name, all_data=None, current_feature=None):
    """Extract key specifications from text based on feature type"""
    if not text or text.strip().lower() in ['', 'not available', 'n/a']:
        return "ℹ️ **No data found.**", "ℹ️ **No data found.**"
    
    # Resolve references first
    if all_data and current_feature:
        text = resolve_references(text, all_data, current_feature)
    
    # Clean the text
    clean_text = clean_and_format_text(text)
    full_text = clean_and_format_text(text, allow_full=True)
    
    # For hardware specs, try to extract key values
    if "hardware" in feature_name.lower() or "specification" in feature_name.lower():
        key_specs = []
        lines = text.split('\n')
        for line in lines[:5]:  # Take first 5 lines
            line = line.strip('- ').strip()
            if line and len(line) < 100:
                if not line.endswith('.'):
                    line += '.'
                key_specs.append(f"• {line}")
        if key_specs:
            return '\n'.join(key_specs), full_text
    
    return clean_text, full_text

def create_comparison_card(danfoss_info, company_info, company_name):
    """Create a comparison card using template"""
    template = load_template('comparison_template.html')
    if template:
        return template.format(danfoss_info=danfoss_info, company_info=company_info, company=company_name)
    
    # Fallback if template not found
    return f"""
<div class="comparison-grid">
    <div class="comparison-card">
        <h4>🔵 <span>Danfoss</span></h4>
        <div class="comparison-card-content">{danfoss_info}</div>
    </div>
    <div class="comparison-card">
        <h4>🔶 <span>{company_name}</span></h4>
        <div class="comparison-card-content">{company_info}</div>
    </div>
</div>
"""

def create_details_section(summary_text, content):
    """Create expandable details section using template"""
    template = load_template('details_template.html')
    if template:
        return template.format(summary_text=summary_text, content=content)
    
    # Fallback if template not found
    return f"""
<details class="details-section">
    <summary>{summary_text}</summary>
    <div class="details-content">{content}</div>
</details>
"""

def create_comparison_table(danfoss_features, company_features, company_name, all_danfoss_data):
    """Create a structured comparison table"""
    
    comparison_data = []
    
    for feature in danfoss_features:
        danfoss_desc = danfoss_features.get(feature, "")
        company_desc = company_features.get(feature, "")
        
        danfoss_clean, danfoss_full = extract_key_specs(danfoss_desc, feature, all_danfoss_data, feature)
        company_clean, company_full = extract_key_specs(company_desc, feature)
        
        comparison_data.append({
            'feature': feature,
            'danfoss': danfoss_clean,
            'danfoss_full': danfoss_full,
            'company': company_clean,
            'company_full': company_full
        })
    
    return comparison_data

def clean_ai_response(response_text):
    """Clean AI response to remove unnecessary intro text and ensure it starts with analysis"""
    if not response_text:
        return "⚠️ **No AI analysis available**"
    
    # Remove common intro phrases
    intro_phrases = [
        "Of course. Here is a professional analysis",
        "Here is a professional analysis",
        "Based on the information provided",
        "Let me analyze",
        "I'll analyze",
        "Here's a comparison",
        "Here is a comparison",
        "Looking at the comparison",
        "Analyzing the features"
    ]
    
    lines = response_text.split('\n')
    cleaned_lines = []
    skip_first_para = False
    
    for line in lines:
        line_lower = line.lower().strip()
        
        # Skip lines that start with intro phrases
        if any(phrase.lower() in line_lower for phrase in intro_phrases):
            skip_first_para = True
            continue
            
        # If we're skipping and find content, start including
        if skip_first_para and line.strip():
            if any(keyword in line_lower for keyword in ['score', '**score**', 'winner', 'comparison', 'analysis', 'danfoss', 'ke2']):
                skip_first_para = False
                cleaned_lines.append(line)
            continue
        
        if not skip_first_para:
            cleaned_lines.append(line)
    
    # Join the cleaned lines
    cleaned_response = '\n'.join(cleaned_lines).strip()
    
    # Ensure we have a score section
    if "score" not in cleaned_response.lower():
        cleaned_response = f"**SCORE**: Analysis in progress...\n\n{cleaned_response}"
    
    return cleaned_response

def get_comparison(company, device):
    try:
        danfoss_json = 'Compared_Data/Danfoss/all_devices.json'
        # Look for the new AI-extracted features JSON
        company_json_files = [f for f in os.listdir(f'Compared_Data/External/{company}') 
                             if f.endswith('_features.json')]
        
        if not company_json_files:
            return f"❌ **No feature data found for {company}**\n\nPlease run the AI PDF extractor first.", "No AI analysis available due to missing data."
        
        company_json = os.path.join(f'Compared_Data/External/{company}', company_json_files[0])
        
        if not os.path.exists(company_json):
            return f"❌ **Company {company} feature file not found.**", "No AI analysis available due to missing data."
        
        danfoss_data = load_json(danfoss_json)
        company_data = load_json(company_json)
        
        if device not in danfoss_data:
            return f"❌ **Device {device} not found in Danfoss data.**", "No AI analysis available due to missing device data."
        
        danfoss_features = danfoss_data[device]
        
        # Get the first (and typically only) company device
        company_device_name = list(company_data.keys())[0] if company_data else "Unknown Device"
        company_features = list(company_data.values())[0] if company_data else {}
        
        # Create structured comparison
        output = f"### Feature Comparison: Danfoss {device} vs {company} {company_device_name}\n\n"
        
        comparison_data = create_comparison_table(danfoss_features, company_features, company, danfoss_data)
        
        ai_comparisons = []
        
        for idx, comparison in enumerate(comparison_data, 1):
            feature = comparison['feature']
            danfoss_info = comparison['danfoss']
            company_info = comparison['company']
            danfoss_full = comparison['danfoss_full']
            company_full = comparison['company_full']
            
            # Use expandable sections for all features to save space
            output += f"""
<details class="details-section" open>
    <summary><strong>{idx}. {feature}</strong></summary>
    <div class="details-content">
"""
            
            # Create side-by-side comparison using template
            output += create_comparison_card(danfoss_info, company_info, company)
            
            # Add full details if different from summary
            has_danfoss_more = len(danfoss_full) > len(danfoss_info) + 20
            has_company_more = len(company_full) > len(company_info) + 20
            
            if has_danfoss_more or has_company_more:
                if has_danfoss_more:
                    output += f"""
<details style="margin: 5px 0; padding: 8px; border: 1px solid #ddd; border-radius: 5px;">
    <summary style="cursor: pointer; font-weight: bold; color: #333;">🔵 View Full Danfoss Details</summary>
    <div style="margin-top: 10px; padding: 10px; background-color: #fafafa; border-radius: 5px;">
        {danfoss_full}
    </div>
</details>
"""
                
                if has_company_more:
                    output += f"""
<details style="margin: 5px 0; padding: 8px; border: 1px solid #ddd; border-radius: 5px;">
    <summary style="cursor: pointer; font-weight: bold; color: #333;">🔶 View Full {company} Details</summary>
    <div style="margin-top: 10px; padding: 10px; background-color: #fafafa; border-radius: 5px;">
        {company_full}
    </div>
</details>
"""
            
            output += """
    </div>
</details>

"""
            
            # Prepare for AI analysis with full data
            ai_comparisons.append(f"{feature}: Danfoss - {clean_and_format_text(danfoss_full, allow_full=True)} | {company} - {clean_and_format_text(company_full, allow_full=True)}")
        
        # AI Analysis with category-based scoring
        prompt = f"""
        Compare these refrigeration controllers for industrial applications:
        
        Danfoss {device} vs {company} {company_device_name}
        
        Feature Analysis:
        {chr(10).join(ai_comparisons)}
        
        Provide a detailed scoring analysis:
        
        1. **CATEGORY SCORES** (Rate each category out of 10 for both devices):
           - Hardware Specifications: Danfoss [X/10] vs {company} [Y/10]
           - Temperature Control: Danfoss [X/10] vs {company} [Y/10]
           - Safety Features: Danfoss [X/10] vs {company} [Y/10]
           - Installation & Setup: Danfoss [X/10] vs {company} [Y/10]
           - Advanced Features: Danfoss [X/10] vs {company} [Y/10]
           - Build Quality & Reliability: Danfoss [X/10] vs {company} [Y/10]
        
        2. **TOTAL SCORE**: Add up all categories
           - Danfoss: [Total]/60
           - {company}: [Total]/60
        
        3. **WINNER**: State which device scored higher and by how much
        
        4. **KEY DIFFERENCES**: 3-4 bullet points of main differences
        
        5. **STRENGTHS & WEAKNESSES**:
           - Danfoss Strengths: 
           - Danfoss Weaknesses:
           - {company} Strengths:
           - {company} Weaknesses:
        
        6. **RECOMMENDATION**: One clear recommendation for buyers based on the scores
        
        Be objective and base scores on actual feature comparisons. Start immediately with the scores.
        """
        
        try:
            model = genai.GenerativeModel("gemini-pro-latest")
            response = model.generate_content(prompt)
            ai_analysis = clean_ai_response(response.text)
        except Exception as e:
            ai_analysis = f"⚠️ **AI Analysis Error:** {str(e)}\n\nPlease check your internet connection and API key configuration."
        
        return output, ai_analysis
        
    except Exception as e:
        error_msg = f"❌ **Error during comparison:** {str(e)}"
        return error_msg, "No AI analysis available due to error."

st.set_page_config(
    page_title="Refrigeration Controller Comparison",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load external CSS
st.markdown(load_css(), unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>Refrigeration Controller Comparison</h1>
    <p>Compare Danfoss devices with competitors using AI analysis</p>
</div>
""", unsafe_allow_html=True)

companies = [d for d in os.listdir('EXTERNAL_COMPANIES') if os.path.isdir(os.path.join('EXTERNAL_COMPANIES', d))]
if not companies:
    st.error("❌ No external companies found in EXTERNAL_COMPANIES folder.")
    st.stop()

# Selection dropdowns in one row
col1, col2 = st.columns(2)

with col1:
    company = st.selectbox("Competitor Company", companies)

with col2:
    if company:
        try:
            danfoss_json = 'Compared_Data/Danfoss/all_devices.json'
            if not os.path.exists(danfoss_json):
                st.error("❌ Danfoss device data not found.")
                st.stop()
                
            danfoss_data = load_json(danfoss_json)
            devices = list(danfoss_data.keys())
            
            if not devices:
                st.error("❌ No Danfoss devices found in data.")
                st.stop()
                
            device = st.selectbox("Danfoss Device", devices)
        except Exception as e:
            st.error(f"❌ **Application Error:** {str(e)}")
            st.stop()

# Compare button below the dropdowns
if company and 'device' in locals():
    compare_btn = st.button("Compare", type="primary", use_container_width=True)
else:
    compare_btn = False

# Comparison results
if company and 'device' in locals() and compare_btn:
    with st.spinner("Analyzing..."):
        comparison_output, ai_output = get_comparison(company, device)
    
    # Display the detailed comparison first
    st.markdown("---")
    st.markdown(comparison_output, unsafe_allow_html=True)
    
    # Show AI Analysis at the bottom - directly visible
    st.markdown("---")
    st.markdown("### 🤖 AI Analysis & Recommendations")
    st.markdown(ai_output)