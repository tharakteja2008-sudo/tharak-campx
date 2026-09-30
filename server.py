"""
CampX Full Dashboard - Backend Server
Complete CampX clone with Live Attendance, Events, Clubs, Notices, and more.
Author: Antigravity for P THARAK TEJA (25BFA32091)
"""

import os
import sys
import json
import time
import hmac
import hashlib
import base64
from datetime import datetime
from flask import Flask, jsonify, send_file, request
import requests

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

app = Flask(__name__)

# ─── Configuration ───────────────────────────────────────────
CAMPX_BASE_URL = "https://svce.campx.in"
CAMPX_API_URL  = "https://api.campx.in"
CAMPX_USERNAME = "25BFA32091"
CAMPX_PASSWORD = "25BFA32091"
CAMPX_TENANT   = "svce"
CAMPX_INSTITUTION = "svce"
CLIENT_ID      = "efa4ddab-3031-4370-ad77-46557d4f0890"
CLIENT_SECRET  = "9KubLTSkNJMStC+Q3MhXUHPCfgbkkEb4ssyib0jfaMs="
MEDIA_BASE_URL = "https://media.campx.in"

DASHBOARD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "campx_dashboard.html")

# ─── Cache ───────────────────────────────────────────────────
_cache = {}
CACHE_TTL = 60           # Refresh attendance every 1 minute
SESSION_TTL = 3600


# ─── Crypto ──────────────────────────────────────────────────
def b64url(data: bytes) -> str:
    return base64.b64encode(data).decode().replace('+', '-').replace('/', '_').replace('=', '')

def generate_client_token():
    payload = json.dumps({"clientId": CLIENT_ID, "iat": int(time.time())}, separators=(',', ':')).encode()
    r = b64url(payload)
    sig = hmac.new(CLIENT_SECRET.encode(), r.encode(), hashlib.sha256).digest()
    return f"{r}.{b64url(sig)}"


# ─── Auth ────────────────────────────────────────────────────
def ensure_login():
    now = time.time()
    if _cache.get("session") and _cache.get("token") and (now - _cache.get("login_time", 0)) < SESSION_TTL:
        return _cache["session"], _cache["token"]

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Logging in to CampX...")
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
        "Origin": CAMPX_BASE_URL,
        "Referer": f"{CAMPX_BASE_URL}/auth/login",
        "x-tenant-id": CAMPX_TENANT,
        "x-institution-code": "auth",
        "x-platform-id": "campx",
        "x-campx-client": generate_client_token()
    }
    payload = {
        "username": CAMPX_USERNAME, "password": CAMPX_PASSWORD,
        "loginId": CAMPX_USERNAME, "loginType": "USER",
        "deviceType": "browser", "clientName": "Chrome",
        "os": "Windows", "osVersion": "10",
        "latitude": 13.6288, "longitude": 79.4192, "tokenType": "WEB"
    }
    try:
        resp = session.post(f"{CAMPX_API_URL}/auth-server/auth-v2/login",
                            headers=headers, json=payload, timeout=30)
        if resp.status_code in (200, 201):
            token = resp.json().get("session", {}).get("token")
            _cache.update({"session": session, "token": token, "login_time": now})
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Login OK")
            return session, token
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Login error: {e}")
    return None, None


def api_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": CAMPX_BASE_URL,
        "Referer": f"{CAMPX_BASE_URL}/{CAMPX_INSTITUTION}/student-workspace",
        "x-tenant-id": CAMPX_TENANT,
        "x-institution-code": CAMPX_INSTITUTION,
        "x-platform-id": "campx",
        "x-campx-client": generate_client_token()
    }


