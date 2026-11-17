(function () {
  "use strict";

  var CATEGORIES = [
    ["money-economics", "Money and economics"],
    ["technical", "Technical"],
    ["history", "History"],
    ["investing", "Investing"],
    ["fiction", "Fiction"],
    ["other", "Other"]
  ];

  var categoryLabel = {};
  CATEGORIES.forEach(function (pair) {
    categoryLabel[pair[0]] = pair[1];
  });

  var els = {
    q: document.getElementById("q"),
    list: document.getElementById("list"),
    category: document.getElementById("category"),
    yearFrom: document.getElementById("year-from"),
    yearTo: document.getElementById("year-to"),
    countAbout: document.getElementById("count-about"),
    countMentions: document.getElementById("count-mentions"),
    countReferenced: document.getElementById("count-referenced"),
    countNote: document.getElementById("count-note"),
    results: document.getElementById("results"),
    status: document.getElementById("status"),
    updated: document.getElementById("updated")
  };

  var books = [];

  function readYear(value) {
    if (value === null || value === undefined || String(value).trim() === "") return null;
    var n = Number(value);
    if (!Number.isFinite(n)) return null;
    return Math.trunc(n);
  }

  function state() {
    return {
      q: els.q.value || "",
      list: els.list.value || "all",
      category: els.category.value || "all",
      yearFrom: readYear(els.yearFrom.value),
      yearTo: readYear(els.yearTo.value)
    };
  }

  function matches(book, current) {
    var q = current.q.trim().toLowerCase();
    if (q) {
      var hay = [
        book.title || "",
        book.subtitle || "",
        (book.authors || []).join(" "),
        book.isbn || "",
        book.bitcoin_relevance || "",
        book.language || ""
      ].join(" ").toLowerCase();
      if (hay.indexOf(q) === -1) return false;
    }
    if (current.yearFrom !== null || current.yearTo !== null) {
      if (book.year == null) return false;
      if (current.yearFrom !== null && book.year < current.yearFrom) return false;
      if (current.yearTo !== null && book.year > current.yearTo) return false;
    }
    return true;
  }

  function byYear(a, b) {
    if (a.year == null && b.year == null) return String(a.title).localeCompare(String(b.title));
    if (a.year == null) return 1;
    if (b.year == null) return -1;
    return a.year - b.year || String(a.title).localeCompare(String(b.title));
  }

  function visibleLists(current) {
    var about = [];
    var mentions = [];
    var referenced = [];
    var i;
    for (i = 0; i < books.length; i += 1) {
      var book = books[i];
      if (!matches(book, current)) continue;
      if (book.list === "about") about.push(book);
      else if (book.list === "mentions") mentions.push(book);
      else if (book.list === "referenced") referenced.push(book);
    }
    if (current.category !== "all") {
      about = about.filter(function (book) { return book.category === current.category; });
      referenced = referenced.filter(function (book) { return book.category === current.category; });
    }
    if (current.list === "about") { mentions = []; referenced = []; }
    if (current.list === "mentions") { about = []; referenced = []; }
    if (current.list === "referenced") { about = []; mentions = []; }
    return { about: about, mentions: mentions, referenced: referenced };
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function renderBook(book) {
    var article = el("article", "book");
    if (book.id) article.id = book.id;
    var meta = el("p", "meta");
    meta.appendChild(el("span", "year", book.year == null ? "Unknown" : String(book.year)));
    if (book.list === "about" && categoryLabel[book.category]) {
      meta.appendChild(document.createTextNode(" · "));
      meta.appendChild(el("span", "cat", categoryLabel[book.category]));
    } else if (book.list === "mentions") {
      meta.appendChild(document.createTextNode(" · "));
      meta.appendChild(el("span", "cat", book.mention_strength === "strong" ? "Strong mention" : "Mention"));
    } else if (book.list === "referenced") {
      meta.appendChild(document.createTextNode(" · "));
      meta.appendChild(el("span", "cat", book.evidence_type === "x-post" ? "X reference only" : "Single passage"));
    }
    if (book.language && book.language !== "eng") {
      meta.appendChild(document.createTextNode(" · "));
      meta.appendChild(el("span", "lang", book.language));
    }
    article.appendChild(meta);
    article.appendChild(el("h3", null, book.title));
    if (book.subtitle) article.appendChild(el("p", "subtitle", book.subtitle));
    article.appendChild(el("p", "authors", (book.authors && book.authors.length) ? book.authors.join(", ") : "Unknown"));
    if (book.original_title && book.original_id) {
      var original = el("p", "original");
      original.appendChild(document.createTextNode("English edition in this catalogue: "));
      var jump = document.createElement("a");
      jump.href = "#" + book.original_id;
      jump.textContent = book.original_title;
      original.appendChild(jump);
      article.appendChild(original);
    }
    if (book.isbn) article.appendChild(el("p", "isbn", "ISBN " + book.isbn));
    article.appendChild(el("p", "relevance", book.bitcoin_relevance));
    var source = el("p", "source");
    var link = document.createElement("a");
    link.href = book.source_url;
    link.textContent = book.source_label || "Source";
    link.rel = "noreferrer";
    source.appendChild(link);
    (book.also_sources || []).forEach(function (extra) {
      if (!extra || !extra.url) return;
      source.appendChild(document.createTextNode(" · "));
      var extraLink = document.createElement("a");
      extraLink.href = extra.url;
      extraLink.textContent = extra.label || "Also";
      extraLink.rel = "noreferrer";
      source.appendChild(extraLink);
    });
    article.appendChild(source);
    return article;
  }

  function renderGroup(title, items) {
    var section = el("section", "group");
    var heading = document.createElement("h2");
    heading.textContent = title + " ";
    heading.appendChild(el("span", "group-count", "(" + items.length + ")"));
    section.appendChild(heading);
    items.forEach(function (book) { section.appendChild(renderBook(book)); });
    return section;
  }

  function render() {
    var current = state();
    var lists = visibleLists(current);
    els.countAbout.textContent = String(lists.about.length);
    els.countMentions.textContent = String(lists.mentions.length);
    els.countReferenced.textContent = String(lists.referenced.length);
    els.category.disabled = current.list === "mentions";
    if (current.list === "mentions") {
      els.countNote.textContent = "Mentions have no category. Strong and moderate full-text passages are listed here.";
    } else if (current.list === "referenced" || lists.referenced.length) {
      els.countNote.textContent = "Referenced entries are not fully verified. Category filters About and Referenced.";
    } else if (current.category !== "all") {
      els.countNote.textContent = "Category filters About and Referenced.";
    } else {
      els.countNote.textContent = "";
    }

    els.results.replaceChildren();
    if (!lists.about.length && !lists.mentions.length && !lists.referenced.length) {
      els.results.appendChild(el("p", "empty", "No books match these filters."));
      return;
    }
    if (lists.about.length) {
      CATEGORIES.forEach(function (pair) {
        var id = pair[0];
        var label = pair[1];
        var items = lists.about.filter(function (book) { return book.category === id; });
        if (items.length) els.results.appendChild(renderGroup(label, items));
      });
    }
    if (lists.mentions.length) {
      els.results.appendChild(renderGroup("Mentions", lists.mentions.slice().sort(byYear)));
    }
    if (lists.referenced.length) {
      var referenced = lists.referenced.slice().sort(byYear);
      var section = renderGroup("Referenced, not yet verified", referenced);
      var note = el("p", "section-note", "X references have no confirmed library record. Single-passage rows are one full-text hit, not a confirmed chapter.");
      section.insertBefore(note, section.children[1] || null);
      els.results.appendChild(section);
    }
  }

  function onFilter(event) {
    if (event) event.preventDefault();
    render();
  }

  ["input", "change"].forEach(function (type) {
    els.q.addEventListener(type, onFilter);
    els.list.addEventListener(type, onFilter);
    els.category.addEventListener(type, onFilter);
    els.yearFrom.addEventListener(type, onFilter);
    els.yearTo.addEventListener(type, onFilter);
  });
  document.getElementById("filters").addEventListener("submit", onFilter);

  var params = new URLSearchParams(window.location.search);
  if (params.has("q")) els.q.value = params.get("q");
  if (params.has("list")) els.list.value = params.get("list");
  if (params.has("category")) els.category.value = params.get("category");
  if (params.has("from")) els.yearFrom.value = params.get("from");
  if (params.has("to")) els.yearTo.value = params.get("to");

  fetch("data/books.json")
    .then(function (response) {
      if (!response.ok) throw new Error("HTTP " + response.status);
      return response.json();
    })
    .then(function (data) {
      books = data.books || [];
      if (data.generated_at) {
        els.updated.dateTime = data.generated_at;
        els.updated.textContent = data.generated_at;
      }
      els.status.textContent = "";
      render();
    })
    .catch(function () {
      els.status.textContent = "The catalogue data did not load. Open this site through a local web server so data/books.json can be fetched.";
    });
})();
