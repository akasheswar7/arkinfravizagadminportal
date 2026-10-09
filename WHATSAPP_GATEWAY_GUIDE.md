# ARK Infra Vizag — 100% Free WhatsApp Gateway Guide

## 📌 Overview
This system provides **100% Free, Automated Bulk WhatsApp Broadcasting** with **Zero Popups** for the ARK Infra Admin Portal (`arkinfravizag.com/admin`).

- **Cost:** ₹0 / $0 Forever (No subscriptions, No UltraMsg, No Meta Cloud API per-message costs).
- **Popup-Free:** Zero browser windows, zero `wa.me/` redirects, zero desktop app popups. Messages deliver silently in the background directly into recipients' WhatsApp.
- **Capacity:** Broadcasts to all 151 members (16 Directors, 135 Agents) and customer leads.
- **Anti-Ban Protection:** Automatic 1.5-second pacing delay between messages to comply with WhatsApp delivery standards.

---

## 🚀 Quick Start (1-Click Startup)

Whenever your computer starts:
1. Double-click **`Start_WhatsApp_Gateway.bat`** on your Desktop.
2. The gateway will start silently on `http://localhost:3300` and automatically open the status dashboard in your browser.

---

## 📱 How to Link Your WhatsApp Number

1. Go to **[arkinfravizag.com/admin](https://www.arkinfravizag.com/admin)**.
2. In the **WhatsApp Broadcast Hub** section, click the button:
   `⚪ WhatsApp Not Linked (Click to Link)`
3. On your mobile phone:
   - Open **WhatsApp**.
   - Tap **⋮ (Three dots)** (Android) or **Settings** (iPhone).
   - Tap **Linked devices** ➔ **Link a device**.
   - Point your phone's camera at the QR code on your computer screen.
4. Within 2 seconds, the button in the Admin Portal will turn green:
   `🟢 WhatsApp Linked (+91 [Phone Number])`

> **Note:** You only need to scan once. Your session is saved permanently in `whatsapp-gateway/auth_info_baileys/`.

---

## 🤖 Sending 1-Click Silent Broadcasts

1. Select your target group (e.g., **All Members (151)**, **Executive Directors**, or **Director Teams**).
2. Type your announcement or choose a preset (e.g., *Meeting Notice*).
3. Ensure member checkboxes are ticked.
4. Click:
   **`🤖 1-Click Silent Send (Zero Popups)`**
5. Sit back! The portal will silently dispatch the message to all members in the background.

---

## 🔄 How to Switch or Unlink Numbers

If you ever want to change the sender phone number:
1. Click the status button in the Admin Portal: `🟢 WhatsApp Linked (+91 ...)`.
2. Click **`Unlink / Connect Another Number`**.
3. A fresh QR code will appear immediately. Scan with your new phone.

---

## 🛠 Gateway Architecture & API Endpoints

- **Engine:** `@whiskeysockets/baileys` on Node.js v24
- **Port:** `3300`
- **Location:** `C:\Users\ravid\OneDrive\Desktop\ARK INFRA\whatsapp-gateway`
- **Session Cache:** `whatsapp-gateway\auth_info_baileys\`

### Available Endpoints:
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Branded QR Dashboard for web browsers |
| `GET` | `/status` | Returns `{ success, connected, phone, qr, activeJob }` |
| `POST` | `/send` | Body: `{ phone, message }` — Sends a single message |
| `POST` | `/bulk-send` | Body: `{ phones: [...], message, delayMs: 1500 }` — Silent bulk queue |
| `POST` | `/logout` | Unlinks the session and clears authentication cache |

---

## ❓ Troubleshooting

| Issue | Cause | Solution |
|---|---|---|
| Button shows `⚪ WhatsApp Not Linked` | Gateway is not running | Double-click `Start_WhatsApp_Gateway.bat` on Desktop |
| QR Code expired | WhatsApp QR refreshed | Wait 5 seconds; the QR code auto-refreshes automatically |
| Admin portal shows old badge | Browser cache | Press `Ctrl + F5` to hard refresh the page |
