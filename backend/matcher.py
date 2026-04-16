"""
Contact matcher: cross-references engagement names against the contacts directory.

Matching strategy:
1. Exact last name match (high confidence)
2. Fuzzy first name match within same last name (medium confidence)
3. Last name only match when engagement has no first name detail (lower confidence)
"""

import csv
import io
from database import get_db


def import_contacts_csv(csv_content: str, community: str = '') -> int:
    """
    Import contacts from CSV content.
    Expected columns: first_name, last_name, phone, email, address, city
    Flexible: will try to detect columns by header names.
    """
    conn = get_db()
    cursor = conn.cursor()
    count = 0

    reader = csv.DictReader(io.StringIO(csv_content))

    # Map flexible column names
    field_map = {}
    if reader.fieldnames:
        for col in reader.fieldnames:
            col_lower = col.lower().strip()
            if col_lower in ('first', 'first_name', 'firstname', 'first name'):
                field_map['first_name'] = col
            elif col_lower in ('last', 'last_name', 'lastname', 'last name', 'surname'):
                field_map['last_name'] = col
            elif col_lower in ('phone', 'telephone', 'tel', 'mobile', 'cell', 'phone number'):
                field_map['phone'] = col
            elif col_lower in ('email', 'e-mail', 'email address'):
                field_map['email'] = col
            elif col_lower in ('address', 'street', 'street address'):
                field_map['address'] = col
            elif col_lower in ('city', 'town'):
                field_map['city'] = col

    for row in reader:
        first = row.get(field_map.get('first_name', 'first_name'), '').strip()
        last = row.get(field_map.get('last_name', 'last_name'), '').strip()

        if not first or not last:
            continue

        phone = row.get(field_map.get('phone', 'phone'), '').strip()
        email = row.get(field_map.get('email', 'email'), '').strip()
        address = row.get(field_map.get('address', 'address'), '').strip()
        city = row.get(field_map.get('city', 'city'), '').strip()

        # Check for duplicate
        cursor.execute("""
            SELECT id FROM contacts
            WHERE first_name = ? AND last_name = ? AND (phone = ? OR email = ?)
        """, (first, last, phone, email))

        if cursor.fetchone() is None:
            cursor.execute("""
                INSERT INTO contacts (first_name, last_name, phone, email, address, city, community)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (first, last, phone, email, address, city, community))
            count += 1

    conn.commit()
    conn.close()
    return count


def import_contacts_vcf(vcf_content: str, community: str = '') -> int:
    """
    Import contacts from VCF (vCard) content.
    Supports standard vCard 3.0/4.0 format.
    """
    conn = get_db()
    cursor = conn.cursor()
    count = 0

    # Parse vCard entries
    cards = vcf_content.split('BEGIN:VCARD')
    for card in cards:
        if not card.strip():
            continue

        first = last = phone = email = address = ''

        for line in card.split('\n'):
            line = line.strip()
            if line.startswith('N:') or line.startswith('N;'):
                parts = line.split(':', 1)[1].split(';')
                last = parts[0].strip() if len(parts) > 0 else ''
                first = parts[1].strip() if len(parts) > 1 else ''
            elif line.startswith('TEL') and not phone:
                phone = line.split(':', 1)[-1].strip()
            elif line.startswith('EMAIL') and not email:
                email = line.split(':', 1)[-1].strip()
            elif line.startswith('ADR'):
                adr_parts = line.split(':', 1)[-1].split(';')
                address = ' '.join(p.strip() for p in adr_parts if p.strip())

        if not first or not last:
            continue

        cursor.execute("""
            SELECT id FROM contacts
            WHERE first_name = ? AND last_name = ? AND (phone = ? OR email = ?)
        """, (first, last, phone, email))

        if cursor.fetchone() is None:
            cursor.execute("""
                INSERT INTO contacts (first_name, last_name, phone, email, address, city, community)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (first, last, phone, email, address, '', community))
            count += 1

    conn.commit()
    conn.close()
    return count


def _normalize(name: str) -> str:
    """Normalize a name for comparison."""
    if not name:
        return ''
    return name.lower().strip()


