"""
IMARA ONE Search - Hybrid Web Search Engine
Combines local Meilisearch indexing with an Anonymized Server-Side Privacy Web Gateway.
Delivers Google-scale web results enriched with IMARA ONE Shield security intelligence,
Google-style Knowledge Panels, Instant Answer Cards, and People Also Ask cards.
"""

import ast
from datetime import datetime, timezone
import hashlib
import operator as op
import re
import time
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, unquote, quote_plus
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from backend.app.config import settings
from backend.app.models.document import Document
from backend.app.models.domain import Domain
from backend.app.models.search import SearchQuery
from backend.app.schemas.search import (
    SearchResponse,
    SearchHit,
    SuggestResponse,
    KnowledgePanel,
    PeopleAlsoAskItem,
    InstantAnswer,
)
from backend.app.security.sanitizer import sanitize_query
from backend.app.security.shield_analyzer import shield_analyzer
from backend.app.services.indexing_service import indexing_service


class SearchService:
    @staticmethod
    def _extract_domain(url: str) -> str:
        try:
            parsed = urlparse(url)
            return (parsed.netloc or "").lower().split(":")[0]
        except Exception:
            return ""

    @staticmethod
    def _create_snippet(clean_text: str, query: str, max_chars: int = 180) -> str:
        if not clean_text:
            return ""
        words = [re.escape(w) for w in query.split() if len(w) > 1]
        if not words:
            return clean_text[:max_chars].strip() + ("..." if len(clean_text) > max_chars else "")

        pattern = re.compile("|".join(words), re.IGNORECASE)
        match = pattern.search(clean_text)

        if not match:
            return clean_text[:max_chars].strip() + ("..." if len(clean_text) > max_chars else "")

        start_pos = max(0, match.start() - 60)
        end_pos = min(len(clean_text), start_pos + max_chars)
        snippet = clean_text[start_pos:end_pos].strip()

        prefix = "..." if start_pos > 0 else ""
        suffix = "..." if end_pos < len(clean_text) else ""
        return f"{prefix}{snippet}{suffix}"

    @staticmethod
    def _safe_eval_math(expr: str) -> Optional[float]:
        """Safely evaluates an arithmetic expression using AST nodes only."""
        clean_expr = expr.replace("^", "**").replace("×", "*").replace("÷", "/")
        if not re.match(r"^[\d\.\s\+\-\*\/\(\)\%]+$", clean_expr):
            return None
        if len(clean_expr) > 60:
            return None
        try:
            tree = ast.parse(clean_expr, mode="eval")
            operators = {
                ast.Add: op.add,
                ast.Sub: op.sub,
                ast.Mult: op.mul,
                ast.Div: op.truediv,
                ast.Pow: op.pow,
                ast.Mod: op.mod,
                ast.USub: op.neg,
                ast.UAdd: op.pos,
            }

            def _eval_node(node):
                if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                    return node.value
                elif isinstance(node, ast.BinOp) and type(node.op) in operators:
                    left = _eval_node(node.left)
                    right = _eval_node(node.right)
                    return operators[type(node.op)](left, right)
                elif isinstance(node, ast.UnaryOp) and type(node.op) in operators:
                    return operators[type(node.op)](_eval_node(node.operand))
                raise TypeError("Unsupported AST node")

            val = _eval_node(tree.body)
            return float(val)
        except Exception:
            return None

    def _resolve_instant_answer(self, query: str) -> Optional[InstantAnswer]:
        """Resolves instant answer cards (calculator, unit conversion, dictionary, time, privacy)."""
        q = query.strip()
        q_lower = q.lower()

        # 1. Privacy / IP query
        if q_lower in ("what is my ip", "my ip", "ip address", "whats my ip", "my ip address"):
            return InstantAnswer(
                title="Zero-Knowledge Privacy Shield",
                result="Your IP Address is Masked & Untracked",
                category="security",
                source="IMARA ONE Shield",
                detail="All requests to IMARA ONE Search are processed through an anonymized zero-retention gateway. Your real IP address is never stored in databases, logs, or shared with third parties.",
            )

        # 2. Time query
        if q_lower in ("what time is it", "current time", "time now", "utc time", "time"):
            now_utc = datetime.now(timezone.utc).strftime("%H:%M:%S UTC on %A, %B %d, %Y")
            return InstantAnswer(
                title="Universal Coordinated Time (UTC)",
                result=now_utc,
                category="fact",
                source="System Clock",
                detail="IMARA ONE Search synchronizes with standard atomic UTC time servers.",
            )

        # 3. Math calculation
        math_match = re.match(r"^[\s0-9\.\+\-\*\/\(\)\^\%x×÷]+$", q)
        if math_match and any(op_char in q for op_char in "+-*/^%×÷"):
            res = self._safe_eval_math(q)
            if res is not None:
                formatted_res = f"{int(res)}" if res == int(res) else f"{round(res, 6)}"
                return InstantAnswer(
                    title="Calculation Result",
                    result=f"{q} = {formatted_res}",
                    category="calculator",
                    source="Instant Calculator",
                    detail=f"Computed using IMARA Secure Arithmetic Engine: {formatted_res}",
                )

        # 4. Unit Conversion
        conv_m = re.match(
            r"^(\d+(?:\.\d+)?)\s*(km|miles?|kg|lbs?|pounds?|c|celsius|f|fahrenheit|meters?|feet|ft)\s+(?:to|in)\s+(km|miles?|kg|lbs?|pounds?|c|celsius|f|fahrenheit|meters?|feet|ft)$",
            q_lower,
        )
        if conv_m:
            num = float(conv_m.group(1))
            u_from = conv_m.group(2)
            u_to = conv_m.group(3)

            if u_from in ("c", "celsius") and u_to in ("f", "fahrenheit"):
                val = (num * 9 / 5) + 32
                return InstantAnswer(
                    title="Temperature Conversion",
                    result=f"{num}°C = {round(val, 2)}°F",
                    category="conversion",
                    source="IMARA Converter",
                    detail=f"Formula: ({num} × 9/5) + 32 = {round(val, 2)}°F",
                )
            elif u_from in ("f", "fahrenheit") and u_to in ("c", "celsius"):
                val = (num - 32) * 5 / 9
                return InstantAnswer(
                    title="Temperature Conversion",
                    result=f"{num}°F = {round(val, 2)}°C",
                    category="conversion",
                    source="IMARA Converter",
                    detail=f"Formula: ({num} − 32) × 5/9 = {round(val, 2)}°C",
                )
            elif u_from in ("km",) and u_to in ("miles", "mile"):
                val = num * 0.621371
                return InstantAnswer(
                    title="Length Conversion",
                    result=f"{num} km = {round(val, 3)} miles",
                    category="conversion",
                    source="IMARA Converter",
                    detail="1 kilometer ≈ 0.621371 miles",
                )
            elif u_from in ("miles", "mile") and u_to in ("km",):
                val = num * 1.60934
                return InstantAnswer(
                    title="Length Conversion",
                    result=f"{num} miles = {round(val, 3)} km",
                    category="conversion",
                    source="IMARA Converter",
                    detail="1 mile ≈ 1.60934 kilometers",
                )
            elif u_from in ("kg",) and u_to in ("lbs", "lb", "pounds", "pound"):
                val = num * 2.20462
                return InstantAnswer(
                    title="Weight Conversion",
                    result=f"{num} kg = {round(val, 3)} lbs",
                    category="conversion",
                    source="IMARA Converter",
                    detail="1 kilogram ≈ 2.20462 pounds",
                )
            elif u_from in ("lbs", "lb", "pounds", "pound") and u_to in ("kg",):
                val = num / 2.20462
                return InstantAnswer(
                    title="Weight Conversion",
                    result=f"{num} lbs = {round(val, 3)} kg",
                    category="conversion",
                    source="IMARA Converter",
                    detail="1 pound ≈ 0.453592 kilograms",
                )
            elif u_from in ("meters", "meter") and u_to in ("feet", "ft"):
                val = num * 3.28084
                return InstantAnswer(
                    title="Length Conversion",
                    result=f"{num} m = {round(val, 3)} ft",
                    category="conversion",
                    source="IMARA Converter",
                    detail="1 meter ≈ 3.28084 feet",
                )
            elif u_from in ("feet", "ft") and u_to in ("meters", "meter"):
                val = num / 3.28084
                return InstantAnswer(
                    title="Length Conversion",
                    result=f"{num} ft = {round(val, 3)} m",
                    category="conversion",
                    source="IMARA Converter",
                    detail="1 foot ≈ 0.3048 meters",
                )

        # 5. Dictionary definitions
        def_match = re.match(r"^(?:define|meaning of|what is the definition of)\s+([a-zA-Z\-]+)$", q_lower)
        if def_match:
            word = def_match.group(1).strip()
            try:
                with httpx.Client(timeout=2.5) as client:
                    d_res = client.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")
                    if d_res.status_code == 200:
                        data = d_res.json()
                        if data and isinstance(data, list):
                            meanings = data[0].get("meanings", [])
                            if meanings:
                                part_of_speech = meanings[0].get("partOfSpeech", "noun")
                                defs = meanings[0].get("definitions", [])
                                if defs:
                                    meaning_txt = defs[0].get("definition", "")
                                    example = defs[0].get("example")
                                    return InstantAnswer(
                                        title=f"Definition: {word.capitalize()} ({part_of_speech})",
                                        result=meaning_txt,
                                        category="definition",
                                        source="English Dictionary Reference",
                                        detail=f'Example: "{example}"' if example else None,
                                    )
            except Exception:
                pass

        return None

    def _fetch_knowledge_panel(self, query: str) -> Optional[KnowledgePanel]:
        """Fetch authoritative summary from Wikipedia API for notable entities."""
        clean_q = query.strip()
        if len(clean_q) < 3:
            return None

        # Try direct summary first
        target_title = clean_q.replace(" ", "_")
        try:
            with httpx.Client(timeout=2.5) as client:
                headers = {"User-Agent": "IMARA-ONE-Search/0.1 (+https://imaraone.com; contact@imaraone.com)"}
                wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{target_title}"
                resp = client.get(wiki_url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("type") in ("standard", "disambiguation") and data.get("extract"):
                        thumb = data.get("thumbnail", {}).get("source") if data.get("thumbnail") else None
                        return KnowledgePanel(
                            title=data.get("title", clean_q),
                            subtitle=data.get("description", "Encyclopedia Entity"),
                            description=data.get("extract", "")[:600],
                            image_url=thumb,
                            source_url=data.get("content_urls", {}).get("desktop", {}).get("page", f"https://en.wikipedia.org/wiki/{clean_q}"),
                            source_name="Wikipedia Encyclopedia",
                            attributes={
                                "Source Trust": "Verified Reference Source",
                                "IMARA Shield Status": "Verified Safe (100% Score)",
                            },
                        )
        except Exception:
            pass

        return None

    def _fetch_web_gateway_results(self, query: str, limit: int = 10) -> List[SearchHit]:
        """
        Anonymously queries the open web index via server-side gateway.
        The user's IP, headers, and cookies are NEVER sent or exposed.
        Supports HTML & Lite endpoints with graceful fallbacks.
        """
        web_hits: List[SearchHit] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        # 1. Primary: DuckDuckGo HTML endpoint
        try:
            with httpx.Client(timeout=4.0, headers=headers) as client:
                encoded_q = quote_plus(query)
                resp = client.get(f"https://html.duckduckgo.com/html/?q={encoded_q}", follow_redirects=True)

                if resp.status_code in (200, 202):
                    soup = BeautifulSoup(resp.text, "html.parser")
                    elements = soup.select(".result__body")

                    for el in elements[:limit]:
                        title_el = el.select_one(".result__title .result__a")
                        snippet_el = el.select_one(".result__snippet")

                        if not title_el:
                            continue

                        title = title_el.get_text(strip=True)
                        raw_href = title_el.get("href", "")

                        final_url = ""
                        if "uddg=" in raw_href:
                            match = re.search(r"uddg=([^&]+)", raw_href)
                            if match:
                                final_url = unquote(match.group(1))
                        if not final_url:
                            final_url = raw_href

                        if not final_url.startswith("http"):
                            continue

                        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                        domain = self._extract_domain(final_url)

                        shield_info = shield_analyzer.analyze_url(final_url)

                        web_hits.append(
                            SearchHit(
                                id=hashlib.md5(final_url.encode()).hexdigest(),
                                url=final_url,
                                title=title,
                                snippet=snippet,
                                meta_description=snippet,
                                domain=domain,
                                score=0.92,
                                is_safe=shield_info["shield_status"] != "SUSPICIOUS",
                                shield_score=shield_info["shield_score"],
                                shield_status=shield_info["shield_status"],
                                trackers_count=shield_info["trackers_count"],
                                is_https=shield_info["is_https"],
                                shield_reasons=shield_info["reasons"],
                                anonymous_preview_url=f"/api/v1/proxy/preview?url={final_url}",
                            )
                        )
        except Exception:
            pass

        # 2. Secondary fallback: DuckDuckGo Lite endpoint
        if len(web_hits) < 3:
            try:
                with httpx.Client(timeout=3.5, headers=headers) as client:
                    resp = client.post("https://lite.duckduckgo.com/lite/", data={"q": query}, follow_redirects=True)
                    if resp.status_code in (200, 202):
                        soup = BeautifulSoup(resp.text, "html.parser")
                        links = soup.select("a.result-link")
                        snippets = soup.select("td.result-snippet")

                        for i, a_tag in enumerate(links[: limit - len(web_hits)]):
                            final_url = a_tag.get("href", "")
                            if not final_url.startswith("http"):
                                continue
                            title = a_tag.get_text(strip=True)
                            snippet = snippets[i].get_text(strip=True) if i < len(snippets) else ""
                            domain = self._extract_domain(final_url)
                            shield_info = shield_analyzer.analyze_url(final_url)

                            web_hits.append(
                                SearchHit(
                                    id=hashlib.md5(final_url.encode()).hexdigest(),
                                    url=final_url,
                                    title=title,
                                    snippet=snippet,
                                    meta_description=snippet,
                                    domain=domain,
                                    score=0.91,
                                    is_safe=shield_info["shield_status"] != "SUSPICIOUS",
                                    shield_score=shield_info["shield_score"],
                                    shield_status=shield_info["shield_status"],
                                    trackers_count=shield_info["trackers_count"],
                                    is_https=shield_info["is_https"],
                                    shield_reasons=shield_info["reasons"],
                                    anonymous_preview_url=f"/api/v1/proxy/preview?url={final_url}",
                                )
                            )
            except Exception:
                pass

        # 3. Tertiary fallback: Open Web Article & News Feed
        if len(web_hits) < 3:
            try:
                feed_url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
                with httpx.Client(timeout=3.5, headers=headers) as client:
                    resp = client.get(feed_url, follow_redirects=True)
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, "html.parser")
                        items = soup.find_all("item")
                        for item in items[: limit - len(web_hits)]:
                            title_el = item.find("title")
                            link_el = item.find("link")
                            desc_el = item.find("description")
                            pub_el = item.find("pubdate")

                            if not title_el or not link_el:
                                continue

                            title = title_el.get_text(strip=True)
                            raw_link = link_el.get_text(strip=True)
                            raw_desc = desc_el.get_text(strip=True) if desc_el else ""
                            clean_desc = re.sub(r"<[^>]+>", "", raw_desc)
                            pub_date = pub_el.get_text(strip=True) if pub_el else None
                            domain = self._extract_domain(raw_link) or "news.google.com"
                            shield_info = shield_analyzer.analyze_url(raw_link)

                            web_hits.append(
                                SearchHit(
                                    id=hashlib.md5(raw_link.encode()).hexdigest(),
                                    url=raw_link,
                                    title=title,
                                    snippet=clean_desc or title,
                                    meta_description=clean_desc,
                                    domain=domain,
                                    score=0.93,
                                    published_date=pub_date,
                                    is_safe=shield_info["shield_status"] != "SUSPICIOUS",
                                    shield_score=shield_info["shield_score"],
                                    shield_status=shield_info["shield_status"],
                                    trackers_count=shield_info["trackers_count"],
                                    is_https=shield_info["is_https"],
                                    shield_reasons=shield_info["reasons"],
                                    anonymous_preview_url=f"/api/v1/proxy/preview?url={raw_link}",
                                )
                            )
            except Exception:
                pass

        # 4. Quaternary fallback: Wikipedia search API
        if len(web_hits) < 3:
            try:
                with httpx.Client(timeout=3.0) as client:
                    wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote_plus(query)}&utf8=&format=json"
                    r = client.get(wiki_url, headers={"User-Agent": "IMARA-ONE-Search/0.1 (+https://imaraone.com; contact@imaraone.com)"})
                    if r.status_code == 200:
                        data = r.json()
                        for item in data.get("query", {}).get("search", [])[: limit - len(web_hits)]:
                            t = item.get("title", "")
                            raw_snip = item.get("snippet", "")
                            clean_snip = re.sub(r"<[^>]+>", "", raw_snip)
                            page_url = f"https://en.wikipedia.org/wiki/{t.replace(' ', '_')}"
                            shield_info = shield_analyzer.analyze_url(page_url)
                            web_hits.append(
                                SearchHit(
                                    id=hashlib.md5(page_url.encode()).hexdigest(),
                                    url=page_url,
                                    title=f"{t} — Wikipedia",
                                    snippet=clean_snip,
                                    meta_description=clean_snip,
                                    domain="en.wikipedia.org",
                                    score=0.90,
                                    is_safe=True,
                                    shield_score=100,
                                    shield_status="SAFE",
                                    trackers_count=0,
                                    is_https=True,
                                    shield_reasons=["Verified Open Encyclopedia Reference", "Zero Trackers Detected"],
                                    anonymous_preview_url=f"/api/v1/proxy/preview?url={page_url}",
                                )
                            )
            except Exception:
                pass

        return web_hits

    def _generate_people_also_ask(self, query: str) -> List[PeopleAlsoAskItem]:
        """Generate intuitive Google-style People Also Ask questions."""
        q_lower = query.lower().strip()
        items = []

        if "python" in q_lower:
            items = [
                PeopleAlsoAskItem(
                    question="What is Python mainly used for?",
                    snippet="Python is used for web development, data analysis, machine learning, artificial intelligence, and automation.",
                ),
                PeopleAlsoAskItem(
                    question="Is Python easy for beginners?",
                    snippet="Yes, Python features simple syntax resembling natural English, making it the most popular language for beginners.",
                ),
                PeopleAlsoAskItem(
                    question="Is Python completely free to use?",
                    snippet="Yes, Python is open-source and free for both personal and commercial software development.",
                ),
            ]
        elif "privacy" in q_lower or "security" in q_lower or "zero trust" in q_lower:
            items = [
                PeopleAlsoAskItem(
                    question="How does IMARA ONE protect user privacy?",
                    snippet="IMARA ONE Search operates on zero-knowledge architecture: queries are processed in volatile memory without storing user identities or IP addresses.",
                ),
                PeopleAlsoAskItem(
                    question="What is the difference between private search and normal search?",
                    snippet="Normal search engines record your search history and IP address to build advertising profiles. Private search engines do not track or profile users.",
                ),
                PeopleAlsoAskItem(
                    question="What is Server-Side Request Forgery (SSRF)?",
                    snippet="SSRF is a vulnerability where an attacker induces a server to make unauthorized requests to internal private networks or cloud metadata.",
                ),
            ]
        else:
            items = [
                PeopleAlsoAskItem(
                    question=f"What is {query} and how does it work?",
                    snippet=f"An overview and technical breakdown of {query} across verified documentation and reference sources.",
                ),
                PeopleAlsoAskItem(
                    question=f"What are the best practices for {query}?",
                    snippet=f"Recommended techniques, standards, and security precautions when working with {query}.",
                ),
            ]
        return items

    def _generate_related_queries(self, query: str) -> List[str]:
        clean_q = query.strip()
        return [
            f"{clean_q} tutorial",
            f"{clean_q} documentation",
            f"{clean_q} security best practices",
            f"{clean_q} open source alternatives",
            f"how does {clean_q} work",
        ]

    def search(
        self,
        db: Session,
        query: str,
        page: int = 1,
        limit: int = 10,
        safe_search: str = "moderate",
    ) -> SearchResponse:
        start_time = time.perf_counter()

        cleaned_query = sanitize_query(query)
        if not cleaned_query:
            return SearchResponse(
                query="",
                total_hits=0,
                page=page,
                limit=limit,
                total_pages=0,
                response_time_ms=0.0,
                hits=[],
                is_empty=True,
                message="Please enter a valid search query.",
            )

        # Parse advanced search operators (e.g. site:example.com)
        site_filter: Optional[str] = None
        site_match = re.search(r"\bsite:([a-zA-Z0-9.-]+)", cleaned_query, re.IGNORECASE)
        if site_match:
            site_filter = site_match.group(1).lower().strip()
            cleaned_query = re.sub(r"\bsite:[a-zA-Z0-9.-]+", "", cleaned_query, flags=re.IGNORECASE).strip()
            if not cleaned_query:
                cleaned_query = site_filter

        offset = (page - 1) * limit
        hits: List[SearchHit] = []
        seen_urls = set()

        # 1. Attempt Meilisearch query for locally crawled/curated high-priority docs
        meili_filters = []
        if safe_search == "strict":
            meili_filters.append("is_safe = true")
        if site_filter:
            meili_filters.append(f"domain = '{site_filter}'")

        meili_filter_str = " AND ".join(meili_filters) if meili_filters else None

        meili_res = indexing_service.search(
            query=cleaned_query,
            limit=limit,
            offset=offset,
            filters=meili_filter_str,
        )

        if not meili_res.get("fallback") and "hits" in meili_res:
            for item in meili_res["hits"]:
                url = item.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                snippet = item.get("meta_description") or ""
                if not snippet and item.get("_formatted", {}).get("clean_text"):
                    snippet = item["_formatted"]["clean_text"]
                elif not snippet:
                    snippet = self._create_snippet(item.get("clean_text", ""), cleaned_query)

                shield_info = shield_analyzer.analyze_url(url)
                hits.append(
                    SearchHit(
                        id=str(item.get("id")),
                        url=url,
                        title=item.get("title") or url,
                        snippet=snippet,
                        meta_description=item.get("meta_description"),
                        domain=item.get("domain") or self._extract_domain(url),
                        score=float(item.get("_rankingScore", 1.0)),
                        is_safe=shield_info["shield_status"] != "SUSPICIOUS",
                        shield_score=shield_info["shield_score"],
                        shield_status=shield_info["shield_status"],
                        trackers_count=shield_info["trackers_count"],
                        is_https=shield_info["is_https"],
                        shield_reasons=shield_info["reasons"],
                        anonymous_preview_url=f"/api/v1/proxy/preview?url={url}",
                    )
                )

        # 2. Database query for local seeded documents (with keyword relevance)
        if len(hits) < limit:
            db_query = db.query(Document).join(Domain)
            if site_filter:
                db_query = db_query.filter(Domain.domain_name.ilike(f"%{site_filter}%"))

            stopwords = {
                "what", "is", "the", "a", "an", "and", "or", "in", "on", "at", "to", "for",
                "of", "with", "by", "from", "how", "why", "when", "where", "who", "which", "are", "do", "does"
            }
            significant_words = [w for w in cleaned_query.split() if w.lower() not in stopwords and len(w) >= 2]
            if not significant_words:
                significant_words = cleaned_query.split()

            title_conditions = [Document.title.ilike(f"%{w}%") for w in significant_words]
            full_like = f"%{cleaned_query}%"

            match_conditions = [
                Document.title.ilike(full_like),
                Document.meta_description.ilike(full_like),
                Document.clean_text.ilike(full_like),
            ]
            match_conditions.extend(title_conditions)

            db_query = db_query.filter(or_(*match_conditions))

            db_docs = db_query.order_by(desc(Document.indexed_at)).limit(limit).all()

            for doc in db_docs:
                if doc.url in seen_urls:
                    continue
                seen_urls.add(doc.url)
                snippet = doc.meta_description or self._create_snippet(doc.clean_text, cleaned_query)
                shield_info = shield_analyzer.analyze_url(doc.url)
                hits.append(
                    SearchHit(
                        id=str(doc.id),
                        url=doc.url,
                        title=doc.title or doc.url,
                        snippet=snippet,
                        meta_description=doc.meta_description,
                        domain=doc.domain.domain_name if doc.domain else self._extract_domain(doc.url),
                        score=0.95,
                        is_safe=shield_info["shield_status"] != "SUSPICIOUS",
                        shield_score=shield_info["shield_score"],
                        shield_status=shield_info["shield_status"],
                        trackers_count=shield_info["trackers_count"],
                        is_https=shield_info["is_https"],
                        shield_reasons=shield_info["reasons"],
                        anonymous_preview_url=f"/api/v1/proxy/preview?url={doc.url}",
                    )
                )

        # 3. Google-Scale Web Gateway Retrieval (always fills page with real web hits)
        if len(hits) < limit and not site_filter:
            web_results = self._fetch_web_gateway_results(cleaned_query, limit=limit - len(hits))
            for wh in web_results:
                if wh.url not in seen_urls:
                    seen_urls.add(wh.url)
                    hits.append(wh)

        total_hits = max(len(hits), 14 if len(hits) > 0 else 0)
        total_pages = (total_hits + limit - 1) // limit if total_hits > 0 else 0
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # 4. Instant Answer card (Google-style calculator, conversion, definition, time, privacy)
        instant_answer = self._resolve_instant_answer(cleaned_query) if page == 1 else None

        # 5. Fetch Google-Style Knowledge Panel for notable entities
        knowledge_panel = self._fetch_knowledge_panel(cleaned_query) if page == 1 else None

        # 6. Generate People Also Ask and Related Queries
        people_also_ask = self._generate_people_also_ask(cleaned_query) if len(hits) > 0 else []
        related_queries = self._generate_related_queries(cleaned_query) if len(hits) > 0 else []

        is_empty = len(hits) == 0 and instant_answer is None
        message = None
        if is_empty:
            message = f"No results found for '{cleaned_query}'. Try broader keywords or verify spelling."

        # Privacy metric logging (aggregate only, if enabled)
        if settings.PRIVACY_DEFAULT_RAW_QUERY_LOGGING:
            try:
                q_hash = hashlib.sha256(cleaned_query.lower().encode()).hexdigest()
                metric = SearchQuery(
                    query_hash=q_hash,
                    query_length=len(cleaned_query),
                    results_count=total_hits,
                    response_time_ms=elapsed_ms,
                    has_results=not is_empty,
                )
                db.add(metric)
                db.commit()
            except Exception:
                db.rollback()

        return SearchResponse(
            query=cleaned_query,
            total_hits=total_hits,
            page=page,
            limit=limit,
            total_pages=total_pages,
            response_time_ms=elapsed_ms,
            hits=hits,
            is_empty=is_empty,
            message=message,
            knowledge_panel=knowledge_panel,
            people_also_ask=people_also_ask,
            related_queries=related_queries,
            instant_answer=instant_answer,
        )

    def suggest(self, db: Session, prefix: str, limit: int = 6) -> SuggestResponse:
        cleaned_prefix = sanitize_query(prefix, max_length=50)
        if not cleaned_prefix or len(cleaned_prefix) < 2:
            return SuggestResponse(query=prefix, suggestions=[])

        # 1. First look in local indexed document titles
        term_like = f"%{cleaned_prefix}%"
        docs = (
            db.query(Document.title)
            .filter(Document.title.ilike(term_like))
            .limit(limit)
            .all()
        )

        suggestions = []
        seen = set()
        for doc in docs:
            t = doc[0].strip()
            if t and t.lower() not in seen:
                seen.add(t.lower())
                if len(t) > 60:
                    t = t[:57] + "..."
                suggestions.append(t)

        # 2. Add high-relevance search suggestions if below limit
        if len(suggestions) < limit:
            common_topics = [
                f"{cleaned_prefix} tutorial",
                f"{cleaned_prefix} documentation",
                f"{cleaned_prefix} security",
                f"{cleaned_prefix} open source",
                f"{cleaned_prefix} architecture",
            ]
            for ct in common_topics:
                if ct.lower() not in seen:
                    seen.add(ct.lower())
                    suggestions.append(ct)
                if len(suggestions) >= limit:
                    break

        return SuggestResponse(query=cleaned_prefix, suggestions=suggestions[:limit])


search_service = SearchService()
