#!/usr/bin/env python3
"""Validate the Bitcoin book catalogue and the static page that reads it.

Stdlib only. Schema checks always run. Pass --spotcheck to request 20 source
URLs and require HTTP 200.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOKS_PATH = ROOT / "data" / "books.json"
UNRESOLVED_PATH = ROOT / "data" / "unresolved.json"
HTML_PATH = ROOT / "index.html"
JS_PATH = ROOT / "js" / "catalogue.js"

CATEGORIES = {
    "money-economics",
    "technical",
    "history",
    "investing",
    "fiction",
    "other",
}
LISTS = {"about", "mentions", "referenced"}
EVIDENCE = {
    "library-record",
    "description-or-contents",
    "title-or-subject",
    "fulltext-strong",
    "fulltext-moderate",
    "fulltext-single",
    "x-post",
    "nakamoto-library",
    "library-subject",
}
CONFIDENCE = {"library-verified", "x-reference-only", "nakamoto-library"}
REQUIRED = [
    "id",
    "title",
    "authors",
    "year",
    "isbn",
    "list",
    "category",
    "bitcoin_relevance",
    "source_url",
]


def isbn13_ok(value: str) -> bool:
    if not re.fullmatch(r"97[89]\d{10}", value or ""):
        return False
    digits = [int(c) for c in value]
    total = sum(d * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits))
    return total % 10 == 0


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def norm_title(title: str) -> str:
    title = (title or "").casefold()
    title = re.sub(r"[^\w\s]", " ", title, flags=re.UNICODE).replace("_", " ")
    return re.sub(r"\s+", " ", title).strip()


def author_key(authors: list) -> str:
    if not authors:
        return ""
    parts = re.sub(r"[^\w]+", " ", authors[0].casefold(), flags=re.UNICODE).split()
    return parts[-1] if parts else ""


def validate_data() -> tuple[list[str], dict]:
    errors: list[str] = []
    catalogue = json.loads(BOOKS_PATH.read_text(encoding="utf-8"))
    unresolved = json.loads(UNRESOLVED_PATH.read_text(encoding="utf-8"))
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", catalogue.get("generated_at") or ""):
        fail(errors, "books.json generated_at must be YYYY-MM-DD")
    if catalogue.get("generated_at") != unresolved.get("generated_at"):
        fail(errors, "generated_at differs between books.json and unresolved.json")
    books = catalogue.get("books")
    if not isinstance(books, list) or not books:
        fail(errors, "books.json must contain a non-empty books array")
        return errors, catalogue

    ids = set()
    isbns = set()
    seen_identity = set()
    for index, book in enumerate(books):
        where = f"books[{index}]"
        if not isinstance(book, dict):
            fail(errors, f"{where} is not an object")
            continue
        for key in REQUIRED:
            if key not in book:
                fail(errors, f"{where} missing {key}")
        title = book.get("title")
        if not isinstance(title, str) or not title.strip():
            fail(errors, f"{where} title must be a non-empty string")
        authors = book.get("authors")
        if not isinstance(authors, list) or not all(isinstance(a, str) and a.strip() for a in authors):
            fail(errors, f"{where} authors must be a list of strings")
            authors = []
        year = book.get("year")
        if year is not None and (not isinstance(year, int) or not 1000 <= year <= 2026):
            fail(errors, f"{where} year must be null or an integer from 1000 to 2026")
        isbn = book.get("isbn")
        if isbn is not None:
            if not isinstance(isbn, str) or not isbn13_ok(isbn):
                fail(errors, f"{where} isbn is not a valid ISBN-13")
            elif isbn in isbns:
                fail(errors, f"{where} duplicate isbn {isbn}")
            else:
                isbns.add(isbn)
        list_name = book.get("list")
        if list_name not in LISTS:
            fail(errors, f"{where} list must be about or mentions")
        category = book.get("category")
        if list_name == "about" and category not in CATEGORIES:
            fail(errors, f"{where} about entry has invalid category {category!r}")
        if list_name == "mentions" and category is not None:
            fail(errors, f"{where} mentions entry must have category null")
        if list_name == "referenced" and category is not None and category not in CATEGORIES:
            fail(errors, f"{where} referenced entry has invalid category {category!r}")
        evidence = book.get("evidence_type")
        confidence = book.get("confidence")
        if evidence not in EVIDENCE:
            fail(errors, f"{where} evidence_type {evidence!r} is invalid")
        if confidence not in CONFIDENCE:
            fail(errors, f"{where} confidence {confidence!r} is invalid")
        if list_name == "referenced" and evidence not in {"x-post", "fulltext-single", "library-subject"}:
            fail(errors, f"{where} referenced entry needs x-post, single-passage, or subject-only evidence")
        if evidence == "nakamoto-library" and "nakamotolibrary.org" not in (book.get("source_url") or ""):
            extras = book.get("also_sources") or []
            if not any("nakamotolibrary.org" in (item.get("url") or "") for item in extras):
                fail(errors, f"{where} nakamoto-library evidence needs a Nakamoto Library URL")
        extras = book.get("also_sources")
        if extras is not None:
            if not isinstance(extras, list):
                fail(errors, f"{where} also_sources must be a list")
            else:
                for item in extras:
                    extra_url = item.get("url") if isinstance(item, dict) else ""
                    if not isinstance(extra_url, str) or "amazon." in extra_url or not extra_url.startswith("https://"):
                        fail(errors, f"{where} also_sources has a bad url")
        if list_name == "mentions" and evidence not in {"description-or-contents", "fulltext-strong", "fulltext-moderate"}:
            fail(errors, f"{where} mentions entry has evidence_type {evidence!r}")
        relevance = book.get("bitcoin_relevance")
        if not isinstance(relevance, str) or not relevance.strip() or "\n" in relevance:
            fail(errors, f"{where} bitcoin_relevance must be one non-empty line")
        elif len(relevance) > 400:
            fail(errors, f"{where} bitcoin_relevance is longer than 400 characters")
        source = book.get("source_url")
        if not isinstance(source, str) or not re.match(
            r"https://(openlibrary\.org/|archive\.org/|www\.loc\.gov/|lccn\.loc\.gov/|x\.com/|nakamotolibrary\.org/)",
            source or "",
        ):
            fail(errors, f"{where} source_url must be an Open Library, Internet Archive, Library of Congress, or X https URL")
        ident = book.get("id")
        if not isinstance(ident, str) or not ident:
            fail(errors, f"{where} id must be a non-empty string")
        elif ident in ids:
            fail(errors, f"{where} duplicate id {ident}")
        else:
            ids.add(ident)
        identity = (norm_title(title or ""), author_key(authors), year, list_name)
        if identity in seen_identity:
            fail(errors, f"{where} duplicate title/author/year/list {identity}")
        else:
            seen_identity.add(identity)
        if re.search(r"second survivability problem", title or "", re.I) and list_name != "referenced":
            fail(errors, f"{where} seed title must stay in the referenced section")
        original_id = book.get("original_id")
        if original_id is not None:
            if not isinstance(original_id, str) or not book.get("original_title"):
                fail(errors, f"{where} original link is incomplete")

    ids_now = {book.get("id") for book in books if isinstance(book, dict)}
    for index, book in enumerate(books):
        original_id = book.get("original_id") if isinstance(book, dict) else None
        if original_id and original_id not in ids_now:
            fail(errors, f"books[{index}] original_id {original_id} is not in the catalogue")
        if original_id and original_id == book.get("id"):
            fail(errors, f"books[{index}] links to itself as the English original")

    items = unresolved.get("items")
    if not isinstance(items, list) or not items:
        fail(errors, "unresolved.json items must be a non-empty list")
    else:
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                fail(errors, f"unresolved[{index}] is not an object")
                continue
            if not isinstance(item.get("reason"), str) or not item["reason"].strip():
                fail(errors, f"unresolved[{index}] needs a reason")
            if not isinstance(item.get("searches"), list):
                fail(errors, f"unresolved[{index}] searches must be a list")

    return errors, catalogue


def validate_page(catalogue: dict) -> list[str]:
    errors: list[str] = []
    html = HTML_PATH.read_text(encoding="utf-8")
    js = JS_PATH.read_text(encoding="utf-8")
    for needed in ("count-about", "count-mentions", "count-referenced", 'href="css/style.css"', 'src="js/catalogue.js"', "data/books.json"):
        if needed not in html and needed not in js:
            fail(errors, f"page is missing {needed}")
    if re.search(r"https?://(cdn|unpkg|jsdelivr|googleapis|gstatic|bootstrap)", html + js, re.I):
        fail(errors, "page references an external CDN or hosted library")
    if re.search(r"""(?:src|href)=["']https?://""", html):
        fail(errors, "index.html links to an absolute external URL for a page asset")
    for category in sorted(CATEGORIES):
        if category not in js:
            fail(errors, f"catalogue.js is missing category {category}")
    if "lists.about.length" not in js or "lists.mentions.length" not in js or "lists.referenced.length" not in js:
        fail(errors, "catalogue.js must set all three counts from the filtered lists")
    if "countAbout.textContent" not in js or "countMentions.textContent" not in js or "countReferenced.textContent" not in js:
        fail(errors, "catalogue.js must write all three count elements")
    # The page must not bake in totals. Counts come from the loaded JSON.
    hardcoded = re.findall(r"\b(?:1[0-9]{3}|[1-9][0-9]{2})\s+books\b", html)
    if hardcoded:
        fail(errors, f"index.html hardcodes a book total: {hardcoded}")
    books = catalogue["books"]
    about = sum(1 for book in books if book["list"] == "about")
    mentions = sum(1 for book in books if book["list"] == "mentions")
    referenced = sum(1 for book in books if book["list"] == "referenced")
    by_category = Counter(book["category"] for book in books if book["list"] == "about")
    if about + mentions + referenced != len(books):
        fail(errors, "list values do not partition the catalogue")
    if sum(by_category.values()) != about:
        fail(errors, "category counts do not add up to the about list")
    # Mirror the unfiltered page: both lists, all categories, no year bound.
    if str(about) == "0" and str(mentions) == "0":
        fail(errors, "unfiltered counts would both be zero")
    print(f"about {about}")
    for category in ["money-economics", "technical", "history", "investing", "fiction", "other"]:
        print(f"  {category} {by_category[category]}")
    print(f"mentions {mentions}")
    print(f"referenced {referenced}")
    print(f"unresolved {len(json.loads(UNRESOLVED_PATH.read_text(encoding='utf-8'))['items'])}")
    errors.extend(validate_enrichment(catalogue))
    return errors


