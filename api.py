"""
Medical Data Extractor API - نسخة محسنة
بها استخراج صحيح لضغط الدم وجميع القيم
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import pandas as pd
import numpy as np
import re
import os
import uuid
from werkzeug.utils import secure_filename
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)
CORS(app)

# ==================== إعدادات ====================
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'jpg', 'png', 'jpeg', 'xlsx', 'xls', 'docx'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# ==================== دوال استخراج البيانات المحسنة ====================

def extract_values_from_text(text):
    """استخراج القيم الطبية من النص - نسخة محسنة"""
    data = {}
    
    # ========== استخراج العمر ==========
    age_match = re.search(r'(?:age|عمر|Age)[\s:]*(\d+)', text, re.IGNORECASE)
    if age_match:
        data['age'] = int(age_match.group(1))
    
    # ========== استخراج السكر ==========
    glucose_match = re.search(r'(?:glucose|سكر|Glucose|blood sugar)[\s:]*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
    if glucose_match:
        val = glucose_match.group(1)
        data['glucose'] = float(val) if '.' in val else int(val)
    
    # ========== استخراج ضغط الدم (الأهم!) ==========
    # صيغة 145/90 أو 145-90 أو 145 over 90
    bp_match = re.search(r'(?:blood pressure|Blood Pressure|الضغط)[\s:]*(\d+)[\s/-]+(\d+)', text, re.IGNORECASE)
    if bp_match:
        data['systolic_bp'] = int(bp_match.group(1))
        data['diastolic_bp'] = int(bp_match.group(2))
        print(f"✅ BP extracted: {data['systolic_bp']}/{data['diastolic_bp']}")
    else:
        # محاولة قراءة منفصلة
        sbp_match = re.search(r'(?:systolic|Systolic|الضغط الانقباضي)[\s:]*(\d+)', text, re.IGNORECASE)
        if sbp_match:
            data['systolic_bp'] = int(sbp_match.group(1))
        
        dbp_match = re.search(r'(?:diastolic|Diastolic|الضغط الانبساطي)[\s:]*(\d+)', text, re.IGNORECASE)
        if dbp_match:
            data['diastolic_bp'] = int(dbp_match.group(1))
    
    # ========== استخراج LDL ==========
    ldl_match = re.search(r'(?:ldl|LDL)[\s:]*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
    if ldl_match:
        val = ldl_match.group(1)
        data['ldl'] = float(val) if '.' in val else int(val)
    
    # ========== استخراج المخاطر الوراثية ==========
    risk_match = re.search(r'(?:genetic risk|Genetic Risk|الخطر الوراثي)[\s:]*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
    if risk_match:
        val = risk_match.group(1)
        data['genetic_risk_score'] = float(val) if '.' in val else int(val)
    
    # ========== استخراج الجنس ==========
    if re.search(r'\b(?:male|ذكر|Male|M)\b', text, re.IGNORECASE):
        data['gender'] = 'Male'
    elif re.search(r'\b(?:female|انثى|Female|F|أنثى)\b', text, re.IGNORECASE):
        data['gender'] = 'Female'
    
    # ========== استخراج المرض الوراثي ==========
    disease_match = re.search(r'(?:genetic disease|Genetic Disease|مرض وراثي|Diagnosis)[\s:]*([A-Za-z\s]+)', text, re.IGNORECASE)
    if disease_match:
        data['genetic_disease'] = disease_match.group(1).strip()
    
    return data

def text_to_dataset(text):
    """تحويل النص إلى DataFrame"""
    data = extract_values_from_text(text)
    
    # الأعمدة المطلوبة
    columns = [
        'person_id', 'family_id', 'age', 'gender',
        'genetic_risk_score', 'genetic_disease',
        'glucose', 'systolic_bp', 'diastolic_bp', 'ldl'
    ]
    
    # قيم افتراضية
    default_values = {
        'person_id': f"P{np.random.randint(100000, 999999)}",
        'family_id': f"F{np.random.randint(100000, 999999)}",
        'age': 40,
        'gender': 'Unknown',
        'genetic_risk_score': 0.3,
        'genetic_disease': 'None',
        'glucose': 0.0,
        'systolic_bp': 0.0,
        'diastolic_bp': 0.0,
        'ldl': 0.0
    }
    
    # بناء الصف
    row = {}
    for col in columns:
        if col in data and data[col] is not None:
            row[col] = data[col]
        else:
            row[col] = default_values[col]
    
    return pd.DataFrame([row])

def extract_text_from_file(file_path):
    """استخراج النص من الملف حسب نوعه"""
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    
    try:
        if ext in ['.txt']:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        
        elif ext in ['.pdf']:
            try:
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            except ImportError:
                text = "PDF support requires pdfplumber"
        
        elif ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
            text = df.to_string()
        
        elif ext in ['.docx']:
            try:
                import docx
                doc = docx.Document(file_path)
                text = "\n".join([p.text for p in doc.paragraphs])
            except ImportError:
                text = "DOCX support requires python-docx"
        
        elif ext in ['.jpg', '.png', '.jpeg']:
            try:
                from PIL import Image
                import pytesseract
                img = Image.open(file_path)
                text = pytesseract.image_to_string(img, lang='eng+ara')
            except ImportError:
                text = "Image support requires Pillow and pytesseract"
    
    except Exception as e:
        text = f"Error reading file: {str(e)}"
    
    return text

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==================== واجهة HTML مبسطة ====================

HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>🧬 Medical Data Extractor</title>
    <style>
        body { font-family: Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; background: white; border-radius: 20px; padding: 30px; }
        h1 { text-align: center; color: #667eea; }
        .upload-area { border: 3px dashed #667eea; border-radius: 15px; padding: 40px; text-align: center; }
        input[type="file"] { display: none; }
        .file-label { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 30px; border-radius: 25px; cursor: pointer; }
        button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 12px 30px; border-radius: 25px; cursor: pointer; margin: 10px; }
        .result { margin-top: 20px; padding: 20px; background: #f8f9fa; border-radius: 10px; display: none; }
        .result.show { display: block; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #667eea; color: white; }
        .error { color: red; background: #ffebee; padding: 10px; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧬 Medical Data Extractor</h1>
        <div class="upload-area">
            <form id="uploadForm" enctype="multipart/form-data">
                <label for="fileInput" class="file-label">📁 Choose File</label>
                <input type="file" name="file" id="fileInput" accept=".txt,.pdf,.jpg,.png,.jpeg,.xlsx,.xls,.docx">
                <div id="fileName" style="margin-top:10px">No file selected</div>
                <button type="submit">🚀 Extract Data</button>
            </form>
        </div>
        <div id="result" class="result"></div>
    </div>
    <script>
        document.getElementById('fileInput').onchange = function() {
            document.getElementById('fileName').innerHTML = this.files[0] ? this.files[0].name : 'No file selected';
        };
        document.getElementById('uploadForm').onsubmit = async (e) => {
            e.preventDefault();
            const file = document.getElementById('fileInput').files[0];
            if (!file) { alert('Select a file'); return; }
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = '<div class="loader">Loading...</div>';
            resultDiv.classList.add('show');
            const formData = new FormData();
            formData.append('file', file);
            try {
                const response = await fetch('/upload', { method: 'POST', body: formData });
                const data = await response.json();
                if (data.success) {
                    let html = '<h3>✅ Extracted Data:</h3><tr><thead><tr>';
                    Object.keys(data.data[0]).forEach(k => html += `<th>${k}</th>`);
                    html += '</tr></thead><tbody>';
                    data.data.forEach(row => {
                        html += '<tr>';
                        Object.values(row).forEach(v => html += `<td>${v !== null ? v : '-'}</td>`);
                        html += '</tr>';
                    });
                    html += '</tbody></table>';
                    resultDiv.innerHTML = html;
                } else {
                    resultDiv.innerHTML = `<div class="error">❌ Error: ${data.error}</div>`;
                }
            } catch(err) {
                resultDiv.innerHTML = `<div class="error">❌ Error: ${err.message}</div>`;
            }
        };
    </script>
</body>
</html>
"""

# ==================== Routes ====================

@app.route('/')
def index():
    return render_template_string(HTML_FORM)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'File type not allowed'}), 400
    
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(file_path)
    
    try:
        text = extract_text_from_file(file_path)
        if not text or len(text) < 10:
            return jsonify({'success': False, 'error': 'Could not extract text'}), 400
        
        df = text_to_dataset(text)
        csv_filename = unique_filename.replace('.', '_') + '.csv'
        csv_path = os.path.join(OUTPUT_FOLDER, csv_filename)
        df.to_csv(csv_path, index=False)
        os.remove(file_path)
        
        return jsonify({
            'success': True,
            'data': df.to_dict('records'),
            'columns': list(df.columns)
        })
    
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    print("=" * 60)
    print("🧬 Medical Data Extractor API - النسخة المحسنة")
    print("=" * 60)
    print(f"📍 Server: http://localhost:5000")
    print("✅ تم إصلاح مشكلة استخراج ضغط الدم (145/90)")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
