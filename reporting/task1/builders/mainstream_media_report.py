"""Task 1 builder for Mainstream Media Report.

This builder creates registry-approved report_input_v1 data views for
`mainstream_media_report`.

Design principles:
- Mainstream scope is Online Media + Printmedia for MVP.
- Raw `Topic Extraction` is retained only as diagnostic metadata, not as the
  final report issue/topic source of truth.
- Report issues are read from cached LLM taxonomy assignments created from
  Title + Content/Article body. The builder never calls an LLM.
- KPI, sentiment, media contributors, and article evidence use the full
  canonical source set.
- Issue-based views are READY only when an explicit issue taxonomy version has
  cached classified articles for the same canonical article/content hash.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from database import db

from reporting.contracts.report_input_contract_v1 import add_limitation
from reporting.enrichment.topic_contract import (
    canonical_content_hash,
    canonical_key_from_values,
    normalize_text,
)
from reporting.enrichment.topic_store import (
    TopicStoreError,
    get_assignment_index,
    get_taxonomy,
)
from reporting.task1.base_builder import (
    BaseReportInputBuilder,
    BuildRequest,
    ReportBuildError,
)


MAINSTREAM_CHANNELS = frozenset({"online_media", "printmedia", "print_media"})
SENTIMENTS = ("positive", "neutral", "negative")
RISK_TERMS = (
    "kecelakaan",
    "korupsi",
    "dugaan",
    "tuntutan",
    "klarifikasi",
    "boikot",
    "krisis",
    "meninggal",
    "tewas",
    "gugatan",
    "kasus",
    "skandal",
    "investigasi",
)


def _safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        value = float(value)
        return int(value) if value.is_integer() else round(value, 4)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


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
    text = text.replace("Rp", "").replace("IDR", "")
    text = text.replace(".", "").replace(",", ".")
    try:
        number = float(text)
    except ValueError:
        return 0
    return int(number) if number.is_integer() else number


def _pct(part: int | float, base: int | float) -> float | None:
    return round(float(part) * 100 / float(base), 1) if base else None


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _norm_key(value: str) -> str:
    return "".join(ch for ch in value.casefold() if ch.isalnum())


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


def _channel_norm(channel: Any) -> str:
    value = _text(channel).casefold()
    aliases = {
        "online": "online_media",
        "online media": "online_media",
        "media online": "online_media",
        "news": "online_media",
        "portal berita": "online_media",
        "print": "printmedia",
        "print media": "printmedia",
        "printmedia": "printmedia",
        "printed media": "printmedia",
        "newspaper": "printmedia",
        "koran": "printmedia",
        "majalah": "printmedia",
    }
    return aliases.get(value, value.replace(" ", "_") or "unknown")


def _sentiment(value: Any) -> str:
    clean = _text(value).casefold()
    if clean in {"positive", "positif", "pos"}:
        return "positive"
    if clean in {"negative", "negatif", "neg"}:
        return "negative"
    if clean in {"neutral", "netral", "neu"}:
        return "neutral"
    return "unclassified"


def _snippet(article: Mapping[str, Any], limit: int = 850) -> str:
    source = _text(article.get("content")) or _text(article.get("title"))
    return source[:limit]


def _rank_articles(articles: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (dict(article) for article in articles),
        key=lambda row: (
            _num(row.get("pr_value")),
            _num(row.get("ad_value")),
            _num(row.get("readership")),
            1 if row.get("sentiment") == "negative" else 0,
            str(row.get("date") or ""),
        ),
        reverse=True,
    )


def _dominant_sentiment(counts: Mapping[str, int]) -> str | None:
    known = {key: int(counts.get(key) or 0) for key in SENTIMENTS}
    if not sum(known.values()):
        return None
    return max(SENTIMENTS, key=lambda item: (known[item], item == "neutral"))


def _risk_posture(sentiment_counts: Mapping[str, int], total: int) -> dict[str, Any]:
    pos = int(sentiment_counts.get("positive") or 0)
    neg = int(sentiment_counts.get("negative") or 0)
    pos_pct = _pct(pos, total) or 0
    neg_pct = _pct(neg, total) or 0
    net = round(pos_pct - neg_pct, 1)
    if neg_pct >= 40 or net <= -20:
        level = "RED / HIGH RISK"
    elif neg_pct >= 25 or net < 0:
        level = "AMBER / WATCH"
    else:
        level = "GREEN / STABLE"
    return {
        "posture": level,
        "net_sentiment": net,
        "positive_share_pct": pos_pct,
        "negative_share_pct": neg_pct,
    }


def _article_id(article: Mapping[str, Any]) -> str:
    return str(article.get("canonical_post_id") or article.get("canonical_key") or "")


class MainstreamMediaReportBuilder(BaseReportInputBuilder):
    report_type_id = "mainstream_media_report"
    builder_version = "1.0.0"

    def build_views(
        self,
        report_input: dict[str, Any],
        request: BuildRequest,
    ) -> None:
        scope = dict(request.scope or {})
        articles, enrichment = self._fetch_mainstream_articles(request, scope)
        if not articles:
            raise ReportBuildError(
                "Tidak ada canonical mainstream article pada scope Mainstream Media."
            )

        taxonomy_version = enrichment.get("taxonomy_version")
        report_input["scope"]["channel_policy"] = (
            "mainstream_only; Online Media + Printmedia for MVP"
        )
        report_input["scope"]["raw_topic_extraction_policy"] = (
            "not_used_as_final_report_issue"
        )
        report_input["scope"]["issue_taxonomy_version"] = taxonomy_version
        report_input["scope"]["issue_enrichment_policy"] = (
            "Title + Content -> cached LLM issue assignment; builder is read-only"
        )

        report_input["metric_readiness"] = self._metric_readiness(articles, enrichment)
        report_input["data_health"] = self._data_health(articles, enrichment)
        for item in report_input["metric_readiness"].get("warnings", []):
            add_limitation(report_input, item)

        self._add_kpi_tiles(report_input, articles, enrichment)
        self._add_channel_distribution(report_input, articles)
        self._add_sentiment_distribution(report_input, articles)
        self._add_sentiment_matrix_by_channel(report_input, articles)
        self._add_media_contributors(report_input, articles)
        self._add_spokesperson_overview(report_input, articles)
        self._add_article_enriched(report_input, articles, enrichment)
        self._add_headlines_summary(report_input, articles, enrichment)

        issue_context = self._issue_context(articles, enrichment)
        if not issue_context["taxonomy_available"]:
            self._mark_issue_views_not_available(
                report_input,
                "Issue taxonomy LLM belum tersedia untuk project/scope ini.",
            )
            return
        if not issue_context["classified_articles"]:
            self._mark_issue_views_not_available(
                report_input,
                "Belum ada cached LLM issue status=classified pada scope ini.",
            )
            return
        if (issue_context["coverage_pct"] or 0) < 100:
            add_limitation(
                report_input,
                "Issue coverage belum 100%; issue ranking memakai artikel yang "
                "sudah selesai diklasifikasikan LLM.",
            )

        self._add_main_topics_top3(report_input, issue_context)
        self._add_top_issues_cards(report_input, issue_context)
        self._add_sentiment_issue_cards(report_input, issue_context)

    def _fetch_mainstream_articles(
        self,
        request: BuildRequest,
        scope: Mapping[str, Any],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        keywords = scope.get("keywords") or None
        excludes = scope.get("exclude_keywords") or None
        match_mode = scope.get("match_mode") or "any"
        channels = request.channels or scope.get("channels") or None

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

        articles = [self._normalize_article(record) for record in raw_records]
        articles = [
            article for article in articles if article["channel_norm"] in MAINSTREAM_CHANNELS
        ]

        taxonomy_version = (
            _text(scope.get("issue_taxonomy_version"))
            or _text(scope.get("mmr_issue_taxonomy_version"))
            or _text(scope.get("topic_taxonomy_version"))
            or None
        )
        taxonomy = None
        assignment_index: dict[tuple[str, str], Mapping[str, Any]] = {}
        if taxonomy_version:
            try:
                taxonomy = get_taxonomy(
                    project_name=request.project_name,
                    taxonomy_version=taxonomy_version,
                )
            except TopicStoreError as exc:
                raise ReportBuildError(str(exc)) from exc
            if taxonomy:
                refs = [
                    {
                        "canonical_post_id": article.get("canonical_post_id"),
                        "canonical_key": article["canonical_key"],
                        "content_hash": article["content_hash"],
                    }
                    for article in articles
                    if article["issue_eligible"]
                ]
                try:
                    assignment_index = get_assignment_index(
                        project_name=request.project_name,
                        taxonomy_version=taxonomy["taxonomy_version"],
                        post_refs=refs,
                    )
                except TopicStoreError as exc:
                    raise ReportBuildError(str(exc)) from exc

        counts = Counter()
        for article in articles:
            assignment = assignment_index.get(
                (article["canonical_key"], article["content_hash"])
            )
            article["issue_assignment"] = dict(assignment) if assignment else None
            if not article["issue_eligible"]:
                counts["ineligible"] += 1
            elif assignment is None:
                counts["unclassified"] += 1
            else:
                counts[str(assignment.get("classification_status"))] += 1

        eligible = sum(1 for article in articles if article["issue_eligible"])
        completed = counts["classified"] + counts["not_relevant"]
        enrichment = {
            "taxonomy_available": bool(taxonomy),
            "taxonomy_version": taxonomy.get("taxonomy_version") if taxonomy else None,
            "taxonomy_name": taxonomy.get("taxonomy_name") if taxonomy else None,
            "issue_status": {
                "issue_eligible_articles": eligible,
                "issue_ineligible_articles": counts["ineligible"],
                "classified": counts["classified"],
                "not_relevant": counts["not_relevant"],
                "review_needed": counts["review_needed"],
                "unclassified": counts["unclassified"],
                "completion_coverage_pct": _pct(completed, eligible),
                "report_issue_coverage_pct": _pct(counts["classified"], eligible),
            },
        }
        return articles, enrichment

    def _normalize_article(self, record: Mapping[str, Any]) -> dict[str, Any]:
        canonical_id = _source_value(record, "_cogan_canonical_post_id", "ID", "id")
        url = _source_value(record, "_cogan_url", "Link URL", "URL", "Url", "Source URL")
        title = _text(_source_value(record, "Title", "Headline", "Judul"))
        content = _text(_source_value(record, "Content", "Article", "Body", "Text", "Isi"))
        channel = _text(_source_value(record, "Channel", "Media Type", "_cogan_channel"))
        media_name = _text(
            _source_value(
                record,
                "Media Name",
                "Media",
                "Publisher",
                "Source",
                "Source Name",
                "Nama Media",
            )
        )
        channel_norm = _channel_norm(channel)
        ad_value = _num(_source_value(record, "Ad Value", "AVE", "Advertising Value"))
        pr_value = _num(_source_value(record, "PR Value", "Public Relations Value"))
        readership = _num(_source_value(record, "Readership", "Audience", "Reach"))
        circulation = _num(_source_value(record, "Circulation", "Sirkulasi"))
        sentiment = _sentiment(_source_value(record, "Sentiment"))
        post_date = _safe(_source_value(record, "_cogan_post_date", "Date", "Published Date"))
        canonical_key = canonical_key_from_values(url=url, canonical_post_id=canonical_id)
        return {
            "canonical_post_id": int(canonical_id) if str(canonical_id or "").isdigit() else None,
            "canonical_key": canonical_key,
            "content_hash": canonical_content_hash(title, content),
            "source_row_id": canonical_id,
            "date": str(post_date)[:10] if post_date else None,
            "channel": channel or "(tidak diketahui)",
            "channel_norm": channel_norm,
            "media_type": channel or None,
            "media_name": media_name or "(media tidak diketahui)",
            "title": title,
            "content": content,
            "content_snippet": (content or title)[:850],
            "sentiment": sentiment,
            "ad_value": ad_value,
            "pr_value": pr_value,
            "readership": readership,
            "circulation": circulation,
            "spokesperson": _text(_source_value(record, "Spokesperson", "Narasumber")) or None,
            "raw_topic_extraction": _text(_source_value(record, "Topic Extraction")) or None,
            "entity_extraction": _text(_source_value(record, "Entity Extraction")) or None,
            "noun": _text(_source_value(record, "Noun")) or None,
            "sentence_type": _text(_source_value(record, "Sentence Type Classification", "Sentence Type")) or None,
            "mood": _text(_source_value(record, "Mood")) or None,
            "aspect": _text(_source_value(record, "Aspect")) or None,
            "source_url": _text(url) or None,
            "issue_eligible": bool(title or content),
        }

    def _metric_readiness(
        self,
        articles: list[Mapping[str, Any]],
        enrichment: Mapping[str, Any],
    ) -> dict[str, Any]:
        total = len(articles)
        warnings: list[str] = []

        def coverage(field: str) -> float | None:
            return _pct(sum(1 for article in articles if article.get(field)), total)

        for field, label, threshold in (
            ("media_name", "Media Name", 80),
            ("source_url", "Article URL", 60),
            ("sentiment", "Sentiment", 80),
        ):
            pct = coverage(field)
            if pct is not None and pct < threshold:
                warnings.append(f"{label}: coverage {pct}% (<{threshold}%).")

        if sum(1 for article in articles if _num(article.get("ad_value"))) == 0:
            warnings.append("Ad Value tidak tersedia/terisi 0 pada scope ini.")
        if sum(1 for article in articles if _num(article.get("pr_value"))) == 0:
            warnings.append("PR Value tidak tersedia/terisi 0 pada scope ini.")

        issue_status = dict(enrichment.get("issue_status") or {})
        if not enrichment.get("taxonomy_available"):
            warnings.append(
                "Issue taxonomy belum tersedia; issue-based views akan N/A sampai enrichment dijalankan."
            )
        elif (issue_status.get("report_issue_coverage_pct") or 0) < 100:
            warnings.append(
                "Issue coverage belum 100%; issue-based views adalah early signal."
            )

        return {
            "status": "READY_WITH_WARNINGS" if warnings else "READY",
            "warnings": warnings,
            "blockers": [],
            "mainstream_article_count": total,
            "issue_status": issue_status,
            "metric_contract": {
                "primary_volume_metric": "article_count",
                "value_metrics": ["ad_value", "pr_value", "readership", "circulation"],
                "raw_topic_extraction_policy": "not_used_as_final_report_issue",
            },
        }

    def _data_health(
        self,
        articles: list[Mapping[str, Any]],
        enrichment: Mapping[str, Any],
    ) -> dict[str, Any]:
        channels = Counter(article.get("channel") or "(unknown)" for article in articles)
        dates = [str(article.get("date")) for article in articles if article.get("date")]
        return {
            "n_articles_unique": len(articles),
            "n_rows_raw": len(articles),
            "duplicate_rows_removed": 0,
            "date_range_actual": {
                "from": min(dates) if dates else None,
                "to": max(dates) if dates else None,
            },
            "channels": [
                {"channel": channel, "articles": count}
                for channel, count in channels.most_common()
            ],
            "coverage_counts": {
                "with_media_name": sum(1 for article in articles if article.get("media_name")),
                "with_source_url": sum(1 for article in articles if article.get("source_url")),
                "with_ad_value": sum(1 for article in articles if _num(article.get("ad_value"))),
                "with_pr_value": sum(1 for article in articles if _num(article.get("pr_value"))),
                "with_spokesperson": sum(1 for article in articles if article.get("spokesperson")),
            },
            "issue_status": dict(enrichment.get("issue_status") or {}),
            "source": "computed_from_builder_canonical_mainstream_articles",
        }

    def _add_kpi_tiles(
        self,
        report_input: dict[str, Any],
        articles: list[Mapping[str, Any]],
        enrichment: Mapping[str, Any],
    ) -> None:
        sentiments = Counter(article["sentiment"] for article in articles)
        posture = _risk_posture(sentiments, len(articles))
        row = {
            "total_news": len(articles),
            "total_articles": len(articles),
            "total_media": len({article["media_name"] for article in articles if article.get("media_name")}),
            "total_ad_value": sum(_num(article.get("ad_value")) for article in articles),
            "total_pr_value": sum(_num(article.get("pr_value")) for article in articles),
            "total_readership": sum(_num(article.get("readership")) for article in articles),
            "total_circulation": sum(_num(article.get("circulation")) for article in articles),
            "dominant_sentiment": _dominant_sentiment(sentiments),
            "media_posture": posture["posture"],
            "net_sentiment": posture["net_sentiment"],
            "issue_taxonomy_version": enrichment.get("taxonomy_version"),
            "issue_coverage_pct": (enrichment.get("issue_status") or {}).get("report_issue_coverage_pct"),
        }
        self.add_quantitative_view(
            report_input,
            view_id="qt_mm_kpi_tiles",
            rows=[row],
            metadata={"description": "Mainstream KPI tiles for report period."},
        )

    def _add_channel_distribution(self, report_input: dict[str, Any], articles: list[Mapping[str, Any]]) -> None:
        total = len(articles)
        rows = []
        grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for article in articles:
            grouped[article["channel"]].append(article)
        for channel, items in sorted(grouped.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            rows.append(
                {
                    "channel": channel,
                    "article_count": len(items),
                    "share_pct": _pct(len(items), total),
                    "ad_value": sum(_num(item.get("ad_value")) for item in items),
                    "pr_value": sum(_num(item.get("pr_value")) for item in items),
                }
            )
        self.add_quantitative_view(report_input, view_id="qt_mm_channel_distribution", rows=rows)

    def _add_sentiment_distribution(self, report_input: dict[str, Any], articles: list[Mapping[str, Any]]) -> None:
        total = len(articles)
        counts = Counter(article["sentiment"] for article in articles)
        rows = [
            {
                "sentiment": sentiment,
                "article_count": counts.get(sentiment, 0),
                "share_pct": _pct(counts.get(sentiment, 0), total),
                "ad_value": sum(_num(article.get("ad_value")) for article in articles if article["sentiment"] == sentiment),
                "pr_value": sum(_num(article.get("pr_value")) for article in articles if article["sentiment"] == sentiment),
            }
            for sentiment in SENTIMENTS
        ]
        unknown = counts.get("unclassified", 0)
        if unknown:
            rows.append({"sentiment": "unclassified", "article_count": unknown, "share_pct": _pct(unknown, total)})
        self.add_quantitative_view(report_input, view_id="qt_mm_sentiment_distribution", rows=rows)

    def _add_sentiment_matrix_by_channel(self, report_input: dict[str, Any], articles: list[Mapping[str, Any]]) -> None:
        grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for article in articles:
            grouped[article["channel"]].append(article)
        rows = []
        for channel, items in sorted(grouped.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            counts = Counter(item["sentiment"] for item in items)
            row = {
                "channel": channel,
                "article_count": len(items),
                "positive_count": counts.get("positive", 0),
                "neutral_count": counts.get("neutral", 0),
                "negative_count": counts.get("negative", 0),
                "positive_pct": _pct(counts.get("positive", 0), len(items)),
                "neutral_pct": _pct(counts.get("neutral", 0), len(items)),
                "negative_pct": _pct(counts.get("negative", 0), len(items)),
                "ad_value": sum(_num(item.get("ad_value")) for item in items),
                "pr_value": sum(_num(item.get("pr_value")) for item in items),
            }
            rows.append(row)
        self.add_quantitative_view(report_input, view_id="qt_mm_sentiment_matrix_by_channel", rows=rows)

    def _issue_context(self, articles: list[Mapping[str, Any]], enrichment: Mapping[str, Any]) -> dict[str, Any]:
        taxonomy_available = bool(enrichment.get("taxonomy_available"))
        classified = [
            article
            for article in articles
            if (article.get("issue_assignment") or {}).get("classification_status") == "classified"
        ]
        return {
            "taxonomy_available": taxonomy_available,
            "taxonomy_version": enrichment.get("taxonomy_version"),
            "coverage_pct": (enrichment.get("issue_status") or {}).get("report_issue_coverage_pct"),
            "classified_articles": classified,
            "groups": self._group_by_issue(classified),
        }

    def _group_by_issue(self, classified_articles: list[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
        groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for article in classified_articles:
            assignment = article.get("issue_assignment") or {}
            label = _text(assignment.get("primary_topic_label")) or _text(assignment.get("primary_topic_id")) or "Unlabeled Issue"
            groups[label].append(article)
        return groups

    def _representative_article(self, items: list[Mapping[str, Any]]) -> Mapping[str, Any]:
        return _rank_articles(items)[0]

    def _add_main_topics_top3(self, report_input: dict[str, Any], context: Mapping[str, Any]) -> None:
        total_articles = sum(len(items) for items in context["groups"].values())
        rows = []
        ranked_groups = sorted(
            context["groups"].items(),
            key=lambda kv: (len(kv[1]), sum(_num(item.get("pr_value")) for item in kv[1])),
            reverse=True,
        )[:3]
        for rank, (issue_label, items) in enumerate(ranked_groups, start=1):
            rep = self._representative_article(items)
            sentiments = Counter(item["sentiment"] for item in items)
            rows.append(
                {
                    "rank": rank,
                    "topic": issue_label,
                    "issue_label": issue_label,
                    "article_count": len(items),
                    "share_pct": _pct(len(items), total_articles),
                    "ad_value": sum(_num(item.get("ad_value")) for item in items),
                    "pr_value": sum(_num(item.get("pr_value")) for item in items),
                    "positive_count": sentiments.get("positive", 0),
                    "neutral_count": sentiments.get("neutral", 0),
                    "negative_count": sentiments.get("negative", 0),
                    "dominant_sentiment": _dominant_sentiment(sentiments),
                    "top_article_title": rep.get("title"),
                    "top_article_media": rep.get("media_name"),
                    "top_article_url": rep.get("source_url"),
                }
            )
        self.add_quantitative_view(
            report_input,
            view_id="qt_mm_main_topics_top3",
            rows=rows,
            metadata={
                "issue_taxonomy_version": context.get("taxonomy_version"),
                "issue_coverage_pct": context.get("coverage_pct"),
            },
        )

    def _add_media_contributors(self, report_input: dict[str, Any], articles: list[Mapping[str, Any]]) -> None:
        grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for article in articles:
            grouped[article["media_name"]].append(article)
        rows = []
        for rank, (media, items) in enumerate(
            sorted(
                grouped.items(),
                key=lambda kv: (len(kv[1]), sum(_num(item.get("pr_value")) for item in kv[1])),
                reverse=True,
            )[:10],
            start=1,
        ):
            rep = self._representative_article(items)
            sentiments = Counter(item["sentiment"] for item in items)
            issue_labels = [
                _text((item.get("issue_assignment") or {}).get("primary_topic_label"))
                for item in items
                if (item.get("issue_assignment") or {}).get("classification_status") == "classified"
            ]
            top_issue = Counter(label for label in issue_labels if label).most_common(1)
            rows.append(
                {
                    "rank": rank,
                    "media_name": media,
                    "channel": rep.get("channel"),
                    "article_count": len(items),
                    "ad_value": sum(_num(item.get("ad_value")) for item in items),
                    "pr_value": sum(_num(item.get("pr_value")) for item in items),
                    "dominant_sentiment": _dominant_sentiment(sentiments),
                    "top_issue": top_issue[0][0] if top_issue else None,
                    "top_article_title": rep.get("title"),
                    "top_article_url": rep.get("source_url"),
                }
            )
        self.add_quantitative_view(report_input, view_id="qt_mm_media_contributors_table", rows=rows)

    def _add_spokesperson_overview(self, report_input: dict[str, Any], articles: list[Mapping[str, Any]]) -> None:
        grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for article in articles:
            if article.get("spokesperson"):
                grouped[str(article["spokesperson"])].append(article)
        if not grouped:
            self.mark_view_na(
                report_input,
                view_id="qt_mm_spokesperson_overview",
                view_type="quantitative",
                reason="Field Spokesperson tidak tersedia/terisi pada scope ini.",
            )
            return
        rows = []
        for rank, (spokesperson, items) in enumerate(sorted(grouped.items(), key=lambda kv: len(kv[1]), reverse=True)[:3], start=1):
            rep = self._representative_article(items)
            sentiments = Counter(item["sentiment"] for item in items)
            issue_labels = [
                _text((item.get("issue_assignment") or {}).get("primary_topic_label"))
                for item in items
                if (item.get("issue_assignment") or {}).get("classification_status") == "classified"
            ]
            rows.append(
                {
                    "rank": rank,
                    "spokesperson": spokesperson,
                    "article_count": len(items),
                    "dominant_sentiment": _dominant_sentiment(sentiments),
                    "top_issues": [label for label, _ in Counter(issue_labels).most_common(3)],
                    "top_media": rep.get("media_name"),
                    "top_article_title": rep.get("title"),
                    "top_article_url": rep.get("source_url"),
                }
            )
        self.add_quantitative_view(report_input, view_id="qt_mm_spokesperson_overview", rows=rows)

    def _article_row(self, article: Mapping[str, Any], *, evidence_id: str) -> dict[str, Any]:
        assignment = article.get("issue_assignment") or {}
        return {
            "evidence_id": evidence_id,
            "source_row_id": article.get("source_row_id"),
            "canonical_key": article.get("canonical_key"),
            "date": article.get("date"),
            "title": article.get("title"),
            "content_snippet": _snippet(article),
            "channel": article.get("channel"),
            "media_name": article.get("media_name"),
            "sentiment": article.get("sentiment"),
            "ad_value": article.get("ad_value"),
            "pr_value": article.get("pr_value"),
            "readership": article.get("readership"),
            "circulation": article.get("circulation"),
            "spokesperson": article.get("spokesperson"),
            "issue_id": assignment.get("primary_topic_id"),
            "issue_label": assignment.get("primary_topic_label"),
            "issue_status": assignment.get("classification_status"),
            "raw_topic_extraction": article.get("raw_topic_extraction"),
            "entity_extraction": article.get("entity_extraction"),
            "noun": article.get("noun"),
            "sentence_type": article.get("sentence_type"),
            "mood": article.get("mood"),
            "aspect": article.get("aspect"),
            "source_url": article.get("source_url"),
        }

    def _add_article_enriched(self, report_input: dict[str, Any], articles: list[Mapping[str, Any]], enrichment: Mapping[str, Any]) -> None:
        ranked = _rank_articles(articles)[:50]
        rows = [self._article_row(article, evidence_id=f"mmr_article:{idx}") for idx, article in enumerate(ranked, start=1)]
        self.add_qualitative_view(
            report_input,
            view_id="ql_mm_article_enriched",
            rows=rows,
            metadata={
                "description": "Top evidence articles by PR Value, Ad Value, readership, and risk.",
                "raw_topic_extraction_policy": "diagnostic_only",
                "issue_taxonomy_version": enrichment.get("taxonomy_version"),
                "issue_status": enrichment.get("issue_status"),
            },
            evidence_reason="MMR master article evidence for narrative and audit.",
        )

    def _add_top_issues_cards(self, report_input: dict[str, Any], context: Mapping[str, Any]) -> None:
        rows = []
        ranked_groups = sorted(
            context["groups"].items(),
            key=lambda kv: (len(kv[1]), sum(_num(item.get("pr_value")) for item in kv[1])),
            reverse=True,
        )[:3]
        for rank, (issue_label, items) in enumerate(ranked_groups, start=1):
            rep = self._representative_article(items)
            sentiments = Counter(item["sentiment"] for item in items)
            rows.append(
                {
                    **self._article_row(rep, evidence_id=f"mmr_top_issue:{rank}"),
                    "rank": rank,
                    "issue_label": issue_label,
                    "article_count": len(items),
                    "dominant_sentiment": _dominant_sentiment(sentiments),
                    "issue_summary_hint": (
                        f"{issue_label} muncul pada {len(items)} artikel classified "
                        f"dengan media contoh {rep.get('media_name')}."
                    ),
                }
            )
        self.add_qualitative_view(
            report_input,
            view_id="ql_mm_top_issues_cards",
            rows=rows,
            metadata={
                "issue_taxonomy_version": context.get("taxonomy_version"),
                "issue_coverage_pct": context.get("coverage_pct"),
            },
            evidence_reason="Representative evidence for top mainstream issues.",
        )

    def _add_sentiment_issue_cards(self, report_input: dict[str, Any], context: Mapping[str, Any]) -> None:
        rows = []
        for sentiment in SENTIMENTS:
            filtered = [article for article in context["classified_articles"] if article["sentiment"] == sentiment]
            groups = self._group_by_issue(filtered)
            ranked = sorted(
                groups.items(),
                key=lambda kv: (len(kv[1]), sum(_num(item.get("pr_value")) for item in kv[1])),
                reverse=True,
            )[:2]
            for idx, (issue_label, items) in enumerate(ranked, start=1):
                rep = self._representative_article(items)
                rows.append(
                    {
                        **self._article_row(rep, evidence_id=f"mmr_sentiment_issue:{sentiment}:{idx}"),
                        "sentiment_bucket": sentiment,
                        "issue_label": issue_label,
                        "article_count": len(items),
                    }
                )
        self.add_qualitative_view(
            report_input,
            view_id="ql_mm_sentiment_issue_cards",
            rows=rows,
            metadata={
                "issue_taxonomy_version": context.get("taxonomy_version"),
                "issue_coverage_pct": context.get("coverage_pct"),
            },
            evidence_reason="Representative issue evidence per sentiment bucket.",
        )

    def _add_headlines_summary(self, report_input: dict[str, Any], articles: list[Mapping[str, Any]], enrichment: Mapping[str, Any]) -> None:
        def sensitive_score(article: Mapping[str, Any]) -> tuple[float, float, float]:
            text = f"{article.get('title') or ''} {article.get('content') or ''}".casefold()
            term_hit = sum(1 for term in RISK_TERMS if term in text)
            sentiment_weight = 3 if article.get("sentiment") == "negative" else 1 if article.get("sentiment") == "neutral" else 0
            return (
                float(term_hit + sentiment_weight),
                float(_num(article.get("pr_value")) + _num(article.get("ad_value"))),
                float(_num(article.get("readership"))),
            )

        ranked = sorted(articles, key=sensitive_score, reverse=True)[:12]
        rows = []
        for idx, article in enumerate(ranked, start=1):
            why = []
            if article.get("sentiment") == "negative":
                why.append("negative media tone")
            if _num(article.get("pr_value")) or _num(article.get("ad_value")):
                why.append("high value exposure")
            text = f"{article.get('title') or ''} {article.get('content') or ''}".casefold()
            hit_terms = [term for term in RISK_TERMS if term in text]
            if hit_terms:
                why.append("risk keyword: " + ", ".join(hit_terms[:3]))
            rows.append(
                {
                    **self._article_row(article, evidence_id=f"mmr_sensitive_headline:{idx}"),
                    "rank": idx,
                    "why_sensitive": "; ".join(why) or "high-impact article evidence",
                }
            )
        self.add_qualitative_view(
            report_input,
            view_id="ql_mm_headlines_summary",
            rows=rows,
            metadata={
                "description": "Sensitive/high-impact article candidates for MMR callout.",
                "issue_taxonomy_version": enrichment.get("taxonomy_version"),
                "issue_status": enrichment.get("issue_status"),
            },
            evidence_reason="Sensitive or high-impact headline evidence.",
        )

    def _mark_issue_views_not_available(self, report_input: dict[str, Any], reason: str) -> None:
        self.mark_view_not_available(
            report_input,
            view_id="qt_mm_main_topics_top3",
            view_type="quantitative",
            reason=reason,
            metadata={"raw_topic_extraction_policy": "not_used_as_final_report_issue"},
        )
        self.mark_view_not_available(
            report_input,
            view_id="ql_mm_top_issues_cards",
            view_type="qualitative",
            reason=reason,
            metadata={"raw_topic_extraction_policy": "not_used_as_final_report_issue"},
        )
        self.mark_view_not_available(
            report_input,
            view_id="ql_mm_sentiment_issue_cards",
            view_type="qualitative",
            reason=reason,
            metadata={"raw_topic_extraction_policy": "not_used_as_final_report_issue"},
        )


BUILDER_CLASS = MainstreamMediaReportBuilder


__all__ = ["MainstreamMediaReportBuilder", "BUILDER_CLASS"]