def _name_similarity(a: str, b: str) -> float:
    """Simple name similarity score (0-1)."""
    a, b = _normalize(a), _normalize(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    # One is prefix of other (e.g., "Moshe" vs "Moishe")
    if a.startswith(b) or b.startswith(a):
        return 0.8
    # Check common Jewish name variants
    variants = {
        'moshe': ['moishe', 'moses'],
        'yosef': ['yossi', 'joseph', 'joe'],
        'yaakov': ['yanky', 'jacob', 'jake'],
        'avraham': ['avrumi', 'avi', 'abraham'],
        'shmuel': ['samuel', 'sam'],
        'dovid': ['david', 'dave'],
        'chaim': ['hyman'],
        'rivka': ['rebecca', 'rivky'],
        'sarah': ['sara'],
        'rachel': ['rochel', 'ruchel'],
        'leah': ['lea'],
        'miriam': ['miri'],
        'chana': ['hannah', 'hanna'],
        'devorah': ['devora', 'deborah', 'debra'],
        'esther': ['esti'],
        'malka': ['malky'],
        'shira': ['shiri'],
        'tziporah': ['tzipi', 'tzipora'],
        'yehuda': ['yehudi', 'judah'],
        'menachem': ['mendel'],
        'eliezer': ['eli', 'lazer'],
        'aharon': ['aaron'],
        'binyamin': ['benjamin', 'ben'],
        'shlomo': ['solomon'],
        'nosson': ['nathan', 'noach'],
    }
    for canonical, alts in variants.items():
        all_names = [canonical] + alts
        if a in all_names and b in all_names:
            return 0.85

    return 0.0


def match_engagement(engagement_id: int) -> list[dict]:
    """
    Find contacts matching an engagement's chatan/kallah names.
    Returns list of matches with confidence scores.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM engagements WHERE id = ?", (engagement_id,))
    eng = cursor.fetchone()
    if not eng:
        conn.close()
        return []

    matches = []

    # Search for chatan's family (by last name)
    if eng['chatan_last']:
        cursor.execute("""
            SELECT * FROM contacts
            WHERE LOWER(last_name) = LOWER(?)
        """, (eng['chatan_last'],))

        for contact in cursor.fetchall():
            sim = _name_similarity(contact['first_name'], eng['chatan_first'])
            if sim >= 0.8:
                match_type = 'chatan'
                confidence = sim
            else:
                match_type = 'chatan_family'
                confidence = 0.7

            matches.append({
                'contact_id': contact['id'],
                'match_type': match_type,
                'confidence': confidence,
                'contact': dict(contact),
            })

    # Search for kallah's family (by last name)
    if eng['kallah_last']:
        cursor.execute("""
            SELECT * FROM contacts
            WHERE LOWER(last_name) = LOWER(?)
        """, (eng['kallah_last'],))

        for contact in cursor.fetchall():
            sim = _name_similarity(contact['first_name'], eng['kallah_first'])
            if sim >= 0.8:
                match_type = 'kallah'
                confidence = sim
            else:
                match_type = 'kallah_family'
                confidence = 0.7

            matches.append({
                'contact_id': contact['id'],
                'match_type': match_type,
                'confidence': confidence,
                'contact': dict(contact),
            })

    conn.close()
    return matches


def save_matches(engagement_id: int, matches: list[dict]) -> int:
    """Save matches to database. Returns count of new matches."""
    conn = get_db()
    cursor = conn.cursor()
    count = 0

    for m in matches:
        try:
            cursor.execute("""
                INSERT INTO matches (engagement_id, contact_id, match_type, confidence)
                VALUES (?, ?, ?, ?)
            """, (engagement_id, m['contact_id'], m['match_type'], m['confidence']))
            count += 1
        except Exception:
            pass  # Duplicate match, skip

    if count > 0:
        cursor.execute(
            "UPDATE engagements SET matched = 1 WHERE id = ?",
            (engagement_id,)
        )

    conn.commit()
    conn.close()
    return count


def run_matching() -> dict:
    """Match all unmatched engagements against contacts."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM engagements WHERE matched = 0")
    unmatched = cursor.fetchall()
    conn.close()

    total_matches = 0
    engagements_matched = 0

    for eng in unmatched:
        matches = match_engagement(eng['id'])
        if matches:
            saved = save_matches(eng['id'], matches)
            total_matches += saved
            if saved > 0:
                engagements_matched += 1

    return {
        'engagements_checked': len(unmatched),
        'engagements_matched': engagements_matched,
        'total_matches': total_matches,
    }
