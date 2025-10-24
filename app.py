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

def get_comparison(company, device):
    danfoss_json = 'Compared_Data/Danfoss/all_devices.json'
    company_json_files = [f for f in os.listdir(f'Compared_Data/External/{company}') if f.endswith('.json') and not f.endswith('_data.json')]
    if not company_json_files:
        return "No feature JSON found for " + company
    
    company_json = os.path.join(f'Compared_Data/External/{company}', company_json_files[0])
    
    if not os.path.exists(company_json):
        return f"Company {company} feature JSON not found."
    
    danfoss_data = load_json(danfoss_json)
    company_data = load_json(company_json)
    
    if device not in danfoss_data:
        return f"Device {device} not found in Danfoss data."
    
    danfoss_features = danfoss_data[device]
    output = f"## Danfoss Device: {device}\n"
    output += f"### vs {company} Device\n"
    
    comparisons = []
    
    for company_device, company_features in company_data.items():
        for feature in danfoss_features:
            danfoss_desc = danfoss_features[feature].strip()
            company_desc = company_features.get(feature, "Not available").strip()
            
            danfoss_summary = summarize_text(danfoss_desc)
            company_summary = summarize_text(company_desc)
            
            output += f"**{feature}:**\n"
            output += f"<span style='color:red'>**Danfoss:** {danfoss_summary}</span>\n"
            output += f"**{company}:** {company_summary}\n\n"
            
            comparisons.append(f"{feature}: Danfoss: {danfoss_summary} | {company}: {company_summary}")
        
        break  # Assuming one device per company
    
    # AI Analysis
    prompt = f"Compare the following refrigeration controller devices based on their features. Provide a balanced comparison highlighting strengths of both devices. Determine which is better overall for industrial refrigeration applications. If one device is better, suggest areas for improvement for the other. Present the final result in a table format with a score like 1-0 (Danfoss better) or 0-1 ({company} better), and include brief explanations.\n\n" + "\n\n".join(comparisons)
    
    try:
        model = genai.GenerativeModel("gemini-pro-latest")
        response = model.generate_content(prompt)
        ai_analysis = response.text
    except Exception as e:
        ai_analysis = f"Error with AI analysis: {e}"
    
    return output, ai_analysis

st.title("Refrigeration Controller Comparison Tool")
st.markdown("Compare Danfoss devices with competitors using AI analysis.")

companies = [d for d in os.listdir('EXTERNAL_COMPANIES') if os.path.isdir(os.path.join('EXTERNAL_COMPANIES', d))]
company = st.selectbox("Select Company", companies)

if company:
    danfoss_json = 'Compared_Data/Danfoss/all_devices.json'
    danfoss_data = load_json(danfoss_json)
    devices = list(danfoss_data.keys())
    device = st.selectbox("Select Danfoss Device", devices)
    
    if st.button("Compare"):
        with st.spinner("Running comparison..."):
            comparison_output, ai_output = get_comparison(company, device)
        
        st.markdown(comparison_output, unsafe_allow_html=True)
        st.markdown("## AI Analysis")
        st.markdown(ai_output)