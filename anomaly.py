"""
anomaly.py — Cogan anomaly detection engine.

VERSI 1.0

Layer ini MURNI komputasi. Tidak ada akses DB, tidak ada MCP.
Kontraknya:

    db.py       -> menyediakan "frames" (daily / hourly / author_daily /
                   duplicate_clusters / term_daily)
    anomaly.py  -> menjalankan seluruh detector di atas frames tersebut
    server.py   -> membungkusnya menjadi satu tool: scan_anomalies()

ATURAN PENTING
--------------
1. Engine ini TIDAK BOLEH dipakai untuk melewati Intent Confirmation pada
   request report/deck. Output-nya sengaja tidak report-ready:
   tidak ada report_input_id, tidak bisa disambung ke build_*_ppt_package.
2. Setiap finding WAJIB membawa evidence berupa canonical_key agar bisa
   langsung di-drill dengan get_posts().
3. Angka tidak pernah menjadi kesimpulan. Finding hanya menandai "ini aneh",
   pembacaan pemicunya tetap lewat konten asli.

PERBAIKAN METODOLOGIS DIBANDING detect_spikes LAMA
--------------------------------------------------
- Baseline memakai rolling median + MAD (bukan mean), sehingga spike besar
  tidak meng-inflate baseline-nya sendiri dan tidak me-masking hari berikutnya.
- Baseline dihitung dari trailing window yang MENGECUALIKAN hari yang diuji.
- Ada day-of-week normalisation (Senin/Minggu tidak lagi jadi false positive).
- Ada absolute floor: campaign sepi tidak di-flag hanya karena 2 -> 5 post.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Callable, Iterable


# =====================================================================
# Konstanta
# =====================================================================

MAD_SCALE = 1.4826          # konversi MAD -> estimasi std dev pada distribusi normal
DEFAULT_WINDOW = 14         # hari trailing untuk baseline
MIN_BASELINE_DAYS = 5       # di bawah ini, baseline tidak dipercaya

# Lantai skala: kita TIDAK PERNAH mengklaim presisi lebih baik dari 18% CV.
#
# Tanpa ini, seri yang kebetulan sangat stabil menghasilkan MAD mendekati nol,
# sehingga z-score meledak dan perubahan 1.2x pun terlihat "critical".
# Data sosial selalu punya variance alami; lantai ini yang menjaga kewarasan.
MIN_CV = 0.18

SENSITIVITY_Z = {
    "low": 3.5,
    "medium": 2.5,
    "high": 1.8,
}

# Effect-size gate. Signifikan secara statistik TIDAK CUKUP —
# perubahannya juga harus cukup besar untuk layak dilaporkan ke manusia.
SENSITIVITY_MIN_RATIO = {
    "low": 1.8,
    "medium": 1.5,
    "high": 1.3,
}

SEVERITY_BANDS = [
    (4.0, "critical"),
    (2.5, "high"),
    (1.5, "medium"),
    (0.0, "low"),
]

MAX_SCORE = 5.0


# =====================================================================
# Struktur finding
# =====================================================================

@dataclass
class Finding:
    """Satu temuan anomali."""

    detector: str
    family: str
    date: str
    severity: str
    score: float          # bounded 0-5, untuk severity band + tampilan
    confidence: float
    observed: float
    expected: float | None
    deviation: str
    narrative: str
    evidence: list[str] = field(default_factory=list)
    next_tool: str = "get_posts"
    next_args: dict[str, Any] = field(default_factory=dict)
    detail: dict[str, Any] = field(default_factory=dict)

    # Tidak di-cap. Dipakai HANYA untuk mengurutkan finding di dalam satu
    # severity band, supaya 12 temuan "critical" tidak berakhir seri di 5.0.
    strength: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "detector": self.detector,
            "family": self.family,
            "date": self.date,
            "severity": self.severity,
            "score": round(self.score, 2),
            "confidence": round(self.confidence, 2),
            "observed": _clean(self.observed),
            "expected": _clean(self.expected) if self.expected is not None else None,
            "deviation": self.deviation,
            "narrative": self.narrative,
            "evidence": self.evidence,
            "next_tool": self.next_tool,
            "next_args": self.next_args,
            "detail": self.detail,
        }


# =====================================================================
# Helper numerik
# =====================================================================

def _clean(value: Any) -> int | float:
    """Angka aman untuk JSON."""
    if value is None:
        return 0
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0
    if math.isnan(number) or math.isinf(number):
        return 0
    if number.is_integer():
        return int(number)
    return round(number, 3)


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _mad(values: list[float], center: float | None = None) -> float:
    """Median Absolute Deviation."""
    if not values:
        return 0.0
    med = _median(values) if center is None else center
    return _median([abs(value - med) for value in values])


def _robust_scale(values: list[float], center: float) -> float:
    """
    Skala robust untuk z-score, DENGAN lantai CV.

    Kenapa lantai itu wajib:
    Seri yang kebetulan stabil (mis. 48,50,49,51,50) punya MAD ~1.
    Tanpa lantai, nilai 60 akan menghasilkan z ~7 dan dilaporkan sebagai
    "critical" — padahal cuma naik 1.2x dan tidak ada artinya buat klien.

    Lantai = MIN_CV * center. Artinya: kita tidak pernah mengaku bisa
    membedakan perubahan yang lebih kecil dari ~18% dari level normal.
    """
    mad = _mad(values, center) * MAD_SCALE

    if values:
        mean_abs = sum(abs(value - center) for value in values) / len(values)
    else:
        mean_abs = 0.0

    floor = center * MIN_CV if center > 0 else 0.0
    scale = max(mad, mean_abs * 1.25, floor)

    # Seri benar-benar nol/konstan di nol.
    if scale <= 0:
        return 1.0
    return scale


def _robust_z(value: float, baseline: list[float]) -> tuple[float, float]:
    """Return (z_score, expected_median)."""
    if not baseline:
        return 0.0, 0.0
    center = _median(baseline)
    scale = _robust_scale(baseline, center)
    if scale <= 0:
        return 0.0, center
    return (value - center) / scale, center


def _severity(score: float) -> str:
    for threshold, label in SEVERITY_BANDS:
        if abs(score) >= threshold:
            return label
    return "low"


def _score_from_z(z_score: float, z_threshold: float) -> float:
    """
    Ubah z-score menjadi skor 0-5 yang bounded dan bisa dibandingkan
    antar-detector.

    Kalibrasi:
    - z tepat di threshold  -> 1.5  (medium)
    - z = 1.7x threshold    -> 2.5  (high)
    - z = 2.7x threshold    -> 4.0  (critical)

    Tanpa ini, z mentah dipakai sebagai skor dan satu hari ekstrem bisa
    menghasilkan skor 180 — merusak seluruh ranking.
    """
    if z_threshold <= 0:
        return 0.0
    return min(1.5 * (abs(z_score) / z_threshold), MAX_SCORE)


def _confidence(baseline_days: int, sample_size: float) -> float:
    """
    Seberapa layak finding ini dipercaya.

    Dua faktor:
    - panjang baseline (makin panjang makin yakin);
    - besar sampel hari itu (5 post tidak sekuat 500 post).
    """
    baseline_factor = min(baseline_days / float(DEFAULT_WINDOW), 1.0)
    sample_factor = min(math.log10(max(sample_size, 1.0) + 1) / 2.0, 1.0)
    return max(0.15, round(0.35 + 0.4 * baseline_factor + 0.25 * sample_factor, 3))


def _parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def _date_str(value: Any) -> str:
    parsed = _parse_date(value)
    return parsed.isoformat() if parsed else ""


def _pct(part: float, whole: float) -> float:
    if not whole:
        return 0.0
    return round(part / whole * 100.0, 1)


def _fmt(value: float) -> str:
    """Format angka untuk narasi manusia."""
    number = float(value or 0)
    if abs(number) >= 1_000_000:
        return f"{number / 1_000_000:.1f}jt"
    if abs(number) >= 1_000:
        return f"{number / 1_000:.1f}rb"
    if number.is_integer():
        return str(int(number))
    return f"{number:.1f}"


# =====================================================================
# Baseline series
# =====================================================================

class Series:
    """
    Deret harian satu metric, lengkap dengan baseline robust.

    Menyediakan:
    - trailing baseline yang MENGECUALIKAN hari yang diuji;
    - day-of-week normalisation;
    - absolute floor.
    """

    def __init__(
        self,
        daily: list[dict[str, Any]],
        key: str,
        window: int = DEFAULT_WINDOW,
        dow_adjust: bool = True,
    ) -> None:
        self.key = key
        self.window = window
        self.dates: list[str] = [_date_str(row.get("date")) for row in daily]
        self.values: list[float] = [float(row.get(key) or 0) for row in daily]
        self.dow_factor: dict[int, float] = {}

        if dow_adjust and len(self.values) >= DEFAULT_WINDOW:
            self.dow_factor = self._compute_dow_factor(daily)

    def _compute_dow_factor(self, daily: list[dict[str, Any]]) -> dict[int, float]:
        """Faktor koreksi hari-dalam-minggu, relatif terhadap median keseluruhan."""
        overall = _median([value for value in self.values if value > 0])
        if overall <= 0:
            return {}

        buckets: dict[int, list[float]] = {}
        for row, value in zip(daily, self.values):
            parsed = _parse_date(row.get("date"))
            if parsed is None:
                continue
            buckets.setdefault(parsed.weekday(), []).append(value)

        factors: dict[int, float] = {}
        for weekday, values in buckets.items():
            if len(values) < 2:
                continue
            local = _median(values)
            if local <= 0:
                continue
            factor = local / overall
            # Jangan biarkan koreksi liar; batasi 0.5x - 2.0x
            factors[weekday] = min(max(factor, 0.5), 2.0)
        return factors

    def _adjust(self, index: int, value: float) -> float:
        if not self.dow_factor:
            return value
        parsed = _parse_date(self.dates[index])
        if parsed is None:
            return value
        factor = self.dow_factor.get(parsed.weekday(), 1.0)
        if factor <= 0:
            return value
        return value / factor

    def baseline_at(self, index: int) -> list[float]:
        """Trailing window, tidak termasuk hari ini."""
        start = max(0, index - self.window)
        return [
            self._adjust(position, self.values[position])
            for position in range(start, index)
        ]

    def evaluate(self, index: int) -> dict[str, Any] | None:
        """Hitung z-score robust untuk satu hari."""
        baseline = self.baseline_at(index)
        if len(baseline) < MIN_BASELINE_DAYS:
            return None

        raw = self.values[index]
        adjusted = self._adjust(index, raw)
        z_score, expected = _robust_z(adjusted, baseline)

        return {
            "date": self.dates[index],
            "raw": raw,
            "adjusted": adjusted,
            "expected": expected,
            "z": z_score,
            "baseline_days": len(baseline),
            "ratio": (adjusted / expected) if expected > 0 else None,
        }


# =====================================================================
# Detector registry
# =====================================================================

DETECTORS: dict[str, dict[str, Any]] = {}


def detector(
    name: str,
    family: str,
    risk_weight: float = 1.0,
    needs: tuple[str, ...] = ("daily",),
) -> Callable:
    """
    Daftarkan satu detector.

    risk_weight menaikkan/menurunkan severity relatif detector lain.
    Contoh: trigger_term punya weight tinggi karena volume kecil pun berbahaya.
    """

    def wrapper(func: Callable) -> Callable:
        DETECTORS[name] = {
            "name": name,
            "family": family,
            "risk_weight": risk_weight,
            "needs": needs,
            "func": func,
        }
        return func

    return wrapper


# ---------------------------------------------------------------------
# FAMILY: volume
# ---------------------------------------------------------------------

@detector("volume_spike", "volume", risk_weight=1.0)
def _volume_spike(ctx: "ScanContext") -> list[Finding]:
    return _level_detector(
        ctx,
        key="posts",
        direction="up",
        detector_name="volume_spike",
        family="volume",
        label="volume post",
        min_absolute=ctx.min_posts,
    )


@detector("interactions_spike", "amplification", risk_weight=1.1)
def _interactions_spike(ctx: "ScanContext") -> list[Finding]:
    return _level_detector(
        ctx,
        key="interactions",
        direction="up",
        detector_name="interactions_spike",
        family="amplification",
        label="interaksi",
        min_absolute=ctx.min_interactions,
    )


@detector("views_spike", "amplification", risk_weight=0.9)
def _views_spike(ctx: "ScanContext") -> list[Finding]:
    return _level_detector(
        ctx,
        key="views",
        direction="up",
        detector_name="views_spike",
        family="amplification",
        label="views",
        min_absolute=ctx.min_interactions,
    )


@detector("volume_drop", "volume", risk_weight=1.2)
def _volume_drop(ctx: "ScanContext") -> list[Finding]:
    """
    Volume ambruk mendadak.

    Ini SERING bukan berita bagus: crawler mati, keyword berubah, scope rusak.
    Dianggap data-integrity signal, bukan "isu mereda".
    """
    findings: list[Finding] = []
    series = ctx.series("posts")

    for index in range(len(series.values)):
        result = series.evaluate(index)
        if result is None:
            continue

        expected = result["expected"]
        observed = result["raw"]

        # Hanya bermakna kalau baseline-nya memang ramai.
        if expected < max(ctx.min_posts, 5):
            continue
        if result["z"] > -ctx.z_threshold:
            continue

        drop_pct = _pct(expected - observed, expected)
        if drop_pct < 60:
            continue

        score = _score_from_z(result["z"], ctx.z_threshold)
        findings.append(
            Finding(
                detector="volume_drop",
                family="volume",
                date=result["date"],
                severity=_severity(score),
                score=score,
                confidence=_confidence(result["baseline_days"], expected),
                observed=observed,
                expected=expected,
                deviation=f"-{drop_pct}% vs baseline",
                narrative=(
                    f"Volume ambruk ke {_fmt(observed)} post "
                    f"(biasanya ~{_fmt(expected)}, turun {drop_pct}%). "
                    "Cek dulu apakah crawler mati / keyword scope berubah "
                    "sebelum menyimpulkan isu mereda."
                ),
                evidence=[],
                next_tool="data_health",
                next_args={"start_date": result["date"], "end_date": result["date"]},
                detail={"drop_pct": drop_pct},
            )
        )
    return findings


@detector("sustained_elevation", "volume", risk_weight=1.3)
def _sustained_elevation(ctx: "ScanContext") -> list[Finding]:
    """
    Regime change: naik pelan tapi bertahan.

    Ini yang paling sering LOLOS dari detect_spikes lama. Naik 1.4x selama
    7 hari tidak pernah menyentuh threshold 1.8x, padahal artinya
    percakapan sudah pindah level — lebih serius daripada blip satu hari.
    """
    findings: list[Finding] = []
    series = ctx.series("posts")
    run_length = 0
    run_dates: list[str] = []
    run_values: list[float] = []
    run_expected: list[float] = []

    for index in range(len(series.values)):
        result = series.evaluate(index)
        elevated = (
            result is not None
            and result["ratio"] is not None
            and result["ratio"] >= 1.25
            and result["raw"] >= ctx.min_posts
        )

        if elevated:
            run_length += 1
            run_dates.append(result["date"])
            run_values.append(result["raw"])
            run_expected.append(result["expected"])
            continue

        if run_length >= ctx.sustained_days:
            findings.append(_build_sustained(ctx, run_dates, run_values, run_expected))
        run_length = 0
        run_dates, run_values, run_expected = [], [], []

    if run_length >= ctx.sustained_days:
        findings.append(_build_sustained(ctx, run_dates, run_values, run_expected))

    return [item for item in findings if item is not None]


def _build_sustained(
    ctx: "ScanContext",
    dates: list[str],
    values: list[float],
    expected: list[float],
) -> Finding | None:
    if not dates:
        return None

    mean_observed = sum(values) / len(values)
    mean_expected = sum(expected) / len(expected) if expected else 0.0
    if mean_expected <= 0:
        return None

    ratio = mean_observed / mean_expected
    score = 1.4 + (ratio - 1.25) * 2.0 + (len(dates) - ctx.sustained_days) * 0.3
    score = min(score, MAX_SCORE)

    return Finding(
        detector="sustained_elevation",
        family="volume",
        date=dates[-1],
        severity=_severity(score),
        score=score,
        confidence=_confidence(DEFAULT_WINDOW, mean_observed),
        observed=round(mean_observed, 1),
        expected=round(mean_expected, 1),
        deviation=f"{ratio:.2f}x selama {len(dates)} hari",
        narrative=(
            f"Percakapan bertahan di ~{ratio:.2f}x baseline selama "
            f"{len(dates)} hari berturut ({dates[0]} s/d {dates[-1]}). "
            "Ini regime change, bukan blip — level normalnya sudah bergeser."
        ),
        evidence=[],
        next_tool="get_posts",
        next_args={"start_date": dates[0], "end_date": dates[-1]},
        detail={"streak_days": len(dates), "dates": dates},
    )


def _level_detector(
    ctx: "ScanContext",
    key: str,
    direction: str,
    detector_name: str,
    family: str,
    label: str,
    min_absolute: float,
) -> list[Finding]:
    """Detector generik untuk lonjakan level satu metric."""
    findings: list[Finding] = []
    series = ctx.series(key)

    for index in range(len(series.values)):
        result = series.evaluate(index)
        if result is None:
            continue

        observed = result["raw"]
        ratio = result["ratio"]

        # Gate 1 — absolute floor. Campaign sepi tidak di-flag hanya karena
        # 2 post menjadi 5 post.
        if observed < min_absolute:
            continue

        # Gate 2 — signifikansi statistik.
        if direction == "up" and result["z"] < ctx.z_threshold:
            continue

        # Gate 3 — effect size. Ini yang mencegah kenaikan 1.2x dilaporkan
        # sebagai "critical" hanya karena serinya kebetulan stabil.
        if ratio is None or ratio < ctx.min_ratio:
            continue

        score = _score_from_z(result["z"], ctx.z_threshold)
        day = ctx.day_by_date.get(result["date"], {})

        findings.append(
            Finding(
                detector=detector_name,
                family=family,
                date=result["date"],
                severity=_severity(score),
                score=score,
                confidence=_confidence(result["baseline_days"], observed),
                observed=observed,
                expected=round(result["expected"], 1),
                deviation=(
                    f"{ratio:.1f}x baseline (z={result['z']:.1f})"
                    if ratio
                    else f"z={result['z']:.1f}"
                ),
                narrative=(
                    f"{label.capitalize()} melonjak ke {_fmt(observed)} "
                    f"(baseline ~{_fmt(result['expected'])}"
                    + (f", {ratio:.1f}x lipat" if ratio else "")
                    + ")."
                ),
                evidence=_evidence_from_day(day),
                next_tool="get_posts",
                next_args={
                    "start_date": result["date"],
                    "end_date": result["date"],
                    "sort_by": "interactions" if key != "posts" else "interactions",
                },
                detail={"dow_adjusted": bool(series.dow_factor)},
            )
        )
    return findings


# ---------------------------------------------------------------------
# FAMILY: amplification quality
# ---------------------------------------------------------------------

@detector("engagement_concentration", "amplification", risk_weight=1.4)
def _engagement_concentration(ctx: "ScanContext") -> list[Finding]:
    """
    Satu post menguasai mayoritas interaksi.

    Pola Bluebird: 1 post eksternal soal CEO menarik ~70% seluruh interaksi.
    Volume terlihat normal, tapi realitanya ini bukan percakapan publik —
    ini satu suara yang diperbesar.
    """
    findings: list[Finding] = []

    for row in ctx.daily:
        total = float(row.get("interactions") or 0)
        top1 = float(row.get("top1_interactions") or 0)
        posts = float(row.get("posts") or 0)

        if total < ctx.min_interactions or posts < 5:
            continue

        share = top1 / total if total > 0 else 0.0
        if share < ctx.concentration_threshold:
            continue

        score = 1.5 + (share - ctx.concentration_threshold) * 8.0
        score = min(score, MAX_SCORE)
        key = row.get("top1_canonical_key")

        findings.append(
            Finding(
                detector="engagement_concentration",
                family="amplification",
                date=_date_str(row.get("date")),
                severity=_severity(score),
                score=score,
                confidence=_confidence(DEFAULT_WINDOW, total),
                observed=round(share * 100, 1),
                expected=round(100.0 / max(posts, 1), 1),
                deviation=f"top-1 post = {share * 100:.0f}% dari total interaksi",
                narrative=(
                    f"Satu post menyumbang {share * 100:.0f}% dari "
                    f"{_fmt(total)} interaksi hari itu (dari {int(posts)} post). "
                    "Angka agregat menyesatkan — ini bukan percakapan luas, "
                    "ini satu konten yang meledak."
                ),
                evidence=[key] if key else [],
                next_tool="top_viral_posts",
                next_args={
                    "start_date": _date_str(row.get("date")),
                    "end_date": _date_str(row.get("date")),
                    "limit": 5,
                },
                detail={
                    "top1_interactions": _clean(top1),
                    "total_interactions": _clean(total),
                    "posts": int(posts),
                },
            )
        )
    return findings


@detector("engagement_rate_outlier", "amplification", risk_weight=1.0)
def _engagement_rate_outlier(ctx: "ScanContext") -> list[Finding]:
    """Interaksi per post jauh di luar kebiasaan (indikasi paid push / bot)."""
    findings: list[Finding] = []

    rates: list[dict[str, Any]] = []
    for row in ctx.daily:
        posts = float(row.get("posts") or 0)
        interactions = float(row.get("interactions") or 0)
        rates.append(
            {
                "date": row.get("date"),
                "rate": (interactions / posts) if posts > 0 else 0.0,
                "posts": posts,
            }
        )

    series = Series(
        [{"date": item["date"], "rate": item["rate"]} for item in rates],
        key="rate",
        window=ctx.window,
        dow_adjust=False,
    )

    for index, item in enumerate(rates):
        if item["posts"] < ctx.min_posts:
            continue
        result = series.evaluate(index)
        if result is None or result["z"] < ctx.z_threshold:
            continue
        if result["expected"] <= 0:
            continue
        if result["ratio"] is None or result["ratio"] < ctx.min_ratio:
            continue

        score = _score_from_z(result["z"], ctx.z_threshold)
        day = ctx.day_by_date.get(result["date"], {})

        findings.append(
            Finding(
                detector="engagement_rate_outlier",
                family="amplification",
                date=result["date"],
                severity=_severity(score),
                score=score,
                confidence=_confidence(result["baseline_days"], item["posts"]),
                observed=round(result["raw"], 1),
                expected=round(result["expected"], 1),
                deviation=f"{result['ratio']:.1f}x interaksi per post",
                narrative=(
                    f"Rata-rata interaksi per post {_fmt(result['raw'])} "
                    f"(biasanya ~{_fmt(result['expected'])}). "
                    "Post tidak bertambah banyak tapi respon meledak — "
                    "periksa apakah ada amplifikasi berbayar atau akun terkoordinasi."
                ),
                evidence=_evidence_from_day(day),
                next_tool="top_viral_posts",
                next_args={"start_date": result["date"], "end_date": result["date"]},
                detail={},
            )
        )
    return findings


@detector("views_interactions_ratio", "data_integrity", risk_weight=0.8)
def _views_interactions_ratio(ctx: "ScanContext") -> list[Finding]:
    """
    Views tinggi tapi interaksi nyaris nol (view farming), atau sebaliknya
    (kemungkinan data error / kolom views bolong).
    """
    findings: list[Finding] = []

    for row in ctx.daily:
        views = float(row.get("views") or 0)
        interactions = float(row.get("interactions") or 0)
        posts = float(row.get("posts") or 0)

        if posts < ctx.min_posts or views < 10_000:
            continue

        ratio = interactions / views if views > 0 else 0.0

        if ratio < 0.0005:
            score = 2.2
            narrative = (
                f"{_fmt(views)} views tapi cuma {_fmt(interactions)} interaksi "
                f"({ratio * 100:.3f}%). Rasio serendah ini biasanya berarti "
                "view farming, autoplay, atau views tidak organik."
            )
        elif ratio > 0.5:
            score = 2.0
            narrative = (
                f"Interaksi {_fmt(interactions)} vs views {_fmt(views)} "
                f"({ratio * 100:.0f}%). Rasio setinggi ini tidak wajar — "
                "kemungkinan besar kolom views bolong, bukan performa luar biasa."
            )
        else:
            continue

        findings.append(
            Finding(
                detector="views_interactions_ratio",
                family="data_integrity",
                date=_date_str(row.get("date")),
                severity=_severity(score),
                score=score,
                confidence=_confidence(DEFAULT_WINDOW, posts),
                observed=round(ratio * 100, 3),
                expected=None,
                deviation=f"interaksi/views = {ratio * 100:.3f}%",
                narrative=narrative,
                evidence=[],
                next_tool="validate_metric_readiness",
                next_args={
                    "start_date": _date_str(row.get("date")),
                    "end_date": _date_str(row.get("date")),
                },
                detail={"views": _clean(views), "interactions": _clean(interactions)},
            )
        )
    return findings


# ---------------------------------------------------------------------
# FAMILY: sentiment
# ---------------------------------------------------------------------

@detector("sentiment_divergence", "sentiment", risk_weight=1.5)
def _sentiment_divergence(ctx: "ScanContext") -> list[Finding]:
    """
    Sentimen by-count hijau, tapi yang VIRAL justru yang negatif.

    Ini nyaris definisi anomali brand-risk, dan tidak akan pernah ketangkap
    oleh spike detector manapun. Pola Gojek: label RED menyesatkan karena
    post negatif nyaris tanpa amplifikasi. Pola Bluebird kebalikannya:
    count pulih (+8.9) tapi engagement-weighted tetap negatif (-14.6).

    PENTING — kenapa ini TIDAK memakai threshold absolut:
    Setiap project punya gap "normal"-nya sendiri. Sebagian besar hari memang
    sedikit divergen karena engagement tidak pernah terdistribusi rata.
    Kalau dipakai ambang tetap (mis. 20 poin), detector ini menyala di ~40%
    hari dan berubah jadi mesin noise.

    Jadi yang dianggap anomali hanya:
    (a) SIGN FLIP  — count bilang positif, engagement bilang negatif
                     (atau sebaliknya). Ini selalu layak dilaporkan.
    (b) OUTLIER    — gap hari ini jauh di luar kebiasaan project itu sendiri,
                     diukur dengan baseline robust yang sama seperti metric lain.
    Keduanya tetap wajib melewati lantai absolut `divergence_threshold`.
    """
    findings: list[Finding] = []

    # Bangun deret gap harian dulu, supaya bisa dibandingkan dengan
    # kebiasaan project ini sendiri.
    gaps: list[dict[str, Any]] = []
    for row in ctx.daily:
        classified = float(row.get("classified_posts") or 0)
        eng_positive = float(row.get("eng_positive") or 0)
        eng_negative = float(row.get("eng_negative") or 0)
        eng_total = eng_positive + eng_negative

        if classified < ctx.min_posts or eng_total < ctx.min_interactions:
            gaps.append({"date": row.get("date"), "gap": 0.0, "valid": False})
            continue

        positive = float(row.get("positive_posts") or 0)
        negative = float(row.get("negative_posts") or 0)
        net_count = _pct(positive, classified) - _pct(negative, classified)
        net_weighted = _pct(eng_positive, eng_total) - _pct(eng_negative, eng_total)

        gaps.append(
            {
                "date": row.get("date"),
                "gap": net_count - net_weighted,
                "abs_gap": abs(net_count - net_weighted),
                "net_count": net_count,
                "net_weighted": net_weighted,
                "eng_total": eng_total,
                "valid": True,
            }
        )

    series = Series(
        [{"date": item["date"], "abs_gap": item.get("abs_gap", 0.0)} for item in gaps],
        key="abs_gap",
        window=ctx.window,
        dow_adjust=False,
    )

    for index, item in enumerate(gaps):
        if not item["valid"]:
            continue

        gap = item["gap"]
        net_count = item["net_count"]
        net_weighted = item["net_weighted"]

        # Lantai absolut. Gap 8 poin tidak pernah menarik, sebesar apapun z-nya.
        if abs(gap) < ctx.divergence_threshold:
            continue

        sign_flip = (net_count > 0 > net_weighted) or (net_count < 0 < net_weighted)

        result = series.evaluate(index)
        is_outlier = (
            result is not None
            and result["z"] >= ctx.z_threshold
            and result["expected"] > 0
        )

        if not (sign_flip or is_outlier):
            continue

        if sign_flip:
            score = 2.6 + abs(gap) / 40.0
            reason = "sign_flip"
        else:
            score = _score_from_z(result["z"], ctx.z_threshold)
            reason = "outlier_vs_own_baseline"
        score = min(score, MAX_SCORE)

        if gap > 0:
            narrative = (
                f"Sentimen by-count terlihat {net_count:+.0f}, tapi ditimbang "
                f"engagement jadi {net_weighted:+.0f} (selisih {abs(gap):.0f} poin). "
                "Post negatif sedikit tapi justru itu yang diamplifikasi. "
                "Jangan laporkan agregat hijau."
            )
        else:
            narrative = (
                f"Sentimen by-count {net_count:+.0f} tapi engagement-weighted "
                f"{net_weighted:+.0f} (lebih positif {abs(gap):.0f} poin). "
                "Label risiko dari count menyesatkan — post negatif nyaris "
                "tanpa amplifikasi, yang jalan justru konten positif."
            )

        findings.append(
            Finding(
                detector="sentiment_divergence",
                family="sentiment",
                date=_date_str(item["date"]),
                severity=_severity(score),
                score=score,
                confidence=_confidence(
                    result["baseline_days"] if result else 0,
                    item["eng_total"],
                ),
                observed=round(net_weighted, 1),
                expected=round(net_count, 1),
                deviation=(
                    f"gap {gap:+.0f} poin"
                    + (" — TANDA BERBALIK" if sign_flip else " (di luar kebiasaan project)")
                ),
                narrative=narrative,
                evidence=[],
                next_tool="get_posts",
                next_args={
                    "start_date": _date_str(item["date"]),
                    "end_date": _date_str(item["date"]),
                    "sentiment": "negative",
                    "sort_by": "interactions",
                },
                detail={
                    "net_by_count": round(net_count, 1),
                    "net_engagement_weighted": round(net_weighted, 1),
                    "reason": reason,
                },
            )
        )
    return findings


@detector("negative_share_spike", "sentiment", risk_weight=1.3)
def _negative_share_spike(ctx: "ScanContext") -> list[Finding]:
    """Porsi negatif melonjak, terlepas dari volume total."""
    findings: list[Finding] = []

    shares = []
    for row in ctx.daily:
        classified = float(row.get("classified_posts") or 0)
        negative = float(row.get("negative_posts") or 0)
        shares.append(
            {
                "date": row.get("date"),
                "share": _pct(negative, classified),
                "classified": classified,
                "negative": negative,
            }
        )

    series = Series(
        [{"date": item["date"], "share": item["share"]} for item in shares],
        key="share",
        window=ctx.window,
        dow_adjust=False,
    )

    for index, item in enumerate(shares):
        if item["classified"] < ctx.min_posts or item["negative"] < 3:
            continue
        result = series.evaluate(index)
        if result is None or result["z"] < ctx.z_threshold:
            continue
        # Effect size untuk share dihitung dalam POIN PERSEN, bukan rasio.
        # Naik dari 14% ke 17% tidak layak dilaporkan meski z-nya tinggi.
        if (result["raw"] - result["expected"]) < ctx.negative_share_min_gap:
            continue

        score = _score_from_z(result["z"], ctx.z_threshold)
        findings.append(
            Finding(
                detector="negative_share_spike",
                family="sentiment",
                date=result["date"],
                severity=_severity(score),
                score=score,
                confidence=_confidence(result["baseline_days"], item["classified"]),
                observed=round(result["raw"], 1),
                expected=round(result["expected"], 1),
                deviation=f"{result['raw']:.0f}% negatif vs baseline {result['expected']:.0f}%",
                narrative=(
                    f"Porsi negatif naik ke {result['raw']:.0f}% "
                    f"(biasanya ~{result['expected']:.0f}%), "
                    f"{int(item['negative'])} post negatif dari "
                    f"{int(item['classified'])} yang terklasifikasi."
                ),
                evidence=[],
                next_tool="get_posts",
                next_args={
                    "start_date": result["date"],
                    "end_date": result["date"],
                    "sentiment": "negative",
                },
                detail={},
            )
        )
    return findings


# ---------------------------------------------------------------------
# FAMILY: actors
# ---------------------------------------------------------------------

@detector("single_author_flood", "actors", risk_weight=1.2, needs=("author_daily",))
def _single_author_flood(ctx: "ScanContext") -> list[Finding]:
    """Satu akun memborong porsi besar percakapan hari itu."""
    findings: list[Finding] = []

    by_date: dict[str, list[dict[str, Any]]] = {}
    for row in ctx.author_daily:
        by_date.setdefault(_date_str(row.get("date")), []).append(row)

    for day_str, authors in by_date.items():
        # Daftar author dipotong di top-N oleh query layer. Kalau total dihitung
        # dari daftar yang terpotong, share-nya jadi terlalu besar (bug halus
        # yang bikin flood palsu). Pakai total hari yang dikirim query.
        declared_total = max(
            (float(item.get("day_total_posts") or 0) for item in authors),
            default=0.0,
        )
        total_posts = declared_total or sum(
            float(item.get("posts") or 0) for item in authors
        )
        if total_posts < max(ctx.min_posts, 10):
            continue

        top = max(authors, key=lambda item: float(item.get("posts") or 0))
        top_posts = float(top.get("posts") or 0)
        share = top_posts / total_posts

        if share < ctx.author_flood_threshold or top_posts < 5:
            continue

        score = 1.5 + (share - ctx.author_flood_threshold) * 9.0
        score = min(score, MAX_SCORE)

        findings.append(
            Finding(
                detector="single_author_flood",
                family="actors",
                date=day_str,
                severity=_severity(score),
                score=score,
                confidence=_confidence(DEFAULT_WINDOW, total_posts),
                observed=round(share * 100, 1),
                expected=None,
                deviation=f"1 akun = {share * 100:.0f}% dari post hari itu",
                narrative=(
                    f"Akun '{top.get('author') or 'tidak diketahui'}' memposting "
                    f"{int(top_posts)}x ({share * 100:.0f}% dari seluruh post hari itu). "
                    "Ini bukan percakapan organik — cek apakah reseller, bot, "
                    "atau akun spam yang perlu dikeluarkan dari scope."
                ),
                evidence=[key for key in (top.get("sample_canonical_key"),) if key],
                next_tool="top_authors",
                next_args={"start_date": day_str, "end_date": day_str, "limit": 10},
                detail={
                    "author": top.get("author"),
                    "author_posts": int(top_posts),
                    "total_posts": int(total_posts),
                },
            )
        )
    return findings


@detector("coordinated_burst", "actors", risk_weight=1.6, needs=("duplicate_clusters",))
def _coordinated_burst(ctx: "ScanContext") -> list[Finding]:
    """
    Banyak akun berbeda memposting teks nyaris identik dalam jendela pendek.

    Ini tanda buzzer/astroturfing. Tidak terlihat sama sekali oleh
    spike detector karena volumenya bisa saja normal.
    """
    findings: list[Finding] = []

    for cluster in ctx.duplicate_clusters:
        size = int(cluster.get("cluster_size") or 0)
        distinct_authors = int(cluster.get("distinct_authors") or 0)
        span_minutes = float(cluster.get("span_minutes") or 0)

        if size < ctx.burst_min_posts or distinct_authors < ctx.burst_min_authors:
            continue
        if span_minutes > ctx.burst_window_minutes:
            continue

        density = size / max(span_minutes / 60.0, 0.25)
        score = 2.0 + min(distinct_authors / 10.0, 2.0) + min(density / 20.0, 1.0)
        score = min(score, MAX_SCORE)

        findings.append(
            Finding(
                detector="coordinated_burst",
                family="actors",
                date=_date_str(cluster.get("date")),
                severity=_severity(score),
                score=score,
                confidence=_confidence(DEFAULT_WINDOW, size),
                observed=size,
                expected=None,
                deviation=(
                    f"{size} post nyaris identik dari {distinct_authors} akun "
                    f"dalam {span_minutes:.0f} menit"
                ),
                narrative=(
                    f"{distinct_authors} akun berbeda memposting teks nyaris sama "
                    f"({size} post) dalam rentang {span_minutes:.0f} menit. "
                    "Pola ini khas buzzer/koordinasi, bukan percakapan spontan."
                ),
                evidence=[
                    key
                    for key in (cluster.get("sample_canonical_keys") or [])
                    if key
                ][:5],
                next_tool="get_posts",
                next_args={
                    "start_date": _date_str(cluster.get("date")),
                    "end_date": _date_str(cluster.get("date")),
                    "keywords": (cluster.get("sample_text") or "")[:60],
                },
                detail={
                    "cluster_size": size,
                    "distinct_authors": distinct_authors,
                    "span_minutes": round(span_minutes, 1),
                    "sample_text": (cluster.get("sample_text") or "")[:200],
                },
            )
        )
    return findings


@detector("new_author_surge", "actors", risk_weight=1.0, needs=("author_daily",))
def _new_author_surge(ctx: "ScanContext") -> list[Finding]:
    """Akun yang belum pernah muncul tiba-tiba masuk jajaran top interaksi."""
    findings: list[Finding] = []

    seen: set[str] = set()
    by_date: dict[str, list[dict[str, Any]]] = {}
    for row in ctx.author_daily:
        by_date.setdefault(_date_str(row.get("date")), []).append(row)

    ordered_dates = sorted(by_date.keys())
    warmup = min(5, max(1, len(ordered_dates) // 3))

    for position, day_str in enumerate(ordered_dates):
        authors = by_date[day_str]
        declared = max(
            (float(item.get("day_total_interactions") or 0) for item in authors),
            default=0.0,
        )
        day_interactions = declared or sum(
            float(item.get("interactions") or 0) for item in authors
        )

        if position >= warmup and day_interactions >= ctx.min_interactions:
            for item in authors:
                name = (item.get("author") or "").strip()
                if not name or name in seen:
                    continue
                interactions = float(item.get("interactions") or 0)
                share = interactions / day_interactions if day_interactions else 0.0
                if share < 0.25:
                    continue

                score = 1.6 + share * 4.0
                score = min(score, MAX_SCORE)
                findings.append(
                    Finding(
                        detector="new_author_surge",
                        family="actors",
                        date=day_str,
                        severity=_severity(score),
                        score=score,
                        confidence=_confidence(position, day_interactions),
                        observed=round(share * 100, 1),
                        expected=None,
                        deviation=f"akun baru langsung {share * 100:.0f}% interaksi",
                        narrative=(
                            f"Akun '{name}' belum pernah muncul di periode ini, "
                            f"tapi langsung menyumbang {share * 100:.0f}% interaksi "
                            f"({_fmt(interactions)}). Suara baru yang langsung besar "
                            "biasanya media, influencer, atau pihak berwenang — "
                            "identifikasi siapa dia."
                        ),
                        evidence=[
                            key
                            for key in (item.get("sample_canonical_key"),)
                            if key
                        ],
                        next_tool="top_authors",
                        next_args={"start_date": day_str, "end_date": day_str},
                        detail={"author": name, "interactions": _clean(interactions)},
                    )
                )

        for item in authors:
            name = (item.get("author") or "").strip()
            if name:
                seen.add(name)

    return findings


# ---------------------------------------------------------------------
# FAMILY: risk content
# ---------------------------------------------------------------------

@detector("trigger_term_appearance", "risk_content", risk_weight=2.0, needs=("term_daily",))
def _trigger_term_appearance(ctx: "ScanContext") -> list[Finding]:
    """
    Munculnya kosakata regulator / hukum / investigasi.

    INI DETECTOR PALING PENTING dan yang paling mustahil ketangkap spike.
    Kasus Aqua/KDM: agregat sentimen hijau (~55-57% positif), tapi ada ~30
    artikel memuat BPKN / YLKI / DPR / audit / investigasi. Volumenya kecil,
    jadi tidak ada spike sama sekali — tapi risk posture-nya merah.
    """
    findings: list[Finding] = []

    for row in ctx.term_daily:
        group = row.get("term_group")
        if group != "trigger":
            continue

        posts = float(row.get("posts") or 0)
        if posts < ctx.trigger_min_posts:
            continue

        matched = row.get("matched_terms") or []
        score = 2.5 + min(posts / 10.0, 2.0)
        score = min(score, MAX_SCORE)

        findings.append(
            Finding(
                detector="trigger_term_appearance",
                family="risk_content",
                date=_date_str(row.get("date")),
                severity=_severity(score),
                score=score,
                confidence=0.9,
                observed=int(posts),
                expected=None,
                deviation=f"{int(posts)} post memuat trigger term",
                narrative=(
                    f"{int(posts)} post memuat istilah pemicu risiko: "
                    f"{', '.join(matched[:6])}. "
                    "Volume kecil, jadi tidak akan muncul sebagai spike — "
                    "tapi ini yang menentukan risk posture, bukan angka agregat."
                ),
                evidence=[
                    key for key in (row.get("sample_canonical_keys") or []) if key
                ][:5],
                next_tool="get_posts",
                next_args={
                    "start_date": _date_str(row.get("date")),
                    "end_date": _date_str(row.get("date")),
                    "keywords": ",".join(matched[:8]),
                },
                detail={"matched_terms": matched},
            )
        )
    return findings


# ---------------------------------------------------------------------
# FAMILY: data integrity
# ---------------------------------------------------------------------

@detector("noise_contamination", "data_integrity", risk_weight=1.4, needs=("term_daily",))
def _noise_contamination(ctx: "ScanContext") -> list[Finding]:
    """
    Porsi post di luar scope brand naik.

    Kasus nyata: 'AQUA Elektronik' & badminton mengotori scope Aqua (~90% noise).
    'BlueBird' satelit (ASTS) menggelembungkan sentimen positif Bluebird.
    Ini bukan anomali brand — ini anomali data, tapi merusak report sama fatalnya.
    """
    findings: list[Finding] = []

    for row in ctx.term_daily:
        if row.get("term_group") != "noise":
            continue

        noise_posts = float(row.get("posts") or 0)
        total_posts = float(row.get("total_posts") or 0)
        if total_posts < ctx.min_posts:
            continue

        share = noise_posts / total_posts if total_posts else 0.0
        if share < ctx.noise_threshold:
            continue

        score = 1.8 + share * 3.5
        score = min(score, MAX_SCORE)
        matched = row.get("matched_terms") or []

        findings.append(
            Finding(
                detector="noise_contamination",
                family="data_integrity",
                date=_date_str(row.get("date")),
                severity=_severity(score),
                score=score,
                confidence=0.85,
                observed=round(share * 100, 1),
                expected=None,
                deviation=f"{share * 100:.0f}% post kemungkinan di luar scope",
                narrative=(
                    f"{int(noise_posts)} dari {int(total_posts)} post "
                    f"({share * 100:.0f}%) memuat kata noise: "
                    f"{', '.join(matched[:5])}. Angka apapun dari hari ini "
                    "tidak bisa dipakai sebelum di-exclude."
                ),
                evidence=[
                    key for key in (row.get("sample_canonical_keys") or []) if key
                ][:5],
                next_tool="count_posts",
                next_args={
                    "start_date": _date_str(row.get("date")),
                    "end_date": _date_str(row.get("date")),
                    "exclude_keywords": ",".join(matched[:8]),
                },
                detail={"matched_terms": matched},
            )
        )
    return findings


@detector("coverage_gap", "data_integrity", risk_weight=1.5)
def _coverage_gap(ctx: "ScanContext") -> list[Finding]:
    """Hari bolong di tengah rentang — data hilang, bukan sepi."""
    findings: list[Finding] = []
    if len(ctx.daily) < 3:
        return findings

    dates = [_parse_date(row.get("date")) for row in ctx.daily]
    dates = [item for item in dates if item is not None]
    if not dates:
        return findings

    present = set(dates)
    cursor = min(dates)
    last = max(dates)
    missing: list[str] = []

    while cursor <= last:
        if cursor not in present:
            missing.append(cursor.isoformat())
        cursor += timedelta(days=1)

    if not missing:
        return findings

    score = 2.0 + min(len(missing) / 3.0, 2.5)
    findings.append(
        Finding(
            detector="coverage_gap",
            family="data_integrity",
            date=missing[0],
            severity=_severity(score),
            score=score,
            confidence=0.95,
            observed=len(missing),
            expected=0,
            deviation=f"{len(missing)} hari tanpa data sama sekali",
            narrative=(
                f"{len(missing)} hari kosong total di tengah rentang "
                f"({', '.join(missing[:5])}"
                + (" ..." if len(missing) > 5 else "")
                + "). Nol post bukan berarti sepi — kemungkinan besar data "
                "tidak masuk. Semua rata-rata di periode ini bias ke bawah."
            ),
            evidence=[],
            next_tool="data_health",
            next_args={"start_date": missing[0], "end_date": missing[-1]},
            detail={"missing_dates": missing},
        )
    )
    return findings


@detector("unclassified_surge", "data_integrity", risk_weight=1.2)
def _unclassified_surge(ctx: "ScanContext") -> list[Finding]:
    """
    Porsi post tanpa sentimen melonjak.

    Kalau denominator sentimen berubah diam-diam, seluruh persentase
    sentimen di report jadi bohong.
    """
    findings: list[Finding] = []

    for row in ctx.daily:
        posts = float(row.get("posts") or 0)
        unclassified = float(row.get("unclassified_posts") or 0)
        if posts < ctx.min_posts:
            continue

        share = unclassified / posts if posts else 0.0
        if share < 0.35:
            continue

        score = 1.6 + share * 3.0
        score = min(score, MAX_SCORE)

        findings.append(
            Finding(
                detector="unclassified_surge",
                family="data_integrity",
                date=_date_str(row.get("date")),
                severity=_severity(score),
                score=score,
                confidence=0.9,
                observed=round(share * 100, 1),
                expected=None,
                deviation=f"{share * 100:.0f}% post tanpa label sentimen",
                narrative=(
                    f"{int(unclassified)} dari {int(posts)} post "
                    f"({share * 100:.0f}%) tidak punya label sentimen. "
                    "Persentase sentimen hari ini dihitung dari denominator "
                    "yang tidak mewakili — jangan dipakai sebagai KPI."
                ),
                evidence=[],
                next_tool="validate_metric_readiness",
                next_args={
                    "start_date": _date_str(row.get("date")),
                    "end_date": _date_str(row.get("date")),
                },
                detail={"unclassified_posts": int(unclassified)},
            )
        )
    return findings


# =====================================================================
# Context + orchestration
# =====================================================================

def _evidence_from_day(day: dict[str, Any]) -> list[str]:
    key = day.get("top1_canonical_key")
    return [key] if key else []


@dataclass
class ScanContext:
    """Semua data + parameter yang dibutuhkan detector."""

    daily: list[dict[str, Any]] = field(default_factory=list)
    hourly: list[dict[str, Any]] = field(default_factory=list)
    author_daily: list[dict[str, Any]] = field(default_factory=list)
    duplicate_clusters: list[dict[str, Any]] = field(default_factory=list)
    term_daily: list[dict[str, Any]] = field(default_factory=list)

    # Parameter tuning
    sensitivity: str = "medium"
    window: int = DEFAULT_WINDOW
    min_posts: int = 10
    min_interactions: int = 100
    sustained_days: int = 4
    concentration_threshold: float = 0.45
    divergence_threshold: float = 30.0
    author_flood_threshold: float = 0.30
    noise_threshold: float = 0.20
    trigger_min_posts: int = 3
    burst_min_posts: int = 5
    burst_min_authors: int = 3
    burst_window_minutes: int = 120
    negative_share_min_gap: float = 12.0

    _series_cache: dict[str, Series] = field(default_factory=dict, repr=False)
    day_by_date: dict[str, dict[str, Any]] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self.daily = sorted(self.daily, key=lambda row: _date_str(row.get("date")))
        self.day_by_date = {_date_str(row.get("date")): row for row in self.daily}

    @property
    def z_threshold(self) -> float:
        return SENSITIVITY_Z.get(self.sensitivity, SENSITIVITY_Z["medium"])

    @property
    def min_ratio(self) -> float:
        """Effect-size gate: perubahan harus cukup besar, bukan cuma signifikan."""
        return SENSITIVITY_MIN_RATIO.get(
            self.sensitivity, SENSITIVITY_MIN_RATIO["medium"]
        )

    def series(self, key: str) -> Series:
        if key not in self._series_cache:
            self._series_cache[key] = Series(self.daily, key, window=self.window)
        return self._series_cache[key]

    def has(self, requirement: str) -> bool:
        return bool(getattr(self, requirement, None))


def run_scan(
    ctx: ScanContext,
    families: Iterable[str] | None = None,
    detectors: Iterable[str] | None = None,
) -> dict[str, Any]:
    """
    Jalankan seluruh detector yang relevan.

    Return payload yang SENGAJA tidak report-ready:
    tidak ada report_input_id, tidak bisa disambung ke build_*_ppt_package.
    """
    family_filter = {item.strip().lower() for item in families or [] if item.strip()}
    detector_filter = {item.strip().lower() for item in detectors or [] if item.strip()}

    findings: list[Finding] = []
    skipped: list[dict[str, str]] = []
    executed: list[str] = []

    for name, spec in DETECTORS.items():
        if family_filter and spec["family"] not in family_filter:
            continue
        if detector_filter and name not in detector_filter:
            continue

        missing = [need for need in spec["needs"] if not ctx.has(need)]
        if missing:
            skipped.append(
                {
                    "detector": name,
                    "reason": f"data tidak tersedia: {', '.join(missing)}",
                }
            )
            continue

        try:
            results = spec["func"](ctx) or []
        except Exception as error:  # pragma: no cover - defensive
            skipped.append({"detector": name, "reason": f"error: {error}"})
            continue

        executed.append(name)
        for item in results:
            # Risk weight diterapkan pada strength (uncapped) untuk ranking,
            # sementara score di-cap untuk severity band + tampilan.
            weighted = item.score * spec["risk_weight"]
            item.strength = weighted
            item.score = min(weighted, MAX_SCORE)
            item.severity = _severity(item.score)
            findings.append(item)

    findings.sort(key=lambda item: (item.strength, item.confidence), reverse=True)

    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for item in findings:
        counts[item.severity] = counts.get(item.severity, 0) + 1

    return {
        "findings": [item.to_dict() for item in findings],
        "summary": {
            "total_findings": len(findings),
            "by_severity": counts,
            "by_family": _count_by(findings, "family"),
            "detectors_run": executed,
            "detectors_skipped": skipped,
        },
        "baseline": {
            "method": "rolling median + MAD (trailing, exclusive)",
            "window_days": ctx.window,
            "min_baseline_days": MIN_BASELINE_DAYS,
            "sensitivity": ctx.sensitivity,
            "z_threshold": ctx.z_threshold,
            "day_of_week_adjusted": len(ctx.daily) >= DEFAULT_WINDOW,
            "days_analysed": len(ctx.daily),
        },
        "guardrail": (
            "Output ini untuk monitoring/eksplorasi, BUKAN bahan deck. "
            "Kalau mau dijadikan report, mulai ulang dari get_report_guide() "
            "dan Intent Confirmation."
        ),
    }


def _count_by(findings: list[Finding], attribute: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in findings:
        key = getattr(item, attribute)
        counts[key] = counts.get(key, 0) + 1
    return counts


def list_detectors() -> list[dict[str, Any]]:
    """Katalog detector, untuk dokumentasi / debugging."""
    return [
        {
            "name": spec["name"],
            "family": spec["family"],
            "risk_weight": spec["risk_weight"],
            "requires": list(spec["needs"]),
            "doc": (spec["func"].__doc__ or "").strip().split("\n")[0],
        }
        for spec in DETECTORS.values()
    ]
