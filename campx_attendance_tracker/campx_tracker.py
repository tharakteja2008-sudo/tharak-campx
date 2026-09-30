"""
CampX Daily Attendance Email Reporter (SVCE Tirupati Edition)
Author: Antigravity
Student: P THARAK TEJA (25BFA32091)
"""

import os
import sys
import json
import base64
import hmac
import hashlib
import time
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

# Ensure console handles emojis safely on Windows
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ----------------- CONFIGURATION -----------------
CAMPX_BASE_URL = os.getenv("CAMPX_BASE_URL", "https://svce.campx.in")
CAMPX_API_URL = os.getenv("CAMPX_API_URL", "https://api.campx.in")
CAMPX_USERNAME = os.getenv("CAMPX_USERNAME", "25BFA32091")
CAMPX_PASSWORD = os.getenv("CAMPX_PASSWORD", "25BFA32091")
CAMPX_TENANT = os.getenv("CAMPX_TENANT", "svce")
CAMPX_INSTITUTION = os.getenv("CAMPX_INSTITUTION", "svce")

# Email Settings
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "tharakteja2008@gmail.com")
SENDER_APP_PASSWORD = os.getenv("SENDER_APP_PASSWORD", "udzdkjvdjsuxhwso")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "tharakteja2008@gmail.com")

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "attendance_history.json")

CLIENT_ID = "efa4ddab-3031-4370-ad77-46557d4f0890"
CLIENT_SECRET = "9KubLTSkNJMStC+Q3MhXUHPCfgbkkEb4ssyib0jfaMs="


def b64url(data: bytes) -> str:
    """Encodes bytes to base64url string without padding."""
    return base64.b64encode(data).decode('utf-8').replace('+', '-').replace('/', '_').replace('=', '')


def generate_campx_client_token():
    """Generates the required HMAC-SHA256 signature for x-campx-client header."""
    payload = {"clientId": CLIENT_ID, "iat": int(time.time())}
    payload_json = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    r = b64url(payload_json)
    sig = hmac.new(CLIENT_SECRET.encode('utf-8'), r.encode('utf-8'), hashlib.sha256).digest()
    return f"{r}.{b64url(sig)}"


def login_to_campx(max_retries=3):
    """Authenticates with SVCE Tirupati CampX portal and returns session token and student info.
    Retries up to max_retries times with exponential backoff on network errors."""
    retry_delays = [10, 30, 60]  # seconds between retries

    for attempt in range(1, max_retries + 1):
        try:
            session = requests.Session()
            login_url = f"{CAMPX_API_URL}/auth-server/auth-v2/login"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Content-Type": "application/json",
                "Origin": CAMPX_BASE_URL,
                "Referer": f"{CAMPX_BASE_URL}/auth/login",
                "x-tenant-id": CAMPX_TENANT,
                "x-institution-code": "auth",
                "x-platform-id": "campx",
                "x-campx-client": generate_campx_client_token()
            }

            payload = {
                "username": CAMPX_USERNAME,
                "password": CAMPX_PASSWORD,
                "loginId": CAMPX_USERNAME,
                "loginType": "USER",
                "deviceType": "browser",
                "clientName": "Chrome",
                "os": "Windows",
                "osVersion": "10",
                "latitude": 13.6288,
                "longitude": 79.4192,
                "tokenType": "WEB"
            }

            print(f"[*] Logging in to SVCE CampX for {CAMPX_USERNAME}... (attempt {attempt}/{max_retries})")
            resp = session.post(login_url, headers=headers, json=payload, timeout=30)
            
            if resp.status_code in (200, 201):
                login_data = resp.json()
                token = login_data.get("session", {}).get("token")
                print(f"[+] Login successful! Session token obtained.")
                return session, token
            else:
                print(f"[-] Login failed [{resp.status_code}]: {resp.text}")
                return None, None

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            delay = retry_delays[min(attempt - 1, len(retry_delays) - 1)]
            print(f"[!] Network error on attempt {attempt}/{max_retries}: {type(e).__name__}")
            if attempt < max_retries:
                print(f"[*] Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"[-] All {max_retries} login attempts failed. Last error: {e}")
                return None, None


def fetch_student_details(session, token):
    """Fetches user profile (Name, Branch, Roll No)."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": CAMPX_BASE_URL,
        "Referer": f"{CAMPX_BASE_URL}/{CAMPX_INSTITUTION}/student-workspace",
        "x-tenant-id": CAMPX_TENANT,
        "x-institution-code": CAMPX_INSTITUTION,
        "x-platform-id": "campx",
        "x-campx-client": generate_campx_client_token()
    }
    
    url = f"{CAMPX_API_URL}/auth-server/auth-v2/workspaces"
    try:
        r = session.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json().get("user", {})
    except Exception as e:
        print(f"[-] Error fetching profile: {e}")
    return {}


def fetch_attendance(session, token):
    """Fetches real-time subject-wise attendance list from CampX."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": CAMPX_BASE_URL,
        "Referer": f"{CAMPX_BASE_URL}/{CAMPX_INSTITUTION}/student-workspace",
        "x-tenant-id": CAMPX_TENANT,
        "x-institution-code": CAMPX_INSTITUTION,
        "x-platform-id": "campx",
        "x-campx-client": generate_campx_client_token()
    }

    url = f"{CAMPX_API_URL}/student-api/student-attendance"
    try:
        r = session.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[-] Error fetching attendance: {e}")
    return []


