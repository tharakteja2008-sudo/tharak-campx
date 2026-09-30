# 🎓 CampX Daily Attendance Email Tracker

Automate your daily attendance monitoring from **CampX** straight to your **Gmail inbox** every evening.

---

## ✨ Features
1. **Daily Delta Calculation**: Shows whether your attendance **increased (📈 +X%)** or **decreased (🔻 -X%)** today.
2. **Missed Class Alerts**: Highlights classes/periods marked **Absent** (❌) vs **Attended** (✅) today.
3. **Attendance Predictor**: Calculates how many classes you can afford to safely miss, or how many you need to reach 75%.
4. **100% Free Cloud Automation**: Runs automatically on GitHub Actions at 6:30 PM IST every college day without needing your PC on.

---

## 🚀 Quick Setup (Choose Option A or Option B)

### Option A: Free 24/7 Cloud Automation (GitHub Actions - Recommended)
1. Create a private GitHub repository and upload this folder (`campx_attendance_tracker`).
2. Go to repository **Settings $\rightarrow$ Secrets and variables $\rightarrow$ Actions**.
3. Add the following secrets:
   - `CAMPX_USERNAME`: Your Roll Number (`25BFA32091`)
   - `CAMPX_PASSWORD`: Your CampX Password
   - `SENDER_EMAIL`: `tharakteja2008@gmail.com`
   - `SENDER_APP_PASSWORD`: 16-character Google App Password ([How to get this](#-how-to-generate-a-google-app-password))
   - `RECIPIENT_EMAIL`: `tharakteja2008@gmail.com`
4. The workflow will automatically run every day at **6:30 PM IST** (and you can also trigger it manually under the **Actions** tab by clicking "Run workflow").

---

### Option B: Run Locally on Your PC
1. Open PowerShell / Command Prompt in this folder.
2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Set your Google App Password in `campx_tracker.py` or as an environment variable:
   ```powershell
   $env:SENDER_APP_PASSWORD="your-16-char-app-password"
   python campx_tracker.py
   ```

---

## 🔑 How to Generate a Google App Password
1. Go to your **Google Account Security**: https://myaccount.google.com/security
2. Ensure **2-Step Verification** is turned **ON**.
3. In the search bar at the top, type **"App passwords"** and click on it.
4. Name the app `CampX Tracker` and click **Create**.
5. Copy the generated **16-character password** (e.g. `abcd efgh ijkl mnop`).
6. Paste this into `SENDER_APP_PASSWORD`.
