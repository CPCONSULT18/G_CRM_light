"""Dedup matching engine: score each lead's contacts against the blocklist.

Confidence rules (from blueprint §6):
  Hard:     email 1:1 exact ; phone + name both match on the same blocklist row
  Probable: phone alone ; domain + fuzzy name
  Soft:     domain alone ; name alone
"""

from .db import get_db
from .normalize import base_domain, norm_email, norm_name, norm_phone


def _build_indexes(db):
    """Index blocklist rows by each normalized key -> set of contacted ids."""
    rows = db.execute("SELECT id, name, email, phone, domain FROM contacted").fetchall()
    by_email, by_phone, by_domain, by_name = {}, {}, {}, {}
    for r in rows:
        e = norm_email(r["email"])
        if e:
            by_email.setdefault(e, set()).add(r["id"])
        p = norm_phone(r["phone"])
        if p:
            by_phone.setdefault(p, set()).add(r["id"])
        d = base_domain(r["domain"] or r["email"])
        if d:
            by_domain.setdefault(d, set()).add(r["id"])
        n = norm_name(r["name"])
        if n:
            by_name.setdefault(n, set()).add(r["id"])
    return by_email, by_phone, by_domain, by_name


def _fuzzy(a, b):
    """True when normalized names share >=2 tokens or one fully contains the other."""
    if not a or not b:
        return False
    if a == b:
        return True
    ta, tb = set(a.split()), set(b.split())
    if not ta or not tb:
        return False
    common = ta & tb
    return len(common) >= 2 or common == min(ta, tb, key=len)


def _lead_keys(db, lead):
    """All normalized keys for a lead (its company's contacts + locations)."""
    contacts = db.execute(
        "SELECT name, email, phone FROM contacts WHERE company_id = ?",
        (lead["company_id"],),
    ).fetchall()
    locations = db.execute(
        "SELECT phone FROM locations WHERE company_id = ?", (lead["company_id"],)
    ).fetchall()
    names = {norm_name(c["name"]) for c in contacts if c["name"]}
    emails = {norm_email(c["email"]) for c in contacts if c["email"]}
    phones = {norm_phone(c["phone"]) for c in contacts if c["phone"]}
    phones |= {norm_phone(l["phone"]) for l in locations if l["phone"]}
    domains = {base_domain(e) for e in emails if e}
    return names, emails, phones, domains


def match_lead(db, lead, idx, country_code):
    """Score one lead against blocklist indexes -> list of (cid, field, confidence)."""
    names, emails, phones, domains = _lead_keys(db, lead)
    by_email, by_phone, by_domain, by_name = idx
    results = []

    for e in emails:
        if e in by_email:
            for cid in by_email[e]:
                results.append((cid, "email", "hard"))

    for p in phones:
        if p in by_phone:
            for cid in by_phone[p]:
                # Hard when a name also matches this same blocklist row.
                cname = _blocklist_name(db, cid)
                if any(_fuzzy(n, cname) for n in names):
                    results.append((cid, "phone", "hard"))
                else:
                    results.append((cid, "phone", "probable"))

    for d in domains:
        if d in by_domain:
            for cid in by_domain[d]:
                cname = _blocklist_name(db, cid)
                if any(_fuzzy(n, cname) for n in names):
                    results.append((cid, "domain", "probable"))
                else:
                    results.append((cid, "domain", "soft"))

    for n in names:
        if n in by_name:
            for cid in by_name[n]:
                results.append((cid, "name", "soft"))

    # Deduplicate (cid, field) pairs, keep the strongest confidence.
    best = {}
    for cid, field, conf in results:
        rank = {"hard": 3, "probable": 2, "soft": 1}[conf]
        key = (cid, field)
        if key not in best or rank > best[key][1]:
            best[key] = (cid, field, conf)
    return list(best.values())


def _blocklist_name(db, cid):
    row = db.execute("SELECT name FROM contacted WHERE id = ?", (cid,)).fetchone()
    return norm_name(row["name"]) if row and row["name"] else ""


def run_match_all(country_code=None):
    """Match all leads against the blocklist. Replaces all previous match results."""
    db = get_db()
    if country_code is None:
        row = db.execute("SELECT value FROM settings WHERE key='country_code'").fetchone()
        country_code = row["value"] if row else "49"

    idx = _build_indexes(db)
    leads = db.execute("SELECT id, company_id FROM leads").fetchall()

    db.execute("DELETE FROM matches")
    counts = {"hard": 0, "probable": 0, "soft": 0}
    for lead in leads:
        for cid, field, conf in match_lead(db, lead, idx, country_code):
            db.execute(
                "INSERT OR IGNORE INTO matches (lead_id, contacted_id, field, confidence) "
                "VALUES (?, ?, ?, ?)",
                (lead["id"], cid, field, conf),
            )
            counts[conf] = counts.get(conf, 0) + 1
    db.commit()
    return {
        "matched": sum(counts.values()),
        "by_confidence": counts,
        "leads_scanned": len(leads),
    }