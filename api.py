from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import random
import io
from datetime import datetime

app = Flask(__name__)
CORS(app)

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Medical Data Extractor API</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; background: white; border-radius: 20px; padding: 30px; }
        h1 { color: #667eea; text-align: center; }
        input, button { padding: 10px; margin: 10px; }
        .result { background: #f0f0f0; padding: 15px; border-radius: 10px; margin-top: 20px; white-space: pre-wrap; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧬 Medical Data Extractor API</h1>
        <p>Upload any file (image, PDF, Excel, Word, TXT) to extract medical data</p>
        <form id="uploadForm" enctype="multipart/form-data">
            <input type="file" id="fileInput" name="file" accept=".txt,.pdf,.jpg,.png,.jpeg,.xlsx,.xls,.docx">
            <button type="submit">Extract Data</button>
            <button type="button" onclick="fetch('/predict', {method:'POST', body:new FormData(document.getElementById('uploadForm'))}).then(r=>r.json()).then(d=>document.getElementById('result').innerHTML=JSON.stringify(d,null,2))">Predict Risk</button>
        </form>
        <div id="result" class="result">Results will appear here...</div>
    </div>
    <script>
        document.getElementById('uploadForm').onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const response = await fetch('/extract', { method: 'POST', body: formData });
            const data = await response.json();
            document.getElementById('result').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
        };
    </script>
</body>
</html>
"""

def extract_text_from_file(content, filename):
    ext = filename.split('.')[-1].lower()
    text = ""
    
    try:
        if ext == 'txt':
            text = content.decode('utf-8', errors='ignore')
        
        elif ext == 'pdf':
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t: text += t + "\n"
            except:
                text = "PDF extraction failed"
        
        elif ext in ['xlsx', 'xls']:
            try:
                import openpyxl
                from io import BytesIO
                wb = openpyxl.load_workbook(BytesIO(content))
                sheet = wb.active
                for row in sheet.iter_rows(values_only=True):
                    text += " | ".join([str(cell) for cell in row if cell]) + "\n"
            except:
                text = "Excel extraction failed"
        
        elif ext == 'docx':
            try:
                import docx
                doc = docx.Document(io.BytesIO(content))
                text = "\n".join([p.text for p in doc.paragraphs])
            except:
                text = "Word extraction failed"
        
        elif ext in ['jpg', 'jpeg', 'png', 'bmp', 'gif']:
            try:
                from PIL import Image
                import pytesseract
                img = Image.open(io.BytesIO(content))
                text = pytesseract.image_to_string(img, lang='eng')
            except:
                text = "OCR extraction failed"
        
        else:
            text = content.decode('utf-8', errors='ignore')
    
    except Exception as e:
        text = f"Error: {str(e)}"
    
    return text[:5000] if text else ""

def extract_medical_data(text):
    data = {
        'age': None, 'glucose': None, 'systolic_bp': None, 'diastolic_bp': None,
        'ldl': None, 'genetic_risk_score': None, 'gender': None, 'genetic_disease': None
    }
    
    if not text: return data
    
    m = re.search(r'(?:age|عمر|Age)[\s:]*(\d+)', text, re.IGNORECASE)
    if m: data['age'] = int(m.group(1))
    
    m = re.search(r'(?:glucose|سكر|Glucose|blood sugar)[\s:]*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
    if m: data['glucose'] = float(m.group(1))
    
    m = re.search(r'(?:blood pressure|الضغط)[\s:]*(\d+)[\s/-]+(\d+)', text, re.IGNORECASE)
    if m:
        data['systolic_bp'] = int(m.group(1))
        data['diastolic_bp'] = int(m.group(2))
    
    m = re.search(r'(?:ldl|LDL)[\s:]*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
    if m: data['ldl'] = float(m.group(1))
    
    m = re.search(r'(?:genetic risk|الخطر الوراثي)[\s:]*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
    if m: data['genetic_risk_score'] = float(m.group(1))
    
    if re.search(r'male|ذكر|Male', text, re.IGNORECASE): data['gender'] = 'Male'
    elif re.search(r'female|انثى|Female', text, re.IGNORECASE): data['gender'] = 'Female'
    
    m = re.search(r'(?:genetic disease|مرض وراثي|Diagnosis)[\s:]*([A-Za-z\s]+)', text, re.IGNORECASE)
    if m: data['genetic_disease'] = m.group(1).strip()
    
    return data

def calculate_risk(data):
    risk = 0.0
    if data.get('age') and data['age'] > 60: risk += 0.25
    elif data.get('age') and data['age'] > 40: risk += 0.125
    if data.get('glucose') and data['glucose'] > 200: risk += 0.20
    elif data.get('glucose') and data['glucose'] > 140: risk += 0.10
    if data.get('systolic_bp') and data['systolic_bp'] > 160: risk += 0.15
    elif data.get('systolic_bp') and data['systolic_bp'] > 140: risk += 0.075
    if data.get('ldl') and data['ldl'] > 190: risk += 0.15
    elif data.get('ldl') and data['ldl'] > 130: risk += 0.075
    if data.get('genetic_risk_score'): risk += data['genetic_risk_score'] * 0.15
    risk = max(0, min(risk, 0.95))
    
    if risk < 0.3: cat, rec = "Low Risk 🟢", ["Annual checkup", "Healthy diet"]
    elif risk < 0.6: cat, rec = "Medium Risk 🟡", ["Monitor health", "Genetic counseling"]
    else: cat, rec = "High Risk 🔴", ["Consult specialist", "Genetic testing"]
    
    return {'score': round(risk, 3), 'percentage': f"{risk*100:.1f}%", 'category': cat, 'recommendations': rec}

@app.route('/', methods=['GET'])
def home():
    return HTML_PAGE

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/extract', methods=['POST'])
def extract():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    try:
        content = file.read()
        text = extract_text_from_file(content, file.filename)
        data = extract_medical_data(text)
        data['person_id'] = f"P{random.randint(100000, 999999)}"
        
        return jsonify({'success': True, 'filename': file.filename, 'extracted_data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    try:
        content = file.read()
        text = extract_text_from_file(content, file.filename)
        data = extract_medical_data(text)
        risk = calculate_risk(data)
        data['person_id'] = f"P{random.randint(100000, 999999)}"
        
        return jsonify({'success': True, 'filename': file.filename, 'extracted_data': data, 'risk_assessment': risk})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
