"""
SimchaLeads - FastAPI Backend
Engagement lead generation from Simchaspot Instagram.
"""

import os
import sys
import json
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Add backend dir to path
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, get_db
from scraper import scrape_and_save, add_engagement_manual, parse_engagement_caption
from matcher import import_contacts_csv, import_contacts_vcf, run_matching
from drafts import generate_all_drafts, generate_drafts_for_engagement
from sender import send_draft

app = FastAPI(title="SimchaLeads", version="1.0.0")

# Serve frontend
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# Initialize database on startup
@app.on_event("startup")
def startup():
    init_db()


# ─── Dashboard ─────────────────────────────────────────────

@app.get("/")
def serve_frontend():
    return FileResponse(os.path.join(FRONTEND_DIR, 'index.html'))


# ─── Stats ─────────────────────────────────────────────────

@app.get("/api/stats")
def get_stats():
    conn = get_db()
    c = conn.cursor()
    stats = {
        'engagements': c.execute("SELECT COUNT(*) FROM engagements").fetchone()[0],
        'contacts': c.execute("SELECT COUNT(*) FROM contacts").fetchone()[0],
        'matches': c.execute("SELECT COUNT(*) FROM matches").fetchone()[0],
        'drafts_pending': c.execute("SELECT COUNT(*) FROM drafts WHERE status = 'draft'").fetchone()[0],
        'drafts_approved': c.execute("SELECT COUNT(*) FROM drafts WHERE status = 'approved'").fetchone()[0],
        'sent': c.execute("SELECT COUNT(*) FROM drafts WHERE status = 'sent'").fetchone()[0],
    }
    conn.close()
    return stats


# ─── Engagements ───────────────────────────────────────────

@app.get("/api/engagements")
def list_engagements(limit: int = 50, offset: int = 0):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT e.*,
            (SELECT COUNT(*) FROM matches m WHERE m.engagement_id = e.id) as match_count,
            (SELECT COUNT(*) FROM drafts d WHERE d.engagement_id = e.id) as draft_count
        FROM engagements e
        ORDER BY e.scraped_at DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


class ManualEngagement(BaseModel):
    chatan_first: str
    chatan_last: str = ''
    kallah_first: str
    kallah_last: str = ''
    source_url: str = ''


@app.post("/api/engagements/manual")
def add_manual_engagement(eng: ManualEngagement):
    count = add_engagement_manual(
        eng.chatan_first, eng.chatan_last,
        eng.kallah_first, eng.kallah_last,
        eng.source_url
    )
    return {'added': count}


