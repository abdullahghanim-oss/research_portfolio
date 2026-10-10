#!/usr/bin/env python3
"""Refresh publication data. Scopus indexing is only asserted on an exact API record match."""
import json, os, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "publications.json"
SCOPUS_AUTHOR_ID = os.getenv("SCOPUS_AUTHOR_ID", "60431094700")
SCOPUS_API_KEY = os.getenv("SCOPUS_API_KEY", "").strip()
ORCID = os.getenv("ORCID", "0000-0002-2901-4161")
OPENALEX_MAILTO = os.getenv("OPENALEX_MAILTO", "").strip()

def get_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent":"ResearchPortfolioBot/1.0 (personal academic website)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        # API responses may include useful request validation details; do not print request headers/secrets.
        print(f"HTTP {e.code} from data provider.")
        if body:
            print("Provider response (truncated):", body[:1500])
        raise

def norm_title(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()

def clean_doi(s):
    if not s: return ""
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", str(s).strip(), flags=re.I).lower()

def author_string(authors):
    if isinstance(authors, list):
        vals=[]
        for a in authors:
            if isinstance(a, dict): vals.append(a.get("authname") or a.get("name") or a.get("display_name") or "")
            else: vals.append(str(a))
        return ", ".join(x for x in vals if x)
    return str(authors or "")

def fetch_scopus():
    if not SCOPUS_API_KEY:
        print("SCOPUS_API_KEY not set; skipping Scopus API.")
        return None
    # Scopus Search API accepts AU-ID as the author identifier search field.
    # Keep query syntax simple and use the documented STANDARD view.
    query = f"AU-ID({SCOPUS_AUTHOR_ID})"
    params = urllib.parse.urlencode({
        "query": query,
        "count": 25,
        "start": 0,
        "sort": "-coverDate",
        "view": "STANDARD"
    })
    url = "https://api.elsevier.com/content/search/scopus?" + params
    data = get_json(url, {"X-ELS-APIKey":SCOPUS_API_KEY,"Accept":"application/json","User-Agent":"ResearchPortfolioBot/1.0"})
    sr = data.get("search-results", {})
    results = sr.get("entry", []) or []
    papers=[]
    for x in results:
        if not x.get("dc:title"): continue
        doi=clean_doi(x.get("prism:doi"))
        eid=x.get("eid","")
        papers.append({
            "title":x.get("dc:title","").strip(),
            "authors":x.get("dc:creator",""),
            "year":int((x.get("prism:coverDate","")[:4]) or 0) or None,
            "venue":x.get("prism:publicationName",""),
            "doi":doi,
            "url":x.get("prism:url") or (f"https://www.scopus.com/record/display.uri?eid={urllib.parse.quote(eid)}" if eid else ""),
            "scopus_url":f"https://www.scopus.com/record/display.uri?eid={urllib.parse.quote(eid)}" if eid else "",
            "scopus_indexed":True,
            "scopus_status":"confirmed",
            "scopus_note":"Matched to a record returned by the Scopus Search API.",
            "source":"Scopus API",
            "scopus_eid":eid,
        })
    print(f"Scopus API returned {len(papers)} records.")
    return papers

def fetch_openalex():
    # OpenAlex provides a useful open bibliographic fallback, but does not verify Scopus indexing.
    query = urllib.parse.urlencode({"filter":f"authorships.author.orcid:https://orcid.org/{ORCID}","per-page":200,"sort":"publication_year:desc"})
    if OPENALEX_MAILTO: query += "&mailto=" + urllib.parse.quote(OPENALEX_MAILTO)
    data = get_json("https://api.openalex.org/works?" + query)
    papers=[]
    for x in data.get("results", []):
        title=(x.get("title") or "").strip()
        if not title: continue
        doi=clean_doi(x.get("doi"))
        authors=[]
        for au in x.get("authorships", []):
            nm=(au.get("author") or {}).get("display_name")
            if nm: authors.append(nm)
        source=(x.get("primary_location") or {}).get("source") or {}
        venue=source.get("display_name","")
        papers.append({
            "title":title,"authors":", ".join(authors),
            "year":x.get("publication_year"),"venue":venue,"doi":doi,
            "url":x.get("doi") or x.get("id",""),"scopus_url":"",
            "scopus_indexed":None,"scopus_status":"not_checked",
            "scopus_note":"Not checked against Scopus: OpenAlex is bibliographic metadata, not proof of Scopus indexing.",
            "source":"OpenAlex","openalex_id":x.get("id","")
        })
    print(f"OpenAlex returned {len(papers)} records.")
    return papers

def merge(scopus, openalex):
    # Keep Scopus records authoritative for Scopus status. Merge by DOI, then normalized title.
    out=[]
    by_doi={}
    by_title={}
    for p in scopus or []:
        out.append(p)
        if p.get("doi"): by_doi[p["doi"]]=p
        by_title[norm_title(p.get("title"))]=p
    for p in openalex or []:
        target=by_doi.get(p.get("doi")) if p.get("doi") else None
        if not target: target=by_title.get(norm_title(p.get("title")))
        if target:
            # Fill missing metadata without overwriting Scopus verification.
            for k in ("authors","year","venue","doi","url"):
                if not target.get(k) and p.get(k): target[k]=p[k]
            if p.get("openalex_id"): target["openalex_id"]=p["openalex_id"]
        else:
            out.append(p)
            if p.get("doi"): by_doi[p["doi"]]=p
            by_title[norm_title(p.get("title"))]=p
    # Stable ordering; do not silently claim false when Scopus was unavailable.
    out.sort(key=lambda p:(p.get("year") or 0, p.get("title","").lower()), reverse=True)
    return out

def main():
    scopus=None
    try:
        scopus=fetch_scopus()
    except Exception as e:
        print("Scopus lookup failed; continuing with fallback metadata source.")
        print(f"Scopus error type: {type(e).__name__}")
    openalex=[]
    try: openalex=fetch_openalex()
    except Exception as e: print("OpenAlex fetch failed:",e)
    if scopus is None and not openalex:
        raise SystemExit("No data source succeeded. Configure SCOPUS_API_KEY or check OpenAlex/ORCID.")
    papers=merge(scopus,openalex)
    # If Scopus API was available, OpenAlex-only records are explicitly unconfirmed, not marked indexed.
    result={
        "updated_at":datetime.now(timezone.utc).isoformat(),
        "provider":"Scopus API + OpenAlex" if scopus is not None else "OpenAlex (Scopus not configured)",
        "scopus_check_performed":scopus is not None,
        "publications":papers
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Wrote {len(papers)} publications to {OUT}")

if __name__=="__main__":
    main()
