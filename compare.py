import json
import os
import sys
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
    # Try AI summarization first
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = LsaSummarizer()
        summary = summarizer(parser.document, 3)
        summarized = ' '.join(str(sentence) for sentence in summary)
        if len(summarized) > max_length:
            return summarized[:max_length] + "..."
        return summarized
    except:
        # Fallback to truncation
        return text[:max_length] + "..."

def compare_features(danfoss_data, company_data, company_name, selected_devices):
    print(f"\n{'='*80}")
    print(f"FEATURE COMPARISON: Danfoss Devices vs {company_name}")
    print(f"{'='*80}\n")
    
    devices_to_compare = selected_devices if selected_devices != ['all'] else list(danfoss_data.keys())
    
    comparisons = []  # To store for AI analysis
    
    for danfoss_device in devices_to_compare:
        if danfoss_device not in danfoss_data:
            print(f"Device {danfoss_device} not found in Danfoss data.")
            continue
        
        danfoss_features = danfoss_data[danfoss_device]
        print(f"Danfoss Device: {danfoss_device}")
        print("-" * 50)
        
        for company_device, company_features in company_data.items():
            print(f"vs {company_name} Device: {company_device}")
            print("-" * 30)
            
            device_comparisons = []
            
            for feature in danfoss_features:
                danfoss_desc = danfoss_features[feature].strip()
                company_desc = company_features.get(feature, "Not available").strip()
                
                danfoss_summary = summarize_text(danfoss_desc)
                company_summary = summarize_text(company_desc)
                
                print(f"\n{feature}:")
                print(f"  Danfoss: {danfoss_summary}")
                print(f"  {company_name}: {company_summary}")
                
                device_comparisons.append(f"{feature}: Danfoss: {danfoss_summary} | {company_name}: {company_summary}")
            
            print("\n" + "="*50)
            comparisons.append(f"Danfoss {danfoss_device} vs {company_name} {company_device}:\n" + "\n".join(device_comparisons))
            break  # Assuming one device per company
    
    # AI Analysis
    if comparisons:
        prompt = f"Compare the following refrigeration controller devices based on their features. Provide a balanced comparison highlighting strengths of both devices. Determine which is better overall for industrial refrigeration applications. If one device is better, suggest areas for improvement for the other. Present the final result in a table format with a score like 1-0 (Danfoss better) or 0-1 ({company_name} better), and include brief explanations.\n\n" + "\n\n".join(comparisons)
        
        try:
            model = genai.GenerativeModel("gemini-pro-latest")
            response = model.generate_content(prompt)
            print("\n" + "="*80)
            print("AI ANALYSIS:")
            print("="*80)
            print(response.text)
        except Exception as e:
            print(f"Error with AI analysis: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python compare.py <company_name>")
        sys.exit(1)
    
    company = sys.argv[1]
    
    danfoss_json = 'Compared_Data/Danfoss/all_devices.json'
    company_json_files = [f for f in os.listdir(f'Compared_Data/External/{company}') if f.endswith('.json') and not f.endswith('_data.json')]
    if not company_json_files:
        print(f"No feature JSON found for {company}.")
        sys.exit(1)
    
    company_json = os.path.join(f'Compared_Data/External/{company}', company_json_files[0])
    
    if not os.path.exists(company_json):
        print(f"Company {company} feature JSON not found.")
        sys.exit(1)
    
    danfoss_data = load_json(danfoss_json)
    company_data = load_json(company_json)
    
    # Prompt user for device selection
    available_devices = list(danfoss_data.keys())
    print("Available Danfoss devices:")
    for i, device in enumerate(available_devices, 1):
        print(f"{i}. {device}")
    choice = input("Enter device number to compare (or 'all' for all devices): ").strip()
    
    if choice.lower() == 'all':
        selected_devices = ['all']
    else:
        try:
            device_index = int(choice) - 1
            if 0 <= device_index < len(available_devices):
                selected_devices = [available_devices[device_index]]
            else:
                print("Invalid number. Comparing all devices.")
                selected_devices = ['all']
        except ValueError:
            print("Invalid input. Comparing all devices.")
            selected_devices = ['all']
    
    compare_features(danfoss_data, company_data, company, selected_devices)