@app.delete("/api/engagements/{engagement_id}")
def delete_engagement(engagement_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM drafts WHERE engagement_id = ?", (engagement_id,))
    c.execute("DELETE FROM matches WHERE engagement_id = ?", (engagement_id,))
    c.execute("DELETE FROM engagements WHERE id = ?", (engagement_id,))
    conn.commit()
    conn.close()
    return {'deleted': True}


# ─── Scraping ─────────────────────────────────────────────

@app.post("/api/scrape")
def run_scrape():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = 'ig_access_token'")
    token_row = c.fetchone()
    c.execute("SELECT value FROM settings WHERE key = 'ig_user_id'")
    uid_row = c.fetchone()
    conn.close()

    token = token_row['value'] if token_row else None
    uid = uid_row['value'] if uid_row else None

    result = scrape_and_save(access_token=token, ig_user_id=uid)
    return result


# ─── Contacts ─────────────────────────────────────────────

@app.get("/api/contacts")
def list_contacts(limit: int = 50, offset: int = 0, search: str = ''):
    conn = get_db()
    c = conn.cursor()
    if search:
        c.execute("""
            SELECT * FROM contacts
            WHERE first_name LIKE ? OR last_name LIKE ? OR phone LIKE ?
            ORDER BY last_name, first_name
            LIMIT ? OFFSET ?
        """, (f'%{search}%', f'%{search}%', f'%{search}%', limit, offset))
    else:
        c.execute("""
            SELECT * FROM contacts
            ORDER BY last_name, first_name
            LIMIT ? OFFSET ?
        """, (limit, offset))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


@app.post("/api/contacts/import")
async def import_contacts(
    file: UploadFile = File(...),
    community: str = Form('')
):
    content = (await file.read()).decode('utf-8', errors='ignore')
    filename = file.filename.lower()

    if filename.endswith('.vcf'):
        count = import_contacts_vcf(content, community)
    elif filename.endswith('.csv'):
        count = import_contacts_csv(content, community)
    else:
        raise HTTPException(400, "Unsupported file format. Use .csv or .vcf")

    return {'imported': count, 'filename': file.filename}


# ─── Matching ─────────────────────────────────────────────

@app.post("/api/match")
def run_match():
    result = run_matching()
    return result


@app.get("/api/matches")
def list_matches(engagement_id: int = None):
    conn = get_db()
    c = conn.cursor()
    if engagement_id:
        c.execute("""
            SELECT m.*, c.first_name, c.last_name, c.phone, c.email, c.address,
                   e.chatan_first, e.chatan_last, e.kallah_first, e.kallah_last
            FROM matches m
            JOIN contacts c ON m.contact_id = c.id
            JOIN engagements e ON m.engagement_id = e.id
            WHERE m.engagement_id = ?
            ORDER BY m.confidence DESC
        """, (engagement_id,))
    else:
        c.execute("""
            SELECT m.*, c.first_name, c.last_name, c.phone, c.email, c.address,
                   e.chatan_first, e.chatan_last, e.kallah_first, e.kallah_last
            FROM matches m
            JOIN contacts c ON m.contact_id = c.id
            JOIN engagements e ON m.engagement_id = e.id
            ORDER BY m.matched_at DESC
        """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


# ─── Drafts ───────────────────────────────────────────────

@app.post("/api/drafts/generate")
def generate_drafts():
    result = generate_all_drafts()
    return result


@app.get("/api/drafts")
def list_drafts(status: str = '', channel: str = '', limit: int = 50, offset: int = 0):
    conn = get_db()
    c = conn.cursor()

    query = """
        SELECT d.*, e.chatan_first, e.chatan_last, e.kallah_first, e.kallah_last
        FROM drafts d
        JOIN engagements e ON d.engagement_id = e.id
        WHERE 1=1
    """
    params = []

    if status:
        query += " AND d.status = ?"
        params.append(status)
    if channel:
        query += " AND d.channel = ?"
        params.append(channel)

    query += " ORDER BY d.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


class DraftUpdate(BaseModel):
    message: str = None
    subject: str = None
    status: str = None
    channel: str = None


@app.put("/api/drafts/{draft_id}")
def update_draft(draft_id: int, update: DraftUpdate):
    conn = get_db()
    c = conn.cursor()

    updates = []
    params = []
    if update.message is not None:
        updates.append("message = ?")
        params.append(update.message)
    if update.subject is not None:
        updates.append("subject = ?")
        params.append(update.subject)
    if update.status is not None:
        updates.append("status = ?")
        params.append(update.status)
    if update.channel is not None:
        updates.append("channel = ?")
        params.append(update.channel)

    if not updates:
        raise HTTPException(400, "No fields to update")

    params.append(draft_id)
    c.execute(f"UPDATE drafts SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    return {'updated': True}


@app.delete("/api/drafts/{draft_id}")
def delete_draft(draft_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM drafts WHERE id = ?", (draft_id,))
    conn.commit()
    conn.close()
    return {'deleted': True}


# ─── Sending ──────────────────────────────────────────────

@app.post("/api/send/{draft_id}")
def send_single(draft_id: int):
    result = send_draft(draft_id)
    if not result['success']:
        raise HTTPException(400, result.get('error', 'Send failed'))
    return result


@app.post("/api/send/bulk")
async def send_bulk(request: Request):
    body = await request.json()
    draft_ids = body.get('draft_ids', [])
    results = []
    for did in draft_ids:
        result = send_draft(did)
        results.append({'draft_id': did, **result})
    return {'results': results}


# ─── Settings ─────────────────────────────────────────────

@app.get("/api/settings")
def get_settings():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT key, value FROM settings")
    settings = {row['key']: row['value'] for row in c.fetchall()}
    conn.close()
    # Mask sensitive values
    for key in settings:
        if any(s in key for s in ['token', 'password', 'secret', 'auth_token']):
            if settings[key]:
                settings[key] = settings[key][:4] + '****'
    return settings


@app.post("/api/settings")
async def update_settings(request: Request):
    body = await request.json()
    conn = get_db()
    c = conn.cursor()
    for key, value in body.items():
        c.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
            (key, value, value)
        )
    conn.commit()
    conn.close()
    return {'updated': len(body)}


# ─── Pipeline (full flow) ─────────────────────────────────

@app.post("/api/pipeline/run")
def run_full_pipeline():
    """Run the full pipeline: scrape -> match -> generate drafts."""
    scrape_result = run_scrape()
    match_result = run_match()
    draft_result = generate_drafts()
    return {
        'scrape': scrape_result,
        'match': match_result,
        'drafts': draft_result,
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)