def process_attendance_data(raw_subjects, prev_history):
    """
    Computes:
    - Overall attendance percentage
    - Total conducted vs attended
    - Daily changes per subject (how many attended / missed today)
    - Overall Delta (+/- %)
    """
    total_conducted = 0
    total_attended = 0
    subjects = []
    
    prev_subjects_map = {}
    if prev_history and "subjects" in prev_history:
        for ps in prev_history["subjects"]:
            prev_subjects_map[ps["subjectId"]] = ps

    today_attended_classes = []
    today_missed_classes = []

    for s in raw_subjects:
        sid = s.get("subjectId")
        sname = s.get("subjectName", "Unknown Subject")
        ref_code = s.get("refCode", "")
        conducted = int(s.get("numberOfClasses", 0))
        present = int(s.get("present", 0))
        absent = int(s.get("absent", 0))
        pct = float(s.get("percentage", 0.0))

        total_conducted += conducted
        total_attended += present

        # Compare with previous run to detect today's new classes
        if sid in prev_subjects_map:
            prev_s = prev_subjects_map[sid]
            new_conducted = conducted - prev_s.get("conducted", conducted)
            new_present = present - prev_s.get("present", present)
            new_absent = absent - prev_s.get("absent", absent)

            if new_present > 0:
                today_attended_classes.append(f"{sname} ({ref_code}) — {new_present} class(es)")
            if new_absent > 0:
                today_missed_classes.append(f"{sname} ({ref_code}) — {new_absent} class(es)")

        subjects.append({
            "subjectId": sid,
            "name": sname,
            "refCode": ref_code,
            "conducted": conducted,
            "attended": present,
            "absent": absent,
            "percentage": round(pct, 2)
        })

    overall_pct = round((total_attended / total_conducted * 100), 2) if total_conducted > 0 else 0.0

    # Delta Calculation
    prev_overall = prev_history.get("overall_percentage", overall_pct) if prev_history else overall_pct
    delta_val = round(overall_pct - prev_overall, 2)
    
    if prev_history is None:
        delta_str = "Initial Setup Report"
    elif delta_val > 0:
        delta_str = f"📈 Increased by +{delta_val}%"
    elif delta_val < 0:
        delta_str = f"🔻 Decreased by {delta_val}%"
    else:
        delta_str = "⚖️ No change (0.00%)"

    current_data = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "overall_percentage": overall_pct,
        "total_conducted": total_conducted,
        "total_attended": total_attended,
        "delta_val": delta_val,
        "delta_str": delta_str,
        "today_attended": today_attended_classes,
        "today_missed": today_missed_classes,
        "subjects": subjects
    }

    return current_data


