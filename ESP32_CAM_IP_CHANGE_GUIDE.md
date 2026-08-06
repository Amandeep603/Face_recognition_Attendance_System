# 📡 ESP32-CAM IP Address Change Guide

### AI Face Recognition Attendance System — Standard Operating Procedure (SOP)

**Document Version:** 1.0  
**Last Updated:** August 6, 2026  
**Applicable Project:** FaceAttendance (Flask + ESP32-CAM)  
**Author:** Medein Labs Engineering  

---

## 📑 Table of Contents

1. [Purpose](#1-purpose)
2. [Network Architecture](#2-network-architecture)
3. [Step 1: Find the New ESP32-CAM IP Address](#3-step-1-find-the-new-esp32-cam-ip-address)
4. [Step 2: Verify the Camera Stream](#4-step-2-verify-the-camera-stream)
5. [Step 3: Update the Project Configuration](#5-step-3-update-the-project-configuration)
6. [Step 4: Search the Codebase for Hardcoded IPs](#6-step-4-search-the-codebase-for-hardcoded-ips)
7. [Step 5: Restart the Flask Application](#7-step-5-restart-the-flask-application)
8. [Step 6: Verify the Dashboard](#8-step-6-verify-the-dashboard)
9. [Troubleshooting](#9-troubleshooting)
10. [Network Connectivity Test](#10-network-connectivity-test)
11. [Static IP Recommendation (Permanent Fix)](#11-static-ip-recommendation-permanent-fix)
12. [Quick Update Checklist](#12-quick-update-checklist)
13. [Appendix](#13-appendix)

---

## 1. Purpose

The ESP32-CAM module connects to your local Wi-Fi network and is assigned an **IP address by the router's DHCP server**. This IP address is used by the Flask attendance system to read the live MJPEG video stream.

### Why Does the IP Address Change?

| Cause | Explanation |
| :--- | :--- |
| **Router Reboot** | The DHCP lease table resets, and a new IP may be assigned. |
| **ESP32-CAM Power Cycle** | The module requests a fresh IP on boot. |
| **DHCP Lease Expiration** | Most routers assign IPs with a 24-hour lease. After expiry, a new IP may be issued. |
| **Network Change** | Switching to a different Wi-Fi hotspot (e.g., phone hotspot vs. home router) changes the entire subnet. |
| **Multiple Devices** | If other devices joined the network while the ESP32-CAM was off, its previous IP may be taken. |

### Impact on the Attendance System

When the IP address changes, the Flask application **cannot connect to the ESP32-CAM stream**. The dashboard will show:

- ❌ **"Camera Offline"** or **"Connecting to ESP32-CAM..."** placeholder
- ❌ Face recognition stops completely
- ❌ Attendance marking halts
- ❌ Registration wizard shows a black/frozen preview

> [!IMPORTANT]
> The system does **not crash** when the IP changes. It enters a graceful reconnection loop and will recover automatically once `config.py` is updated with the correct IP and the server is restarted.

---

## 2. Network Architecture

The following diagram shows how the components communicate:

```
┌─────────────────┐         Wi-Fi          ┌─────────────────────┐
│                 │◄──────────────────────► │                     │
│   ESP32-CAM     │    HTTP /capture or     │   Wi-Fi Router      │
│   (AI-Thinker)  │    MJPEG /stream        │   (DHCP Server)     │
│                 │                         │                     │
│  IP: Dynamic    │                         │  Gateway: 192.168.x.1│
└─────────────────┘                         └──────────┬──────────┘
                                                       │
                                                       │ LAN / Wi-Fi
                                                       │
                                            ┌──────────▼──────────┐
                                            │                     │
                                            │   Flask Server      │
                                            │   (Your Laptop)     │
                                            │                     │
                                            │  Reads camera URL   │
                                            │  from config.py     │
                                            │                     │
                                            │  Dashboard:         │
                                            │  http://127.0.0.1:  │
                                            │  5000               │
                                            └─────────────────────┘
```

**Data Flow:**

```
ESP32-CAM  ──► [JPEG/MJPEG frames over HTTP] ──►  Flask Server (camera_stream.py)
                                                        │
                                                        ▼
                                                  face_engine.py (AI recognition)
                                                        │
                                                        ▼
                                                  attendance_manager.py (CSV logging)
                                                        │
                                                        ▼
                                                  Web Dashboard (HTML/JS/CSS)
```

> [!NOTE]
> The Flask application reads the camera URL from **`config.py`** at startup. If the ESP32-CAM's IP changes, you must update this file and restart Flask.

---

## 3. Step 1: Find the New ESP32-CAM IP Address

### Method A: Arduino IDE Serial Monitor (Recommended)

1. Connect the ESP32-CAM to your computer via USB-to-TTL adapter.
2. Open **Arduino IDE**.
3. Go to **Tools → Serial Monitor**.
4. Set baud rate to **`115200`**.
5. Press the **RST (Reset)** button on the ESP32-CAM board.

You will see output similar to:

```
ets Jun  8 2016 00:22:57

rst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)
...
WiFi connected
Camera Ready! Use 'http://192.168.43.105' to connect
```

> [!TIP]
> The IP address is displayed on the line that says **`Camera Ready! Use 'http://X.X.X.X' to connect`**. Copy this IP address — you will need it in the next steps.

### Method B: Router Admin Panel

1. Open your browser and go to your router's admin page (usually `http://192.168.1.1` or `http://192.168.0.1`).
2. Navigate to **Connected Devices** or **DHCP Client List**.
3. Look for a device named **`ESP32`** or **`Espressif`**.
4. Note the assigned IP address.

### Method C: Network Scanner App

Use a free network scanner app on your phone:

- **Android:** [Fing](https://play.google.com/store/apps/details?id=com.overlook.android.fing)
- **iOS:** [Network Analyzer](https://apps.apple.com/app/network-analyzer/id562315041)

Scan your local network and look for a device manufactured by **Espressif Inc.**

---

## 4. Step 2: Verify the Camera Stream

Before updating the code, verify that the ESP32-CAM is actually serving frames at the new IP.

### Test 1: Open the Camera Web UI

Open a browser and navigate to:

```
http://NEW_IP/
```

**Example:**
```
http://192.168.43.105/
```

**Expected Result:**  
You should see the ESP32-CAM's built-in web interface with resolution controls and a "Start Stream" button.

### Test 2: Test the MJPEG Stream (Port 81)

Some ESP32-CAM firmware versions serve a continuous MJPEG stream on port 81:

```
http://NEW_IP:81/stream
```

**Example:**
```
http://192.168.43.105:81/stream
```

**Expected Result:**  
A continuous live video feed should appear in your browser.

### Test 3: Test the Snapshot Capture Endpoint

All ESP32-CAM firmware versions support a single-frame JPEG capture:

```
http://NEW_IP/capture
```

**Example:**
```
http://192.168.43.105/capture
```

**Expected Result:**  
A single JPEG image should load in your browser.

> [!WARNING]
> If **none** of the above URLs respond, the ESP32-CAM is either:
> - Not connected to Wi-Fi
> - On a different network/subnet than your computer
> - Powered off or malfunctioning
>
> Resolve the network issue before proceeding.

### Understanding the Two Camera Modes

| Mode | URL Pattern | How It Works | Typical FPS |
| :--- | :--- | :--- | :--- |
| **MJPEG Stream** | `http://IP:81/stream` | Persistent HTTP connection, continuous frames | 15–25 FPS |
| **Capture Snapshot** | `http://IP/capture` | Individual HTTP GET per frame, polled rapidly | 4–8 FPS |

Our system supports **both modes** via the `CAPTURE_MODE` flag in `config.py`:

```python
# In config.py:
CAPTURE_MODE = True   # Use /capture endpoint (snapshot polling)
CAPTURE_MODE = False  # Use :81/stream endpoint (MJPEG stream)
```

---

## 5. Step 3: Update the Project Configuration

### Project Structure

```
FaceAttendance/
├── config.py                  ◄── PRIMARY CONFIGURATION FILE (update here)
├── camera_stream.py           # Stream reader (reads from config.py)
├── face_engine.py             # AI recognition engine
├── attendance_manager.py      # CSV attendance manager
├── app.py                     # Flask web server
├── static/                    # CSS, JS, assets
│   └── js/
│       └── main.js            # May contain fallback URL
├── templates/                 # HTML templates
├── test_stream.py             # Stream connectivity test
├── test_imports.py            # Environment verification test
└── start.bat                  # Windows launch script
```

### Update `config.py` (Primary — Required)

Open `config.py` and locate the **Camera Stream Configuration** section (around line 28–31):

**Before (old IP):**
```python
# Camera Stream Configuration (ESP32-CAM & Local Fallback)
CAMERA_URL = "http://192.168.18.142:81/stream"
ESP32_STREAM_URL = CAMERA_URL
CAMERA_SOURCE = CAMERA_URL
```

**After (new IP):**
```python
# Camera Stream Configuration (ESP32-CAM & Local Fallback)
CAMERA_URL = "http://192.168.18.150:81/stream"
ESP32_STREAM_URL = CAMERA_URL
CAMERA_SOURCE = CAMERA_URL
```

> [!IMPORTANT]
> **`config.py` is the ONLY file you need to update.** All other modules (`camera_stream.py`, `face_engine.py`, `app.py`) import the camera URL from `config.py` at runtime. You do **not** need to edit them.

### Also Check `CAPTURE_MODE`

If your ESP32-CAM uses `/capture` instead of `:81/stream`, also update the mode:

```python
# For /capture endpoint (snapshot polling):
CAMERA_URL = "http://192.168.43.105/capture"
CAPTURE_MODE = True

# For :81/stream endpoint (MJPEG stream):
CAMERA_URL = "http://192.168.43.105:81/stream"
CAPTURE_MODE = False
```

### Secondary Files (Optional — Only if hardcoded)

These files may contain **hardcoded fallback URLs** that should also be updated:

| File | Line | What to Change |
| :--- | :--- | :--- |
| `static/js/main.js` | ~330 | Fallback URL in `promptChangeSource()` |
| `test_stream.py` | ~5 | `STREAM_URL` constant |
| `test_imports.py` | ~59 | `stream_url` variable |
| `start.bat` | ~7 | Display banner URL |

---

## 6. Step 4: Search the Codebase for Hardcoded IPs

If you are unsure whether the old IP address is hardcoded anywhere else, perform a **project-wide search**.

### VS Code

Press:
```
Ctrl + Shift + F
```

Search for the **old IP address**:
```
192.168.18.142
```

Also search for the stream path pattern:
```
:81/stream
```

And the capture pattern:
```
/capture
```

### Command Line (PowerShell)

```powershell
# Search all Python, JS, HTML, and batch files for the old IP
Get-ChildItem -Path "C:\path\to\FaceAttendance" -Recurse -Include *.py,*.js,*.html,*.bat,*.md |
  Select-String -Pattern "192.168.18.142" |
  Format-Table Path, LineNumber, Line -AutoSize
```

### Command Line (Linux/Mac)

```bash
grep -rn "192.168.18.142" --include="*.py" --include="*.js" --include="*.html" --include="*.bat" .
```

### Files That Typically Contain the IP

| File | Why It May Have the IP | Must Update? |
| :--- | :--- | :--- |
| `config.py` | Primary configuration source | ✅ **YES** |
| `test_stream.py` | Standalone stream test script | ⚠️ Recommended |
| `test_imports.py` | Environment verification test | ⚠️ Recommended |
| `static/js/main.js` | UI fallback URL in camera source prompt | ⚠️ Recommended |
| `start.bat` | Display banner text | ⚙️ Optional |
| `README.md` | Documentation examples | ⚙️ Optional |
| `TEST_REPORT.md` | Test report references | ⚙️ Optional |
| `.env.example` | Environment variable template | ⚙️ Optional |

---

## 7. Step 5: Restart the Flask Application

After saving `config.py`, you **must restart** the Flask server for the changes to take effect.

### Why Is a Restart Required?

Python reads `config.py` once at import time. The camera URL is loaded into memory when the server starts. Changing the file on disk does **not** update the running process — you must stop and restart it.

### Stop the Current Server

In the terminal where `python app.py` is running, press:

```
Ctrl + C
```

You should see:
```
^C
[CameraStream] Stopped stream thread.
```

### Start the Server Again

```bash
python app.py
```

Or double-click `start.bat` on Windows.

### Verify Startup Output

Look for these indicators in the console:

```
[CameraStream] Mode: CAPTURE (snapshot polling) | Source: http://NEW_IP/capture
[CameraStream] Started stream thread for source: http://NEW_IP/capture

==============================================================================
   AI FACE RECOGNITION ATTENDANCE SYSTEM - ENTERPRISE EDITION
==============================================================================

[*] Target Stream Source: http://NEW_IP/capture

 [01] Python 3.11 Runtime & Operating System           [OK]
 [02] Core AI & Computer Vision Libraries              [OK]
 [03] ESP32-CAM Stream & Network Config                [OK]  ◄── This must say OK
 ...
 [10] Admin Security & Session Encryption              [OK]

[*] Pre-flight Checklist Completed | Status: ALL READY

 * Running on http://127.0.0.1:5000
```

> [!CAUTION]
> If check **[03] ESP32-CAM Stream & Network Config** shows **[FAILED]**, the new IP is not reachable. Go back to [Step 2](#4-step-2-verify-the-camera-stream) and verify network connectivity.

---

## 8. Step 6: Verify the Dashboard

Open your web browser and navigate to:

```
http://127.0.0.1:5000
```

Or from another device on the same network:

```
http://YOUR_LAPTOP_IP:5000
```

### Verification Checklist

| Component | What to Check | Expected State |
| :--- | :--- | :--- |
| **Live Stream** | Video feed panel on the left side | 🟢 Live camera frames visible |
| **Camera Status** | Status indicator in sidebar | 🟢 "ESP32 Online" |
| **FPS Counter** | Frames per second display | 🟢 4–25 FPS (depends on mode) |
| **Face Detection** | Stand in front of camera | 🟢 Green/red bounding boxes appear |
| **Recognition** | Show a registered face | 🟢 Name + confidence % displayed |
| **Attendance Panel** | Right side attendance list | 🟢 Student name appears with timestamp |
| **Liveness Badge** | Anti-spoofing status overlay | 🟢 "Live Face Verified" in green |

> [!TIP]
> If the video feed shows **"Connecting to ESP32-CAM..."** for more than 10 seconds, the new IP is incorrect or the ESP32-CAM is not on the same network. Double-check your configuration.

---

## 9. Troubleshooting

| # | Problem | Possible Cause | Solution |
| :--- | :--- | :--- | :--- |
| 1 | **Camera web page not opening** (`http://NEW_IP/`) | ESP32-CAM not connected to Wi-Fi, wrong IP, or powered off | Verify power LED is on. Check Serial Monitor for the correct IP. Ensure your computer is on the **same Wi-Fi network**. |
| 2 | **`/stream` not working but `/capture` works** | Firmware doesn't enable the MJPEG stream server on port 81 | Set `CAPTURE_MODE = True` in `config.py` and use `http://IP/capture` as the URL. |
| 3 | **`/capture` not working but web UI loads** | The camera module (OV2640) initialization failed | Press the **RST** button on the ESP32-CAM. If it persists, check the ribbon cable connection to the camera sensor. |
| 4 | **Dashboard shows "Camera Offline"** | `config.py` still has the old IP, or Flask was not restarted | Update `CAMERA_URL` in `config.py`, save, and restart with `python app.py`. |
| 5 | **Face recognition stopped** | No camera frames reaching `face_engine.py` | Fix the camera connection first. Recognition resumes automatically when frames are available. |
| 6 | **Attendance not marking** | Anti-spoofing rejecting frames as "Spoof Detected", or the student is not registered | Check the recognition log at `logs/recognition.log`. Ensure the student is in `known_faces/` and `encodings.pkl` is up to date. |
| 7 | **Very low FPS (< 2 FPS)** | ESP32-CAM is set to high resolution (UXGA/SXGA), or Wi-Fi signal is weak | Lower the resolution via the ESP32-CAM web UI (Settings → Resolution → VGA or CIF). Move the ESP32-CAM closer to the router. |
| 8 | **Server starts but no one can access it** | Flask is bound to `127.0.0.1` instead of `0.0.0.0` | Check `config.py`: `HOST = "0.0.0.0"` (should allow all network access). |
| 9 | **"Connection refused" from phone/tablet** | Firewall blocking port 5000 | On Windows: Allow Python through Windows Firewall. On the prompt that appears when you first run `python app.py`, click **"Allow"**. |
| 10 | **Stream works in browser but not in Flask** | URL format mismatch (e.g., trailing slash, wrong port) | Ensure the URL in `config.py` exactly matches what works in the browser. No trailing slash for `/capture`. |

---

## 10. Network Connectivity Test

Before updating `config.py`, verify that your computer can reach the ESP32-CAM.

### Ping Test

Open a terminal (Command Prompt or PowerShell) and run:

```bash
ping 192.168.43.105
```

**Expected Response (Success):**

```
Pinging 192.168.43.105 with 32 bytes of data:
Reply from 192.168.43.105: bytes=32 time=5ms TTL=255
Reply from 192.168.43.105: bytes=32 time=3ms TTL=255
Reply from 192.168.43.105: bytes=32 time=4ms TTL=255
Reply from 192.168.43.105: bytes=32 time=3ms TTL=255

Ping statistics for 192.168.43.105:
    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
```

**Failed Response (Problem):**

```
Pinging 192.168.43.105 with 32 bytes of data:
Request timed out.
Request timed out.

Ping statistics for 192.168.43.105:
    Packets: Sent = 4, Received = 0, Lost = 4 (100% loss),
```

> [!WARNING]
> If ping fails with **100% loss**, the ESP32-CAM is unreachable. Check:
> - Is the ESP32-CAM powered on? (Red LED should be on)
> - Is your computer connected to the **same Wi-Fi network**?
> - Is the IP address correct? (Recheck Serial Monitor)

### HTTP Connectivity Test (Python)

```python
python -c "
import urllib.request
try:
    resp = urllib.request.urlopen('http://192.168.43.105/capture', timeout=5)
    print(f'SUCCESS: HTTP {resp.status}, Content-Length: {len(resp.read())} bytes')
except Exception as e:
    print(f'FAILED: {e}')
"
```

---

## 11. Static IP Recommendation (Permanent Fix)

To **permanently prevent** the IP address from changing, assign a **static IP** to the ESP32-CAM in your Arduino sketch.

### Recommended Static IP

```
192.168.18.200
```

This is typically outside the DHCP range (most routers assign `.2` to `.100`) and avoids conflicts.

### Arduino Code Modification

Add these lines **before** `WiFi.begin()` in your ESP32-CAM sketch:

```cpp
#include <WiFi.h>

const char* ssid = "YOUR_WIFI_NAME";
const char* password = "YOUR_WIFI_PASSWORD";

// Static IP Configuration
IPAddress local_IP(192, 168, 18, 200);      // Desired static IP
IPAddress gateway(192, 168, 18, 1);          // Your router's gateway IP
IPAddress subnet(255, 255, 255, 0);          // Subnet mask
IPAddress primaryDNS(8, 8, 8, 8);            // Google DNS (optional)
IPAddress secondaryDNS(8, 8, 4, 4);          // Google DNS (optional)

void setup() {
    Serial.begin(115200);
    
    // Configure static IP BEFORE WiFi.begin()
    if (!WiFi.config(local_IP, gateway, subnet, primaryDNS, secondaryDNS)) {
        Serial.println("Static IP configuration failed!");
    }
    
    WiFi.begin(ssid, password);
    
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    
    Serial.println("");
    Serial.print("Camera Ready! Use 'http://");
    Serial.print(WiFi.localIP());
    Serial.println("' to connect");
}
```

### Important Notes for Static IP

> [!CAUTION]
> - The **gateway IP** must match your router's IP (usually `192.168.1.1`, `192.168.0.1`, or `192.168.18.1`).
> - The **subnet** should be `255.255.255.0` for most home networks.
> - The **static IP** must be on the same subnet as your router (e.g., if the router is `192.168.18.1`, use `192.168.18.X`).
> - Choose an IP **outside your router's DHCP range** to avoid conflicts. Check your router admin panel for the DHCP range.

### Router-Side Static IP (Alternative)

Instead of modifying the Arduino code, you can reserve a static IP in your router:

1. Open router admin panel (`http://192.168.18.1`)
2. Find **DHCP Reservation** or **Address Reservation**
3. Add the ESP32-CAM's **MAC address** with the desired IP (`192.168.18.200`)
4. Save and reboot the router

This approach does not require re-flashing the ESP32-CAM.

---

## 12. Quick Update Checklist

Use this checklist every time the ESP32-CAM IP address changes:

```
┌──────────────────────────────────────────────────────────────────┐
│           ESP32-CAM IP ADDRESS CHANGE CHECKLIST                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  □  1. Get the new IP from Serial Monitor / Router / Fing app   │
│                                                                  │
│  □  2. Test in browser: http://NEW_IP/ (web UI loads?)          │
│                                                                  │
│  □  3. Test endpoint: http://NEW_IP/capture (image loads?)      │
│        OR: http://NEW_IP:81/stream (video plays?)               │
│                                                                  │
│  □  4. Open config.py in your editor                            │
│                                                                  │
│  □  5. Update CAMERA_URL = "http://NEW_IP/capture"              │
│        (or "http://NEW_IP:81/stream" if stream works)           │
│                                                                  │
│  □  6. Set CAPTURE_MODE = True (for /capture)                   │
│        or CAPTURE_MODE = False (for :81/stream)                 │
│                                                                  │
│  □  7. Save config.py (Ctrl + S)                                │
│                                                                  │
│  □  8. Stop Flask server (Ctrl + C in terminal)                 │
│                                                                  │
│  □  9. Restart Flask: python app.py                             │
│                                                                  │
│  □ 10. Verify 10/10 startup checks pass (all [OK])             │
│                                                                  │
│  □ 11. Open dashboard: http://127.0.0.1:5000                   │
│                                                                  │
│  □ 12. Confirm live video feed is visible                       │
│                                                                  │
│  □ 13. Test face recognition (stand in front of camera)         │
│                                                                  │
│  □ 14. Verify attendance is marked in the panel                 │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 13. Appendix

### A. Sample `config.py` — Camera Section

```python
import os

# ==============================================================================
#  AI Face Recognition Attendance System - Enterprise Configuration
# ==============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ┌─────────────────────────────────────────────────────────────────┐
# │  CAMERA STREAM CONFIGURATION                                    │
# │  Update CAMERA_URL when the ESP32-CAM IP address changes.       │
# └─────────────────────────────────────────────────────────────────┘

CAMERA_URL = "http://192.168.43.105/capture"   # ◄── CHANGE THIS IP
ESP32_STREAM_URL = CAMERA_URL
CAMERA_SOURCE = CAMERA_URL

CAPTURE_MODE = True          # True = /capture (snapshot), False = :81/stream (MJPEG)
AUTO_RECONNECT = True        # Auto-reconnect on Wi-Fi dropouts
CAMERA_RECONNECT_INTERVAL = 1.5   # Seconds between reconnect attempts
CAMERA_FPS_TARGET = 15       # Target FPS
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
JPEG_QUALITY = 80
STREAM_READ_TIMEOUT = 5.0

# Face Recognition
RECOGNITION_TOLERANCE = 0.45
FRAME_SKIP = 3
PROCESS_SCALE = 0.5
DETECTION_MODEL = "hog"

# Anti-Spoofing
ANTI_SPOOFING_ENABLED = True
```

### B. Sample Startup Verification Output

When the server starts correctly, you should see:

```
==============================================================================
   AI FACE RECOGNITION ATTENDANCE SYSTEM - ENTERPRISE EDITION
==============================================================================

[*] Server Initializing: 2026-08-06 18:00:46
[*] Target Stream Source: http://192.168.43.105/capture

------------------------------------------------------------------------------
  #   SYSTEM PRE-FLIGHT VERIFICATION ITEM                 STATUS
------------------------------------------------------------------------------
 [01] Python 3.11 Runtime & Operating System           [OK]
 [02] Core AI & Computer Vision Libraries              [OK]
 [03] ESP32-CAM Stream & Network Config                [OK]
 [04] Known Faces Database & Encodings Cache           [OK]
 [05] Daily Attendance Storage & Permissions           [OK]
 [06] Unknown Visitor Auto-Capture Registry            [OK]
 [07] Institutional Reports Export Engine              [OK]
 [08] Multi-File Rotating Logging Subsystem            [OK]
 [09] Web Templates & Static Client Assets             [OK]
 [10] Admin Security & Session Encryption              [OK]
------------------------------------------------------------------------------
[*] Pre-flight Checklist Completed | Status: ALL READY
==============================================================================

 * Running on http://127.0.0.1:5000
 * Running on http://192.168.43.245:5000
```

### C. Common ESP32-CAM Firmware Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `http://IP/` | GET | Camera web interface (HTML) |
| `http://IP/capture` | GET | Single JPEG snapshot |
| `http://IP:81/stream` | GET | Continuous MJPEG stream |
| `http://IP/status` | GET | Camera sensor status (JSON) |
| `http://IP/control?var=framesize&val=8` | GET | Change resolution (VGA=8) |
| `http://IP/control?var=quality&val=10` | GET | Change JPEG quality (4–63) |

### D. IP Address History Log

Keep a record of IP changes for your institution:

| Date | Old IP | New IP | Reason | Updated By |
| :--- | :--- | :--- | :--- | :--- |
| 2026-08-06 | `192.168.18.142:81/stream` | `192.168.43.105/capture` | Changed to phone hotspot | Admin |
| | | | | |
| | | | | |

---

> **Document End** — For questions or issues, contact the system administrator or refer to the project [README.md](./README.md).
