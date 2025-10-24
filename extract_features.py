import json
import re
import os
import sys

def extract_features(text, language='en'):
    features = {
        "1. Hardware features and specifications": "",
        "2. Functions": "",
        "3. Core features": "",
        "4. Additional features": "",
        "5. User experience": "",
        "6. Connectivity": "",
        "7. Standards compliance": "",
        "8. Notes": ""
    }

    # Keywords for each feature (add more as needed, support en/es)
    keywords = {
        "1. Hardware features and specifications": ["power supply", "voltage", "relay", "sensor", "transducer", "alimentación", "voltaje", "relé", "sonda", "dimension", "protection", "protección"],
        "2. Functions": ["control", "defrost", "valve", "compressor", "alarm", "temperature", "controlar", "descongelamiento", "válvula", "compresor", "alarma"],
        "3. Core features": ["controller", "regulation", "controlador", "regulación"],
        "4. Additional features": ["remote", "monitoring", "modbus", "remoto", "monitoreo"],
        "5. User experience": ["display", "button", "menu", "pantalla", "botón", "menú"],
        "6. Connectivity": ["modbus", "rs-485", "communication", "comunicación"],
        "7. Standards compliance": ["standard", "compliance", "norma", "cumplimiento"],
        "8. Notes": ["warning", "caution", "note", "advertencia", "precaución", "nota"]
    }

    lines = text.split('\n')
    for line in lines:
        line_lower = line.lower()
        for feature, keys in keywords.items():
            if any(key in line_lower for key in keys):
                features[feature] += line.strip() + ' '
                break

    # Clean up
    for f in features:
        features[f] = re.sub(r'\s+', ' ', features[f]).strip()

    return features

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_features.py <company_name>")
        sys.exit(1)
    
    company = sys.argv[1]
    company_dir = f'Compared_Data/External/{company}'
    
    if not os.path.exists(company_dir):
        print(f"Company directory {company_dir} not found.")
        sys.exit(1)
    
    txt_files = [f for f in os.listdir(company_dir) if f.endswith('.txt')]
    if not txt_files:
        print("No txt file found.")
        sys.exit(1)
    
    txt_file = txt_files[0]
    with open(os.path.join(company_dir, txt_file), 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Detect language roughly
    if 'el' in text.lower() or 'controlador' in text.lower():
        lang = 'es'
    else:
        lang = 'en'
    
    features = extract_features(text, lang)
    
    # Assume device name from txt file
    device_name = txt_file.replace('.txt', '').replace('-', ' ').replace('_', ' ')
    
    data = {device_name: features}
    json_path = os.path.join(company_dir, f'{device_name.replace(" ", "_")}.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print(f"Features extracted for {device_name} and saved to {json_path}.")