def cached_api_get(cache_key, endpoint, ttl=CACHE_TTL):
    """Generic cached GET request to CampX API."""
    now = time.time()
    if _cache.get(cache_key) and (now - _cache.get(cache_key + "_t", 0)) < ttl:
        return jsonify({"data": _cache[cache_key], "cached": True, "timestamp": _cache[cache_key + "_t"]})

    session, token = ensure_login()
    if not session:
        return jsonify({"error": "Login failed"}), 500

    try:
        resp = session.get(f"{CAMPX_API_URL}{endpoint}", headers=api_headers(), timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            _cache[cache_key] = data
            _cache[cache_key + "_t"] = now
            return jsonify({"data": data, "cached": False, "timestamp": now})
        return jsonify({"error": f"API returned {resp.status_code}"}), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Routes ──────────────────────────────────────────────────

@app.route('/')
def index():
    if os.path.exists(DASHBOARD_FILE):
        return send_file(DASHBOARD_FILE)
    return "<h1>Dashboard not found</h1>", 404


# === LIVE ATTENDANCE ===
@app.route('/api/attendance')
def get_attendance():
    return cached_api_get("attendance", "/student-api/student-attendance")


# === SUBJECTS (Faculty, Credits, Syllabus) ===
@app.route('/api/subjects')
def get_subjects():
    return cached_api_get("subjects", "/student-api/subjects")


# === STUDENT PROFILE ===
@app.route('/api/profile')
def get_profile():
    return cached_api_get("profile", "/auth-server/auth-v2/workspaces", ttl=3600)


# === CAMPUS EVENTS ===
@app.route('/api/events')
def get_events():
    return cached_api_get("events", "/student-api/campus-events", ttl=300)


# === CAMPUS CLUBS ===
@app.route('/api/clubs')
def get_clubs():
    return cached_api_get("clubs", "/student-api/clubs", ttl=600)


# === NOTIFICATIONS / DIGITAL NOTICE BOARD ===
@app.route('/api/notifications')
def get_notifications():
    return cached_api_get("notifications", "/student-api/notifications", ttl=120)


# === CHATS ===
@app.route('/api/chats')
def get_chats():
    return cached_api_get("chats", "/student-api/chats", ttl=60)


# === MEDIA PROXY (for club/event images) ===
@app.route('/api/media/<path:key>')
def proxy_media(key):
    """Proxy media files from CampX CDN to avoid CORS issues."""
    try:
        resp = requests.get(f"{MEDIA_BASE_URL}/{key}", timeout=10,
                            headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            from flask import Response
            return Response(resp.content,
                            content_type=resp.headers.get('content-type', 'image/png'))
    except:
        pass
    return "", 404


# === CACHE MANAGEMENT ===
@app.route('/api/refresh')
def refresh_cache():
    _cache.clear()
    return jsonify({"status": "All caches cleared", "timestamp": time.time()})


@app.route('/api/status')
def status():
    now = time.time()
    cached_keys = [k for k in _cache if not k.endswith("_t") and k not in ("session", "token", "login_time")]
    return jsonify({
        "server": "running",
        "time": datetime.now().isoformat(),
        "session_active": _cache.get("session") is not None,
        "cached_data": cached_keys,
        "endpoints": {
            "attendance": "/api/attendance",
            "subjects": "/api/subjects",
            "profile": "/api/profile",
            "events": "/api/events",
            "clubs": "/api/clubs",
            "notifications": "/api/notifications",
            "chats": "/api/chats",
        }
    })


# ─── Main ────────────────────────────────────────────────────
if __name__ == '__main__':
    print()
    print("=" * 58)
    print("  🎓 CampX Full Dashboard — SVCE Tirupati")
    print("  ────────────────────────────────────────────────")
    print("  📊 Dashboard:     http://localhost:5000")
    print("  📡 API Status:    http://localhost:5000/api/status")
    print("  📋 Attendance:    http://localhost:5000/api/attendance")
    print("  📚 Subjects:      http://localhost:5000/api/subjects")
    print("  🎪 Events:        http://localhost:5000/api/events")
    print("  🏛️  Clubs:         http://localhost:5000/api/clubs")
    print("  🔔 Notifications: http://localhost:5000/api/notifications")
    print("=" * 58)
    print()
    app.run(host='127.0.0.1', port=5000, debug=False)
