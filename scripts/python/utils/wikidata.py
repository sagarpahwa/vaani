"""
Wikidata SPARQL helpers for candidate speaker discovery.
Queries one occupation QID at a time — avoids timeouts from large VALUES clauses.
Rate-limited to 1.2 seconds between requests.
"""

import logging
import time
import urllib.error

from SPARQLWrapper import JSON, SPARQLWrapper

log = logging.getLogger(__name__)

ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "VaaniBot/1.0 (public-speaking-intelligence-research)"
DELAY = 1.2  # seconds between requests
PAGE_SIZE = 200  # conservative page size — Wikidata is stable up to ~500 but 200 is safer

# Wikidata occupation QID → our profession_category
OCCUPATION_MAP: dict[str, str] = {
    "Q82955": "politician",
    "Q15253558": "activist",
    "Q1622272": "academic",  # university professor
    "Q2059704": "academic",  # academic
    "Q10697012": "academic",  # philosopher
    "Q43845": "business_leader",  # businessperson
    "Q1930187": "journalist",
    "Q36180": "author",  # writer
    "Q482980": "author",  # author
    "Q49757": "author",  # poet
    "Q245068": "comedian",
    "Q901": "scientist",
    "Q170790": "scientist",  # mathematician
    "Q40348": "lawyer",
    "Q193391": "politician",  # diplomat
    "Q11900058": "activist",  # human rights activist
    "Q14467526": "activist",  # women's rights activist
    "Q33999": "entertainer",  # actor
    "Q177220": "entertainer",  # singer
    "Q2526255": "entertainer",  # film director
    "Q3338853": "religious_leader",
}

# Query per occupation — avoids huge VALUES joins that cause Wikidata 504s
_QUERY = """\
SELECT ?item ?itemLabel ?wikiTitle ?birthYear ?deathYear ?countryLabel
WHERE {{
  ?item wdt:P31 wd:Q5 ;
        wdt:P106 wd:{occ_qid} .
  ?wikiLink schema:about ?item ;
            schema:inLanguage "en" ;
            schema:isPartOf <https://en.wikipedia.org/> .
  BIND(REPLACE(STR(?wikiLink), "https://en.wikipedia.org/wiki/", "") AS ?wikiTitle)
  OPTIONAL {{ ?item wdt:P569 ?bd . BIND(YEAR(?bd) AS ?birthYear) }}
  OPTIONAL {{ ?item wdt:P570 ?dd . BIND(YEAR(?dd) AS ?deathYear) }}
  OPTIONAL {{ ?item wdt:P27 ?country . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}}
LIMIT {limit}
OFFSET {offset}
"""


def _sparql_client() -> SPARQLWrapper:
    s = SPARQLWrapper(ENDPOINT, agent=USER_AGENT)
    s.setReturnFormat(JSON)
    return s


def fetch_page(
    occ_qid: str, offset: int, limit: int = PAGE_SIZE, max_retries: int = 3
) -> list[dict]:
    """Fetch one page for a single occupation QID. Retries on 429 with 65s backoff."""
    query = _QUERY.format(occ_qid=occ_qid, limit=limit, offset=offset)
    for attempt in range(1, max_retries + 1):
        sparql = _sparql_client()
        sparql.setQuery(query)
        try:
            results = sparql.query().convert()
            time.sleep(DELAY)
            return results["results"]["bindings"]
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 65  # Wikidata's 1 req/min rate limit during outage
                log.warning(
                    "429 rate-limited [%s]. Waiting %ds (attempt %d/%d)…",
                    occ_qid,
                    wait,
                    attempt,
                    max_retries,
                )
                time.sleep(wait)
                if attempt == max_retries:
                    raise
            else:
                log.error("SPARQL HTTP error [%s offset=%d]: %s", occ_qid, offset, e)
                time.sleep(DELAY * 2)
                raise
        except Exception as e:
            log.error("SPARQL error [%s offset=%d]: %s", occ_qid, offset, e)
            time.sleep(DELAY * 2)
            raise
    raise RuntimeError(f"Max retries exceeded for {occ_qid} offset={offset}")


def parse_row(row: dict, occ_qid: str) -> dict | None:
    """Normalise a SPARQL binding dict. Returns None if the row is unusable."""
    item_uri = row.get("item", {}).get("value", "")
    qid = item_uri.rsplit("/", 1)[-1] if "/" in item_uri else None
    if not qid or not qid.startswith("Q"):
        return None

    name = row.get("itemLabel", {}).get("value", "")
    if not name or name == qid:  # Wikidata falls back to QID when no English label exists
        return None

    birth_raw = row.get("birthYear", {}).get("value")
    death_raw = row.get("deathYear", {}).get("value")

    return {
        "wikidata_id": qid,
        "canonical_name": name,
        "wikipedia_title": row.get("wikiTitle", {}).get("value", ""),
        "country_or_region": row.get("countryLabel", {}).get("value") or None,
        "birth_year": int(birth_raw) if birth_raw else None,
        "death_year": int(death_raw) if death_raw else None,
        "profession_category": OCCUPATION_MAP.get(occ_qid, "other"),
        "occupation_qid": occ_qid,
    }
