-- =====================================================================
-- COGAN DATABASE SCHEMA (PostgreSQL)
-- =====================================================================
-- Model data:
--   * Satu CAMPAIGN dianggap satu "klien".
--   * Satu POST (postingan) bisa masuk ke BEBERAPA campaign sekaligus
--     (di kolom Campaigns dipisah koma). Ini hubungan "banyak-ke-banyak".
--   * Kolom yang dipakai tool diangkat jadi kolom rapi; SELURUH kolom
--     asli tetap disimpan utuh di kolom `raw` (JSONB) -> tidak ada yang
--     hilang, dan format apapun tetap muat.
--
-- Aman dijalankan berulang (semua IF NOT EXISTS).
-- =====================================================================

-- 1. campaigns -> daftar campaign/klien (mis. "Aqua", "KDM Sidak Pabrik Air")
CREATE TABLE IF NOT EXISTS campaigns (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,            -- nama tampilan apa adanya
    name_norm   TEXT NOT NULL UNIQUE,     -- versi huruf kecil & rapi (buat cari & cegah duplikat)
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. posts -> data mentah monitoring (jutaan baris). TIDAK menyimpan
--    campaign di sini; keanggotaan campaign ada di tabel post_campaigns.
CREATE TABLE IF NOT EXISTS posts (
    id              BIGSERIAL PRIMARY KEY,
    source_no       BIGINT,
    post_date       TIMESTAMPTZ,
    channel         TEXT,
    author          TEXT,
    title           TEXT,
    content         TEXT,
    sentiment       TEXT,                 -- selalu huruf kecil: positive/negative/neutral
    engagement      DOUBLE PRECISION,
    potential_reach DOUBLE PRECISION,
    url             TEXT,
    raw             JSONB NOT NULL DEFAULT '{}'::jsonb,
    loaded_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_posts_date    ON posts (post_date);
CREATE INDEX IF NOT EXISTS idx_posts_channel ON posts (channel);
CREATE INDEX IF NOT EXISTS idx_posts_fts
    ON posts USING GIN (to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(content,'')));

-- 3. post_campaigns -> jembatan: post mana milik campaign mana
--    (satu post bisa punya banyak baris di sini = masuk banyak campaign).
CREATE TABLE IF NOT EXISTS post_campaigns (
    post_id     BIGINT  NOT NULL REFERENCES posts(id)     ON DELETE CASCADE,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    PRIMARY KEY (post_id, campaign_id)
);
-- index kunci untuk "ambil semua post campaign X":
CREATE INDEX IF NOT EXISTS idx_pc_campaign ON post_campaigns (campaign_id, post_id);

-- 4. campaign_guidance -> panduan wordcloud per campaign (opsional)
CREATE TABLE IF NOT EXISTS campaign_guidance (
    campaign_id INTEGER PRIMARY KEY REFERENCES campaigns(id) ON DELETE CASCADE,
    guidance    JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5. generated_outputs -> histori semua hasil (wordcloud/report/sentiment/dll)
CREATE TABLE IF NOT EXISTS generated_outputs (
    id           BIGSERIAL PRIMARY KEY,
    campaign_id  INTEGER REFERENCES campaigns(id) ON DELETE SET NULL,
    kind         TEXT NOT NULL,           -- 'wordcloud', 'weekly_report', dst
    params       JSONB NOT NULL DEFAULT '{}'::jsonb,
    result       JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_outputs_campaign_kind
    ON generated_outputs (campaign_id, kind, created_at DESC);
