# ARK Infra — Executive Admin & Dynamic CMS Portal

Official Executive Admin and Management Portal for **ARK Infra**.

---

## 🚀 Features

- **Executive Overview Dashboard:** Live business metrics, director counts, agent rosters, and customer lead counters.
- **Directors Management:** Full CRUD operations with bio, contact details, executive quotes, and photo uploads.
- **Agents Roster:** Complete field consultant management mapped directly to reporting directors.
- **Customer Leads Tracker:** Filter and update site visit and registration statuses in real time.
- **Visual Gallery:** Project inspection and celebration photo showcase.
- **Homepage Announcements:** Real-time dynamic banner controller for the public website.
- **Confidential PDF Reports:** ReportLab-powered luxury dossier and customer summary generator.
- **WhatsApp Broadcast Dispatch:** Direct dispatch link generator for field teams.

---

## ⚙️ Environment Variables (Vercel / Cloud Setup)

When deploying to **Vercel**, add these variables under **Project Settings &rarr; Environment Variables**:

| Variable | Description | Example / Recommended Value |
| :--- | :--- | :--- |
| `MONGODB_URI` | MongoDB Atlas Connection String | `mongodb+srv://...` |
| `DATABASE_NAME` | Active Database Name | `arkinfradev` |
| `JWT_SECRET` | Secret key for JWT session tokens | `ark_infra_jwt_secret_key_8492018392183902` |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `JWT_EXPIRATION_MINUTES` | Session validity | `480` |
| `ADMIN_EMAIL` | Executive login email | `admin@arkinfravizag.com` |
| `ADMIN_PASSWORD` | Executive login password | *(Your chosen password)* |
| `ALLOWED_ORIGINS` | Permitted web origins | `*` |
| `STORAGE_MODE` | Storage mode (`local` or `cloud`) | `local` |

---

## 🛠️ Deploy to Vercel

1. Import this repository into [Vercel](https://vercel.com).
2. Framework Preset: **Other**.
3. Add the **Environment Variables** listed above.
4. Click **Deploy**!
