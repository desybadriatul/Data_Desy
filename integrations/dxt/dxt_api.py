from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Union
import os

DXT_APP_CODE = os.environ.get("DXT_APP_CODE", "")
DXT_PASS_CODE = os.environ.get("DXT_PASS_CODE", "")
DXT_BASE_URL = os.environ.get("DXT_BASE_URL", "https://apigw.dxt360.app/stopgap-sonar-dataops")
import time
import threading
import httpx

import logging

logger = logging.getLogger(__name__)


APP_CODE = DXT_APP_CODE
BASE_URL = DXT_BASE_URL
LOGIN_PATH = "/login"
RAWDATA_PATH = "/all-data"
CAMPAIGN_PATH = "/campaign"
INJECT_PATH = "/inject"
TAG_PATH = "/tag"
UPDATE_ENGAGEMENT_PATH = "/update_engagement"
PASS_KEY = DXT_PASS_CODE


class Channel:
    Twitter: int = 1
    Facebook: int = 2
    OnlineMedia: int = 3
    Forum: int = 4
    Blog: int = 5
    Instagram: int = 6
    Youtube: int = 7
    PrintedMedia: int = 8
    Radio: int = 9
    TV: int = 10
    Tiktok: int = 11


CHANNEL_MAPPING = {
    1: "Twitter",
    2: "Facebook",
    3: "OnlineMedia",
    4: "Forum",
    5: "Blog",
    6: "Instagram",
    7: "Youtube",
    8: "PrintedMedia",
    9: "Radio",
    10: "TV",
    11: "Tiktok",
}

CHANNEL_MAPPING_STR = {v.lower(): k for k, v in CHANNEL_MAPPING.items()}

# Per-channel valid `engagements` field names for update_engagement().
# Reference only — NOT enforced by update_engagement(). Note TikTok uses the
# SINGULAR `num_share_l`, while Facebook uses the PLURAL `num_shares_l`.
ENGAGEMENT_FIELDS: Dict[int, List[str]] = {
    Channel.Twitter: ["num_replies_l", "num_rts_l"],
    Channel.Facebook: ["num_likes_l", "num_shares_l", "num_comments_l"],
    Channel.Instagram: ["num_likes_l", "num_comments_l", "num_views_l"],
    Channel.Youtube: ["num_likes_l", "num_comments_l", "num_views_l"],
    Channel.Tiktok: ["num_likes_l", "num_share_l", "num_comments_l", "num_views_l"],
}

CLIENTS: Dict[str, Dict[str, Union[str, int, None]]] = {
    "LeMinerale": {"email": "dopslemin@sonar.id", "passwd": PASS_KEY, "token": ""},
    "Bluebird": {"email": "dopsbluebird@sonar.id", "passwd": PASS_KEY, "token": ""},
    "Blackpink": {"email": "dopsblackpink@sonar.id", "passwd": PASS_KEY, "token": ""},
    "Timah": {"email": "dopstimah@sonar.id", "passwd": PASS_KEY, "token": ""},
    "Diskominfo": {"email": "dopsdiskominfo@sonar.id", "passwd": PASS_KEY, "token": ""},
    "Combiphar": {"email": "dopscombiphar@sonar.id", "passwd": PASS_KEY, "token": ""},
    "Nojorono": {"email": "dopsnojorono@sonar.id", "passwd": PASS_KEY, "token": ""},
    "Wisdom": {"email": "dopswisdom@sonar.id", "passwd": PASS_KEY, "token": ""},
    "Nipis Madu": {"email": "dopsnipis@sonar.id", "passwd": PASS_KEY, "token": ""},
    "BKP": {"email": "dopsbkp@sonar.id", "passwd": PASS_KEY, "token": ""},
    "Tokocrypto": {"email": "dopstokocrypto@sonar.id", "passwd": PASS_KEY, "token": ""},
    "Kementrian PU": {"email": "dopspu@sonar.id", "passwd": PASS_KEY, "token": ""},
    "Sasa": {"email": "dopssasa@sonar.id", "passwd": PASS_KEY, "token": ""},
    "Kaltimtara": {"email": "dopskaltim@sonar.id", "passwd": PASS_KEY, "token": ""},
    "HC3": {"email": "dopsahm@sonar.id", "passwd": PASS_KEY, "token": ""},
    "AHM": {"email": "dopsahmrisk@sonar.id", "passwd": PASS_KEY, "token": ""},
    "Pintu": {"email": "dopspintu@sonar.id", "passwd": PASS_KEY, "token": ""},
    "CFX": {"email": "dopscfx@sonar.id", "passwd": PASS_KEY, "token": ""},
    "VML": {"email": "dopsvml@sonar.id", "passwd": PASS_KEY, "token": ""},
    "Imip": {"email": "dopsimip@sonar.id", "passwd": PASS_KEY, "token": ""},
    "Gopay": {"email": "dopsgopay@sonar.id", "passwd": PASS_KEY, "token": ""},
    "DPRD Jateng": {"email": "dopsdprdjateng@sonar.id", "passwd": PASS_KEY, "token": ""},
    "Telkomsel": {"email": "dopstelkomsel@sonar.id", "passwd": PASS_KEY, "token": ""},
    "DFI": {"email": "dopsdfiretail@sonar.id", "passwd": PASS_KEY, "token": ""},
}