def validate_enrichment(catalogue: dict) -> list[str]:
    errors: list[str] = []
    path = ROOT / "data" / "enrichment.json"
    if not path.exists():
        fail(errors, "data/enrichment.json is missing")
        return errors
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", payload.get("fetched_date") or ""):
        fail(errors, "enrichment.json fetched_date must be YYYY-MM-DD")
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        fail(errors, "enrichment.json entries must be an object keyed by catalogue id")
        return errors
    ids = {book["id"] for book in catalogue["books"]}
    for key, rec in entries.items():
        if key not in ids:
            fail(errors, f"enrichment {key} is not a catalogue id")
            continue
        if not isinstance(rec, dict):
            fail(errors, f"enrichment {key} is not an object")
            continue
        summary = rec.get("summary")
        source = rec.get("summary_source")
        if summary and (not isinstance(source, str) or not source.startswith("https://openlibrary.org/")):
            fail(errors, f"enrichment {key} summary needs an Open Library source")
        if rec.get("gr_rating_count") and (not isinstance(rec.get("gr_url"), str) or not rec["gr_url"].startswith("https://www.goodreads.com/")):
            fail(errors, f"enrichment {key} Goodreads rating needs a Goodreads URL")
        for num_key in ("ol_rating_avg", "ol_rating_count", "ol_want_to_read", "ol_already_read", "gr_rating_avg", "gr_rating_count"):
            value = rec.get(num_key)
            if value is not None and not isinstance(value, (int, float)):
                fail(errors, f"enrichment {key} {num_key} must be numeric")
        blob = json.dumps(rec)
        if "amazon." in blob:
            fail(errors, f"enrichment {key} contains an Amazon link")
    if html_has := True:
        js = (ROOT / "js" / "catalogue.js").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        if 'id="sort"' not in html:
            fail(errors, "page is missing the sort control")
        if "data/enrichment.json" not in js:
            fail(errors, "catalogue.js must load data/enrichment.json")
        if "gr-count" not in js or "gr-avg" not in js or "ol-want" not in js:
            fail(errors, "catalogue.js is missing a ratings sort")
    return errors


