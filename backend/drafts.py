"""
Draft message generator.
Creates personalized mazel tov + discount messages for matched contacts.
"""

from database import get_db


def get_templates() -> dict:
    """Load message templates from settings."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    settings = {row['key']: row['value'] for row in cursor.fetchall()}
    conn.close()
    return settings


def generate_message(template: str, engagement: dict, contact: dict,
                     match_type: str, settings: dict) -> str:
    """Fill in a message template with engagement + contact details."""
    chatan = engagement['chatan_first']
    if engagement.get('chatan_last'):
        chatan += f" {engagement['chatan_last']}"

    kallah = engagement['kallah_first']
    if engagement.get('kallah_last'):
        kallah += f" {engagement['kallah_last']}"

    # Determine recipient name
    if match_type in ('chatan', 'chatan_family'):
        recipient = f"{contact['first_name']} {contact['last_name']}"
    else:
        recipient = f"{contact['first_name']} {contact['last_name']}"

    return template.format(
        recipient_name=recipient,
        chatan=chatan,
        kallah=kallah,
        business_name=settings.get('business_name', 'CodePros'),
        discount=settings.get('discount_percent', '5'),
    )


def generate_drafts_for_engagement(engagement_id: int) -> int:
    """Generate draft messages for all matches of an engagement."""
    conn = get_db()
    cursor = conn.cursor()
    settings = get_templates()

    # Get engagement
    cursor.execute("SELECT * FROM engagements WHERE id = ?", (engagement_id,))
    eng = cursor.fetchone()
    if not eng:
        conn.close()
        return 0

    eng_dict = dict(eng)

    # Get matches with contact info
    cursor.execute("""
        SELECT m.*, c.first_name, c.last_name, c.phone, c.email
        FROM matches m
        JOIN contacts c ON m.contact_id = c.id
        WHERE m.engagement_id = ?
    """, (engagement_id,))

    matches = cursor.fetchall()
    count = 0

    for match in matches:
        match_dict = dict(match)
        contact_dict = {
            'first_name': match_dict['first_name'],
            'last_name': match_dict['last_name'],
            'phone': match_dict['phone'],
            'email': match_dict['email'],
        }

        # Check if draft already exists for this match
        cursor.execute("""
            SELECT id FROM drafts WHERE match_id = ?
        """, (match_dict['id'],))
        if cursor.fetchone():
            continue

        # Generate drafts for each available channel
        channels = []
        if contact_dict.get('phone'):
            channels.extend(['sms', 'whatsapp'])
        if contact_dict.get('email'):
            channels.append('email')

        for channel in channels:
            template_key = f'message_template_{channel}'
            template = settings.get(template_key, settings.get('message_template_sms', ''))

            message = generate_message(
                template, eng_dict, contact_dict,
                match_dict['match_type'], settings
            )

            subject = None
            if channel == 'email':
                subject = settings.get('email_subject_template', 'Mazel Tov!').format(
                    business_name=settings.get('business_name', 'CodePros'),
                    recipient_name=f"{contact_dict['first_name']} {contact_dict['last_name']}",
                    chatan=eng_dict['chatan_first'],
                    kallah=eng_dict['kallah_first'],
                )

            recipient_name = f"{contact_dict['first_name']} {contact_dict['last_name']}"

            cursor.execute("""
                INSERT INTO drafts
                (engagement_id, match_id, recipient_name, recipient_phone,
                 recipient_email, channel, subject, message, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'draft')
            """, (
                engagement_id, match_dict['id'],
                recipient_name,
                contact_dict.get('phone', ''),
                contact_dict.get('email', ''),
                channel, subject, message
            ))
            count += 1

    conn.commit()
    conn.close()
    return count


def generate_all_drafts() -> dict:
    """Generate drafts for all matched engagements that don't have drafts yet."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT e.id FROM engagements e
        JOIN matches m ON m.engagement_id = e.id
    """)

    engagement_ids = [row['id'] for row in cursor.fetchall()]
    conn.close()

    total = 0
    for eid in engagement_ids:
        total += generate_drafts_for_engagement(eid)

    return {
        'engagements_processed': len(engagement_ids),
        'drafts_created': total,
    }