_TOKEN_CACHE: Dict[str, Dict[str, Optional[Union[str, int]]]] = {}
_LOGIN_LOCKS: Dict[str, threading.Lock] = {}
_API_INSTANCES: Dict[str, "DxtApi"] = {}


@dataclass
class Account:
    """
    Mutable account state container.

    Parameters
    ----------
    email : str
        Login email.
    passwd : str
        Login password.
    token : str | None
        Access token (may be updated at runtime).
    expires_on : int | None
        Token expiry as epoch seconds (None if unknown).
    """

    email: str
    passwd: str
    token: Optional[str] = None
    expires_on: Optional[int] = None

    def __str__(self) -> str:
        return f'<Account {self.email}: token={"set" if self.token else "unset"} expires_on={self.expires_on}>'

    __repr__ = __str__


class DxtApi:
    """
    Synchronous client for the DXT API with token caching, retry/backoff, and safe re-login.

    Notes
    -----
    - Token state is cached per client name in `_TOKEN_CACHE`. New instances will
      reuse cached tokens automatically.
    - A threading.Lock is used per client to avoid concurrent login attempts.
    """

    def __init__(
        self,
        client: str,
        timeout: float = 60.0,
        max_retries: int = 5,
        backoff_factor: float = 0.5,
    ) -> None:
        """
        Initialize DxtApi.

        Parameters
        ----------
        client : str
            Client name as key in `CLIENTS` mapping.
        timeout : float
            Per-request timeout seconds.
        max_retries : int
            Maximum retry attempts for transient errors.
        backoff_factor : float
            Base backoff factor (seconds) used with exponential backoff.
        """
        if client not in CLIENTS:
            raise ValueError(f"Unknown client '{client}'")

        raw = CLIENTS[client]
        self.project_name: str = client
        self.account: Account = Account(
            email=str(raw.get("email", "")),
            passwd=str(raw.get("passwd", "")),
            token=raw.get("token") or None,
            expires_on=_normalize_epoch(raw.get("expires_on")),
        )

        self.base_url = BASE_URL
        self.app_code = APP_CODE
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        self._token: Optional[str] = self.account.token
        self._expires_on: Optional[int] = self.account.expires_on
        self._client: Optional[httpx.Client] = None

        # per-client thread lock for login to avoid concurrent logins
        self._login_lock = _LOGIN_LOCKS.setdefault(self.project_name, threading.Lock())

        # persist initial token into runtime cache so other instances can reuse
        _TOKEN_CACHE.setdefault(
            self.project_name, {"token": self._token, "expires_on": self._expires_on}
        )

        self._default_headers: Dict[str, str] = {"X-Apig-AppCode": self.app_code}
        if self._token:
            self._default_headers["access-token"] = self._token

    def _get_client(self) -> httpx.Client:
        """
        Return a Client instance, re-creating if closed.

        Returns
        -------
        httpx.Client
            The HTTP client for sending requests.
        """
        if self._client is None or getattr(self._client, "is_closed", False):
            timeout = httpx.Timeout(self.timeout)
            self._client = httpx.Client(timeout=timeout)
        return self._client

    def close(self) -> None:
        """
        Close the underlying HTTP client.
        """
        if self._client:
            self._client.close()
            self._client = None

    def login(self) -> "DxtApi":
        """
        Perform login and update token state.

        Returns
        -------
        DxtApi
            The same instance after login.
        """
        with self._login_lock:
            cached = _TOKEN_CACHE.get(self.project_name, {})
            cached_token = cached.get("token")
            cached_expires = cached.get("expires_on")
            if cached_token and cached_expires and not _is_expired(cached_expires):
                self._token = cached_token
                self._expires_on = cached_expires
                self._default_headers["access-token"] = self._token
                logger.debug(f"[{self.account}] Reused cached token (no login needed).")
                return self

            client = self._get_client()
            auth = httpx.BasicAuth(self.account.email, self.account.passwd)
            headers = dict(self._default_headers)
            try:
                resp = client.post(
                    f"{self.base_url}{LOGIN_PATH}", headers=headers, auth=auth
                )
            except Exception as exc:
                logger.exception(f"[{self.account}] Login transport error: {exc}")
                raise

            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError:
                body = _safe_text(resp)
                logger.exception(
                    f"[{self.account}] Login failed: status={resp.status_code} body={body}"
                )
                raise

            data = _safe_json(resp)
            token = data.get("token")
            expires_on_raw = data.get("expires_on")

            if not token:
                logger.exception(
                    f"[{self.account}] Login response missing token: {data}"
                )
                raise RuntimeError("Login did not return token")

            expires_on = _normalize_epoch(expires_on_raw)

            self._token = token
            self._expires_on = expires_on
            self.account.token = token
            self.account.expires_on = expires_on
            self._default_headers["access-token"] = token
            _TOKEN_CACHE[self.project_name] = {"token": token, "expires_on": expires_on}

            try:
                CLIENTS[self.project_name]["token"] = token
                CLIENTS[self.project_name]["expires_on"] = expires_on
            except Exception:
                logger.debug(
                    "Failed to write-back to module-level client dict (non-fatal)"
                )

            logger.info(
                f"[{self.account}] Login successful (expires_on={self._expires_on})"
            )
            return self

    def _ensure_token(self) -> None:
        """
        Ensure a valid token exists for this client. Re-login if missing or expired.
        """
        cached = _TOKEN_CACHE.get(self.project_name, {})
        cached_token = cached.get("token")
        cached_expires = cached.get("expires_on")
        if cached_token and cached_expires and not _is_expired(cached_expires):
            self._token = cached_token
            self._expires_on = cached_expires
            self._default_headers["access-token"] = self._token
            return

        self.login()

    def _request_with_retry(
        self,
        method: str,
        path: str,
        *,
        json: Optional[dict] = None,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> httpx.Response:
        """
        Make a request with retry/backoff and automatic re-login on 401.

        Parameters
        ----------
        method : str
            HTTP method (GET, POST, etc.).
        path : str
            Request path (should start with '/').
        json : dict | None
            JSON body to send.
        params : dict | None
            Query params.
        headers : dict | None
            Additional headers to merge on top of defaults.

        Returns
        -------
        httpx.Response
            The final response object.
        """
        self._ensure_token()
        url = f"{self.base_url}{path}"
        client = self._get_client()
        merged_headers = {**self._default_headers, **(headers or {})}
        attempt = 0
        retried_after_login = False

        while True:
            attempt += 1
            try:
                resp = client.request(
                    method, url, json=json, params=params, headers=merged_headers
                )
            except (
                httpx.TransportError,
                httpx.ReadTimeout,
                httpx.ConnectTimeout,
            ) as exc:
                logger.warning(
                    f"Transport error on {url}: {exc} (attempt {attempt}/{self.max_retries})"
                )
                if attempt >= self.max_retries:
                    logger.exception(f"Exceeded max retries for {url}")
                    raise
                time.sleep(self.backoff_factor * (2 ** (attempt - 1)))
                continue

            if resp.status_code == 401 and not retried_after_login:
                retried_after_login = True
                try:
                    self.login()
                    merged_headers = {**self._default_headers, **(headers or {})}
                    continue
                except Exception as exc:
                    logger.exception(f"Re-login failed after 401: {exc}")
                    return resp

            if resp.status_code == 429 and attempt < self.max_retries:
                retry_after = resp.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait = float(retry_after)
                    except (ValueError, TypeError):
                        wait = self.backoff_factor * (2 ** (attempt - 1))
                else:
                    wait = max(2.0, self.backoff_factor * (2 ** (attempt - 1)))
                logger.warning(
                    f"Rate limited (429) on {url}, waiting {wait:.1f}s (attempt {attempt}/{self.max_retries})"
                )
                time.sleep(wait)
                continue

            if 500 <= resp.status_code < 600 and attempt < self.max_retries:
                logger.warning(
                    f"Server error {resp.status_code} on {url} (attempt {attempt}/{self.max_retries})"
                )
                time.sleep(self.backoff_factor * (2 ** (attempt - 1)))
                continue

            return resp

    def get_campaigns_name(self, campaign_ids: Union[List[int], Set[int]]) -> List[Any]:
        """
        Fetch campaign names for given campaign IDs.

        Parameters
        ----------
        campaign_ids : list[int] | set[int]
            Campaign IDs to fetch.

        Returns
        -------
        list
            `data_list` as returned by the API.

        Raises
        ------
        httpx.HTTPStatusError
            If the request returns a non-2xx response.
        ValueError
            If response JSON is malformed.
        """
        self._ensure_token()
        params = {"campaign_ids": ",".join(map(str, campaign_ids))}
        resp = self._request_with_retry(
            "GET", CAMPAIGN_PATH, headers=None, params=params
        )
        resp.raise_for_status()
        data = _safe_json(resp)
        return data.get("data_list", [])

    def get_campaigns(self) -> Dict[str, Any]:
        """
        Fetch campaigns metadata.

        Returns
        -------
        dict
            Parsed JSON response.

        Raises
        ------
        httpx.HTTPStatusError
            If the request returns a non-2xx response.
        ValueError
            If response JSON is malformed.
        """
        self._ensure_token()
        resp = self._request_with_retry("GET", CAMPAIGN_PATH, headers=None)
        resp.raise_for_status()
        return _safe_json(resp)

    def get_inject_status(self, job_id: str) -> Dict[str, Any]:
        self._ensure_token()
        params = {"job_id": job_id}
        resp = self._request_with_retry("GET", INJECT_PATH, headers=None, params=params)
        resp.raise_for_status()
        return _safe_json(resp)

    def get_tag(self, campaign_id: str):
        self._ensure_token()
        params = {"campaign_id": campaign_id}
        resp = self._request_with_retry("GET", TAG_PATH, headers=None, params=params)
        resp.raise_for_status()
        return _safe_json(resp)

    def inject(self, channel_id: int, posts_payload: List[Dict[str, Any]]) -> bool:
        self._ensure_token()
        payload = {"channel": channel_id, "posts": posts_payload}

        resp = self._request_with_retry("POST", INJECT_PATH, json=payload, headers=None)
        data_json = _safe_json(resp)
        return data_json

    def update_engagement(
        self, channel_id: int, data_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Update engagement metrics for posts on a single channel.

        Parameters
        ----------
        channel_id : int
            DXT channel id (see `Channel`).
        data_list : list[dict]
            Items shaped ``{"object_id": str, "engagements": {<field>: int, ...}}``.
            Valid ``engagements`` field names per channel are in
            `ENGAGEMENT_FIELDS` (note TikTok's singular ``num_share_l``).

        Returns
        -------
        dict
            Parsed JSON body. On success: ``{"updated_posts": [...]}``. On a
            failure status the body is returned as-is (e.g.
            ``{"status": "Failed", "error_message": ...}``) — this mirrors
            `inject()` and does not raise on non-2xx.
        """
        self._ensure_token()
        payload = {"channel_id": channel_id, "data_list": data_list}
        resp = self._request_with_retry(
            "POST", UPDATE_ENGAGEMENT_PATH, json=payload, headers=None
        )
        return _safe_json(resp)

    def fetch_rawdata(
        self,
        start_date: int,
        end_date: int,
        campaign_ids: List[int],
        query: str = "",
        channel_ids: Optional[List[Union[int, str]]] = None,
    ) -> List[dict]:
        """
        Stream/fetch raw data using token pagination.

        Parameters
        ----------
        start_date : int
            Start timestamp in epoch seconds.
        end_date : int
            End timestamp in epoch seconds.
        campaign_ids : list[int]
            Campaign IDs.
        query : str
            Specific rule for raw data.
        channel_ids : list[int | str] | None
            Optional list of channel id to filter (e.g. [1, 2]). Default is [0] which means all channels.
        Returns
        -------
        list[dict]
            Accumulated data list from paginated results.
        """
        self._ensure_token()
        if channel_ids is None:
            channel_ids = [0]
        campaign_list = list(map(str, campaign_ids))
        campaign_csv = ",".join(campaign_list)
        start_ts = int(start_date)
        end_ts = int(end_date)
        results: List[dict] = []

        logger.info(
            f"[{self.account}] Fetching raw data {start_date}->{end_date} for {campaign_list}"
        )

        for ch in channel_ids:
            token: Optional[str] = None
            channel_count = 0
            print(f"[{self.account}] Fetching channel {ch}...")
            while True:
                payload = {
                    "token": token or "*",
                    "start_ts": start_ts,
                    "end_ts": end_ts,
                    "limit": 100,
                    "channel": str(ch),
                    "query": query,
                    "campaign_ids": campaign_csv,
                }

                resp = self._request_with_retry(
                    "POST", RAWDATA_PATH, json=payload, headers=None
                )
                try:
                    resp.raise_for_status()
                except httpx.HTTPStatusError:
                    body = _safe_text(resp)
                    logger.warning(
                        f"[{self.account}] Request failed: status={resp.status_code} -> {body}"
                    )
                    break

                try:
                    data_json = _safe_json(resp)
                except ValueError:
                    logger.warning(
                        f"[{self.account}] Response not JSON: status={getattr(resp, 'status_code', 'N/A')}"
                    )
                    break

                status = data_json.get("status")
                total = data_json.get("total", 0)
                data_list = data_json.get("data_list", [])

                if not data_list:
                    break

                if status == "OK" and total > 0:
                    results.extend(data_list)
                    channel_count += len(data_list)
                    token = data_json.get("next_token")
                    if not token:
                        break
                    time.sleep(0.1)
                    continue
                else:
                    logger.warning(
                        f"[{self.account}] No more data or unexpected response: {data_json}"
                    )
                    break

            print(
                f"[{self.account}] Finished channel {ch}: {channel_count} records (running total {len(results)})"
            )

        print(f"[{self.account}] Fetched {len(results)} raw data items")
        return results


def get_dxt_api(client: str, **kwargs) -> DxtApi:
    """
    Return a cached DxtApi instance for the given client (singleton per client).

    Parameters
    ----------
    client : str
        Project name.
    **kwargs :
        Passed to DxtApi constructor on first creation.

    Returns
    -------
    DxtApi
        Shared instance for the client.
    """
    if client not in _API_INSTANCES:
        _API_INSTANCES[client] = DxtApi(client, **kwargs)
    return _API_INSTANCES[client]


def _normalize_epoch(value: Optional[Union[str, int, float]]) -> Optional[int]:
    """
    Normalize epoch timestamp to seconds (int) when possible.

    Parameters
    ----------
    value : str | int | float | None
        Raw epoch (may be milliseconds) or None.

    Returns
    -------
    int | None
        Normalized epoch seconds or None.
    """
    if value is None or value == "":
        return None
    try:
        iv = int(value)
    except Exception:
        return None

    if iv > 10**12:
        return int(iv / 1000)
    return iv


def _is_expired(expires_on: Optional[int]) -> bool:
    """
    Determine whether an epoch seconds timestamp is expired relative to now.

    Parameters
    ----------
    expires_on : int | None
        Epoch seconds or None.

    Returns
    -------
    bool
        True if expired or unknown.
    """
    if expires_on is None:
        return True

    now = int(datetime.now(timezone.utc).timestamp())
    return expires_on <= now


def _safe_text(resp: httpx.Response) -> str:
    """
    Safely get text from httpx.Response.

    Parameters
    ----------
    resp : httpx.Response
        Response object.

    Returns
    -------
    str
        Response text or '<unreadable>'.
    """
    try:
        return resp.text
    except Exception:
        return "<unreadable>"


def _safe_json(resp: httpx.Response) -> Dict[str, Any]:
    """
    Safely parse response JSON, raising ValueError if invalid.

    Parameters
    ----------
    resp : httpx.Response
        Response object.

    Returns
    -------
    dict
        Parsed JSON.
    """
    try:
        return resp.json()
    except ValueError as exc:
        logger.exception(f"Failed to parse JSON response: {exc}")
        raise
