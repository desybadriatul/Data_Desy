"""Task 1 builder for Competitive Analysis.

Creates registry-approved `report_input_v1` views for `competitive_analysis`.

Design rules v3:
- Task 1 only prepares data: no final deck narrative and no invented benchmark.
- Brand universe must be explicit via client_brand + competitor_brands.
- Competitive scope is campaign-first: fetch each campaign in the brand universe; keyword matching is fallback only.
- Multi-campaign rows are counted once for each requested campaign membership.
- KPI/SOV/SOE/sentiment/channel/content views use full canonical rows in scope.
- Final Competitive Topic/Narrative views use cached LLM taxonomy assignments
  from Title + Content / Content. Raw Topic Extraction is diagnostic only.
- Legacy Aspect and Entity Extraction are not core dependencies. They may exist
  in raw exports, but this builder does not require them and marks those views
  explicitly unavailable instead of returning silent empty tables.
- Every topic-level number is aggregated from classified canonical rows, so topic
  figures can be audited through evidence IDs, assignment coverage, and Data Pack.
- Qualitative evidence rows keep source_url for appendix/data pack; Task 2 uses
  Evidence IDs on main slides.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from database import db

try:
    from reporting.enrichment.topic_contract import (
        canonical_content_hash,
        canonical_key_from_values,
        topic_text_for_llm,
    )
    from reporting.enrichment.topic_store import (
        get_assignment_index,
        list_taxonomies,
    )
except Exception:  # pragma: no cover - keeps builder importable before shared patch install
    import hashlib

    def _fallback_norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    def canonical_content_hash(title: Any, content: Any) -> str:  # type: ignore[misc]
        basis = f"{_fallback_norm(title).casefold()}\n{_fallback_norm(content).casefold()}"
        return hashlib.sha256(basis.encode("utf-8")).hexdigest()

    def canonical_key_from_values(*, url: Any, canonical_post_id: Any) -> str:  # type: ignore[misc]
        clean_url = _fallback_norm(url)
        if clean_url:
            return f"url:{clean_url.casefold()}"
        if canonical_post_id is None or str(canonical_post_id).strip() == "":
            raise ValueError("canonical_post_id wajib tersedia bila URL kosong")
        return f"id:{canonical_post_id}"

    def topic_text_for_llm(title: Any, content: Any) -> str:  # type: ignore[misc]
        title_text = _fallback_norm(title)[:80]
        content_text = _fallback_norm(content)[:780]
        if title_text and content_text:
            return f"Judul: {title_text}\nKonten: {content_text}"
        return f"Judul: {title_text}" if title_text else f"Konten: {content_text}"

    def get_assignment_index(**_: Any) -> dict[tuple[str, str], dict[str, Any]]:  # type: ignore[misc]
        return {}

    def list_taxonomies(project_name: str) -> list[dict[str, Any]]:  # type: ignore[misc]
        return []

from reporting.contracts.report_input_contract_v1 import add_limitation
from reporting.enrichment.global_relevance_filter import (
    apply_global_relevance_filter,
    compact_exclusion_examples,
)
from reporting.enrichment.taxonomy_evolution import (
    extract_taxonomy_evolution_candidates,
)
from reporting.task1.base_builder import BaseReportInputBuilder, BuildRequest, ReportBuildError


SENTIMENTS = ("positive", "neutral", "negative")
SOCIAL_CHANNELS = {
    "instagram", "ig", "tiktok", "facebook", "fb", "twitter", "x", "youtube", "yt", "threads",
}


# ---------------------------------------------------------------------------
# Generic field and value helpers
# ---------------------------------------------------------------------------


def _safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        value = float(value)
        return int(value) if value.is_integer() else round(value, 4)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _norm_key(value: Any) -> str:
    return "".join(ch for ch in str(value or "").casefold() if ch.isalnum())


def _num(value: Any) -> int | float:
    value = _safe(value)
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    if not text:
        return 0
    text = text.replace("Rp", "").replace("IDR", "").replace(" ", "")
    # Prefer Indonesian thousand separator handling for raw exports.
    if text.count(",") == 1 and text.count(".") >= 1:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", "")
    try:
        number = float(text)
    except ValueError:
        return 0
    return int(number) if number.is_integer() else round(number, 4)


def _pct(part: int | float, base: int | float) -> float | None:
    return round(float(part) * 100 / float(base), 1) if base else None


def _flatten_lookup(record: Mapping[str, Any]) -> dict[str, Any]:
    lookup: dict[str, Any] = {}

    def add_map(item: Mapping[str, Any]) -> None:
        for key, value in item.items():
            if isinstance(key, str):
                lookup.setdefault(_norm_key(key), value)

    add_map(record)
    for nested_key in ("raw", "raw_data", "payload", "data", "json", "metadata"):
        nested = record.get(nested_key)
        if isinstance(nested, Mapping):
            add_map(nested)
    return lookup


def _source_value(record: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        value = record.get(name)
        if value is not None and str(value).strip() != "":
            return value
    lookup = _flatten_lookup(record)
    for name in names:
        value = lookup.get(_norm_key(name))
        if value is not None and str(value).strip() != "":
            return value
    return None


def _channel_norm(value: Any) -> str:
    channel = _text(value).casefold()
    aliases = {
        "ig": "instagram",
        "instagram": "instagram",
        "tiktok": "tiktok",
        "tik tok": "tiktok",
        "fb": "facebook",
        "facebook": "facebook",
        "twitter": "twitter",
        "x": "twitter",
        "x/twitter": "twitter",
        "youtube": "youtube",
        "yt": "youtube",
        "online media": "online_media",
        "media online": "online_media",
        "online": "online_media",
        "printmedia": "printmedia",
        "print media": "printmedia",
        "forum": "forum",
        "threads": "threads",
    }
    return aliases.get(channel, channel.replace(" ", "_") or "unknown")


def _sentiment(value: Any) -> str:
    clean = _text(value).casefold()
    if clean in {"positive", "positif", "pos"}:
        return "positive"
    if clean in {"negative", "negatif", "neg"}:
        return "negative"
    if clean in {"neutral", "netral", "neu"}:
        return "neutral"
    return "unclassified"


def _split_terms(value: Any, *, limit: int = 12) -> list[str]:
    text = _text(value)
    if not text:
        return []
    for sep in ("|", ";", "\n"):
        text = text.replace(sep, ",")
    terms: list[str] = []
    seen: set[str] = set()
    for raw in text.split(","):
        term = _text(raw)
        if not term:
            continue
        key = term.casefold()
        if key not in seen:
            terms.append(term[:120])
            seen.add(key)
        if len(terms) >= limit:
            break
    return terms


def _brand_key(value: str) -> str:
    return _norm_key(value)


def _brand_match(text: str, candidates: Iterable[str]) -> str | None:
    haystack = _brand_key(text)
    if not haystack:
        return None
    for brand in candidates:
        key = _brand_key(brand)
        if key and (haystack == key or key in haystack or haystack in key):
            return brand
    return None


def _dominant_sentiment(counts: Mapping[str, int]) -> str | None:
    known = {key: int(counts.get(key) or 0) for key in SENTIMENTS}
    if not sum(known.values()):
        return None
    return max(SENTIMENTS, key=lambda item: (known[item], item == "neutral"))


def _safe_div(numerator: int | float, denominator: int | float) -> float | None:
    if not denominator:
        return None
    return round(float(numerator) / float(denominator), 4)


class CompetitiveAnalysisBuilder(BaseReportInputBuilder):
    report_type_id = "competitive_analysis"
    builder_version = "1.1.0"

    def build_views(self, report_input: dict[str, Any], request: BuildRequest) -> None:
        scope = dict(request.scope or {})
        brand_universe = self._brand_universe(request, scope)
        records = self._fetch_records(request, scope, brand_universe)
        if not records:
            raise ReportBuildError("Tidak ada canonical records pada scope Competitive Analysis.")

        normalized = [self._normalize_record(row, brand_universe, request) for row in records]
        rows = [row for row in normalized if row["brand"]]
        unmapped_count = len(normalized) - len(rows)

        if not rows:
            raise ReportBuildError(
                "Tidak ada row yang bisa dipetakan ke client_brand/competitor_brands. "
                "Pastikan field Campaign/Brand/Tag atau keyword brand tersedia."
            )

        relevance_result = apply_global_relevance_filter(
            rows,
            project_name=request.project_name,
            report_type_id=self.report_type_id,
            client_brand=request.client_brand or (brand_universe[0] if brand_universe else request.project_name),
            brand_universe=brand_universe,
            scope=scope,
            analysis_objective=request.analysis_objective,
            row_brand_field="brand",
            keep_review_rows=True,
        )
        rows = relevance_result["clean_rows"]
        self._attach_relevance_filter_summary(report_input, relevance_result)
        if not rows:
            raise ReportBuildError(
                "Tidak ada clean/review row setelah global relevance/noise filter Competitive Analysis."
            )

        topic_context = self._attach_llm_topic_assignments(report_input, rows, request)

        report_input["scope"]["competitive_analysis_policy"] = {
            "brand_universe": brand_universe,
            "client_brand": request.client_brand or (brand_universe[0] if brand_universe else None),
            "competitor_brands": list(request.competitor_brands),
            "unmapped_rows_excluded": unmapped_count,
            "topic_policy": "LLM competitive topic/narrative taxonomy from Title + Content; raw Topic Extraction diagnostic only",
            "topic_enrichment": topic_context,
            "evidence_url_policy": "Task 1 keeps URLs for audit; Task 2 should use Evidence IDs on main slides and full URLs only in appendix/data pack.",
        }

        if not request.competitor_brands:
            add_limitation(
                report_input,
                "competitor_brands tidak diisi; output bersifat single-brand diagnostic, bukan benchmark kompetitif penuh.",
            )
        if unmapped_count:
            add_limitation(
                report_input,
                f"{unmapped_count} row tidak dapat dipetakan ke brand universe dan dikeluarkan dari competitive views.",
            )

        report_input["metric_readiness"] = self._metric_readiness(rows, brand_universe)
        report_input["data_health"] = self._data_health(rows, normalized, brand_universe)
        for warning in report_input["metric_readiness"].get("warnings", []):
            add_limitation(report_input, warning)

        self._add_brand_volume_engagement(report_input, rows, brand_universe)
        self._add_sentiment_by_brand(report_input, rows, brand_universe)
        self._add_issue_sentiment_by_brand(report_input, rows, brand_universe)
        self._add_channel_mix_by_brand(report_input, rows, brand_universe)
        self._add_content_type_by_brand(report_input, rows, brand_universe)
        self._add_kpi_summary_by_brand(report_input, rows, brand_universe)
        self._add_sentiment_channel_by_brand(report_input, rows, brand_universe)
        self._add_brand_status(report_input, rows, request, brand_universe)

        self.mark_view_not_available(
            report_input,
            view_id="ql_ca_aspect_sentiment_by_brand",
            view_type="qualitative",
            reason=(
                "Legacy Aspect/ABSA column is not used as a core CA dependency. "
                "Topic/narrative drivers are produced by cached LLM classification from Title + Content."
            ),
            metadata={"replacement_view": "ql_ca_topic_sentiment_by_brand", "aspect_policy": "deprecated_raw_field_not_core"},
        )
        self.mark_view_not_available(
            report_input,
            view_id="ql_ca_competitive_entities",
            view_type="qualitative",
            reason=(
                "Entity Extraction is optional diagnostic metadata. Competitive brand universe comes from client_brand + competitor_brands, "
                "not raw entity extraction."
            ),
            metadata={"entity_policy": "optional_diagnostic_not_core"},
        )
        self._add_positive_negative_highlights(report_input, rows, brand_universe)
        self._add_top_authors_by_brand(report_input, rows, brand_universe)
        self._add_top_social_posts_by_brand(report_input, rows, brand_universe)
        self._add_topic_sentiment_by_brand(report_input, rows, brand_universe)

    def _attach_relevance_filter_summary(
        self,
        report_input: dict[str, Any],
        relevance_result: Mapping[str, Any],
    ) -> None:
        summary = dict(relevance_result.get("summary") or {})
        summary["examples"] = compact_exclusion_examples(
            relevance_result.get("excluded_rows") or [],
            limit=8,
        )
        report_input["scope"]["global_relevance_filter"] = summary
        excluded = int(summary.get("excluded_count") or 0)
        review = int(summary.get("review_count") or 0)
        if excluded:
            add_limitation(
                report_input,
                f"Global relevance filter mengeluarkan {excluded} row noise sebelum SOV/SOE/sentiment Competitive Analysis dihitung.",
            )
        if review:
            add_limitation(
                report_input,
                f"{review} row competitive scope masuk review relevance ber-confidence rendah; tetap dihitung tetapi ditandai dalam audit scope.",
            )

    # ------------------------------------------------------------------
    # Fetch and normalize
    # ------------------------------------------------------------------

    def _fetch_records(
        self,
        request: BuildRequest,
        scope: Mapping[str, Any],
        brand_universe: list[str],
    ) -> list[Mapping[str, Any]]:
        """Fetch records campaign-first for every requested brand.

        Daily/MMR can fetch one campaign. Competitive Analysis must fetch the
        client campaign plus every competitor campaign. If the same canonical
        post belongs to multiple requested campaigns, it is intentionally
        represented once per campaign so campaign-level counts match the raw
        `Campaigns` membership rule. Keyword matching is not used as the primary
        campaign scope here; it remains only as a defensive fallback inside
        `_normalize_record` when campaign metadata is absent.
        """
        keywords = scope.get("keywords") or None
        excludes = scope.get("exclude_keywords") or None
        match_mode = scope.get("match_mode") or "any"
        channels = request.channels or scope.get("channels") or None

        campaigns = brand_universe or [request.project_name]
        fetched: list[Mapping[str, Any]] = []
        missing_campaigns: list[str] = []

        for campaign in campaigns:
            campaign_name = _text(campaign)
            if not campaign_name:
                continue
            try:
                raw_records = db.fetch_raw_records(
                    campaign_name,
                    request.start_date,
                    request.end_date,
                    None,
                    keywords,
                    excludes,
                    match_mode,
                    channels,
                )
            except Exception as exc:
                raise ReportBuildError(f"Gagal menarik raw canonical records untuk campaign '{campaign_name}': {exc}") from exc
            if raw_records is None:
                missing_campaigns.append(campaign_name)
                continue

            seen_within_campaign: set[str] = set()
            count = 0
            for record in raw_records:
                item = dict(record)
                canonical_id = _source_value(item, "_cogan_canonical_post_id", "ID", "id", "Post ID")
                url = _source_value(item, "_cogan_url", "Link URL", "URL", "Url", "Source URL")
                dedupe_key = str(canonical_id or url or count)
                if dedupe_key in seen_within_campaign:
                    continue
                seen_within_campaign.add(dedupe_key)
                item["_cogan_campaign_scope"] = campaign_name
                item["_cogan_requested_campaign"] = campaign_name
                fetched.append(item)
                count += 1
            if count == 0:
                missing_campaigns.append(campaign_name)

        # Optional very defensive fallback for legacy/single-project installs.
        if not fetched:
            try:
                raw_records = db.fetch_raw_records(
                    request.project_name,
                    request.start_date,
                    request.end_date,
                    None,
                    keywords,
                    excludes,
                    match_mode,
                    channels,
                )
            except Exception as exc:
                raise ReportBuildError(f"Gagal menarik raw canonical records: {exc}") from exc
            if raw_records is None:
                raise ReportBuildError(f"Project '{request.project_name}' tidak ditemukan.")
            fetched = list(raw_records)

        return fetched

    def _brand_universe(self, request: BuildRequest, scope: Mapping[str, Any]) -> list[str]:
        raw = []
        if request.client_brand:
            raw.append(request.client_brand)
        else:
            raw.append(request.project_name)
        raw.extend(request.competitor_brands)
        for key in ("brands", "brand_universe", "competitors", "competitor_brands"):
            value = scope.get(key)
            if isinstance(value, str):
                raw.extend(part.strip() for part in value.split(",") if part.strip())
            elif isinstance(value, Iterable) and not isinstance(value, (bytes, str, Mapping)):
                raw.extend(str(item).strip() for item in value if str(item).strip())
        result: list[str] = []
        seen: set[str] = set()
        for item in raw:
            clean = _text(item)
            key = clean.casefold()
            if clean and key not in seen:
                result.append(clean)
                seen.add(key)
        return result

    def _normalize_record(self, record: Mapping[str, Any], brand_universe: list[str], request: BuildRequest) -> dict[str, Any]:
        title = _text(_source_value(record, "Title", "Headline", "Judul"))
        content = _text(_source_value(record, "Content", "Caption", "Text", "Article", "Body", "Isi"))
        campaign_scope = _text(_source_value(record, "_cogan_campaign_scope", "_cogan_requested_campaign"))
        campaign = _text(_source_value(
            record,
            "Campaigns",
            "Campaign",
            "Brand",
            "Tag",
            "Client",
            "Company",
            "Project",
            "_cogan_campaign",
        ))
        author = _text(_source_value(record, "Author", "Username", "Account", "Author Name", "Media Name", "Publisher"))
        channel = _text(_source_value(record, "Channel", "Source", "Platform", "Media Type", "_cogan_channel"))
        channel_norm = _channel_norm(channel)
        url = _text(_source_value(record, "Link URL", "URL", "Url", "Source URL", "_cogan_url"))
        canonical_id = _source_value(record, "_cogan_canonical_post_id", "ID", "id", "Post ID")

        brand = _brand_match(campaign_scope, brand_universe)
        if not brand:
            brand = _brand_match(campaign, brand_universe)
        if not brand:
            brand = _brand_match(" ".join([title, content, author]), brand_universe)
        if not brand and len(brand_universe) == 1:
            brand = brand_universe[0]

        likes = _num(_source_value(record, "Likes", "Like", "Like Count"))
        comments = _num(_source_value(record, "Comments", "Comment", "Comment Count", "Replies"))
        shares = _num(_source_value(record, "Shares", "Share", "Share Count"))
        retweets = _num(_source_value(record, "Retweets", "Retweet", "Reposts", "Repost"))
        replies = _num(_source_value(record, "Replies", "Reply"))
        raw_engagement = _num(_source_value(record, "Engagement", "Interactions", "Interaction", "Total Engagement"))
        views = _num(_source_value(record, "Views", "View", "Play Count"))
        interactions = self._canonical_interactions(channel_norm, likes, comments, shares, retweets, replies, raw_engagement)

        post_date = _safe(_source_value(record, "_cogan_post_date", "Date", "Published Date", "Created At"))
        raw_topic = _text(_source_value(record, "Topic Extraction", "Topic", "Issue", "Narrative"))
        raw_aspect = _text(_source_value(record, "Aspect Based Sentiment", "Aspect", "ABSA Aspect", "Aspect Sentiment"))
        raw_entity = _text(_source_value(record, "Entity Extraction", "Entity", "Entities", "Named Entity"))
        content_type = _text(_source_value(record, "Media Type", "Content Type", "Post Type", "Format")) or channel or "Unknown"
        sentiment = _sentiment(_source_value(record, "Sentiment"))

        canonical_key = None
        content_hash = None
        topic_text = None
        try:
            canonical_key = canonical_key_from_values(url=url, canonical_post_id=canonical_id)
            content_hash = canonical_content_hash(title, content)
            topic_text = topic_text_for_llm(title, content)
        except Exception:
            canonical_key = None
            content_hash = None
            topic_text = None

        return {
            "source_row_id": str(canonical_id) if canonical_id is not None else None,
            "brand": brand,
            "campaign": campaign_scope or brand or campaign or "(unmapped)",
            "campaign_raw": campaign,
            "campaign_scope": campaign_scope or None,
            "title": title,
            "content": content,
            "content_snippet": (content or title)[:900],
            "author": author or "(unknown)",
            "channel": channel or "(unknown)",
            "channel_norm": channel_norm,
            "content_type": content_type,
            "sentiment": sentiment,
            "topic": "Unclassified / Needs LLM",
            "topic_id": None,
            "topic_label": None,
            "primary_topic_id": None,
            "classification_status": "unclassified",
            "topic_confidence": None,
            "topic_reason": None,
            "topic_text": topic_text,
            "canonical_key": canonical_key,
            "content_hash": content_hash,
            "raw_topic_diagnostic": raw_topic or None,
            "raw_aspect_diagnostic": raw_aspect or None,
            "raw_entity_diagnostic": raw_entity or None,
            "aspect": None,
            "entity": None,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "retweets": retweets,
            "replies": replies,
            "raw_engagement": raw_engagement,
            "interactions": interactions,
            "views": views,
            "potential_reach": _num(_source_value(record, "Potential Reach", "Reach", "Audience")),
            "ad_value": _num(_source_value(record, "Ad Value", "AVE", "Advertising Value")),
            "pr_value": _num(_source_value(record, "PR Value", "Public Relations Value")),
            "buzz": comments,
            "verified_account": _text(_source_value(record, "Verified Account", "Verified", "Is Verified")) or None,
            "source_url": url or None,
            "date": str(post_date)[:10] if post_date else None,
        }

    def _canonical_interactions(
        self,
        channel_norm: str,
        likes: int | float,
        comments: int | float,
        shares: int | float,
        retweets: int | float,
        replies: int | float,
        raw_engagement: int | float,
    ) -> int | float:
        if channel_norm in {"instagram", "youtube"}:
            return likes + comments
        if channel_norm in {"facebook", "tiktok"}:
            return likes + comments + shares
        if channel_norm == "twitter":
            return likes + replies + retweets
        return raw_engagement or likes + comments + shares + replies + retweets

    # ------------------------------------------------------------------
    # LLM topic/narrative enrichment
    # ------------------------------------------------------------------

    def _resolve_competitive_taxonomy_version(self, request: BuildRequest) -> str | None:
        scope = dict(request.scope or {})
        for key in ("topic_taxonomy_version", "competitive_taxonomy_version", "ca_topic_taxonomy_version"):
            value = _text(scope.get(key))
            if value:
                return value
        try:
            taxonomies = list_taxonomies(request.project_name)
        except Exception:
            return None
        candidates = []
        for item in taxonomies or []:
            version = _text(item.get("taxonomy_version"))
            name = _text(item.get("taxonomy_name"))
            blob = f"{version} {name}".casefold()
            if "competitive" in blob or "competitor" in blob or "ca_topic" in blob:
                candidates.append(item)
        if not candidates:
            return None
        candidates.sort(key=lambda item: _text(item.get("updated_at") or item.get("created_at")), reverse=True)
        return _text(candidates[0].get("taxonomy_version")) or None

    def _topic_refs(self, rows: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
        refs = []
        seen: set[tuple[str, str]] = set()
        for row in rows:
            canonical_key = _text(row.get("canonical_key"))
            content_hash = _text(row.get("content_hash"))
            if not canonical_key or not content_hash:
                continue
            key = (canonical_key, content_hash)
            if key in seen:
                continue
            seen.add(key)
            refs.append({
                "canonical_key": canonical_key,
                "content_hash": content_hash,
                "canonical_post_id": row.get("source_row_id"),
            })
        return refs

    def _attach_llm_topic_assignments(
        self,
        report_input: dict[str, Any],
        rows: list[dict[str, Any]],
        request: BuildRequest,
    ) -> dict[str, Any]:
        taxonomy_version = self._resolve_competitive_taxonomy_version(request)
        eligible_refs = self._topic_refs(rows)
        if not taxonomy_version:
            add_limitation(
                report_input,
                "Competitive topic/narrative taxonomy belum tersedia; workflow harus menjalankan auto LLM taxonomy/classification sebelum final CA preview.",
            )
            return {
                "status": "NO_TAXONOMY",
                "taxonomy_version": None,
                "eligible_rows": len(eligible_refs),
                "processed_rows": 0,
                "classified_rows": 0,
                "coverage_pct": 0,
                "policy": "No raw Topic Extraction fallback for final CA topic views.",
            }

        try:
            assignments = get_assignment_index(
                project_name=request.project_name,
                taxonomy_version=taxonomy_version,
                post_refs=eligible_refs,
            )
        except Exception as exc:
            add_limitation(report_input, f"Gagal membaca cached LLM topic assignment: {exc}")
            assignments = {}

        processed = 0
        classified = 0
        not_relevant = 0
        review_needed = 0
        for row in rows:
            canonical_key = _text(row.get("canonical_key"))
            content_hash = _text(row.get("content_hash"))
            assignment = assignments.get((canonical_key, content_hash)) if canonical_key and content_hash else None
            if not assignment:
                continue
            status = _text(assignment.get("classification_status")).casefold()
            processed += 1
            row["classification_status"] = status
            row["primary_topic_id"] = assignment.get("primary_topic_id")
            row["topic_id"] = assignment.get("primary_topic_id")
            row["topic_label"] = assignment.get("primary_topic_label")
            row["topic"] = assignment.get("primary_topic_label") or row.get("topic")
            row["topic_confidence"] = assignment.get("confidence")
            row["topic_reason"] = assignment.get("classification_reason")
            row["taxonomy_version"] = taxonomy_version
            if status == "classified":
                classified += 1
            elif status == "not_relevant":
                not_relevant += 1
            elif status == "review_needed":
                review_needed += 1

        eligible = len(eligible_refs)
        coverage = round(processed * 100 / eligible, 1) if eligible else 0
        classified_coverage = round(classified * 100 / eligible, 1) if eligible else 0
        context = {
            "status": "READY" if classified else "NO_CLASSIFIED_TOPICS",
            "taxonomy_version": taxonomy_version,
            "eligible_rows": eligible,
            "processed_rows": processed,
            "classified_rows": classified,
            "not_relevant_rows": not_relevant,
            "review_needed_rows": review_needed,
            "coverage_pct": coverage,
            "classified_coverage_pct": classified_coverage,
            "policy": "Final CA topic/narrative metrics are aggregated from cached LLM assignments only.",
        }
        if eligible and processed < eligible:
            add_limitation(report_input, f"Competitive topic coverage {coverage}% ({processed}/{eligible}); topic/narrative views memakai cached LLM assignments yang tersedia.")
        evolution = extract_taxonomy_evolution_candidates(
            rows,
            taxonomy_version=taxonomy_version,
            assignment_field=None,
        )
        context["taxonomy_evolution"] = evolution
        if evolution.get("candidate_count"):
            add_limitation(
                report_input,
                "Ada emerging competitive topic candidate dari review_needed/Topik Baru; buat taxonomy version baru agar percakapan baru tidak terus masuk bucket Topik Baru.",
            )
        if not classified:
            add_limitation(report_input, "Belum ada row classified pada competitive taxonomy; topic/narrative views ditandai NOT_AVAILABLE, bukan memakai raw Topic Extraction.")
        report_input["scope"]["competitive_topic_enrichment"] = context
        report_input["scope"]["taxonomy_evolution"] = evolution
        return context

    def _classified_topic_rows(self, rows: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
        return [
            row for row in rows
            if _text(row.get("classification_status")).casefold() == "classified"
            and _text(row.get("topic_label") or row.get("topic"))
            and _text(row.get("primary_topic_id")) != "not_relevant"
        ]

    # ------------------------------------------------------------------
    # Readiness / health
    # ------------------------------------------------------------------

    def _metric_readiness(self, rows: list[Mapping[str, Any]], brand_universe: list[str]) -> dict[str, Any]:
        total = len(rows)
        warnings: list[str] = []
        brands_present = {row.get("brand") for row in rows if row.get("brand")}
        missing_brands = [brand for brand in brand_universe if brand not in brands_present]
        if missing_brands:
            warnings.append("Brand universe belum lengkap dalam data: " + ", ".join(missing_brands))
        if total and sum(1 for row in rows if row.get("source_url")) * 100 / total < 50:
            warnings.append("URL evidence coverage <50%; audit evidence mungkin terbatas.")
        if sum(1 for row in rows if _num(row.get("interactions"))) == 0:
            warnings.append("Interactions/Engagement 0 atau tidak tersedia; SOE dan efficiency perlu dibaca sebagai N/A/low confidence.")
        return {
            "status": "READY_WITH_WARNINGS" if warnings else "READY",
            "warnings": warnings,
            "blockers": [],
            "brand_universe": brand_universe,
            "brand_count": len(brand_universe),
            "record_count": total,
            "metric_contract": {
                "sov": "brand_content_count / total_content_count",
                "soe": "brand_interactions / total_interactions",
                "engagement_efficiency": "interactions / content_count",
                "views_are_separate": True,
                "raw_topic_extraction_policy": "diagnostic_only_not_final",
                "topic_narrative_policy": "cached LLM taxonomy from Title + Content",
            },
        }

    def _data_health(self, rows: list[Mapping[str, Any]], normalized: list[Mapping[str, Any]], brand_universe: list[str]) -> dict[str, Any]:
        dates = [str(row.get("date")) for row in rows if row.get("date")]
        channels = Counter(row.get("channel") or "(unknown)" for row in rows)
        brands = Counter(row.get("brand") or "(unmapped)" for row in normalized)
        return {
            "n_rows_raw": len(normalized),
            "n_rows_competitive_mapped": len(rows),
            "unmapped_rows_excluded": len(normalized) - len(rows),
            "date_range_actual": {"from": min(dates) if dates else None, "to": max(dates) if dates else None},
            "channels": [{"channel": key, "rows": count} for key, count in channels.most_common()],
            "brands": [{"brand": key, "rows": count} for key, count in brands.most_common()],
            "coverage_counts": {
                "with_source_url": sum(1 for row in rows if row.get("source_url")),
                "with_interactions": sum(1 for row in rows if _num(row.get("interactions"))),
                "with_views": sum(1 for row in rows if _num(row.get("views"))),
                "with_llm_topic_assignment": sum(1 for row in rows if row.get("classification_status") in {"classified", "not_relevant", "review_needed"}),
                "with_llm_classified_topic": sum(1 for row in rows if row.get("classification_status") == "classified"),
                "with_source_topic_diagnostic": sum(1 for row in rows if row.get("raw_topic_diagnostic")),
                "with_source_aspect_diagnostic": sum(1 for row in rows if row.get("raw_aspect_diagnostic")),
            },
            "source": "computed_from_builder_canonical_records",
            "brand_universe": brand_universe,
        }

    # ------------------------------------------------------------------
    # Quantitative views
    # ------------------------------------------------------------------

    def _brand_groups(self, rows: Iterable[Mapping[str, Any]], brand_universe: list[str]) -> dict[str, list[Mapping[str, Any]]]:
        grouped: dict[str, list[Mapping[str, Any]]] = {brand: [] for brand in brand_universe}
        for row in rows:
            brand = str(row.get("brand") or "")
            grouped.setdefault(brand, []).append(row)
        return grouped

    def _add_brand_volume_engagement(self, report_input: dict[str, Any], rows: list[Mapping[str, Any]], brand_universe: list[str]) -> None:
        total_content = len(rows)
        total_interactions = sum(_num(row.get("interactions")) for row in rows)
        grouped = self._brand_groups(rows, brand_universe)
        output = []
        for brand, items in grouped.items():
            content_count = len(items)
            interactions = sum(_num(row.get("interactions")) for row in items)
            output.append({
                "campaign": brand,
                "brand": brand,
                "count_content": content_count,
                "engagement": interactions,
                "interactions": interactions,
                "sov_pct": _pct(content_count, total_content),
                "soe_pct": _pct(interactions, total_interactions),
                "engagement_per_content": _safe_div(interactions, content_count),
            })
        output.sort(key=lambda row: (_num(row["engagement"]), _num(row["count_content"])), reverse=True)
        self.add_quantitative_view(report_input, view_id="qt_ca_brand_volume_engagement", rows=output)

    def _add_sentiment_by_brand(self, report_input: dict[str, Any], rows: list[Mapping[str, Any]], brand_universe: list[str]) -> None:
        output = []
        grouped = self._brand_groups(rows, brand_universe)
        for brand, items in grouped.items():
            total = len(items)
            for sentiment in SENTIMENTS:
                selected = [row for row in items if row.get("sentiment") == sentiment]
                output.append({
                    "campaign": brand,
                    "brand": brand,
                    "sentiment": sentiment,
                    "count_content": len(selected),
                    "share_pct": _pct(len(selected), total),
                    "engagement": sum(_num(row.get("interactions")) for row in selected),
                })
        self.add_quantitative_view(report_input, view_id="qt_ca_sentiment_by_brand", rows=output)

    def _add_issue_sentiment_by_brand(self, report_input: dict[str, Any], rows: list[Mapping[str, Any]], brand_universe: list[str]) -> None:
        classified_rows = self._classified_topic_rows(rows)
        if not classified_rows:
            self.mark_view_not_available(
                report_input,
                view_id="qt_ca_issue_sentiment_by_brand",
                view_type="quantitative",
                reason="Belum ada cached LLM competitive topic/narrative assignments yang classified. Workflow harus menjalankan auto-classification; raw Topic Extraction tidak dipakai sebagai fallback.",
                metadata={"topic_policy": "llm_required_no_raw_topic_fallback"},
            )
            return

        counter: dict[tuple[str, str, str], dict[str, Any]] = {}
        for row in classified_rows:
            topic = str(row.get("topic_label") or row.get("topic") or "Other")
            topic_id = str(row.get("primary_topic_id") or row.get("topic_id") or "")
            key = (topic, str(row.get("brand") or ""), str(row.get("sentiment") or "unclassified"))
            item = counter.setdefault(key, {
                "topic": topic,
                "topic_id": topic_id,
                "campaign": key[1],
                "brand": key[1],
                "sentiment": key[2],
                "count_content": 0,
                "engagement": 0,
                "taxonomy_version": row.get("taxonomy_version"),
            })
            item["count_content"] += 1
            item["engagement"] += _num(row.get("interactions"))
        output = sorted(counter.values(), key=lambda row: (_num(row["engagement"]), _num(row["count_content"])), reverse=True)[:80]
        topic_context = dict(report_input.get("scope", {}).get("competitive_topic_enrichment") or {})
        self.add_quantitative_view(report_input, view_id="qt_ca_issue_sentiment_by_brand", rows=output, metadata={"topic_policy": "cached_llm_competitive_topic_taxonomy", **topic_context})

    def _add_channel_mix_by_brand(self, report_input: dict[str, Any], rows: list[Mapping[str, Any]], brand_universe: list[str]) -> None:
        output = []
        grouped = self._brand_groups(rows, brand_universe)
        for brand, items in grouped.items():
            total = len(items)
            by_channel = defaultdict(list)
            for row in items:
                by_channel[str(row.get("channel") or "(unknown)")].append(row)
            for channel, selected in by_channel.items():
                interactions = sum(_num(row.get("interactions")) for row in selected)
                output.append({
                    "campaign": brand,
                    "brand": brand,
                    "channel": channel,
                    "count_content": len(selected),
                    "share_pct": _pct(len(selected), total),
                    "engagement": interactions,
                })
        output.sort(key=lambda row: (_num(row["engagement"]), _num(row["count_content"])), reverse=True)
        self.add_quantitative_view(report_input, view_id="qt_ca_channel_mix_by_brand", rows=output)

    def _add_content_type_by_brand(self, report_input: dict[str, Any], rows: list[Mapping[str, Any]], brand_universe: list[str]) -> None:
        output = []
        grouped = self._brand_groups(rows, brand_universe)
        for brand, items in grouped.items():
            by_type = defaultdict(list)
            for row in items:
                by_type[str(row.get("content_type") or "Unknown")].append(row)
            for content_type, selected in by_type.items():
                output.append({
                    "campaign": brand,
                    "brand": brand,
                    "media_type": content_type,
                    "content_type": content_type,
                    "count_content": len(selected),
                    "buzz": sum(_num(row.get("buzz")) for row in selected),
                    "engagement": sum(_num(row.get("interactions")) for row in selected),
                    "views": sum(_num(row.get("views")) for row in selected),
                })
        output.sort(key=lambda row: (_num(row["engagement"]), _num(row["count_content"])), reverse=True)
        self.add_quantitative_view(report_input, view_id="qt_ca_content_type_by_brand", rows=output)

    def _add_kpi_summary_by_brand(self, report_input: dict[str, Any], rows: list[Mapping[str, Any]], brand_universe: list[str]) -> None:
        grouped = self._brand_groups(rows, brand_universe)
        output = []
        for brand, items in grouped.items():
            sentiments = Counter(row.get("sentiment") for row in items)
            pos = sentiments.get("positive", 0)
            neg = sentiments.get("negative", 0)
            pos_pct = _pct(pos, len(items)) or 0
            neg_pct = _pct(neg, len(items)) or 0
            interactions = sum(_num(row.get("interactions")) for row in items)
            output.append({
                "campaign": brand,
                "brand": brand,
                "count_content": len(items),
                "sum_engagement": interactions,
                "sum_interactions": interactions,
                "sum_potential_reach": sum(_num(row.get("potential_reach")) for row in items),
                "sum_ad_value": sum(_num(row.get("ad_value")) for row in items),
                "sum_pr_value": sum(_num(row.get("pr_value")) for row in items),
                "sum_views": sum(_num(row.get("views")) for row in items),
                "dominant_sentiment": _dominant_sentiment(sentiments),
                "net_sentiment": round(pos_pct - neg_pct, 1),
                "engagement_per_content": _safe_div(interactions, len(items)),
            })
        output.sort(key=lambda row: (_num(row["sum_engagement"]), _num(row["count_content"])), reverse=True)
        self.add_quantitative_view(report_input, view_id="qt_ca_kpi_summary_by_brand", rows=output)

    def _add_sentiment_channel_by_brand(self, report_input: dict[str, Any], rows: list[Mapping[str, Any]], brand_universe: list[str]) -> None:
        grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
        for row in rows:
            key = (str(row.get("brand") or ""), str(row.get("channel") or "(unknown)"), str(row.get("sentiment") or "unclassified"))
            item = grouped.setdefault(key, {"campaign": key[0], "brand": key[0], "channel": key[1], "sentiment": key[2], "count_content": 0, "engagement": 0})
            item["count_content"] += 1
            item["engagement"] += _num(row.get("interactions"))
        output = sorted(grouped.values(), key=lambda row: (_num(row["engagement"]), _num(row["count_content"])), reverse=True)
        self.add_quantitative_view(report_input, view_id="qt_ca_sentiment_channel_by_brand", rows=output)

    def _add_brand_status(self, report_input: dict[str, Any], rows: list[Mapping[str, Any]], request: BuildRequest, brand_universe: list[str]) -> None:
        client = request.client_brand or (brand_universe[0] if brand_universe else request.project_name)
        output = []
        for brand in brand_universe:
            if brand.casefold() == str(client or "").casefold():
                tag = "client"
            elif brand in request.competitor_brands:
                tag = "competitor"
            else:
                tag = "benchmark"
            output.append({"campaign": brand, "brand": brand, "tag": tag, "has_data": any(row.get("brand") == brand for row in rows)})
        self.add_quantitative_view(report_input, view_id="qt_ca_brand_status", rows=output)

    # ------------------------------------------------------------------
    # Qualitative views
    # ------------------------------------------------------------------

    def _rank_rows(self, rows: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
        return sorted(rows, key=lambda row: (_num(row.get("interactions")), _num(row.get("views"))), reverse=True)

    def _evidence_row(self, row: Mapping[str, Any], evidence_id: str, *, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
        base = {
            "evidence_id": evidence_id,
            "campaign": row.get("brand"),
            "brand": row.get("brand"),
            "channel": row.get("channel"),
            "author": row.get("author"),
            "title": row.get("title"),
            "content": row.get("content_snippet") or row.get("content") or row.get("title"),
            "sentiment": row.get("sentiment"),
            "engagement": _num(row.get("interactions")),
            "interactions": _num(row.get("interactions")),
            "views": _num(row.get("views")),
            "source_url": row.get("source_url"),
            "source_row_id": row.get("source_row_id"),
            "date": row.get("date"),
        }
        if extra:
            base.update(dict(extra))
        return base

    def _add_aspect_sentiment_by_brand(self, report_input: dict[str, Any], rows: list[Mapping[str, Any]], brand_universe: list[str]) -> None:
        grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
        representative: dict[tuple[str, str, str], Mapping[str, Any]] = {}
        for row in rows:
            aspect = str(row.get("aspect") or "General / Unspecified")
            key = (str(row.get("brand") or ""), aspect, str(row.get("sentiment") or "unclassified"))
            item = grouped.setdefault(key, {"campaign": key[0], "brand": key[0], "aspect_based_sentiment": aspect, "aspect": aspect, "sentiment": key[2], "count_content": 0, "engagement": 0})
            item["count_content"] += 1
            item["engagement"] += _num(row.get("interactions"))
            if key not in representative or _num(row.get("interactions")) > _num(representative[key].get("interactions")):
                representative[key] = row
        output = []
        per_brand_counter: Counter[str] = Counter()
        for key, item in sorted(grouped.items(), key=lambda kv: (_num(kv[1]["engagement"]), _num(kv[1]["count_content"])), reverse=True):
            brand = key[0]
            if per_brand_counter[brand] >= 5:
                continue
            per_brand_counter[brand] += 1
            rep = representative.get(key) or {}
            row_out = dict(item)
            row_out.update({"evidence_id": f"CA{len(output)+1:02d}", "source_url": rep.get("source_url"), "content": rep.get("content_snippet") or rep.get("title"), "source_row_id": rep.get("source_row_id")})
            output.append(row_out)
        self.add_qualitative_view(report_input, view_id="ql_ca_aspect_sentiment_by_brand", rows=output, metadata={"aspect_policy": "source aspect if available; falls back to topic/general signal"}, evidence_reason="competitive aspect sentiment evidence")

    def _add_competitive_entities(self, report_input: dict[str, Any], rows: list[Mapping[str, Any]], brand_universe: list[str]) -> None:
        counter: dict[tuple[str, str], dict[str, Any]] = {}
        rep: dict[tuple[str, str], Mapping[str, Any]] = {}
        for row in rows:
            terms = _split_terms(row.get("entity")) or []
            for entity in terms:
                key = (str(row.get("brand") or ""), entity)
                item = counter.setdefault(key, {"campaign": key[0], "brand": key[0], "entity": entity, "count_content": 0, "engagement": 0})
                item["count_content"] += 1
                item["engagement"] += _num(row.get("interactions"))
                if key not in rep or _num(row.get("interactions")) > _num(rep[key].get("interactions")):
                    rep[key] = row
        if not counter:
            # Keep the view explicit and useful: entity extraction is optional in many exports.
            self.mark_view_not_available(report_input, view_id="ql_ca_competitive_entities", view_type="qualitative", reason="Entity Extraction tidak tersedia pada scope ini.")
            return
        output = []
        per_brand: Counter[str] = Counter()
        for key, item in sorted(counter.items(), key=lambda kv: (_num(kv[1]["engagement"]), _num(kv[1]["count_content"])), reverse=True):
            brand = key[0]
            if per_brand[brand] >= 5:
                continue
            per_brand[brand] += 1
            row = rep.get(key) or {}
            row_out = dict(item)
            row_out.update({"evidence_id": f"CE{len(output)+1:02d}", "source_url": row.get("source_url"), "content": row.get("content_snippet") or row.get("title"), "source_row_id": row.get("source_row_id")})
            output.append(row_out)
        self.add_qualitative_view(report_input, view_id="ql_ca_competitive_entities", rows=output, evidence_reason="competitive entity evidence")

    def _add_positive_negative_highlights(self, report_input: dict[str, Any], rows: list[Mapping[str, Any]], brand_universe: list[str]) -> None:
        output = []
        counter = 1
        for brand in brand_universe:
            brand_rows = [row for row in rows if row.get("brand") == brand]
            for sentiment in ("positive", "negative"):
                selected = [row for row in self._rank_rows(brand_rows) if row.get("sentiment") == sentiment][:3]
                for row in selected:
                    output.append(self._evidence_row(row, f"E{counter:02d}", extra={"highlight_type": sentiment}))
                    counter += 1
        self.add_qualitative_view(report_input, view_id="ql_ca_positive_negative_highlights", rows=output, evidence_reason="competitive positive/negative highlight")

    def _add_top_authors_by_brand(self, report_input: dict[str, Any], rows: list[Mapping[str, Any]], brand_universe: list[str]) -> None:
        output = []
        for brand in brand_universe:
            brand_rows = [row for row in rows if row.get("brand") == brand]
            grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
            for row in brand_rows:
                grouped[str(row.get("author") or "(unknown)")].append(row)
            ranked = sorted(grouped.items(), key=lambda kv: sum(_num(row.get("interactions")) for row in kv[1]), reverse=True)[:5]
            for idx, (author, selected) in enumerate(ranked, start=1):
                top = self._rank_rows(selected)[0]
                output.append({
                    "evidence_id": f"A{len(output)+1:02d}",
                    "campaign": brand,
                    "brand": brand,
                    "author": author,
                    "channel": top.get("channel"),
                    "verified_account": top.get("verified_account"),
                    "sentiment": _dominant_sentiment(Counter(row.get("sentiment") for row in selected)),
                    "count_content": len(selected),
                    "engagement": sum(_num(row.get("interactions")) for row in selected),
                    "content": top.get("content_snippet") or top.get("title"),
                    "source_url": top.get("source_url"),
                    "source_row_id": top.get("source_row_id"),
                    "rank": idx,
                })
        self.add_qualitative_view(report_input, view_id="ql_ca_top_authors_by_brand", rows=output, evidence_reason="competitive top author evidence")

    def _add_top_social_posts_by_brand(self, report_input: dict[str, Any], rows: list[Mapping[str, Any]], brand_universe: list[str]) -> None:
        output = []
        counter = 1
        for brand in brand_universe:
            brand_rows = [row for row in self._rank_rows(rows) if row.get("brand") == brand and row.get("channel_norm") in SOCIAL_CHANNELS][:5]
            if not brand_rows:
                brand_rows = [row for row in self._rank_rows(rows) if row.get("brand") == brand][:5]
            for row in brand_rows:
                output.append(self._evidence_row(row, f"P{counter:02d}", extra={"topic": row.get("topic_label") or row.get("topic"), "topic_id": row.get("primary_topic_id"), "content_type": row.get("content_type")}))
                counter += 1
        self.add_qualitative_view(report_input, view_id="ql_ca_top_social_posts_by_brand", rows=output, evidence_reason="competitive top post evidence")

    def _add_topic_sentiment_by_brand(self, report_input: dict[str, Any], rows: list[Mapping[str, Any]], brand_universe: list[str]) -> None:
        classified_rows = self._classified_topic_rows(rows)
        if not classified_rows:
            self.mark_view_not_available(
                report_input,
                view_id="ql_ca_topic_sentiment_by_brand",
                view_type="qualitative",
                reason="Belum ada cached LLM competitive topic/narrative assignments yang classified. Workflow harus menjalankan auto-classification; raw Topic Extraction tidak dipakai sebagai fallback.",
                metadata={"topic_policy": "llm_required_no_raw_topic_fallback"},
            )
            return

        grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
        rep: dict[tuple[str, str, str], Mapping[str, Any]] = {}
        for row in classified_rows:
            topic = str(row.get("topic_label") or row.get("topic") or "Other")
            topic_id = str(row.get("primary_topic_id") or row.get("topic_id") or "")
            key = (str(row.get("brand") or ""), topic, str(row.get("sentiment") or "unclassified"))
            item = grouped.setdefault(key, {
                "campaign": key[0],
                "brand": key[0],
                "topic": topic,
                "topic_id": topic_id,
                "competitive_narrative": topic,
                "sentiment": key[2],
                "count_content": 0,
                "engagement": 0,
                "taxonomy_version": row.get("taxonomy_version"),
            })
            item["count_content"] += 1
            item["engagement"] += _num(row.get("interactions"))
            if key not in rep or _num(row.get("interactions")) > _num(rep[key].get("interactions")):
                rep[key] = row
        output = []
        per_brand: Counter[str] = Counter()
        for key, item in sorted(grouped.items(), key=lambda kv: (_num(kv[1]["engagement"]), _num(kv[1]["count_content"])), reverse=True):
            brand = key[0]
            if per_brand[brand] >= 10:
                continue
            per_brand[brand] += 1
            row = rep.get(key) or {}
            row_out = dict(item)
            row_out.update({
                "evidence_id": f"T{len(output)+1:02d}",
                "channel": row.get("channel"),
                "author": row.get("author"),
                "content": row.get("content_snippet") or row.get("title"),
                "source_url": row.get("source_url"),
                "source_row_id": row.get("source_row_id"),
                "classification_reason": row.get("topic_reason"),
                "confidence": row.get("topic_confidence"),
            })
            output.append(row_out)
        topic_context = dict(report_input.get("scope", {}).get("competitive_topic_enrichment") or {})
        self.add_qualitative_view(
            report_input,
            view_id="ql_ca_topic_sentiment_by_brand",
            rows=output,
            metadata={"topic_policy": "cached_llm_competitive_topic_taxonomy", **topic_context},
            evidence_reason="competitive LLM topic/narrative sentiment evidence",
        )


BUILDER_CLASS = CompetitiveAnalysisBuilder


__all__ = ["CompetitiveAnalysisBuilder", "BUILDER_CLASS"]