def spotcheck(catalogue: dict, limit: int = 20) -> list[str]:
    errors: list[str] = []
    books = catalogue["books"]
    picked = []
    seen = set()

    def take(book):
        url = book["source_url"]
        if url in seen:
            return
        seen.add(url)
        picked.append(book)

    for category in ["money-economics", "technical", "history", "investing", "fiction", "other"]:
        for book in books:
            if book.get("category") == category:
                take(book)
                break
    for book in books:
        if book["list"] == "mentions":
            take(book)
    for book in books:
        if "loc.gov" in book["source_url"]:
            take(book)
            break
    for book in books:
        if "/books/" in book["source_url"]:
            take(book)
            if len(picked) >= limit:
                break
    stride = max(1, len(books) // limit)
    index = 0
    while len(picked) < limit and index < len(books):
        take(books[index])
        index += stride
    picked = picked[:limit]
    if len(picked) < limit:
        fail(errors, f"could only select {len(picked)} source URLs")

    ua = "bitcoin-books-catalogue/0.1 (source spot check)"
    results = []
    for book in picked:
        url = book["source_url"]
        status = None
        detail = ""
        for attempt in range(3):
            try:
                request = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "text/html"})
                with urllib.request.urlopen(request, timeout=30) as response:
                    status = response.status
                    response.read(200)
                break
            except Exception as exc:
                status = getattr(exc, "code", None)
                detail = str(exc)
                time.sleep(1.2 * (attempt + 1))
        time.sleep(0.6)
        ok = status == 200
        results.append({
            "status": status,
            "ok": ok,
            "url": url,
            "title": book["title"],
            "detail": detail,
        })
        print(f"{status} {url}")
        if not ok:
            fail(errors, f"spotcheck {status} {url} {detail}")

    out = Path("/opt/cursor/artifacts/source_checks.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"checked": len(results), "results": results}, indent=2) + "\n", encoding="utf-8")
    print(f"spotcheck wrote {out}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spotcheck", action="store_true")
    args = parser.parse_args()
    errors, catalogue = validate_data()
    if catalogue.get("books"):
        errors.extend(validate_page(catalogue))
    if args.spotcheck and catalogue.get("books"):
        errors.extend(spotcheck(catalogue))
    if errors:
        print(f"{len(errors)} error(s):", file=sys.stderr)
        for error in errors[:40]:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
