import json
import os
import re
import pdfplumber

def extract_text_from_pdf(pdf_path):
    text = ''
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + '\n'
    except Exception as e:
        print(f"Error extracting {pdf_path}: {e}")
    return text

def parse_extracted_data(content):
    data = {}
    current_device = None
    current_feature = None

    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('## '):
            current_device = line[3:]
            data[current_device] = {}
        elif line.startswith('### '):
            current_feature = line[4:]
            data[current_device][current_feature] = ""
        elif current_device and current_feature and line:
            data[current_device][current_feature] += line + '\n'

    # Clean up trailing newlines
    for device in data:
        for feature in data[device]:
            data[device][feature] = data[device][feature].strip()
    return data

# Paths
danfoss_data_path = 'DANFOSS_DEVICES_DATA/extracted_danfoss_data.txt'
external_companies_dir = 'EXTERNAL_COMPANIES'
compared_data_dir = 'Compared_Data'

# Create Compared_Data
os.makedirs(compared_data_dir, exist_ok=True)

# Process Danfoss
if os.path.exists(danfoss_data_path):
    with open(danfoss_data_path, 'r', encoding='utf-8') as f:
        content = f.read()
    danfoss_data = parse_extracted_data(content)

    danfoss_dir = os.path.join(compared_data_dir, 'Danfoss')
    os.makedirs(danfoss_dir, exist_ok=True)

    # Save overall JSON
    with open(os.path.join(danfoss_dir, 'all_devices.json'), 'w', encoding='utf-8') as f:
        json.dump(danfoss_data, f, indent=4)

    # Save separate JSON per device
    for device, features in danfoss_data.items():
        device_dir = os.path.join(danfoss_dir, device.replace(' ', '_'))
        os.makedirs(device_dir, exist_ok=True)
        with open(os.path.join(device_dir, f'{device.replace(" ", "_")}.json'), 'w', encoding='utf-8') as f:
            json.dump({device: features}, f, indent=4)
        # Also save the original txt sections
        with open(os.path.join(device_dir, f'{device.replace(" ", "_")}_data.txt'), 'w', encoding='utf-8') as f:
            for feature, desc in features.items():
                f.write(f'### {feature}\n{desc}\n\n')
else:
    print("Danfoss data file not found.")

# Process External Companies
external_dir = os.path.join(compared_data_dir, 'External')
os.makedirs(external_dir, exist_ok=True)

if os.path.exists(external_companies_dir):
    for company in os.listdir(external_companies_dir):
        company_path = os.path.join(external_companies_dir, company)
        if os.path.isdir(company_path):
            company_data = {}
            company_json_dir = os.path.join(external_dir, company)
            os.makedirs(company_json_dir, exist_ok=True)
            
            for file in os.listdir(company_path):
                if file.endswith('.pdf'):
                    pdf_path = os.path.join(company_path, file)
                    text = extract_text_from_pdf(pdf_path)
                    txt_file = file.replace('.pdf', '.txt')
                    txt_path = os.path.join(company_json_dir, txt_file)
                    with open(txt_path, 'w', encoding='utf-8') as f:
                        f.write(text)
                    # For now, save text; parsing features would require manual or advanced NLP
                    company_data[file.replace('.pdf', '')] = text
            
            # Save company JSON with extracted texts
            with open(os.path.join(company_json_dir, f'{company}_data.json'), 'w', encoding='utf-8') as f:
                json.dump(company_data, f, indent=4)

print("Data organized in Compared_Data folder.")