# Bitcoin books

A static catalogue of books whose bibliographic records support one of two claims:

- **About:** Bitcoin is the subject, or a major subject, of the book.
- **Mentions:** a fetched table of contents or description documents a chapter, passage, or case study that discusses Bitcoin.

Definitive coverage is the aim, not a claim this list has reached it. Anything that was investigated and still lacked that evidence is in [`data/unresolved.json`](data/unresolved.json), not on the site.

## Counts on 2026-11-17

About: **1867**

| Category | Books |
| --- | ---: |
| money-economics | 1011 |
| technical | 275 |
| history | 31 |
| investing | 490 |
| fiction | 23 |
| other | 37 |

Mentions: **3**. Unresolved items: **97** (the seed title, prior candidates that could not be supported, and short notes on records set aside as non-books, authorless, or undated).

`other` is the leftover: law and regulation, religion, philosophy, dictionaries, and a few records whose title is not in Latin script. General Bitcoin books, buying guides, and technical books are in the named categories. A translation keeps its own entry. When the library records show the same author and the foreign title is the English title’s wording, the entry links to that English edition.

## What was consulted

Records were fetched on 2026-11-17 from:

- [Open Library Search](https://openlibrary.org/dev/docs/api/search) (`subject:bitcoin`, `title:bitcoin`, and ISBN lookups) and, where the search record was thin, the work or edition JSON.
- The Library of Congress books JSON API (`https://www.loc.gov/books/?q=bitcoin&fo=json`). A hit was kept only when the title or a subject heading contains Bitcoin. Full-text hits on unrelated scans were not kept.

The keyless Google Books API (`books.googleapis.com`) returned HTTP 429, daily quota exceeded, on every attempt. It was not used. That is a coverage gap: some books may be described only there.

An earlier candidate list was used only as a set of titles and ISBNs to look up again. Its summaries were not copied.

A record was kept when a fetched field supported the claim:

- a subject heading containing Bitcoin, or
- the title or subtitle containing Bitcoin, or
- for a few works checked individually, an edition description that presents Bitcoin as a major subject, or a table of contents / description that names a chapter or passage.

Editions, subtitle variants, and ISBN variants of the same work were collapsed to one entry. Translations catalogued under a different title were kept as their own entries. Blank stationery (notebooks, sketchbooks, coloring books, planners, puzzles) was not treated as a book about Bitcoin. Records with no author, or no year from 2008 through 2026, were left out.

## Seed title

**The Second Survivability Problem** is not in the published catalogue. Open Library has no work with that title. Library of Congress book searches for the title, and for Francis Bothwell, did not return a matching book. Google Books could not be queried. The searches and the negative results are the seed item in `data/unresolved.json`.

## Data files

[`data/books.json`](data/books.json) is the catalogue:

```json
{
  "generated_at": "2026-11-17",
  "sources_note": "short note",
  "books": [
    {
      "id": "the-bitcoin-standard-2018-ammous",
      "title": "The Bitcoin Standard",
      "subtitle": null,
      "authors": ["Saifedean Ammous"],
      "year": 2018,
      "isbn": "9781119473862",
      "list": "about",
      "category": "money-economics",
      "bitcoin_relevance": "One sentence grounded in the source record.",
      "source_url": "https://openlibrary.org/works/OL20984004W",
      "source_label": "Open Library",
      "language": "eng"
    }
  ]
}
```

| Field | Required | Meaning |
| --- | --- | --- |
| `id` | yes | Stable slug. Unique. |
| `title` | yes | Title from the record. A subtitle that was stored in the title field is left there. |
| `subtitle` | no | Separate subtitle when the record has one. `null` if absent. |
| `authors` | yes | Non-empty list. Narrators and translators are dropped. |
| `year` | yes | Earliest supported publication year, 2008–2026. |
| `isbn` | yes | One ISBN-13 when a valid one was present, otherwise `null`. |
| `list` | yes | `about` or `mentions`. |
| `category` | yes | For `about`: `money-economics`, `technical`, `history`, `investing`, `fiction`, or `other`. For `mentions`: `null`. |
| `bitcoin_relevance` | yes | One line stating the evidence. |
| `source_url` | yes | The Open Library or Library of Congress record that supports the line. |
| `source_label` | no | Human label for the link. |
| `language` | no | Open Library language code when the record has one. |

`generated_at` is the date the files were built. The page shows that date as “Last updated”.

[`data/unresolved.json`](data/unresolved.json) uses the same `generated_at`. Each item has `title`, `authors`, `year`, `isbn`, `candidate_origin` (`seed`, `prior_catalog`, or `exclusion_summary`), `reason`, and `searches` (source, query, URL, and what came back). Exclusion summaries have a null title and describe records that were set aside as a group.

## How to add a book

1. Find a record on Open Library, the Library of Congress, or the Google Books API (no key). The record has to be fetched, not guessed.
2. Decide the list from that record only:
   - **about** if Bitcoin is the subject or a major subject (subject heading, or the title/subtitle, or a description of the whole book);
   - **mentions** only if a table of contents, description, or note documents a chapter, passage, or case study;
   - otherwise add an item to `data/unresolved.json` and stop.
3. If an entry with the same author and title (ignoring subtitle and ISBN) is already in `books`, merge into that entry instead of adding another.
4. Set `category` only for `about`. Use the record’s subjects and title, in this order: fiction; history (including war, battle, biography, “the story of”); technical (programming, protocol, Lightning, cryptography); investing; law, religion, or philosophy as `other`; money and economics; otherwise `other`.
5. Write `bitcoin_relevance` as one sentence a reader could check on `source_url`.
6. Bump `generated_at` on both JSON files if the update is part of a new build.
7. Run `python3 scripts/validate.py`. Use `python3 scripts/validate.py --spotcheck` when you can reach the source sites.

## The page

`index.html`, `css/style.css`, and `js/catalogue.js` are plain HTML, CSS, and JavaScript. There is no framework and no CDN. Paths are relative, so the same files work at the root of a host or under a `/bitcoin-books/` path.

Serve the directory over HTTP (opening the file directly will not load the JSON):

```bash
python3 -m http.server 8765
```

Then open `http://127.0.0.1:8765/`.

Search matches title, subtitle, authors, ISBN, the relevance line, and language. The year boxes are an inclusive range. The category control filters the About list only. Both counts are the number of rows currently shown in each list.

## Checks

`scripts/validate.py` checks required fields, ISBN-13 checksums, list and category values, source URLs, duplicate ids, duplicate ISBNs, duplicate title/author/year rows, the seed staying in the unresolved file, and that the page computes both counts from the loaded data instead of hardcoding them.

## Publishing later with GitHub Pages

This repository also has a `main` branch (an initial README commit). This catalogue lives on `cursor/bitcoin-books-catalogue`, which is not automatically the default branch.

When you want a public site, and not before:

1. In the repository on GitHub, open **Settings → Pages**.
2. Under **Build and deployment**, choose **Deploy from a branch**.
3. Set the branch to `cursor/bitcoin-books-catalogue` and the folder to `/ (root)`.
4. Save. GitHub will build from this branch’s root, where `index.html` is.

If you would rather publish “the default branch”, change the default branch to `cursor/bitcoin-books-catalogue` first, then choose the default branch and `/ (root)`. Do not point Pages at `main`: that branch is only the initial README.

No live URL is claimed here. Pages was not enabled by this work.
