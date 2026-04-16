"""
Message sender modules for SMS, WhatsApp, and Email.
Each sender can be configured via settings.
"""

import json
import smtplib
import base64
import urllib.request
import urllib.error
import urllib.parse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from database import get_db


def _get_setting(key: str, default: str = '') -> str:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else default


def send_sms(to_phone: str, message: str) -> dict:
    """
    Send SMS via Twilio.
    Requires settings: twilio_account_sid, twilio_auth_token, twilio_from_number
    """
    account_sid = _get_setting('twilio_account_sid')
    auth_token = _get_setting('twilio_auth_token')
    from_number = _get_setting('twilio_from_number')

    if not all([account_sid, auth_token, from_number]):
        return {'success': False, 'error': 'Twilio not configured. Set twilio_account_sid, twilio_auth_token, twilio_from_number in settings.'}

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

    data = urllib.parse.urlencode({
        'To': to_phone,
        'From': from_number,
        'Body': message,
    }).encode()

    credentials = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()

    req = urllib.request.Request(url, data=data, headers={
        'Authorization': f'Basic {credentials}',
    })

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            return {'success': True, 'sid': result.get('sid', '')}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        return {'success': False, 'error': f"Twilio error {e.code}: {error_body}"}


def send_whatsapp(to_phone: str, message: str) -> dict:
    """
    Send WhatsApp message via Twilio WhatsApp API.
    Requires settings: twilio_account_sid, twilio_auth_token, twilio_whatsapp_from
    """
    account_sid = _get_setting('twilio_account_sid')
    auth_token = _get_setting('twilio_auth_token')
    from_number = _get_setting('twilio_whatsapp_from')

    if not all([account_sid, auth_token, from_number]):
        return {'success': False, 'error': 'Twilio WhatsApp not configured. Set twilio_whatsapp_from in settings.'}

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

    if not to_phone.startswith('whatsapp:'):
        to_phone = f"whatsapp:{to_phone}"
    if not from_number.startswith('whatsapp:'):
        from_number = f"whatsapp:{from_number}"

    data = urllib.parse.urlencode({
        'To': to_phone,
        'From': from_number,
        'Body': message,
    }).encode()

    credentials = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()

    req = urllib.request.Request(url, data=data, headers={
        'Authorization': f'Basic {credentials}',
    })

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            return {'success': True, 'sid': result.get('sid', '')}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        return {'success': False, 'error': f"WhatsApp error {e.code}: {error_body}"}


def send_email(to_email: str, subject: str, message: str) -> dict:
    """
    Send email via SMTP.
    Requires settings: smtp_host, smtp_port, smtp_user, smtp_password, smtp_from_email, smtp_from_name
    """
    smtp_host = _get_setting('smtp_host', 'smtp.gmail.com')
    smtp_port = int(_get_setting('smtp_port', '587'))
    smtp_user = _get_setting('smtp_user')
    smtp_password = _get_setting('smtp_password')
    from_email = _get_setting('smtp_from_email')
    from_name = _get_setting('smtp_from_name', 'CodePros')

    if not all([smtp_user, smtp_password, from_email]):
        return {'success': False, 'error': 'SMTP not configured. Set smtp_host, smtp_port, smtp_user, smtp_password, smtp_from_email in settings.'}

    msg = MIMEMultipart()
    msg['From'] = f"{from_name} <{from_email}>"
    msg['To'] = to_email
    msg['Subject'] = subject or 'Mazel Tov!'
    msg.attach(MIMEText(message, 'plain'))

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def send_draft(draft_id: int) -> dict:
    """Send a specific draft message."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,))
    draft = cursor.fetchone()

    if not draft:
        conn.close()
        return {'success': False, 'error': 'Draft not found'}

    if draft['status'] == 'sent':
        conn.close()
        return {'success': False, 'error': 'Already sent'}

    draft_dict = dict(draft)
    channel = draft_dict['channel']

    if channel == 'sms':
        result = send_sms(draft_dict['recipient_phone'], draft_dict['message'])
    elif channel == 'whatsapp':
        result = send_whatsapp(draft_dict['recipient_phone'], draft_dict['message'])
    elif channel == 'email':
        result = send_email(draft_dict['recipient_email'], draft_dict.get('subject', ''), draft_dict['message'])
    else:
        result = {'success': False, 'error': f'Unknown channel: {channel}'}

    # Update draft status
    new_status = 'sent' if result['success'] else 'failed'
    cursor.execute("""
        UPDATE drafts SET status = ?, sent_at = ? WHERE id = ?
    """, (new_status, datetime.now().isoformat() if result['success'] else None, draft_id))

    conn.commit()
    conn.close()

    return result