def calculate_bunk_margin(conducted, attended, target_pct=75.0):
    """Calculates safe bunks or classes needed to hit 75%."""
    if conducted == 0:
        return "Not enough data recorded yet."
    
    current_pct = (attended / conducted) * 100
    if current_pct >= target_pct:
        # margin = max bunks without falling below target
        margin = int((attended * 100 / target_pct) - conducted)
        if margin > 0:
            return f"🎉 <b>Safe Zone:</b> You can miss <b>{margin} class(es)</b> and still maintain above {target_pct}%."
        else:
            return f"⚠️ <b>Borderline:</b> You are at {current_pct:.2f}%. Avoid missing classes to stay above {target_pct}%."
    else:
        # classes needed to reach target_pct
        req = int(((target_pct / 100 * conducted) - attended) / (1 - (target_pct / 100))) + 1
        return f"🚨 <b>Warning:</b> You need to attend <b>{req} consecutive classes</b> to reach {target_pct}%."


def generate_email_html(data, student_info):
    """Renders a responsive HTML attendance dashboard email."""
    name = student_info.get("fullName", "P THARAK TEJA")
    roll = student_info.get("rollNo", "25BFA32091")
    branch = student_info.get("branchCode", "CSE(CSD)")
    pct = data["overall_percentage"]
    date_formatted = datetime.now().strftime("%A, %d %B %Y")
    
    badge_color = "#10b981" if pct >= 75 else "#ef4444"
    delta_color = "#10b981" if data["delta_val"] > 0 else ("#ef4444" if data["delta_val"] < 0 else "#64748b")
    margin_info = calculate_bunk_margin(data["total_conducted"], data["total_attended"], 75.0)

    # Missed Classes Box
    if data["today_missed"]:
        items = "".join([f"<li style='color: #dc2626; margin-bottom: 4px;'>❌ <b>{c}</b> (ABSENT)</li>" for c in data["today_missed"]])
        missed_html = f"""
        <div style='background: #fef2f2; border-left: 4px solid #ef4444; padding: 14px; border-radius: 8px; margin: 15px 0;'>
            <h4 style='margin: 0 0 8px 0; color: #991b1b;'>Classes Missed Today:</h4>
            <ul style='margin: 0; padding-left: 20px;'>{items}</ul>
        </div>
        """
    else:
        missed_html = """
        <div style='background: #f0fdf4; border-left: 4px solid #10b981; padding: 12px; border-radius: 8px; margin: 15px 0; color: #166534;'>
            <b>✨ Excellent!</b> No classes were missed today.
        </div>
        """

    # Attended Classes Box
    attended_html = ""
    if data["today_attended"]:
        items = "".join([f"<li style='color: #16a34a; margin-bottom: 4px;'>✅ {c}</li>" for c in data["today_attended"]])
        attended_html = f"""
        <div style='background: #f0fdf4; border-left: 4px solid #10b981; padding: 14px; border-radius: 8px; margin: 15px 0;'>
            <h4 style='margin: 0 0 8px 0; color: #166534;'>Classes Attended Today:</h4>
            <ul style='margin: 0; padding-left: 20px;'>{items}</ul>
        </div>
        """

    # Subject Table Rows
    subject_rows = ""
    for s in sorted(data["subjects"], key=lambda x: x["percentage"]):
        s_color = "#10b981" if s["percentage"] >= 75 else "#ef4444"
        subject_rows += f"""
        <tr style='border-bottom: 1px solid #f1f5f9;'>
            <td style='padding: 10px 8px;'>
                <div style='font-weight: 600; color: #1e293b;'>{s['name']}</div>
                <div style='font-size: 11px; color: #64748b;'>Code: {s['refCode']}</div>
            </td>
            <td style='padding: 10px 8px; text-align: center; color: #334155;'>{s['attended']}/{s['conducted']}</td>
            <td style='padding: 10px 8px; text-align: right; color: {s_color}; font-weight: 800;'>{s['percentage']}%</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 14px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.06); border: 1px solid #e2e8f0; }}
            .header {{ background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%); color: #ffffff; padding: 24px; text-align: center; }}
            .content {{ padding: 24px; color: #334155; line-height: 1.5; }}
            .pct-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 20px; }}
            .pct-title {{ font-size: 12px; text-transform: uppercase; letter-spacing: 1.2px; color: #64748b; font-weight: 700; margin-bottom: 4px; }}
            .pct-num {{ font-size: 42px; font-weight: 900; color: {badge_color}; line-height: 1; margin: 8px 0; }}
            .delta-tag {{ display: inline-block; padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 700; color: {delta_color}; background: #ffffff; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }}
            .footer {{ background: #f8fafc; padding: 16px; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2 style="margin: 0; font-size: 20px; letter-spacing: -0.5px;">🎓 Sri Venkateswara College of Engineering</h2>
                <p style="margin: 4px 0 0 0; opacity: 0.9; font-size: 13px;">Daily Attendance Alert • {date_formatted}</p>
                <div style="margin-top: 10px; font-size: 12px; background: rgba(255,255,255,0.15); display: inline-block; padding: 3px 12px; border-radius: 12px;">
                    {name} ({roll}) • {branch}
                </div>
            </div>

            <div class="content">
                <div class="pct-card">
                    <div class="pct-title">Overall Attendance</div>
                    <div class="pct-num">{pct}%</div>
                    <div class="delta-tag">{data['delta_str']}</div>
                    <div style="font-size: 13px; color: #64748b; margin-top: 10px;">
                        Classes Attended: <b>{data['total_attended']}</b> / <b>{data['total_conducted']}</b>
                    </div>
                </div>

                {missed_html}
                {attended_html}

                <div style="background: #f8fafc; border: 1px dashed #cbd5e1; padding: 14px; border-radius: 8px; margin: 18px 0; font-size: 14px; color: #334155;">
                    💡 {margin_info}
                </div>

                <h4 style="margin: 22px 0 10px 0; color: #0f172a; font-size: 15px;">📊 Subject-wise Attendance:</h4>
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    <thead>
                        <tr style="background: #f1f5f9; color: #475569; text-align: left;">
                            <th style="padding: 8px;">Subject</th>
                            <th style="padding: 8px; text-align: center;">Attended</th>
                            <th style="padding: 8px; text-align: right;">%</th>
                        </tr>
                    </thead>
                    <tbody>
                        {subject_rows}
                    </tbody>
                </table>
            </div>

            <div class="footer">
                CampX Automated Notification System • SVCE Tirupati<br>
                Recipient: {RECIPIENT_EMAIL}
            </div>
        </div>
    </body>
    </html>
    """
    return html


