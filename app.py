import streamlit as st
import json
import os
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
import google.generativeai as genai

# Configure Gemini API
genai.configure(api_key="AIzaSyA8A6aAqKdUi-HvKXSPNPZV0D8B3EgVZCg")

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
        output = f"# 🔄 Device Comparison\n\n"
        output += f"## 🔵 **Danfoss {device}** vs 🔶 **{company} {company_device_name}**\n\n"
        
        comparison_data = create_comparison_table(danfoss_features, company_features, company, danfoss_data)
        
        # Create organized sections
        output += "---\n\n"
        
        ai_comparisons = []
        
        for idx, comparison in enumerate(comparison_data, 1):
            feature = comparison['feature']
            danfoss_info = comparison['danfoss']
            company_info = comparison['company']
            danfoss_full = comparison['danfoss_full']
            company_full = comparison['company_full']
            
            # Color-coded feature headers
            colors = ['🔴', '🟠', '🟡', '🟢', '🔵', '🟣', '🟤', '⚫']
            color_icon = colors[idx-1] if idx <= len(colors) else '🔘'
            
            output += f"### {color_icon} {idx}. {feature}\n\n"
            
            # Create side-by-side comparison with cards
            output += f"""
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px;">
    <div style="padding: 20px; background: linear-gradient(135deg, #e3f2fd 0%, #f8fafe 100%); border-left: 5px solid #2196f3; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
        <h4 style="color: #1976d2; margin-top: 0; display: flex; align-items: center;">
            🔵 <span style="margin-left: 8px;">Danfoss</span>
        </h4>
        <div style="color: #333; line-height: 1.6;">{danfoss_info}</div>
    </div>
    <div style="padding: 20px; background: linear-gradient(135deg, #fff3e0 0%, #fffaf5 100%); border-left: 5px solid #ff9800; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
        <h4 style="color: #f57c00; margin-top: 0; display: flex; align-items: center;">
            🔶 <span style="margin-left: 8px;">{company}</span>
        </h4>
        <div style="color: #333; line-height: 1.6;">{company_info}</div>
    </div>
</div>
"""
            
            # Add expandable sections using Streamlit components if there's more content
            has_danfoss_more = len(danfoss_full) > len(danfoss_info) + 20
            has_company_more = len(company_full) > len(company_info) + 20
            
            if has_danfoss_more or has_company_more:
                output += f"\n\n**🔍 Detailed Information:**\n\n"
                
                if has_danfoss_more:
                    output += f"""
<details style="margin: 10px 0; padding: 15px; background: #f0f8ff; border-radius: 8px; border: 1px solid #2196f3;">
    <summary style="cursor: pointer; color: #1976d2; font-weight: bold; font-size: 16px;">
        📖 🔵 Complete Danfoss Details → Click to expand
    </summary>
    <div style="margin-top: 15px; padding: 10px; background: white; border-radius: 5px; border-left: 3px solid #2196f3;">
        {danfoss_full}
    </div>
</details>
"""
                
                if has_company_more:
                    output += f"""
<details style="margin: 10px 0; padding: 15px; background: #fff8f0; border-radius: 8px; border: 1px solid #ff9800;">
    <summary style="cursor: pointer; color: #f57c00; font-weight: bold; font-size: 16px;">
        📖 🔶 Complete {company} Details → Click to expand
    </summary>
    <div style="margin-top: 15px; padding: 10px; background: white; border-radius: 5px; border-left: 3px solid #ff9800;">
        {company_full}
    </div>
</details>
"""
            
            output += f"""
<hr style="border: none; height: 3px; background: linear-gradient(to right, #2196f3, #ff9800); margin: 40px 0; border-radius: 3px;">
"""
            
            # Prepare for AI analysis with full data
            ai_comparisons.append(f"{feature}: Danfoss - {clean_and_format_text(danfoss_full, allow_full=True)} | {company} - {clean_and_format_text(company_full, allow_full=True)}")
        
        # AI Analysis with improved prompt
        prompt = f"""
        Compare these refrigeration controllers for industrial applications:
        
        Danfoss {device} vs {company} {company_device_name}
        
        Feature Analysis:
        {chr(10).join(ai_comparisons)}
        
        Provide a direct analysis with:
        1. **SCORE**: X-Y format (1-0 = Danfoss wins, 0-1 = {company} wins, 1-1 = tie)
        2. **WINNER**: State which device is better overall
        3. **KEY DIFFERENCES**: 3-4 bullet points of main differences
        4. **STRENGTHS**: What each device does best
        5. **RECOMMENDATION**: One sentence recommendation for buyers
        
        Be concise and direct. Start immediately with the analysis.
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
    page_title="🔄 Refrigeration Controller Comparison",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .feature-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1rem;
        border-radius: 8px;
        color: white;
        margin: 0.5rem 0;
    }
    
    .comparison-section {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        color: white;
    }
    
    .ai-section {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .stSelectbox > div > div > div {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 20px;
        padding: 0.5rem 2rem;
        font-weight: bold;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        transition: transform 0.2s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>🔄 Refrigeration Controller Comparison Tool</h1>
    <p><strong>Compare Danfoss devices with competitors using AI-powered analysis</strong></p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="feature-card">
    <h3>🚀 This tool provides:</h3>
    <ul>
        <li>📊 <strong>Structured Feature Comparison</strong> - Side-by-side comparison of key features</li>
        <li>🤖 <strong>AI Analysis</strong> - Intelligent evaluation and recommendations</li>
        <li>✅ <strong>Data Validation</strong> - Clear indication when data is missing or incomplete</li>
        <li>🎨 <strong>Interactive Interface</strong> - Expandable details and colorful presentation</li>
    </ul>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# Company selection
st.markdown("""
<div class="comparison-section">
    <h3>🏢 Select Companies and Devices for Comparison</h3>
</div>
""", unsafe_allow_html=True)

companies = [d for d in os.listdir('EXTERNAL_COMPANIES') if os.path.isdir(os.path.join('EXTERNAL_COMPANIES', d))]
if not companies:
    st.error("❌ No external companies found in EXTERNAL_COMPANIES folder.")
    st.stop()

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 🔶 Competitor Company")
    company = st.selectbox("Choose competitor", companies, label_visibility="collapsed")

with col2:
    st.markdown("#### 🔵 Danfoss Device")
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
                
            device = st.selectbox("Choose Danfoss device", devices, label_visibility="collapsed")
        except Exception as e:
            st.error(f"❌ **Application Error:** {str(e)}")
            st.stop()

# Comparison button and results
if company and 'device' in locals():
    st.markdown("---")
    
    # Center the button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 **Start Comparison**", type="primary", use_container_width=True):
            with st.spinner("🔄 Analyzing devices and generating comparison..."):
                comparison_output, ai_output = get_comparison(company, device)
            
            # Display the structured comparison
            st.markdown(comparison_output, unsafe_allow_html=True)
            
            # Display AI Analysis in a colorful expandable section
            st.markdown("""
            <div class="ai-section">
                <h3>🤖 AI Analysis & Recommendations</h3>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("📊 **View AI Analysis**", expanded=True):
                st.markdown(ai_output)
                
            # Add helpful information
            st.markdown("---")
            st.markdown("""
            <div style="background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); padding: 1rem; border-radius: 8px; text-align: center;">
                <p><strong>💡 Tip:</strong> The AI analysis provides professional insights to help with decision-making. Use this alongside the detailed feature comparison above.</p>
            </div>
            """, unsafe_allow_html=True)