from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import random
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ==================== الصفحة الرئيسية ====================
@app.route('/', methods=['GET'])
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Medical Data Extractor</title>
        <style>
            body { font-family: Arial; background: #667eea; padding: 20px; }
            .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 20px; padding: 30px; }
            input, button { padding: 10px; margin: 10px; }
            .result { background: #f0f0f0; padding: 15px; border-radius: 10px; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Medical Data Extractor</h1>
            <p>Upload a file to extract medical data</p>
            <form id="form" enctype="multipart/form-data">
                <input type="file" id="file" name="file">
                <button type="submit">Extract</button>
            </form>
            <div id="result" class="result"></div>
        </div>
        <script>
            document.getElementById('form').onsubmit = async (e) => {
                e.preventDefault();
                const file = document.getElementById('file').files[0];
                if (!file) return;
                const formData = new FormData();
                formData.append('file', file);
                const res = await fetch('/extract', { method: 'POST', body: formData });
                const data = await res.json();
                document.getElementById('result').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
            };
        </script>
    </body>
    </html>
    """

# ==================== فحص الصحة ====================
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'timestamp': str(datetime.now())})

# ==================== استخراج البيانات ====================
@app.route('/extract', methods=['POST'])
def extract():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    try:
        content = file.read()
        text = content.decode('utf-8', errors='ignore')
        
        # استخراج البيانات
        data = {
            'person_id': f"P{random.randint(100000, 999999)}",
            'filename': file.filename,
            'age': None,
            'glucose': None,
            'systolic_bp': None,
            'diastolic_bp': None,
            'ldl': None
        }
        
        # Age
        m = re.search(r'(?:age|عمر|Age)[\s:]*(\d+)', text, re.IGNORECASE)
        if m: data['age'] = int(m.group(1))
        
        # Glucose
        m = re.search(r'(?:glucose|سكر|Glucose|blood sugar)[\s:]*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
        if m: data['glucose'] = float(m.group(1))
        
        # Blood Pressure
        m = re.search(r'(?:blood pressure|الضغط)[\s:]*(\d+)[\s/-]+(\d+)', text, re.IGNORECASE)
        if m:
            data['systolic_bp'] = int(m.group(1))
            data['diastolic_bp'] = int(m.group(2))
        
        # LDL
        m = re.search(r'(?:ldl|LDL)[\s:]*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
        if m: data['ldl'] = float(m.group(1))
        
        return jsonify({'success': True, 'data': data, 'text_preview': text[:500]})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== توقع المخاطر ====================
@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    try:
        content = file.read()
        text = content.decode('utf-8', errors='ignore')
        
        data = {}
        m = re.search(r'(?:age|عمر|Age)[\s:]*(\d+)', text, re.IGNORECASE)
        if m: data['age'] = int(m.group(1))
        
        m = re.search(r'(?:glucose|سكر|Glucose)[\s:]*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
        if m: data['glucose'] = float(m.group(1))
        
        m = re.search(r'(?:blood pressure|الضغط)[\s:]*(\d+)[\s/-]+(\d+)', text, re.IGNORECASE)
        if m:
            data['systolic_bp'] = int(m.group(1))
            data['diastolic_bp'] = int(m.group(2))
        
        # Calculate risk
        risk = 0.0
        if data.get('age') and data['age'] > 60: risk += 0.25
        elif data.get('age') and data['age'] > 40: risk += 0.125
        if data.get('glucose') and data['glucose'] > 200: risk += 0.20
        elif data.get('glucose') and data['glucose'] > 140: risk += 0.10
        if data.get('systolic_bp') and data['systolic_bp'] > 160: risk += 0.15
        elif data.get('systolic_bp') and data['systolic_bp'] > 140: risk += 0.075
        
        risk = min(risk, 0.95)
        
        if risk < 0.3: category = "Low Risk"
        elif risk < 0.6: category = "Medium Risk"
        else: category = "High Risk"
        
        return jsonify({
            'success': True,
            'extracted_data': data,
            'risk_score': round(risk, 3),
            'risk_percentage': f"{risk*100:.1f}%",
            'risk_category': category
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== Swagger ====================
@app.route('/swagger', methods=['GET'])
def swagger():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Swagger UI</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
        <script>
            window.onload = () => {
                SwaggerUIBundle({
                    url: "/swagger.json",
                    dom_id: '#swagger-ui',
                    presets: [SwaggerUIBundle.presets.apis],
                    layout: "BaseLayout"
                });
            };
        </script>
    </body>
    </html>
    """

@app.route('/swagger.json', methods=['GET'])
def swagger_json():
    return {
        "openapi": "3.0.0",
        "info": {"title": "Medical Data Extractor", "version": "1.0.0"},
        "paths": {
            "/health": {"get": {"summary": "Health check"}},
            "/extract": {"post": {"summary": "Extract medical data", "requestBody": {"required": True, "content": {"multipart/form-data": {"schema": {"type": "object", "properties": {"file": {"type": "string", "format": "binary"}}}}}}},
            "/predict": {"post": {"summary": "Predict risk", "requestBody": {"required": True, "content": {"multipart/form-data": {"schema": {"type": "object", "properties": {"file": {"type": "string", "format": "binary"}}}}}}}
        }
    }

if __name__ == '__main__':
    print("=" * 50)
    print("Server running at: http://localhost:5000")
    print("Swagger UI: http://localhost:5000/swagger")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