def send_email(subject, html_content):
    """Sends the formatted email report using Gmail SMTP."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"SVCE CampX Tracker <{SENDER_EMAIL}>"
    msg["To"] = RECIPIENT_EMAIL

    msg.attach(MIMEText(html_content, "html"))

    try:
        print(f"[*] Sending daily attendance email to {RECIPIENT_EMAIL}...")
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        server.quit()
        print("[+] Daily attendance email sent successfully!")
        return True
    except Exception as e:
        print(f"[-] Failed to send email: {e}")
        return False


def run_tracker():
    """Main execution entrypoint."""
    print("=" * 60)
    print(f"CampX Attendance Tracker Triggered: {datetime.now()}")
    print("=" * 60)

    # 1. Login
    session, token = login_to_campx()
    if not token:
        print("[-] Login failed. Exiting.")
        return

    # 2. Fetch Student Profile & Attendance
    student_info = fetch_student_details(session, token)
    raw_subjects = fetch_attendance(session, token)

    if not raw_subjects:
        print("[-] No attendance records received. Exiting.")
        return

    # 3. Load previous history & calculate delta
    prev_history = None
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                prev_history = json.load(f)
        except Exception:
            pass

    data = process_attendance_data(raw_subjects, prev_history)
    print(f"[+] Overall Attendance: {data['overall_percentage']}% ({data['total_attended']}/{data['total_conducted']})")
    print(f"[+] Status: {data['delta_str']}")

    # 4. Generate & Send Email
    subject = f"CampX Attendance: {data['overall_percentage']}% | SVCE Tirupati ({datetime.now().strftime('%d %b')})"
    html_content = generate_email_html(data, student_info)
    send_email(subject, html_content)

    # 5. Save History for Next Run
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print("[+] History saved successfully for tomorrow's delta calculation.")
    print("=" * 60)


if __name__ == "__main__":
    run_tracker()
