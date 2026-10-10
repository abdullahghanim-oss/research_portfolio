# Research portfolio with automatic publication refresh

This is a GitHub Pages starter for Abdullah Ghanim Jaber. The site reads `publications.json`, and GitHub Actions refreshes that file daily.

## Included
- `index.html`: responsive research portfolio UI with search, year filter, and Scopus-status filter.
- `update_publications.py`: retrieves records from Scopus (when an API key is configured) and OpenAlex using your ORCID; merges likely duplicates by DOI then normalized title.
- `.github/workflows/refresh-publications.yml`: daily GitHub Actions workflow.
- `publications.json`: generated data file at the repository root.

## Install into your existing repository
1. Download and extract this ZIP.
2. Upload/replace `index.html`, `update_publications.py`, and `publications.json` at the repository root.
3. Upload `.github/workflows/refresh-publications.yml` preserving the `.github/workflows` folder structure.
4. In GitHub, open **Settings → Secrets and variables → Actions → New repository secret**.
   - Name: `SCOPUS_API_KEY`
   - Value: your Elsevier/Scopus API key.
5. Open **Settings → Actions → General** and ensure workflows are allowed to run. Under workflow permissions, allow read/write repository contents if required.
6. Open **Actions → Refresh research publications → Run workflow** for the first run.
7. Wait for the workflow to finish, then check the deployed Pages site after the commit/deployment completes.

## Scopus API key
Get an API key through the Elsevier Developer Portal: https://dev.elsevier.com/. Access and rate limits depend on your account/institution and Elsevier policies. Never put the key in `index.html`, JavaScript, or any public file. Store it only as the GitHub Actions secret named `SCOPUS_API_KEY`.

If you do not configure the key, the workflow attempts OpenAlex using your ORCID. OpenAlex records are shown as **Scopus status unavailable / not checked**, not as confirmed Scopus records. This avoids falsely asserting that a publication is indexed.

## Google Scholar limitation
Google Scholar does not offer an official public API for arbitrary profile publication syncing. This starter does not scrape Scholar pages or fabricate live Scholar metrics. Use the Google Scholar profile link, and treat Scholar-specific counts as separate metrics. A future importer can ingest an exported Scholar BibTeX/CSV file, but that export itself is not automatic.

## Important accuracy notes
- “Scopus indexed” is displayed only for a document returned by the Scopus Search API for the configured Scopus author ID.
- A title/DOI match is useful but can need manual review when preprints, conference versions, and final journal versions differ.
- “Not confirmed in Scopus” is not proof of non-indexing, particularly if API access fails, the API returns incomplete author results, or the record has not yet been added.
- OpenAlex is a fallback bibliographic source; it is not a Scopus verification service.
- The script is a starter integration. Verify results against your Scopus profile and review any duplicate or missing records.

## Profile identifiers
- Scopus Author ID: `60431094700`
- ORCID: `0000-0002-2901-4161`
- Google Scholar: https://scholar.google.com/citations?user=6HiI4toAAAAJ&hl=en
