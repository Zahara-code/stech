# SwtchTech POS System — Deployment Guide

## Overview
This is a Python Flask web application. It runs as a local web server and is accessed via a browser.

---

## 1. Install on a Computer (Local / Tablet Access)

### Requirements
- Python 3.10 or newer
- pip (Python package manager)

### Step-by-Step Setup

```bash
# 1. Copy the swtchtech folder to your computer

# 2. Open Terminal (Mac/Linux) or Command Prompt (Windows)
cd path/to/swtchtech

# 3. Create a virtual environment
python -m venv venv

# 4. Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 5. Install dependencies
pip install -r requirements.txt

# 6. Run the system
python run.py
```

Open your browser and go to: **http://localhost:5000**

---

## 2. Access from a Tablet on the Same WiFi

1. Find your computer's local IP address:
   - Windows: Open cmd → type `ipconfig` → look for IPv4 Address (e.g. 192.168.1.100)
   - Mac/Linux: Open terminal → type `ifconfig` or `ip addr`

2. The app already listens on `0.0.0.0` so it's accessible on your network

3. On the tablet (iPad, Android tablet), open the browser and type:
   **http://192.168.1.100:5000** (replace with your computer's IP)

4. The interface is fully responsive and works on tablets

**Tip:** Bookmark the URL on the tablet. On iPad/Android, you can "Add to Home Screen" for a native app feel.

---

## 3. Make it Start Automatically on Windows

Create a file `start_swtchtech.bat` with:
```
@echo off
cd C:\path\to\swtchtech
call venv\Scripts\activate
python run.py
pause
```
Double-click this file to start the system each time.

---

## 4. Host Online (Access from Anywhere)

### Option A: Railway (Recommended — Free Tier Available)
1. Go to https://railway.app and sign up
2. Install Railway CLI: `npm install -g @railway/cli`
3. In the swtchtech folder:
   ```bash
   railway login
   railway init
   railway up
   ```
4. Railway will give you a public URL like `https://swtchtech-xxx.up.railway.app`

### Option B: Render (Free Tier)
1. Go to https://render.com and sign up
2. Create a new "Web Service"
3. Connect your GitHub repo (push the swtchtech folder to GitHub first)
4. Set:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
5. Render gives you a free public URL

### Option C: DigitalOcean / VPS (Most Reliable, ~$6/month)
```bash
# On your Ubuntu server:
sudo apt update && sudo apt install python3-pip python3-venv nginx -y
cd /var/www && git clone your-repo swtchtech && cd swtchtech
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
gunicorn --bind 0.0.0.0:8000 app:app &
```
Then configure nginx to proxy to port 8000.

---

## 5. Database

The system uses **SQLite** (file-based database stored in `instance/swtchtech.db`).

- **Backup:** Just copy `instance/swtchtech.db` to a safe location
- **Restore:** Replace the file
- **For online hosting:** SQLite works for small shops. For larger scale, you can upgrade to PostgreSQL by changing the `SQLALCHEMY_DATABASE_URI` in `app.py`

---

## 6. Default Credentials (CHANGE AFTER FIRST LOGIN!)

| Role  | Username | Password  |
|-------|----------|-----------|
| Admin | admin    | admin123  |
| Sales | sales1   | sales123  |

Change passwords immediately via **Staff Accounts → Edit**

---

## 7. Access Control Summary

| Feature              | Admin | Sales |
|----------------------|-------|-------|
| Dashboard            | ✅    | ✅    |
| New Sale / POS       | ✅    | ✅    |
| Sales History        | ✅    | ✅    |
| View Products        | ✅    | ✅    |
| Add/Edit Products    | ✅    | ✅    |
| Delete Products      | ✅    | ❌    |
| Stock Updates        | ✅    | ✅    |
| Stock History        | ✅    | ✅    |
| Categories           | ✅    | ❌    |
| Staff Accounts       | ✅    | ❌    |
| Reports              | ✅    | ❌    |
