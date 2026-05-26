"""One-off audit: OSINT collection vs extraction coverage per case."""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.osint_data_utils import flatten_osint_items, osint_has_error, text_from_osint_item

DB = Path(__file__).resolve().parents[1] / "osint_platform.db"


def main() -> None:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print("=== CASES ===")
    cur.execute("SELECT id, name, case_type, status FROM cases ORDER BY id")
    cases = [dict(r) for r in cur.fetchall()]
    for c in cases:
        print(c)

    print("\n=== OSINT QUERIES BY CASE / TYPE ===")
    cur.execute(
        """
        SELECT case_id, query_type, status, COUNT(*) AS n
        FROM osint_queries
        GROUP BY case_id, query_type, status
        ORDER BY case_id, query_type
        """
    )
    for r in cur.fetchall():
        print(dict(r))

    print("\n=== EXTRACTED STATEMENTS BY CASE / DECISION ===")
    cur.execute(
        """
        SELECT case_id, cleanup_decision, COUNT(*) AS n
        FROM extracted_statements
        GROUP BY case_id, cleanup_decision
        ORDER BY case_id
        """
    )
    for r in cur.fetchall():
        print(dict(r))

    print("\n=== ALERT MATCHES SUMMARY ===")
    cur.execute(
        """
        SELECT case_id, status, action_taken, COUNT(*) AS n,
               SUM(CASE WHEN extracted_statement_id IS NOT NULL THEN 1 ELSE 0 END) AS with_extract
        FROM alert_matches
        GROUP BY case_id, status, action_taken
        ORDER BY case_id
        """
    )
    for r in cur.fetchall():
        print(dict(r))

    by_case: dict[int, dict] = defaultdict(
        lambda: {
            "queries": 0,
            "results": 0,
            "errors": 0,
            "articles": 0,
            "short_text": 0,
            "no_url": 0,
            "extractable": 0,
            "thin_with_url": 0,
            "query_types": set(),
        }
    )

    cur.execute(
        """
        SELECT q.case_id, q.query_type, r.data, r.status
        FROM osint_results r
        JOIN osint_queries q ON q.id = r.query_id
        """
    )
    for row in cur.fetchall():
        cid = row["case_id"] or 0
        qtype = row["query_type"]
        by_case[cid]["results"] += 1
        by_case[cid]["query_types"].add(qtype)
        data_raw = row["data"]
        if not data_raw:
            continue
        try:
            data = json.loads(data_raw) if isinstance(data_raw, str) else data_raw
        except json.JSONDecodeError:
            by_case[cid]["errors"] += 1
            continue
        if osint_has_error(data) or row["status"] == "error":
            by_case[cid]["errors"] += 1
            continue
        for art in flatten_osint_items(data):
            by_case[cid]["articles"] += 1
            t = text_from_osint_item(art)
            url = str(art.get("url") or "").strip()
            tl = len(t.strip())
            if not url:
                by_case[cid]["no_url"] += 1
            if tl < 80 and not url:
                by_case[cid]["short_text"] += 1
            elif tl >= 80:
                by_case[cid]["extractable"] += 1
            elif url and tl < 200:
                by_case[cid]["thin_with_url"] += 1

    cur.execute("SELECT case_id, COUNT(*) FROM osint_queries GROUP BY case_id")
    for cid, n in cur.fetchall():
        by_case[cid or 0]["queries"] = n

    print("\n=== ARTICLE / EXTRACTION FUNNEL BY CASE ===")
    for cid in sorted(by_case):
        s = by_case[cid]
        s["query_types"] = sorted(s["query_types"])
        cur.execute(
            "SELECT COUNT(DISTINCT source_url) FROM extracted_statements WHERE case_id=? AND source_url != ''",
            (cid,),
        )
        extracted_urls = cur.fetchone()[0]
        s["extracted_urls"] = extracted_urls
        print(f"Case {cid}:", json.dumps(s, ensure_ascii=False))

    print("\n=== ACTIONED MATCHES WITHOUT EXTRACTION ===")
    cur.execute(
        """
        SELECT id, case_id, title, url, LENGTH(excerpt) AS excerpt_len,
               status, action_taken, extracted_statement_id
        FROM alert_matches
        WHERE status = 'actioned' AND extracted_statement_id IS NULL
        LIMIT 25
        """
    )
    rows = [dict(r) for r in cur.fetchall()]
    print(f"Count: {len(rows)}")
    for r in rows:
        print(r)

    print("\n=== MATCHES WITH SHORT EXCERPT (<200 chars) ===")
    cur.execute(
        """
        SELECT id, case_id, status, action_taken, LENGTH(excerpt) AS excerpt_len, url
        FROM alert_matches
        WHERE LENGTH(COALESCE(excerpt,'')) < 200
        ORDER BY id DESC
        LIMIT 20
        """
    )
    for r in cur.fetchall():
        print(dict(r))

    print("\n=== OSINT ERROR / UNAVAILABLE RESULTS ===")
    cur.execute(
        """
        SELECT q.case_id, q.query_type, r.status, r.data
        FROM osint_results r
        JOIN osint_queries q ON q.id = r.query_id
        WHERE r.status = 'error' OR r.data LIKE '%unavailable%' OR r.data LIKE '%\"error\"%'
        LIMIT 15
        """
    )
    for r in cur.fetchall():
        d = r["data"]
        try:
            parsed = json.loads(d) if isinstance(d, str) else d
            msg = parsed.get("message") or parsed.get("error") or parsed.get("status")
        except Exception:
            msg = str(d)[:120]
        print({"case_id": r["case_id"], "type": r["query_type"], "status": r["status"], "msg": msg})

    print("\n=== CASE 1 — EXTRACTION GAP ===")
    cur.execute("SELECT source_url FROM extracted_statements WHERE case_id=1")
    extracted = {r[0] for r in cur.fetchall() if r[0]}
    articles: list[tuple] = []
    cur.execute(
        """
        SELECT r.data, q.query_type
        FROM osint_results r
        JOIN osint_queries q ON q.id = r.query_id
        WHERE q.case_id = 1 AND r.status = 'completed'
        """
    )
    by_source: dict[str, int] = defaultdict(int)
    for data_raw, qtype in cur.fetchall():
        try:
            data = json.loads(data_raw) if isinstance(data_raw, str) else data_raw
        except json.JSONDecodeError:
            continue
        if osint_has_error(data):
            continue
        for art in flatten_osint_items(data):
            url = str(art.get("url") or "")
            tlen = len(text_from_osint_item(art).strip())
            title = str(art.get("title") or "")[:70]
            source = str(art.get("source") or qtype)
            articles.append((url, tlen, title, source))
            by_source[source] += 1

    not_ext = [a for a in articles if a[0] and a[0] not in extracted]
    print(f"Articles total: {len(articles)}, unique URLs not extracted: {len({a[0] for a in not_ext})}")
    print(f"Thin (<200 chars) pending: {len([a for a in not_ext if a[1] < 200])}")
    print("By source:", dict(sorted(by_source.items(), key=lambda x: -x[1])[:12]))
    print("Sample pending (thin):")
    for a in sorted(not_ext, key=lambda x: x[1])[:10]:
        print(f"  {a[1]:3d} chars | {a[3][:20]} | {a[2]}")

    print("\n=== ORPHAN OSINT (case_id NULL) ===")
    cur.execute(
        "SELECT query_type, COUNT(*) FROM osint_queries WHERE case_id IS NULL GROUP BY query_type"
    )
    for r in cur.fetchall():
        print(dict(r))

    conn.close()


if __name__ == "__main__":
    main()
