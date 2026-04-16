# SimchaLeads

Automated engagement lead management system for **CodePros**. Monitors [Simchaspot](https://www.instagram.com/simchaspot/) Instagram for new engagement announcements, cross-references couples with your contact directory, generates personalized mazel tov messages with a discount offer, and lets you review and send them via SMS, WhatsApp, or email.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Instagram API Setup](#instagram-api-setup)
  - [Twilio Setup (SMS & WhatsApp)](#twilio-setup-sms--whatsapp)
  - [Email Setup (SMTP)](#email-setup-smtp)
- [Usage](#usage)
  - [Starting the App](#starting-the-app)
  - [Dashboard Overview](#dashboard-overview)
  - [Importing Contacts](#importing-contacts)
  - [Adding Engagements](#adding-engagements)
  - [Running the Pipeline](#running-the-pipeline)
  - [Reviewing & Sending Drafts](#reviewing--sending-drafts)
- [API Reference](#api-reference)
- [Contact File Formats](#contact-file-formats)
- [Name Matching](#name-matching)
- [Message Templates](#message-templates)

---

## Features

- **Instagram Scraper** - Fetches engagement announcements from Simchaspot via Meta Graph API
- **Manual Entry** - Add engagements manually from the dashboard
- **Contact Import** - Import contacts from CSV or VCF files (export from Smartlist Phone app)
- **Smart Matching** - Cross-references engagement names with your contact directory, including Jewish name variant recognition (e.g., Moshe/Moishe, Rivka/Rivky)
- **Draft Generator** - Auto-creates personalized mazel tov messages with your discount offer
- **Multi-Channel Sending** - Send via SMS (Twilio), WhatsApp (Twilio), or Email (SMTP)
- **Review Workflow** - Draft > Approve > Send workflow so you control every message
- **Web Dashboard** - Clean, responsive UI to manage the entire pipeline

---

## Architecture

| Component       | Technology           |
|-----------------|----------------------|
| Backend         | Python 3.12, FastAPI |
| Database        | SQLite               |
| Frontend        | HTML, CSS, JavaScript|
| Instagram API   | Meta Graph API       |
| SMS & WhatsApp  | Twilio API           |
| Email           | SMTP (Gmail, etc.)   |

---

## Project Structure

```
SimchaLeads/
├── backend/
│   ├── main.py          # FastAPI app - API routes and server
│   ├── database.py      # SQLite schema, connection, initialization
│   ├── scraper.py       # Instagram scraper (Graph API + web fallback)
│   ├── matcher.py       # Contact matching with name variant support
│   ├── drafts.py        # Message draft generator
│   └── sender.py        # SMS, WhatsApp, and Email senders
├── frontend/
│   ├── index.html       # Dashboard UI
│   ├── css/
│   │   └── style.css    # Styles
│   └── js/
│       └── app.js       # Frontend logic
├── data/                # Database files (auto-created, gitignored)
├── .env.example         # Environment variable template
├── .gitignore
├── requirements.txt     # Python dependencies
├── start.bat            # Windows launcher
└── README.md
```

---

## Prerequisites

- **Python 3.10+** - [Download](https://www.python.org/downloads/)
- **pip** - Included with Python
- **Smartlist Phone app** - For exporting your contact directory ([Google Play](https://play.google.com/store/apps/details?id=com.lionscribe.elist) / [App Store](https://apps.apple.com/us/app/smartlist-local-directory/id447390050))

Optional (for sending messages):
- **Twilio account** - For SMS and WhatsApp ([twilio.com](https://www.twilio.com/))
- **Meta Developer account** - For Instagram API ([developers.facebook.com](https://developers.facebook.com/))
- **Gmail App Password** - For email sending ([Google Account](https://myaccount.google.com/apppasswords))

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/codepros100-dev/SimchaLeads.git
cd SimchaLeads

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize the database
python backend/database.py

# 4. Start the server
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Or on Windows, simply double-click **`start.bat`**.

Then open **http://127.0.0.1:8000** in your browser.

---

## Configuration

All settings can be configured from the **Settings** tab in the dashboard, or by editing the database directly.

### Instagram API Setup

1. Create a [Meta Developer](https://developers.facebook.com/) account
2. Create a new app with **Instagram Graph API** product
3. Connect your Instagram Business account
4. Generate a long-lived access token
5. In the dashboard Settings tab, enter:
   - `ig_access_token` - Your Meta Graph API token
   - `ig_user_id` - The Instagram user ID for Simchaspot

> **Without API credentials**: You can still add engagements manually from the Engagements tab.

### Twilio Setup (SMS & WhatsApp)

1. Create a [Twilio](https://www.twilio.com/) account
2. Get a phone number with SMS capabilities
3. For WhatsApp, enable the [Twilio WhatsApp Sandbox](https://www.twilio.com/docs/whatsapp/sandbox)
4. In the dashboard Settings tab, enter:
   - `twilio_account_sid` - Your Account SID
   - `twilio_auth_token` - Your Auth Token
   - `twilio_from_number` - Your Twilio phone number (e.g., +17325551234)
   - `twilio_whatsapp_from` - Your WhatsApp-enabled number

### Email Setup (SMTP)

For Gmail:
1. Enable [2-Step Verification](https://myaccount.google.com/security) on your Google account
2. Generate an [App Password](https://myaccount.google.com/apppasswords)
3. In the dashboard Settings tab, enter:
   - `smtp_host` - `smtp.gmail.com`
   - `smtp_port` - `587`
   - `smtp_user` - Your Gmail address
   - `smtp_password` - Your app password (NOT your Gmail password)
   - `smtp_from_email` - Your Gmail address
   - `smtp_from_name` - `CodePros`

---

## Usage

### Starting the App

```bash
# Windows
start.bat

# Any OS
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000** in your browser.

### Dashboard Overview

The dashboard shows six stat cards:
- **Engagements** - Total engagement announcements tracked
- **Contacts** - Total contacts in your directory
- **Matches** - Engagements matched to contacts
- **Pending Drafts** - Messages awaiting your review
- **Approved** - Messages you've approved, ready to send
- **Sent** - Messages successfully delivered

Quick action buttons let you run individual steps or the full pipeline.

### Importing Contacts

1. **Export from Smartlist**: Open Smartlist Phone app > Select contacts > Share/Export to your phone contacts
2. **Export from phone**: Export your phone contacts as a `.csv` or `.vcf` file
3. **Upload**: Go to the **Contacts** tab > Upload the file
4. **Community** (optional): Tag contacts with a community name (e.g., "Lakewood")

### Adding Engagements

**Automatically (with Instagram API configured):**
- Click **"Scrape Instagram"** on the dashboard
- The scraper fetches recent Simchaspot posts and extracts engagement names

**Manually:**
- Go to the **Engagements** tab
- Fill in the Chatan and Kallah names
- Click **"Add Engagement"**

### Running the Pipeline

Click **"Run Full Pipeline"** on the dashboard. This runs three steps in sequence:

1. **Scrape** - Fetches new engagements from Instagram
2. **Match** - Cross-references names against your contact directory
3. **Generate Drafts** - Creates personalized messages for each match

You can also run each step individually from the Quick Actions panel.

### Reviewing & Sending Drafts

1. Go to the **Drafts & Send** tab
2. Filter by status (Draft, Approved, Sent) or channel (SMS, WhatsApp, Email)
3. For each draft you can:
   - **Edit** - Modify the message text
   - **Approve** - Mark as ready to send
   - **Delete** - Remove the draft
   - **Send** - Deliver the message (requires channel configuration)
4. Use **"Approve All"** and **"Send All Approved"** for bulk actions

---

## API Reference

All endpoints are available at `http://127.0.0.1:8000/api/`.

### Stats
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats` | Dashboard statistics |

### Engagements
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/engagements` | List all engagements |
| POST | `/api/engagements/manual` | Add engagement manually |
| DELETE | `/api/engagements/{id}` | Delete an engagement |

**POST body** for manual engagement:
```json
{
  "chatan_first": "Moshe",
  "chatan_last": "Cohen",
  "kallah_first": "Sarah",
  "kallah_last": "Levy"
}
```

### Contacts
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/contacts` | List contacts (supports `?search=`) |
| POST | `/api/contacts/import` | Import CSV or VCF file (multipart form) |

### Matching
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/match` | Run matching on all unmatched engagements |
| GET | `/api/matches` | List all matches (supports `?engagement_id=`) |

### Drafts
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/drafts/generate` | Generate drafts for all matched engagements |
| GET | `/api/drafts` | List drafts (supports `?status=`, `?channel=`) |
| PUT | `/api/drafts/{id}` | Update draft (message, status, channel) |
| DELETE | `/api/drafts/{id}` | Delete a draft |

### Sending
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/send/{id}` | Send a single draft |
| POST | `/api/send/bulk` | Send multiple drafts (`{"draft_ids": [1,2,3]}`) |

### Settings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings` | Get all settings (sensitive values masked) |
| POST | `/api/settings` | Update settings (`{"key": "value"}`) |

### Pipeline
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/pipeline/run` | Run full pipeline (scrape + match + drafts) |

---

## Contact File Formats

### CSV Format
```csv
first_name,last_name,phone,email,address,city
Moshe,Cohen,732-555-1234,moshe@email.com,123 Main St,Lakewood
Sarah,Levy,732-555-5678,sarah@email.com,456 Oak Ave,Lakewood
```

Flexible column names are supported:
- Name: `first`, `first_name`, `firstname`, `first name`
- Name: `last`, `last_name`, `lastname`, `last name`, `surname`
- Phone: `phone`, `telephone`, `tel`, `mobile`, `cell`
- Email: `email`, `e-mail`, `email address`
- Address: `address`, `street`, `street address`
- City: `city`, `town`

### VCF Format (vCard)
Standard vCard 3.0/4.0 format as exported from phone contacts:
```
BEGIN:VCARD
VERSION:3.0
N:Cohen;Moshe;;;
TEL:732-555-1234
EMAIL:moshe@email.com
ADR:;;123 Main St;Lakewood;NJ;08701;
END:VCARD
```

---

## Name Matching

The matcher uses a multi-level strategy:

1. **Exact last name match** - Finds all contacts sharing the engagement's last name
2. **First name similarity** - Scores how closely first names match
3. **Jewish name variants** - Recognizes common variant spellings

### Supported Name Variants

| Canonical | Also matches |
|-----------|-------------|
| Moshe | Moishe, Moses |
| Yosef | Yossi, Joseph, Joe |
| Yaakov | Yanky, Jacob, Jake |
| Avraham | Avrumi, Avi, Abraham |
| Shmuel | Samuel, Sam |
| Dovid | David, Dave |
| Chaim | Hyman |
| Yehuda | Yehudi, Judah |
| Menachem | Mendel |
| Eliezer | Eli, Lazer |
| Aharon | Aaron |
| Binyamin | Benjamin, Ben |
| Shlomo | Solomon |
| Nosson | Nathan, Noach |
| Rivka | Rebecca, Rivky |
| Sarah | Sara |
| Rachel | Rochel, Ruchel |
| Leah | Lea |
| Miriam | Miri |
| Chana | Hannah, Hanna |
| Devorah | Devora, Deborah, Debra |
| Esther | Esti |
| Malka | Malky |
| Shira | Shiri |
| Tziporah | Tzipi, Tzipora |

### Match Types

| Type | Description | Confidence |
|------|-------------|------------|
| `chatan` | Direct match to the chatan | 0.85 - 1.0 |
| `kallah` | Direct match to the kallah | 0.85 - 1.0 |
| `chatan_family` | Same last name as chatan | 0.7 |
| `kallah_family` | Same last name as kallah | 0.7 |

---

## Message Templates

Templates use placeholder variables that get filled in automatically:

| Variable | Description | Example |
|----------|-------------|---------|
| `{recipient_name}` | Contact's full name | Moshe Cohen |
| `{chatan}` | Chatan's full name | Dovid Goldstein |
| `{kallah}` | Kallah's full name | Sarah Levy |
| `{business_name}` | Your business name | CodePros |
| `{discount}` | Discount percentage | 5 |

### Default SMS/WhatsApp Template
```
Mazel Tov {recipient_name} on the engagement of {chatan} & {kallah}!

From all of us at {business_name}, we wish you a beautiful journey ahead.

As a special mazel tov gift, we'd like to offer you {discount}% off our services.

Reach out anytime to learn more!
- {business_name}
```

### Default Email Template
```
Dear {recipient_name},

Mazel Tov on the engagement of {chatan} & {kallah}!

From all of us at {business_name}, we wish you a beautiful journey ahead.

As a special mazel tov gift, we'd like to offer you {discount}% off our services.

We'd love to help make this simcha even more special.
Feel free to reach out anytime to learn more about what we offer.

With warm wishes,
{business_name}
```

Templates can be customized in the **Settings** tab.

---

## License

Private - CodePros Internal Use
