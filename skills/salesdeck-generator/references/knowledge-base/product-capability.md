<!-- Source: REF-04_DATAXET_Product_Feature_Capability.docx -->
# DATAXET:SONAR — Product & Feature Capability (REF-04)

Approved single source of truth for what Sonar can and cannot do. Consult before stating any capability. Honour every 'Do not claim' line.

---

DATAXET:SONAR
Product & Feature Capability Repository
Detail limitasi produk/fitur Sonar

# 1. Tujuan Dokumen
Dokumen ini menjadi single source of truth untuk menjelaskan produk dan fitur Dataxet Sonar. Format ini dirancang agar mudah dibaca manusia sekaligus mudah dikonsumsi oleh LLM/prompt automation.

| Pipeline | Bagian Capability yang Paling Dipakai |
| --- | --- |
| Pre-Sales Generator | Deskripsi, business problem, use case, kapabilitas, limitasi. |
| Sales Deck Generator | Deskripsi, business problem, use case, kapabilitas, insight/value proposition. |
| Onboarding Generator | Kapabilitas, output, data source, requirement/dependency, limitasi. |
| Deliverable Generator | Output, data source, requirement, KPI, report/alert capability. |
| Report Generator | Data source, KPI, insight yang bisa dihasilkan, limitation. |
| Insight Automation | KPI, insight, alert/report logic, data limitation. |


# 2. Ringkasan Produk/Fitur yang Dicakup

| No | Group | Produk/Fitur | Sumber Utama |
| --- | --- | --- | --- |
| 1 | A. Core Products | DXT360 Platform | S1 p.1-17; S2 p.5-10 |
| 2 | A. Core Products | DXT360 Analytics Platform | S1 p.2-17, p.51-83; S2 p.9-10 |
| 3 | A. Core Products | DXT360 TrendWatch / Viral Meter | S1 p.1; S2 p.12-14 |
| 4 | A. Core Products | DXT360 Social Media Management | S1 p.1; S2 p.12 |
| 5 | B. Analytics Workflow & Data Management Modules | Campaign Library / Campaign Setup | S1 p.3-4, p.97-99; S2 p.10 |
| 6 | B. Analytics Workflow & Data Management Modules | Dashboard Library | S1 p.4-5, p.55-60 |
| 7 | B. Analytics Workflow & Data Management Modules | Widget Library | S1 p.5, p.17-51, p.55-60 |
| 8 | B. Analytics Workflow & Data Management Modules | Insight Report Library | S1 p.6; S2 p.5 |
| 9 | B. Analytics Workflow & Data Management Modules | Theme Library / Custom Report | S1 p.7, p.79-83, p.99-106 |
| 10 | B. Analytics Workflow & Data Management Modules | Tags & Label Management | S1 p.8, p.51-55, p.61-72 |
| 11 | B. Analytics Workflow & Data Management Modules | My Data Workspace | S1 p.61-72 |
| 12 | B. Analytics Workflow & Data Management Modules | Raw Data Export | S1 p.66-83, p.106-107 |
| 13 | B. Analytics Workflow & Data Management Modules | Dashboard Label Filter | S1 p.51-55 |
| 14 | C. AI, Automation & Alerting | AI Insight Summary | S1 p.83-99 |
| 15 | C. AI, Automation & Alerting | AI Report | S1 p.99-106 |
| 16 | C. AI, Automation & Alerting | Smart Alert / Advanced Alert | S1 p.107-123; S2 p.15, p.19-20 |
| 17 | C. AI, Automation & Alerting | Daily Email Digest / Automated Alert Delivery | S1 p.79-83, p.99-123; S2 p.12-15, p.19-20 |
| 18 | D. Research & Service Offerings | Custom Analyst Report / Insight Report | S2 p.5, p.12-15, p.18-20; S1 p.6-7 |
| 19 | D. Research & Service Offerings | Managed Services | S2 p.10, p.20 |
| 20 | D. Research & Service Offerings | EVO Consultancy Report | S2 p.12, p.14-15 |
| 21 | D. Research & Service Offerings | Deep Social Search Feature | S2 p.13-14 |
| 22 | D. Research & Service Offerings | Sonar Influence | S2 p.12, p.18 |
| 23 | D. Research & Service Offerings | Marketplace Analytics / E-commerce Analysis | S2 p.13, p.18 |
| 24 | D. Research & Service Offerings | Mainstream Media Services / Media Monitoring Report | S1 p.14-17, p.30-34, p.47-49; S2 p.13 |
| 25 | D. Research & Service Offerings | Crisis Investigation Report | S2 p.15, p.19-20; S1 p.107-123 |
| 26 | D. Research & Service Offerings | Audience Profiling & Persona Report | S1 p.34-41, p.89-97; S2 p.12 |
| 27 | E. Dashboard Widgets | Trend Analysis Widget | S1 p.17-19 |
| 28 | E. Dashboard Widgets | Sentiment Overview Widget | S1 p.20-22, p.65-69 |
| 29 | E. Dashboard Widgets | Top Authors Widget | S1 p.22-23 |
| 30 | E. Dashboard Widgets | Top Words Widget | S1 p.23-25 |
| 31 | E. Dashboard Widgets | Top Hashtags Widget | S1 p.25-28 |
| 32 | E. Dashboard Widgets | Social Media Distribution Widget | S1 p.28-30 |
| 33 | E. Dashboard Widgets | Mainstream Media Distribution Widget | S1 p.30-32 |
| 34 | E. Dashboard Widgets | Mentions Widget | S1 p.32-34 |
| 35 | E. Dashboard Widgets | Gender Widget | S1 p.34-36 |
| 36 | E. Dashboard Widgets | Locations Widget | S1 p.36-38 |
| 37 | E. Dashboard Widgets | Peak Hours Widget | S1 p.38-39 |
| 38 | E. Dashboard Widgets | Interest Widget | S1 p.39-41 |
| 39 | E. Dashboard Widgets | Spokespersons Widget | S1 p.41-42 |
| 40 | E. Dashboard Widgets | Topic Overview Widget | S1 p.43-45 |
| 41 | E. Dashboard Widgets | Sentence Type Widget | S1 p.45-47 |
| 42 | E. Dashboard Widgets | Media Value Widget | S1 p.47-49 |
| 43 | E. Dashboard Widgets | Competitive Analysis / Share of Voice Widget | S1 p.49-51 |


# 3. Product & Feature Capability Detail

# A. Core Products

## 1. DXT360 Platform
Sumber utama: S1 p.1-17; S2 p.5-10

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | DXT360 Platform |
| 2. Deskripsi Singkat | Umbrella platform media intelligence terintegrasi untuk mengakses percakapan media, metrik digital, dan riset dalam satu environment. Platform terdiri dari Analytics, TrendWatch, dan Social Media Management. |
| 3. Business Problem yang Diselesaikan | Silo data lintas media; proses monitoring manual; sulit menyatukan social, online, mainstream, dan reporting; sulit membangun insight cepat dari big data. |
| 4. Use Case / Scenario | Enterprise media intelligence, brand monitoring, competitor monitoring, PR/media monitoring, campaign tracking, crisis monitoring, research workflow, dan automated reporting. |
| 5. Kapabilitas | Integrated data collection, indexing/search, dashboard, widget, raw data, report library, alert, AI/NLP processing, multilingual support, multi-project setup. |
| 6. Output yang Dihasilkan | Dashboard, raw data export, automated/custom reports, AI reports, alert, insight reports, API/managed services jika dikonfigurasi. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Social: X/Twitter, Facebook, Instagram, YouTube, TikTok. Digital/Mainstream: Online Media, Blog, Forum. Traditional: Printed Media, TV, Radio. Tambahan dari sales deck: Google/other social management channels, marketplace/e-commerce, magazines/broadcast TV, dan data partnership jika tersedia. Data field utama: Content/post, author/account, timestamp, URL, channel/source, campaign/tag/label, sentiment, topic/sentence type jika aktif, engagement metrics seperti likes, comments/replies, shares/retweets/quotes, views, reach/potential reach. Article/title/content, media name/source, publish date, URL, media type, sentiment, spokesperson jika terdeteksi, ad value, PR value, page rank, monthly pageview, unique visitors, country rank, circulation/duration sesuai channel. |
| 8. Requirement / Dependency | Keyword/account setup, campaign/tag/label structure, source activation, dashboard/report configuration, user role/access, dan validasi kebutuhan client. |
| 9. KPI yang Bisa Dijawab | Mention/buzz, engagement, reach/potential reach, sentiment, SOV/competitive metrics, media value, pageview/UV, distribution by channel/source, top topic/hashtag/author. |
| 10. Insight yang Bisa Dihasilkan | Brand health, reputation movement, competitor positioning, campaign effectiveness, issue escalation, audience/channel performance, media exposure value. |
| 11. Limitasi Produk/Fitur | - Data hanya mencakup sumber publik, sumber berizin, atau sumber yang sudah masuk coverage/provider Sonar; private account, private group, closed community, DM/inbox, dan data internal platform tidak boleh dijanjikan. - Coverage multi-channel tidak berarti semua field tersedia penuh di semua channel. Likes, comments, shares, views, reach, pageview, PR value, ad value, spokesperson, demographic, dan topic bisa berbeda per source. - Data dapat mengalami delay karena proses collection, filtering, indexing, ingestion, API limit, source availability, external provider, atau volume pemrosesan yang tinggi. - Akurasi output sangat bergantung pada keyword, account, source, tag, label, date range, dan filter yang dikonfigurasi saat campaign/dashboard/report dibuat. - Output AI/NLP seperti sentiment, topic, sentence type, demographic inference, dan summary perlu validasi manusia, terutama untuk isu reputasi, politik, hukum, krisis, dan konteks lokal. - Sonar tidak otomatis menjawab revenue, conversion, market share aktual, churn, atau data bisnis internal klien kecuali ada integrasi data tambahan yang disepakati. - Do not claim: Sonar membaca seluruh internet, memiliki data private/non-public, atau memberikan insight final tanpa konteks dan validasi manusia. |


## 2. DXT360 Analytics
Sumber utama: S1 p.2-17, p.51-83; S2 p.9-10

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | DXT360 Analytics |
| 2. Deskripsi Singkat | Produk analytics untuk mengintegrasikan mainstream, traditional, online, dan social media analysis dalam satu platform agar tim dapat mengambil keputusan komunikasi dan bisnis berbasis data. |
| 3. Business Problem yang Diselesaikan | Tim harus berpindah-pindah tools, sulit memfilter data real-time, dashboard tidak konsisten, dan laporan membutuhkan banyak kerja manual. |
| 4. Use Case / Scenario | Brand perception analysis, audience listening, campaign performance, benchmarking, media monitoring, issue tracking, market/industry monitoring, brand health, crisis investigation. |
| 5. Kapabilitas | Campaign setup, dashboard customization, widget-based analysis, real-time filtering, multi-dashboard, multi-project, raw data export, AI/report module, sentiment/topic/author/media metrics. |
| 6. Output yang Dihasilkan | Customizable dashboard, widget visualizations, My Data feed, raw data default/pivot, PDF/image/widget/dashboard export, AI/analyst reports. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Social: X/Twitter, Facebook, Instagram, YouTube, TikTok. Digital/Mainstream: Online Media, Blog, Forum. Traditional: Printed Media, TV, Radio. Tambahan dari sales deck: Google/other social management channels, marketplace/e-commerce, magazines/broadcast TV, dan data partnership jika tersedia. Data field utama: Content/post, author/account, timestamp, URL, channel/source, campaign/tag/label, sentiment, topic/sentence type jika aktif, engagement metrics seperti likes, comments/replies, shares/retweets/quotes, views, reach/potential reach. Article/title/content, media name/source, publish date, URL, media type, sentiment, spokesperson jika terdeteksi, ad value, PR value, page rank, monthly pageview, unique visitors, country rank, circulation/duration sesuai channel. |
| 8. Requirement / Dependency | Campaign keyword/account, selected sources, date range, tag/label taxonomy, dashboard template/widget selection, user access, and report objective. |
| 9. KPI yang Bisa Dijawab | Buzz/mentions, posts/articles, engagement, likes, comments, shares, views, potential reach, sentiment, topic, SOV, media value, article volume, authors, location/demographic proxies. |
| 10. Insight yang Bisa Dihasilkan | Channel performance, perception driver, emerging issue, competitive gap, campaign impact, content resonance, spokesperson/media influence, audience theme. |
| 11. Limitasi Produk/Fitur | - Platform membantu monitoring, indexing, dashboard, export, dan analisis media intelligence, tetapi bukan pengganti full strategic research/manual investigation untuk semua kebutuhan bisnis. - Dashboard hanya menampilkan data dari campaign, source, tag, label, dan filter yang sudah aktif; data di luar setup tersebut tidak otomatis muncul. - Realtime/near real-time harus dijelaskan sebagai monitoring cepat dengan kemungkinan delay, bukan instant tanpa jeda pemrosesan. - Dua dashboard atau report bisa memiliki angka berbeda jika campaign, tag, label, date range, channel, atau filter yang dipakai berbeda. - Data cleansing tetap diperlukan karena irrelevant posts, spam, duplicate content, off-topic mention, dan keyword noise masih bisa masuk jika setup terlalu luas. - Tidak semua widget cocok untuk semua channel/use case; metric availability dan channel support harus dicek sebelum dijanjikan ke klien. - Do not claim: dashboard adalah insight final. Dashboard adalah visualisasi/agregasi yang tetap perlu interpretasi dan evidence review. |


## 3. DXT360 TrendWatch / Viral Meter
Sumber utama: S1 p.1; S2 p.12-14

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | DXT360 TrendWatch / Viral Meter |
| 2. Deskripsi Singkat | Fitur/produk monitoring real-time untuk membaca tren social media dan noteworthy content level negara agar tim dapat mengantisipasi viral moment. |
| 3. Business Problem yang Diselesaikan | Tim terlambat membaca tren; peluang konten/isu viral terlewat; monitoring tren dilakukan manual; sulit memahami topik yang sedang naik. |
| 4. Use Case / Scenario | Trend watch, issue tracking, social media audit, viral topic discovery, content opportunity scanning, early signal monitoring untuk brand atau industri. |
| 5. Kapabilitas | Real-time trend monitoring, viral topic/content detection, trend/hashtag/topic observation, supporting signal for issue tracking and campaign strategy. |
| 6. Output yang Dihasilkan | Trend list/snapshot, viral meter output, topic/hashtag signal, alert/report input, insight for content and issue tracking. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Utamanya social/digital trend sources; mengikuti coverage campaign/source yang aktif. Data fields dapat mencakup content, author, topic/hashtag, engagement, view/reach signal, timestamp, URL. |
| 8. Requirement / Dependency | Objective/industry scope, keyword/topic/account scope, geography/country focus, source activation, threshold/alert/report expectation jika dipakai untuk warning. |
| 9. KPI yang Bisa Dijawab | Buzz growth, engagement growth, top topic, top hashtag, top content, channel/source distribution, share of attention jika dibandingkan dengan kompetitor/topik lain. |
| 10. Insight yang Bisa Dihasilkan | Emerging trend, viral potential, content opportunity, issue early signal, competitor/cultural moment, timing recommendation. |
| 11. Limitasi Produk/Fitur | - TrendWatch membaca sinyal tren yang sudah mulai muncul di data publik/terpantau; fitur ini bukan prediksi absolut sebelum ada sinyal percakapan. - Viral content belum tentu relevan dengan brand atau industri klien; perlu filtering berdasarkan objective, keyword, category, geography, dan brand safety. - Country-level trend tidak selalu mewakili target audience klien, segmen tertentu, atau area regional yang lebih kecil. - Trend bisa berubah cepat; output perlu digunakan dengan timestamp dan tidak boleh dianggap stabil untuk periode panjang tanpa re-check. - Noise dari entertainment trend, fandom, politik, giveaway, meme, bot-like activity, atau kontroversi bisa mendominasi jika scope tidak dikurasi. - Tidak semua tren dapat ditangkap jika terjadi di private space, tidak match keyword, atau berada di source yang belum aktif. - Do not claim: semua viral moment pasti terdeteksi atau semua trend aman dijadikan rekomendasi konten. |


## 4. DXT360 Social Media Management
Sumber utama: S1 p.1; S2 p.12

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | DXT360 Social Media Management |
| 2. Deskripsi Singkat | Aplikasi social media management yang robust namun ringan untuk mengelola channel populer seperti Twitter/X, Facebook, Instagram, Google, dan channel lain yang tersedia. |
| 3. Business Problem yang Diselesaikan | Pengelolaan asset social tersebar; tim membutuhkan tool untuk audit/asset management; sulit mengonsolidasikan aktivitas social dan performa channel. |
| 4. Use Case / Scenario | Social media audit, asset management, owned channel management, campaign coordination, content/channel performance review. |
| 5. Kapabilitas | Support social channel management, channel overview, social performance context, integration with monitoring/reporting workflow jika tersedia dalam package. |
| 6. Output yang Dihasilkan | Channel management view, social media performance inputs, audit/report material, social asset management output. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Social channels such as X/Twitter, Facebook, Instagram, Google/other supported channels. Data field dapat mencakup account/page/profile, post/content, engagement, comments, timestamp, status/performance. |
| 8. Requirement / Dependency | Authorized account/page access jika dibutuhkan, social channel list, ownership/access permission, monitoring/report objective. |
| 9. KPI yang Bisa Dijawab | Owned post volume, engagement, channel activity, follower/potential reach where available, response/comment indicators where supported. |
| 10. Insight yang Bisa Dihasilkan | Owned social asset health, content/channel effectiveness, operational gap, channel optimization opportunity. |
| 11. Limitasi Produk/Fitur | - Kemampuan publish, schedule, manage comment, inbox, atau asset management bergantung pada integrasi channel, API policy, dan authorization akun resmi klien. - Tidak semua format konten memiliki support yang sama, misalnya Stories, Reels, Shorts, carousel, live, atau format khusus platform lain. - Tool membantu operasional social media, tetapi bukan pengganti strategi konten, brand tone, creative direction, approval legal, atau workflow crisis response. - Tidak otomatis menjamin peningkatan engagement karena performa konten tetap dipengaruhi creative, timing, audience, paid support, dan algoritma platform. - Akses competitor account tidak sama dengan owned account authorization; data kompetitor hanya sebatas public/available data. - Platform policy dapat berubah sewaktu-waktu dan berdampak pada fitur/field yang tersedia. - Do not claim: tool ini adalah CRM, ticketing system, paid media buying tool, atau dapat mengelola akun tanpa authorization. |


# B. Analytics Workflow & Data Management Modules

## 5. Campaign Library / Campaign Setup
Sumber utama: S1 p.3-4, p.97-99; S2 p.10

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Campaign Library / Campaign Setup |
| 2. Deskripsi Singkat | Modul awal untuk membuat dan mengelola campaign berbasis keyword tracking atau account tracking, termasuk status, source, tag, dan detail aktivitas. |
| 3. Business Problem yang Diselesaikan | Campaign setup tidak terstruktur; keyword/account monitoring tercecer; sulit mengaitkan data collection ke dashboard/report; status tracking tidak jelas. |
| 4. Use Case / Scenario | Onboarding monitoring project, brand/competitor/campaign setup, issue tracking setup, source assignment, dashboard/report foundation. |
| 5. Kapabilitas | Create campaign, manage Draft/Active/Inactive, assign tags and sources, view created/modified date, user activity, source types. |
| 6. Output yang Dihasilkan | Campaign configuration, active/inactive source list, data collection scope, source/tag mapping untuk dashboard dan report. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Input keywords/accounts/hashtags/person/product/service. Coverage mengikuti source yang dipilih: social, online, mainstream, traditional, forum/blog, marketplace jika tersedia. |
| 8. Requirement / Dependency | Keyword/account list, Boolean/exclusion rules jika memakai advanced mode, source selection, campaign objective, date/historical requirement, tag taxonomy. |
| 9. KPI yang Bisa Dijawab | Tidak menjawab KPI secara langsung, tetapi menjadi basis untuk buzz, mention, sentiment, engagement, SOV, distribution, dan reporting KPI lain. |
| 10. Insight yang Bisa Dihasilkan | Membantu memastikan insight sesuai scope; mencegah data campur; memperjelas perbandingan own brand vs competitor vs issue. |
| 11. Limitasi Produk/Fitur | - Campaign hanya menangkap data yang match dengan keyword, account, hashtag, source, atau rule yang dimasukkan dalam setup. - Keyword yang terlalu broad meningkatkan noise, irrelevant post, spam, buzzer, atau konteks umum yang tidak terkait brand. - Keyword yang terlalu sempit menurunkan recall dan bisa melewatkan slang, typo, singkatan, bahasa lokal, meme, indirect mention, atau isu yang tidak menyebut brand secara eksplisit. - Exclusion keyword harus dikalibrasi: terlalu agresif dapat membuang data relevan, terlalu longgar membuat noise tetap masuk. - Perubahan keyword/setup tidak boleh dijanjikan otomatis memperbaiki seluruh historical dataset; dampaknya bergantung pada source, provider, dan konfigurasi campaign. - AI dapat membantu membuat keyword package, tetapi validasi BD/CX/Insight tetap wajib agar scope sesuai kebutuhan klien. - Do not claim: satu keyword setup langsung sempurna tanpa tuning, QA, dan revisi setelah melihat sample data. |


## 6. Dashboard Library
Sumber utama: S1 p.4-5, p.55-60

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Dashboard Library |
| 2. Deskripsi Singkat | Library template dashboard siap pakai untuk membuat dashboard berbasis kebutuhan analisis seperti competitor analysis, campaign tracking, dan sentiment analysis. |
| 3. Business Problem yang Diselesaikan | Tim harus membuat dashboard dari nol; visualisasi tidak konsisten; waktu setup lama; stakeholder butuh view cepat untuk use case umum. |
| 4. Use Case / Scenario | Quick setup dashboard untuk campaign, competitor, sentiment, brand health, issue monitoring, reporting dashboard. |
| 5. Kapabilitas | Preset dashboard template, predefined widgets, quick use template, customizable dashboard based on analysis goals. |
| 6. Output yang Dihasilkan | Dashboard siap pakai dengan widgets seperti mention tracking, trend chart, comparison graph, sentiment visuals, dan exportable view. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Data source mengikuti campaign/tag/source yang dipilih. Field tergantung widget yang dipakai: mentions, sentiment, engagement, channel distribution, media value, topic, author, etc. |
| 8. Requirement / Dependency | Campaign/tag source, tujuan analisis, template yang dipilih, periode data, widget configuration, layout preference. |
| 9. KPI yang Bisa Dijawab | Buzz, engagement, sentiment, SOV, trend, channel distribution, top words/hashtags/authors, media value sesuai widgets. |
| 10. Insight yang Bisa Dihasilkan | Dashboard-level pattern, channel driver, competitor gap, sentiment shift, trend movement, campaign performance overview. |
| 11. Limitasi Produk/Fitur | - Template dashboard mempercepat setup, tetapi belum tentu cocok 100% untuk objective, industri, stakeholder, atau KPI tiap klien. - Hasil dashboard bergantung pada campaign/tag/source yang dipilih; jika source/filter salah, visualisasi dan export juga salah. - Predefined widgets tetap perlu dikonfigurasi ulang bila metric, channel, label, atau chart yang dibutuhkan berbeda dari template. - Export dashboard mengikuti filter aktif saat export sehingga tidak boleh dianggap angka final tanpa validasi konfigurasi. - Dashboard bisa berubah setelah data ingestion yang terlambat masuk atau setelah sentiment/label/manual cleaning diperbarui. - Do not claim: template dashboard otomatis menjadi client-ready insight tanpa customization dan analyst review. |


## 7. Widget Library
Sumber utama: S1 p.5, p.17-51, p.55-60

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Widget Library |
| 2. Deskripsi Singkat | Library untuk memilih dan mengombinasikan widget visualisasi sesuai kebutuhan dashboard. |
| 3. Business Problem yang Diselesaikan | Tim membutuhkan visualisasi spesifik tanpa membangun dari nol; dashboard perlu fleksibel berdasarkan kebutuhan PR, marketing, research, atau CX. |
| 4. Use Case / Scenario | Dashboard customization, report preparation, performance monitoring, issue analysis, sentiment/topic/author/media analysis. |
| 5. Kapabilitas | Browse/select widgets, use preconfigured widgets, customize data source, metrics, view type, and dashboard layout. |
| 6. Output yang Dihasilkan | Set widget visual seperti line/stacked chart, pie chart, table, map, bubble chart, wordcloud, bar chart, dashboard cards. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Coverage mengikuti channel applicable tiap widget. Field tergantung widget: buzz, engagement, sentiment, topic, author, hashtags, distribution, media value, etc. |
| 8. Requirement / Dependency | Selected campaign/tag/label, widget type, metric, visualization type, grid size, date range, filters. |
| 9. KPI yang Bisa Dijawab | Widget-specific KPI seperti buzz, engagement, sentiment, media value, SOV, top words/hashtags, location, peak hour, author contribution. |
| 10. Insight yang Bisa Dihasilkan | Visual diagnosis untuk trend, issue, sentiment, channel distribution, influencer/author, media exposure, dan competitive performance. |
| 11. Limitasi Produk/Fitur | - Widget menghitung berdasarkan campaign, tag, label, date range, channel, dan filter yang aktif; angka bisa berbeda jika satu parameter berubah. - Widget adalah visualisasi/agregasi, bukan sumber data audit utama. Untuk investigasi, tetap buka My Data/raw data/evidence URL. - Beberapa widget misleading jika volume data terlalu kecil, data belum lengkap, atau source tertentu masih delay. - Metric availability berbeda per channel; widget tertentu tidak boleh dipaksakan jika field seperti views, reach, shares, location, gender, atau media value tidak tersedia. - Widget preset perlu disesuaikan dengan use case agar tidak menghasilkan chart yang cantik tetapi tidak menjawab pertanyaan bisnis. - Do not claim: semua widget cocok untuk semua channel, semua KPI, dan semua jenis report. |


## 8. Insight Report Library
Sumber utama: S1 p.6; S2 p.5

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Insight Report Library |
| 2. Deskripsi Singkat | Library template untuk membuat presentasi/report berbasis insight dengan content blocks seperti Performance Overview, Summary Activity, dan Competitive Highlights. |
| 3. Business Problem yang Diselesaikan | Tim sulit mengubah data menjadi storytelling; laporan campaign kurang konsisten; insight deck membutuhkan banyak formatting manual. |
| 4. Use Case / Scenario | Campaign impact summary, stakeholder presentation, recurring report foundation, insight-driven deck/report generation. |
| 5. Kapabilitas | Select report template, build structured insight presentation, use predefined content blocks, export report. |
| 6. Output yang Dihasilkan | Exportable insight report/presentation structure, performance overview, summary activity, competitive highlights, report blocks. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Mengambil output dari campaign/dashboard/widget. Data fields mengikuti metrics dan visual yang dipilih di report template. |
| 8. Requirement / Dependency | Report objective, template selection, campaign/tag/source, reporting period, stakeholder audience, content blocks needed. |
| 9. KPI yang Bisa Dijawab | Performance summary, buzz, engagement, sentiment, competitor comparison, channel/activity metrics, media/report KPIs sesuai template. |
| 10. Insight yang Bisa Dihasilkan | Campaign impact narrative, performance driver, competitive highlights, stakeholder-ready summary, action-oriented reporting. |
| 11. Limitasi Produk/Fitur | - Template report membantu struktur storytelling, tetapi tetap perlu disesuaikan dengan objective, stakeholder, brand context, dan gaya komunikasi klien. - Report otomatis dapat menjadi generik jika hanya memakai template tanpa analyst interpretation dan evidence selection. - Kualitas report mengikuti kualitas dashboard/campaign/filter yang menjadi input; data noisy akan menghasilkan insight yang noisy. - Content blocks seperti Performance Overview atau Competitive Highlights harus divalidasi agar tidak overclaim penyebab, dampak, atau rekomendasi. - Tidak semua template cocok untuk semua industri atau masalah bisnis; perlu mapping use case sebelum dipakai. - Do not claim: template report otomatis menggantikan analyst/client-specific narrative. |


## 9. Theme Library / Custom Report
Sumber utama: S1 p.7, p.79-83, p.99-106

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Theme Library / Custom Report |
| 2. Deskripsi Singkat | Command center untuk membuat custom reports berulang atau one-time dengan template seperti Integrated Alert, Media Monitoring, atau saved themes. |
| 3. Business Problem yang Diselesaikan | Client membutuhkan report dengan jadwal dan struktur berbeda-beda; report harus konsisten dan dapat diulang tanpa manual setup tiap periode. |
| 4. Use Case / Scenario | Recurring report, one-time report, integrated alert report, media monitoring report, monthly/weekly summary, dashboard-to-report workflow. |
| 5. Kapabilitas | Choose report templates, preview report, generate recurring/one-time export, customize content and structure. |
| 6. Output yang Dihasilkan | Recurring/one-time custom report, report preview, export, automated delivery if configured. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Menggunakan data dari dashboard/campaign/widget yang dipilih. Field mengikuti report template dan widget source. |
| 8. Requirement / Dependency | Report template/theme, dashboard/source filter, frequency, delivery time, recipient list, content structure, report objective. |
| 9. KPI yang Bisa Dijawab | Report-level KPI sesuai template: alert metrics, media monitoring volume, sentiment, distribution, media value, campaign performance, etc. |
| 10. Insight yang Bisa Dihasilkan | Repeatable narrative, reporting consistency, scheduled stakeholder update, trend and issue continuity. |
| 11. Limitasi Produk/Fitur | - Custom/recurring report mengikuti template, source filter, dashboard/widget, frequency, dan recipient yang dikonfigurasi; kesalahan konfigurasi akan berulang otomatis. - Report generation/export dapat membutuhkan waktu tergantung volume data, kompleksitas widget, sistem queue, dan package. - Recurring report tidak otomatis menangkap isu di luar jadwal kirim; untuk eskalasi cepat perlu Smart Alert/Advanced Alert. - Template custom report harus dikunci dengan definisi KPI, audience, dan output agar tidak berubah-ubah antar periode. - Email/report delivery dapat dipengaruhi status report, recipient setting, email policy/spam filter, dan package support. - Do not claim: recurring custom report sama dengan real-time crisis alert. |


## 10. Tags & Label Management
Sumber utama: S1 p.8, p.51-55, p.61-72

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Tags & Label Management |
| 2. Deskripsi Singkat | Fitur pengelompokan data/campaign agar data dapat disegmentasikan berdasarkan brand, topic, objective, issue, campaign phase, complaint, crisis, atau kategori lain. |
| 3. Business Problem yang Diselesaikan | Data dari banyak campaign sulit dipisahkan; report campur antara own brand/competitor/topic; stakeholder butuh segmentasi yang konsisten. |
| 4. Use Case / Scenario | Own brand vs competitor grouping, issue/category segmentation, campaign phase tracking, complaint/crisis labeling, product/topic comparison. |
| 5. Kapabilitas | Create/manage tags, assign colors, link tags to campaigns, manually/automatically apply labels, filter dashboard/report by tags/labels. |
| 6. Output yang Dihasilkan | Segmented campaign/group, label-filtered dashboard, export/report filtered by label, cleaner raw data and custom report scope. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Labels/tags dapat diterapkan pada mentions dari social, online, mainstream/traditional channels tergantung source. Field meliputi label name, tag name, campaign, content, sentiment, URL, metrics. |
| 8. Requirement / Dependency | Taxonomy/tagging rules, label definitions, campaign mapping, user process untuk apply label/manual correction, filter source. |
| 9. KPI yang Bisa Dijawab | KPI by segment: mention, sentiment, engagement, media value, SOV, topic, channel distribution, complaint count, crisis-related volume. |
| 10. Insight yang Bisa Dihasilkan | Issue segmentation, topic/category driver, product comparison, complaint/praise mapping, crisis evidence grouping. |
| 11. Limitasi Produk/Fitur | - Kualitas tag/label sangat bergantung pada definisi taxonomy, konsistensi penerapan, dan governance antar user/tim. - Label manual dapat bias jika tidak ada guideline yang jelas untuk issue, complaint, crisis, product, campaign phase, atau competitor grouping. - Label otomatis/AI tetap perlu sampling QA, terutama untuk isu sensitif dan report strategis. - Dashboard Label Filter hanya seakurat label yang sudah diterapkan; data yang belum dilabeli bisa tidak masuk analisis label-based. - Perubahan label dapat mengubah angka dashboard/report/export sehingga perlu versioning atau catatan perubahan untuk recurring report. - Do not claim: label selalu objektif/sempurna tanpa QA dan definisi operasional. |


## 11. My Data Workspace
Sumber utama: S1 p.61-72

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | My Data Workspace |
| 2. Deskripsi Singkat | Workspace pusat untuk melihat, memfilter, mengelola, membersihkan, menerjemahkan, memberi label, mengedit sentiment, mengekspor, dan membuat AI report dari mentions yang terkumpul. |
| 3. Business Problem yang Diselesaikan | Analyst/CX perlu workspace operasional untuk audit data, mengurangi noise, validasi sentiment, mencari mention, dan menyiapkan bahan laporan. |
| 4. Use Case / Scenario | Raw data review, data cleansing, sentiment QA, translation, label management, issue investigation, follow post, export/report generation. |
| 5. Kapabilitas | Filter by campaign/tag/label/date/channel/keyword/demographic/categorization, mentions feed, edit sentiment, translate content, delete/recover data, follow post, generate AI report/raw data. |
| 6. Output yang Dihasilkan | Filtered mentions feed, clean dataset, manual sentiment updates, translated content, labeled data, raw data export, AI insight/report input. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Social posts, comments/replies, online news, forum discussions, video/mainstream mentions. Field: Content/post, author/account, timestamp, URL, channel/source, campaign/tag/label, sentiment, topic/sentence type jika aktif, engagement metrics seperti likes, comments/replies, shares/retweets/quotes, views, reach/potential reach. Article/title/content, media name/source, publish date, URL, media type, sentiment, spokesperson jika terdeteksi, ad value, PR value, page rank, monthly pageview, unique visitors, country rank, circulation/duration sesuai channel. |
| 8. Requirement / Dependency | Active campaign/source, filter source, date range, search/advanced filters, user permission, operational QA workflow. |
| 9. KPI yang Bisa Dijawab | Mention, post/article count, sentiment distribution, engagement, channel breakdown, demographic/category filters, labels, content operations count. |
| 10. Insight yang Bisa Dihasilkan | Data quality issue, core evidence, recurring complaint, sentiment correction rationale, topic/label-specific insight, content needing follow-up. |
| 11. Limitasi Produk/Fitur | - My Data hanya menampilkan mentions yang masuk ke campaign/source/filter; bukan seluruh data internet atau full crawl universe. - Beberapa mentions dapat berstatus Analyzing sampai proses sentiment/AI selesai; sementara itu sentiment-based widget/filter bisa belum lengkap. - Search dan advanced filter bergantung pada indexed fields dan konfigurasi source; hasil dapat berubah setelah data baru masuk atau cleaning dilakukan. - Sentiment editing, deleting, recovery, label management, dan follow post membutuhkan governance agar data report tetap konsisten. - Deleted post memiliki batas retention sesuai konfigurasi/dokumentasi dan tidak boleh diasumsikan selalu dapat dipulihkan selamanya. - Translation otomatis membantu pemahaman, tetapi nuance lokal, slang, idiom, dan konteks sensitif tetap perlu dicek manusia. - Do not claim: My Data adalah raw engineering crawl penuh atau selalu final sebelum proses AI/indexing selesai. |


## 12. Raw Data Export
Sumber utama: S1 p.66-83, p.106-107

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Raw Data Export |
| 2. Deskripsi Singkat | Fitur untuk menghasilkan dan mengunduh data dalam format Excel melalui My Data atau Exports section, dengan opsi Default Version dan Pivot Version. |
| 3. Business Problem yang Diselesaikan | Tim membutuhkan data mentah untuk validasi, pivot, manual analysis, reporting, archiving, atau handover ke client/analyst. |
| 4. Use Case / Scenario | Detailed investigation, data validation, manual analysis, operational review, comparative reporting, campaign summary, management presentation, scheduled export. |
| 5. Kapabilitas | Generate raw data, choose Default/Pivot format, customize file name, track export progress, download/view/delete export, create scheduled/custom export. |
| 6. Output yang Dihasilkan | Excel raw data default format, pivot/summary-friendly export, scheduled export output, downloadable report/export file. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Default Version: post/media mention level. Pivot Version: grouped by campaign/media type/engagement metric. Fields mengikuti channel/source/filter yang digunakan. |
| 8. Requirement / Dependency | Filtered dataset, export format selection, file name, dashboard/widget selection for exports section, frequency/date range, notification setting. |
| 9. KPI yang Bisa Dijawab | Post-level metrics, summary trend metrics, campaign/channel/media type grouping, engagement/sentiment/media metrics, article/social counts. |
| 10. Insight yang Bisa Dihasilkan | Audit trail, data validation, pivot analysis, trend comparison, campaign/channel summary, evidence extraction. |
| 11. Limitasi Produk/Fitur | - Export mengikuti filter, source, date range, dan dataset saat generate; jika filter salah, hasil Excel juga salah. - Default Version dan Pivot Version memiliki struktur berbeda; row count, grouping, dan layout bisa berbeda dari dashboard karena proses summarization/restructuring. - Export besar membutuhkan waktu dan dapat antre dalam background process; jangan dijanjikan selalu instan. - Raw export bukan jaminan full internet/full crawl universe; hanya data yang tersedia dalam campaign/filter/package. - Sorting hasil export dapat berbeda dari sorting dashboard, sehingga perlu re-check sebelum dipakai untuk report final. - File raw data tetap perlu cleaning, deduplication, pivoting, labeling, sampling, atau data dictionary agar tidak salah interpretasi. - Do not claim: Excel export otomatis sudah siap menjadi insight report tanpa analisis lanjutan. |


## 13. Dashboard Label Filter
Sumber utama: S1 p.51-55

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Dashboard Label Filter |
| 2. Deskripsi Singkat | Enhancement yang memungkinkan semua dashboard widgets difilter berdasarkan Labels setelah memilih satu campaign/tag. |
| 3. Business Problem yang Diselesaikan | Dashboard terlalu luas; analyst perlu fokus pada topic/issue tertentu tanpa membuat dashboard baru; export/share harus konsisten dengan filter. |
| 4. Use Case / Scenario | Issue drill-down, campaign sub-topic analysis, complaint/crisis segment tracking, product/initiative comparison, label-based report export. |
| 5. Kapabilitas | Select campaign/tag, apply up to 10 labels, recalculate all widgets using Campaign/Tag intersection Label logic, reflect filter in export/share. |
| 6. Output yang Dihasilkan | Label-filtered dashboard, widget visuals, dashboard/widget export, send to email/WhatsApp, raw data export scoped to labels. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Menggunakan labels pada dataset campaign/tag. Field mengikuti widget; filter logic Campaign/Tag intersection Label. |
| 8. Requirement / Dependency | At least one campaign/tag selected, labels already created/applied, dashboard widgets configured, source filters set. |
| 9. KPI yang Bisa Dijawab | KPI by label: buzz, engagement, sentiment, distribution, topic, top words, media value, spokesperson, mentions, location, peak hour, etc. |
| 10. Insight yang Bisa Dihasilkan | Focused issue performance, topic-level driver, label-specific sentiment, cleaner reporting segmentation. |
| 11. Limitasi Produk/Fitur | - Label filter hanya aktif jika minimal satu campaign/tag dipilih; tanpa source tersebut filter label tidak dapat digunakan. - Output dashboard hanya menampilkan irisan Campaign/Tag dan Label yang dipilih; data relevan yang belum dilabeli tidak akan masuk hasil filter. - Maksimum label yang dapat dipilih mengikuti konfigurasi fitur; jangan menjanjikan unlimited label filtering. - Semua widget dan export mengikuti label filter aktif, sehingga salah label/salah filter akan memengaruhi seluruh visual dan output share/export. - Kualitas insight label-based bergantung pada konsistensi definisi label dan QA penerapan label. - Do not claim: label filter memperbaiki kualitas data secara otomatis; filter hanya mempersempit data berdasarkan label yang sudah ada. |


# C. AI, Automation & Alerting

## 14. AI Insight Summary
Sumber utama: S1 p.83-99

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | AI Insight Summary |
| 2. Deskripsi Singkat | Fitur AI yang membuat ringkasan kontekstual dari dataset terfilter di My Data untuk membantu membaca campaign performance dan insight secara cepat. |
| 3. Business Problem yang Diselesaikan | Analyst membutuhkan waktu lama membaca volume data besar; stakeholder butuh summary cepat; insight awal sulit dibuat tanpa export manual. |
| 4. Use Case / Scenario | Daily/weekly campaign summary, company daily media summary, spokesperson/executive mentions, demographic/label-based summary, agency/client snapshot, executive performance snapshot. |
| 5. Kapabilitas | Generate AI summary from filtered dataset, role/objective-aware narrative, status notification, copy/email/PDF/download/translate/edit output. |
| 6. Output yang Dihasilkan | Short contextual narrative, email output, clipboard text, PDF summary, translated summary, editable summary content. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Input berasal dari selected dataset di My Data: campaign, tags, labels, date range, channel, sentiment/demographic filters. Output language follows account default and can be translated. |
| 8. Requirement / Dependency | AI feature activation via Admin Panel, available quota, filtered dataset, selected campaign/tag/label/date range, clear report objective/template context. |
| 9. KPI yang Bisa Dijawab | Narrative summary dapat membaca buzz, sentiment, engagement, media exposure, SOV/competitive performance, demographic/topic signals sesuai filter. |
| 10. Insight yang Bisa Dihasilkan | Campaign performance driver, sentiment change, risk/win, competitive standing, topic/audience pattern, executive-ready snapshot. |
| 11. Limitasi Produk/Fitur | - AI Summary bergantung pada dataset yang dipilih di My Data; jika campaign, tag, label, date range, channel, atau filter salah, narasinya juga bisa salah arah. - AI menghasilkan narrative summary, bukan audit final. Human review tetap wajib untuk insight sensitif, krisis, hukum, politik, dan executive reporting. - Fitur memerlukan aktivasi, quota, dan package yang mendukung; jika quota habis atau fitur tidak aktif, summary tidak dapat dibuat. - AI bisa melewatkan nuance lokal, sarcasm, slang, mixed language, kultur platform, atau konteks internal klien. - Translate/edit output dapat membantu distribusi, tetapi perubahan bahasa dan edit manual harus dicek agar tidak mengubah makna data. - AI tidak boleh membuat klaim penyebab/kausalitas di luar data yang tersedia. - Do not claim: AI Summary menggantikan analyst, crisis consultant, atau keputusan final stakeholder. |


## 15. AI Report
Sumber utama: S1 p.99-106

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | AI Report |
| 2. Deskripsi Singkat | Enhanced module yang menggabungkan AI Generated Report/AI Summary dan Custom Report dalam satu flow untuk one-time atau recurring AI-generated reporting. |
| 3. Business Problem yang Diselesaikan | Tim membutuhkan report otomatis yang lebih terstruktur, bisa dijadwalkan, dan tidak hanya summary default; laporan AI perlu template dan status management. |
| 4. Use Case / Scenario | One-time report from My Data, recurring scheduled AI report, campaign performance, industry trends, competitive analysis, stakeholder email delivery. |
| 5. Kapabilitas | Select template, generate one-time report, schedule recurring report, edit narrative elements, translate, download PDF, copy text, send email, view browser, manage statuses. |
| 6. Output yang Dihasilkan | AI Report templates: Campaign Performance, Industry Trends, Competitive Analysis. Output: PDF/browser/email/text report with narrative and charts/metrics. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Source filter from My Data or Report Library, campaign/tag/source, report template, delivery interval/time, recipient emails. Charts/metrics generated from filtered dataset. |
| 8. Requirement / Dependency | AI feature activation, quota, report template, report name, send time type, delivery time, recipient emails, source filter. |
| 9. KPI yang Bisa Dijawab | Campaign performance, industry trend indicators, competitive SOV/engagement/sentiment, media/social metrics based on selected template. |
| 10. Insight yang Bisa Dihasilkan | Structured campaign narrative, trend explanation, competitive positioning, executive/client-ready finding, recurring reporting summary. |
| 11. Limitasi Produk/Fitur | - AI Report mengikuti source filter, template, schedule, dan quota yang dikonfigurasi; salah setup dapat menghasilkan recurring report yang salah berulang. - Narrative text dapat diedit, tetapi charts, graph visuals, metrics, dan numerical data tidak boleh diedit agar akurasi data tetap terjaga. - Quota, activation, report status, recipient email, dan delivery configuration memengaruhi apakah report dapat dibuat/dikirim. - Template Campaign Performance, Industry Trends, dan Competitive Analysis hanya relevan jika data dan objective sesuai. - AI Report tetap perlu review manusia untuk nuance, action point, rekomendasi, dan sensitive issue. - Translation dapat mengubah nuance, sedangkan metric/angka harus tetap mengikuti dataset asli. - Do not claim: AI Report adalah laporan strategis final tanpa review dan context enrichment. |


## 16. Smart Alert / Advanced Alert
Sumber utama: S1 p.107-123; S2 p.15, p.19-20

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Smart Alert / Advanced Alert |
| 2. Deskripsi Singkat | Early warning system untuk mendeteksi potensi eskalasi isu lintas social media dan online media berdasarkan perubahan volume, engagement velocity, risk/negativity, story/issue, dan channel state. |
| 3. Business Problem yang Diselesaikan | Klien terlambat mengetahui isu negatif atau krisis; monitoring manual tidak menangkap percepatan isu; sulit menentukan prioritas respons dari banyak channel. |
| 4. Use Case / Scenario | Crisis monitoring, negative issue tracking, public policy/brand reputation alert, social + online media escalation, CX/Insight evidence handover. |
| 5. Kapabilitas | All-channel state detection, channel state, risk/negativity, neg_story_title/story_title, driver post/article, notification card, raw data detail workbook, WATCH/HOT/CRISIS/COOLDOWN logic. |
| 6. Output yang Dihasilkan | Notifikasi Smart Alert, raw data detail workbook, scope overview, channel overview, issue/story overview, social post detail, online article detail, driver evidence. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Social: Instagram, TikTok, X; Online Media. Fields: state, risk/negativity, total post/article, engagement, likes/comments/shares/views/replies/retweets/quotes, neg_story_title, story_title, article/post evidence, URL. |
| 8. Requirement / Dependency | Scope monitoring, keyword/source setup, snapshot schedule, threshold/risk calibration, recipient/channel notification, raw data output template, validated alert logic per channel. |
| 9. KPI yang Bisa Dijawab | Total alert posts/articles, engagement, WATCH/HOT/CRISIS/COOLDOWN counts, risk level, sentiment counts, story_now, article_now, channel state, escalation flag. |
| 10. Insight yang Bisa Dihasilkan | Early warning, issue escalation driver, channel penyebab, top negative issue/story, evidence-based alert explanation, follow-up priority. |
| 11. Limitasi Produk/Fitur | - Smart Alert adalah early warning, bukan vonis krisis final. Keputusan apakah isu benar-benar krisis tetap membutuhkan validasi manusia dan konteks komunikasi klien. - Kecepatan alert bergantung pada konfigurasi monitoring, package, channel, threshold, dan SLA; standard snapshot umumnya dapat dibuat berkala, sementara advanced/crisis package dapat disepakati misalnya 30-60 menit sesuai setup. - Sonar tidak menjamin mengetahui krisis sebelum ada sinyal publik. Sistem mendeteksi potensi eskalasi ketika percakapan, engagement, pemberitaan, atau risk signal mulai muncul di data terpantau. - Tidak semua isu naik bertahap; beberapa isu dapat langsung melonjak dari NORMAL ke HOT/CRISIS dalam satu snapshot karena influencer, media nasional, repost viral, atau akun besar. - Akurasi alert bergantung pada keyword, scope, source coverage, exclusion, alert rule, dan baseline normal per industri/channel. - Threshold WATCH/HOT/CRISIS perlu dikalibrasi per brand, industri, market, channel, dan objective agar tidak terlalu sensitif atau terlalu lambat. - Data availability bergantung pada channel/provider; comment/reply/engagement/story/article field dapat delay atau tidak lengkap. - Private account, private group, closed community, DM, dan data non-public tidak boleh dijanjikan sebagai coverage. - Risk/negativity bukan sekadar sentiment; interpretasi perlu melihat issue context, engagement growth, story risk, article risk, dan evidence driver. - Raw Data Detail adalah evidence/agregasi terpilih untuk menjelaskan alert, bukan full raw crawl engineering. |


## 17. Daily Email Digest / Automated Alert Delivery
Sumber utama: S1 p.79-83, p.99-123; S2 p.12-15, p.19-20

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Daily Email Digest / Automated Alert Delivery |
| 2. Deskripsi Singkat | Layanan pengiriman summary atau alert berkala melalui email/WhatsApp/notification untuk mempersingkat distribusi insight dan early warning ke stakeholder. |
| 3. Business Problem yang Diselesaikan | Stakeholder tidak rutin membuka dashboard; update harian/berkala harus dikirim otomatis; isu perlu diketahui cepat tanpa menunggu report manual. |
| 4. Use Case / Scenario | Daily media summary, advanced alert, WhatsApp alert notification, Monday/weekly summary, executive snapshot, recurring AI report delivery. |
| 5. Kapabilitas | Scheduled/automated delivery, send-to-email, alert notification, recurring report output, notification progress/status. |
| 6. Output yang Dihasilkan | Email digest, WhatsApp alert notification, recurring report, notification card, link/export/report attachment if configured. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Input dari Smart Alert, AI Report, custom report, dashboard/export. Data fields mengikuti template alert/report yang dikirim. |
| 8. Requirement / Dependency | Recipient email/WhatsApp group, schedule/frequency, report/alert template, source filter, notification rules, account/package support. |
| 9. KPI yang Bisa Dijawab | Report/alert KPIs sesuai template: volume, sentiment, engagement, story/issue, state, media value, campaign/competitor metrics. |
| 10. Insight yang Bisa Dihasilkan | Timely awareness, issue priority, daily/weekly movement, stakeholder alignment, escalation readiness. |
| 11. Limitasi Produk/Fitur | - Digest/automated delivery mengikuti jadwal, template, source filter, dan recipient yang dikonfigurasi; salah setup akan mengirim output yang salah secara berulang. - Daily/weekly digest bukan immediate escalation; jika klien butuh peringatan cepat, gunakan Smart Alert/Advanced Alert dengan cadence/SLA khusus. - Pengiriman email/WhatsApp/notification bergantung pada package support, recipient list, email policy, spam filter, WhatsApp group setup, dan status report/alert. - Automated output tidak selalu menyertakan human interpretation kecuali ada analyst support/managed service dalam scope. - Report/alert tetap perlu dicek dengan evidence detail sebelum dipakai sebagai dasar keputusan krisis atau statement publik. - Do not claim: digest otomatis sama dengan 24/7 human monitoring atau crisis advisory. |


# D. Research & Service Offerings

## 18. Custom Analyst Report / Insight Report
Sumber utama: S2 p.5, p.12-15, p.18-20; S1 p.6-7

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Custom Analyst Report / Insight Report |
| 2. Deskripsi Singkat | Report yang disusun berdasarkan goals dan challenge client agar insight relevan, tepat waktu, dan actionable; dapat berupa summary report, intel report, insight report, crisis report, issue tracking, media report, atau custom analyst report. |
| 3. Business Problem yang Diselesaikan | Dashboard saja belum cukup untuk menjawab pertanyaan strategis; stakeholder membutuhkan narasi, interpretasi, rekomendasi, dan executive-ready analysis. |
| 4. Use Case / Scenario | Brand perception, campaign performance, competitor benchmarking, media monitoring, brand health, crisis investigation, issue tracking, marketplace analysis, executive reporting. |
| 5. Kapabilitas | Analyst interpretation, storytelling, insight synthesis, chart/table curation, evidence selection, recommendation/action point, recurring or ad-hoc report. |
| 6. Output yang Dihasilkan | Summary report, Intel report, insight report, crisis report, issue tracking report, online/mainstream media report, monthly/quarterly report, client-ready deck/document. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Menggunakan data DXT360 dan sumber/reporting scope client. Field: Content/post, author/account, timestamp, URL, channel/source, campaign/tag/label, sentiment, topic/sentence type jika aktif, engagement metrics seperti likes, comments/replies, shares/retweets/quotes, views, reach/potential reach. Article/title/content, media name/source, publish date, URL, media type, sentiment, spokesperson jika terdeteksi, ad value, PR value, page rank, monthly pageview, unique visitors, country rank, circulation/duration sesuai channel. plus evidence and analyst notes. |
| 8. Requirement / Dependency | Clear business objective, reporting period, keywords/campaigns, competitor list, source coverage, report template/format, audience/stakeholder, delivery cadence. |
| 9. KPI yang Bisa Dijawab | KPI disesuaikan: buzz, engagement, sentiment, SOV, channel/media distribution, media value, campaign metrics, competitor metrics, issue volume, top driver. |
| 10. Insight yang Bisa Dihasilkan | Strategic implication, cause/driver analysis, reputation risk, campaign effectiveness, competitor movement, audience perception, recommended action. |
| 11. Limitasi Produk/Fitur | - Kualitas report bergantung pada kejelasan brief, objective, reporting period, keyword/campaign setup, competitor list, source coverage, dan konteks bisnis klien. - Custom analyst report tidak boleh dijanjikan instan seperti dashboard; SLA harus disepakati berdasarkan kompleksitas, volume data, jumlah stakeholder, dan level analysis. - Report tidak dapat mengisi data yang tidak tersedia; analyst hanya boleh membuat inference hati-hati dengan limitation note jika evidence terbatas. - Rekomendasi report bukan keputusan final bisnis/PR/legal; keputusan tetap berada pada klien dengan mempertimbangkan konteks internal mereka. - Comparative report harus memakai periode, source, keyword, dan scope yang fair agar tidak bias. - Manual interpretation bisa berbeda antar analyst; perlu template, rubric, evidence QA, dan review untuk menjaga konsistensi. - Do not claim: report membuktikan kausalitas seperti sales naik/turun jika tidak ada data internal pendukung. |


## 19. Managed Services
Sumber utama: S2 p.10, p.20

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Managed Services |
| 2. Deskripsi Singkat | Layanan asistensi/operasional dari Sonar untuk membantu monitoring, reporting, alert handling, dan follow-up data/insight sesuai kebutuhan client. |
| 3. Business Problem yang Diselesaikan | Client tidak memiliki cukup kapasitas internal untuk mengelola dashboard, data cleansing, alert validation, atau recurring report. |
| 4. Use Case / Scenario | Assisted monitoring, crisis support, managed reporting, dashboard operation, analyst support, ad-hoc analysis, client success enablement. |
| 5. Kapabilitas | Human-assisted analysis, platform setup/operation support, report delivery support, alert validation, data/evidence preparation. |
| 6. Output yang Dihasilkan | Managed report, data evidence pack, alert summary, dashboard setup/support, analyst notes, client update. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Menggunakan data platform dan sumber yang masuk scope engagement. Coverage mengikuti kontrak/package dan setup campaign/source. |
| 8. Requirement / Dependency | Scope of work, SLA/timeline, source list, reporting cadence, stakeholder workflow, escalation path, access/approval, analyst brief. |
| 9. KPI yang Bisa Dijawab | Operational KPI: timeliness, volume processed, alert/report delivery, issue counts, sentiment/media metrics depending on service scope. |
| 10. Insight yang Bisa Dihasilkan | Faster response, validated issue interpretation, clearer reporting, reduced operational burden, better continuity of monitoring. |
| 11. Limitasi Produk/Fitur | - Managed service hanya mencakup aktivitas yang tertulis dalam SOW/kontrak; tambahan brand, competitor, channel, market, report, bahasa, atau adhoc request dapat menjadi scope creep. - SLA harus tertulis: response time, working hour, weekend/holiday support, escalation flow, report frequency, dan deliverable format. - Human analyst support bukan 24/7 kecuali secara eksplisit disepakati dalam package/SOW. - Adhoc analysis, custom data pull, crisis update, atau evidence pack membutuhkan waktu sesuai kompleksitas dan ketersediaan data. - Managed service tetap membutuhkan PIC klien untuk approval, context, issue priority, escalation contact, dan feedback rutin. - Output quality akan menurun jika feedback klien, taxonomy, objective, atau escalation workflow tidak jelas. - Do not claim: managed service mencakup semua kebutuhan tanpa batas atau menggantikan crisis/PR/legal team klien. |


## 20. EVO Consultancy Report
Sumber utama: S2 p.12, p.14-15

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | EVO Consultancy Report |
| 2. Deskripsi Singkat | Consultancy report periodik untuk menjawab kebutuhan analisis yang lebih strategis, biasanya per quarter/semester, seperti brand health atau brand perception. |
| 3. Business Problem yang Diselesaikan | Client membutuhkan interpretasi strategis di atas monitoring rutin; butuh rekomendasi dan pembacaan tren jangka menengah/panjang. |
| 4. Use Case / Scenario | Brand health, brand perception, audience listening, research/industry monitoring, brand listening, executive strategic review. |
| 5. Kapabilitas | Strategic synthesis, quarterly/semester trend review, issue/opportunity analysis, action recommendation, consulting-style narrative. |
| 6. Output yang Dihasilkan | EVO light consultancy report, EVO consultancy report quarter/semester, strategic findings and recommendations. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Menggunakan DXT360/social/online/mainstream/traditional datasets, reports, campaign tags, and analyst interpretation. Data fields mengikuti objective dan report design. |
| 8. Requirement / Dependency | Quarter/semester scope, objectives, KPI framework, client context, campaign/source setup, competitor/benchmark list, analyst workshop/input if needed. |
| 9. KPI yang Bisa Dijawab | Brand health metrics, sentiment trend, SOV, engagement, media exposure, campaign/competitor benchmarking, topic/issue trend. |
| 10. Insight yang Bisa Dihasilkan | Strategic risk/opportunity, perception shift, competitive implication, audience behavior pattern, roadmap/recommendation. |
| 11. Limitasi Produk/Fitur | - EVO Consultancy Report membutuhkan metodologi, scope, KPI framework, dan objective yang jelas; tidak cukup hanya menarik dashboard snapshot. - Karena sifatnya strategis/periodik, report ini tidak boleh dijanjikan sebagai real-time alert atau daily operational report. - Kesimpulan jangka menengah/panjang bergantung pada konsistensi data collection, periode pembanding, dan kualitas benchmark. - Recommendation perlu validasi dengan konteks bisnis klien, market condition, campaign calendar, dan data internal jika tersedia. - Detail deliverable, kedalaman analisis, workshop, revision round, dan SLA perlu ditetapkan dalam SOW karena belum otomatis melekat pada platform. - Do not claim: EVO Report dapat memberikan strategi final tanpa input klien dan validasi consultant/analyst. |


## 21. Deep Social Search Feature
Sumber utama: S2 p.13-14

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Deep Social Search Feature |
| 2. Deskripsi Singkat | Fitur pencarian/pendalaman data social yang disebut untuk market research, industry monitoring, trend watch, dan issue tracking. |
| 3. Business Problem yang Diselesaikan | Analyst perlu mencari percakapan/topik spesifik di social secara lebih dalam dibanding dashboard umum; sulit menemukan evidence dan tren tersembunyi. |
| 4. Use Case / Scenario | Issue tracking, trend watch, market research, industry monitoring, brand listening, competitor/audience deep dive. |
| 5. Kapabilitas | Deep search across social dataset, keyword/topic exploration, evidence retrieval, issue/topic discovery support. |
| 6. Output yang Dihasilkan | Search results, mention evidence, topic/issue dataset, report input, supporting evidence for analysis. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Social media sources within available coverage. Fields: content, author, timestamp, URL, engagement, sentiment/topic/category where available. |
| 8. Requirement / Dependency | Search query/keyword rules, source scope, date range, language/region filters, analyst objective. |
| 9. KPI yang Bisa Dijawab | Mention volume, engagement, sentiment, top topics/words/hashtags, author/source metrics depending on search result. |
| 10. Insight yang Bisa Dihasilkan | Hidden issue discovery, audience language pattern, competitor topic, content opportunity, evidence-driven investigation. |
| 11. Limitasi Produk/Fitur | - Deep Social Search hanya dapat mencari data yang tersedia dalam coverage, indexed dataset, source, dan periode yang didukung. - Query terlalu luas dapat menghasilkan noise tinggi; query terlalu sempit dapat melewatkan variasi bahasa, typo, slang, hashtag, dan indirect mention. - Tidak semua historical social data tersedia dengan kedalaman yang sama di semua platform/provider. - Search result adalah bahan investigasi/evidence, bukan kesimpulan final tanpa clustering, sampling, dan context review. - Private/closed social spaces, deleted content, atau content yang tidak masuk coverage tidak dapat dijamin ditemukan. - Do not claim: fitur ini bisa mencari semua percakapan social media lintas platform tanpa batas historis. |


## 22. Sonar Influence
Sumber utama: S2 p.12, p.18

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Sonar Influence |
| 2. Deskripsi Singkat | Offering untuk membaca influencer/KOL/author influence dan campaign performance, disebut dalam package campaign performance dan Telkomsel case. |
| 3. Business Problem yang Diselesaikan | Client perlu memahami siapa author/influencer yang berperan, seberapa kuat pengaruh konten, dan kontribusi influencer terhadap campaign/market conversation. |
| 4. Use Case / Scenario | Campaign performance analysis, influencer/KOL profiling, competitor/content benchmark, audience reach/influence analysis, marketplace/brand movement support. |
| 5. Kapabilitas | Influencer/profile analysis, top author detection, engagement/visibility assessment, support for influencer/campaign reporting. |
| 6. Output yang Dihasilkan | Influence report/input, top author/influencer list, campaign performance insight, author/content evidence. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Social media and influencer datasets where available; fields can include author/profile, content, engagement, views/reach/potential reach, topic, sentiment, channel. |
| 8. Requirement / Dependency | Influencer/account list or campaign scope, source/channel coverage, period, KPI definition for influence, data access availability. |
| 9. KPI yang Bisa Dijawab | Engagement, views, reach/potential reach, mentions, author contribution, sentiment, content volume, campaign influence indicators. |
| 10. Insight yang Bisa Dihasilkan | Influencer driver, KOL fit, audience resonance, content amplification, competitor/influencer movement. |
| 11. Limitasi Produk/Fitur | - Influence tidak boleh dibaca hanya dari follower count; perlu melihat engagement quality, relevance, sentiment, issue context, audience fit, dan brand safety. - Author/profile data terbatas pada informasi publik dan field yang tersedia per channel; identity, interest, gender, location, dan influence signal bisa tidak lengkap. - Fake, bot, fanbase, repost account, parody account, atau buzzer activity dapat memengaruhi ranking top author/influencer. - Engagement tinggi dapat berasal dari kontroversi atau kritik, bukan selalu pengaruh positif. - Scoring methodology, influencer database coverage, dan platform support perlu divalidasi Product sebelum dijadikan janji komersial. - Do not claim: Sonar Influence otomatis menentukan KOL terbaik untuk collaboration tanpa manual brand safety review. |


## 23. Marketplace Analytics / E-commerce Analysis
Sumber utama: S2 p.13, p.18

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Marketplace Analytics / E-commerce Analysis |
| 2. Deskripsi Singkat | Offering/report untuk menganalisis marketplace/e-commerce seperti produk, harga, store, views, feedback, dan movement, sebagaimana contoh Telkomsel di Tokopedia dan Shopee. |
| 3. Business Problem yang Diselesaikan | Client sulit mengukur performa produk di marketplace, competitor movement, pricing, store performance, dan customer feedback dari e-commerce. |
| 4. Use Case / Scenario | Marketplace analysis, product/service performance monitoring, competitor pricing benchmark, store/location analysis, customer feedback categorization. |
| 5. Kapabilitas | Collect/analyze marketplace product data, compare pricing/shipping/views/feedback, isolate top stores, categorize feedback by location where available. |
| 6. Output yang Dihasilkan | Marketplace analysis report, product movement dashboard/report, competitor pricing/feedback summary, store performance insight. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | E-commerce/marketplace data where available. Fields can include product listing, price, shipping, product views, customer feedback/review, store, location, competitor/brand. |
| 8. Requirement / Dependency | Marketplace scope, product/SKU/keyword list, competitor list, platform selection, period, feedback taxonomy, access/coverage validation. |
| 9. KPI yang Bisa Dijawab | Product views, price, shipping cost, review/feedback volume/sentiment, store performance, product availability, competitor product movement. |
| 10. Insight yang Bisa Dihasilkan | Pricing gap, channel/store driver, customer feedback theme, competitor movement, product performance opportunity. |
| 11. Limitasi Produk/Fitur | - Coverage marketplace, SKU, seller, official store/reseller, review, stock, pricing, dan shipping bergantung pada platform/source yang disepakati. - Harga, diskon, stock, product views, rating, dan shipping berubah cepat sehingga setiap output harus diberi timestamp/cut-off period. - Marketplace analytics tidak otomatis membaca transaksi aktual, revenue, atau conversion jika tidak ada integrasi data internal klien. - Product matching perlu validasi karena nama produk, varian, bundle, ukuran, promo, dan duplicate listing bisa membuat comparison tidak apple-to-apple. - Review analysis hanya menggunakan review/feedback yang tersedia publik atau source terotorisasi; deleted/hidden/restricted review tidak dijamin masuk. - Anti-scraping limitation, provider availability, dan perubahan platform marketplace dapat memengaruhi freshness/completeness data. - Do not claim: semua marketplace dan semua data seller/SKU bisa diambil real-time tanpa batas. |


## 24. Mainstream Media Services / Media Monitoring Report
Sumber utama: S1 p.14-17, p.30-34, p.47-49; S2 p.13

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Mainstream Media Services / Media Monitoring Report |
| 2. Deskripsi Singkat | Service/report untuk memonitor online media, mainstream/traditional media, daily summary, dan online/mainstream media report. |
| 3. Business Problem yang Diselesaikan | PR/Comms perlu memantau pemberitaan lintas media, reputasi, coverage value, story/framing, spokesperson, dan exposure media secara rutin. |
| 4. Use Case / Scenario | Media monitoring, company daily media summary, online media report, mainstream media report, spokesperson monitoring, policy/corporate reputation tracking. |
| 5. Kapabilitas | Monitor online/print/TV/radio, calculate media metrics, identify spokesperson/story/media distribution, summarize daily/monthly coverage. |
| 6. Output yang Dihasilkan | Online media report, mainstream media report, daily summary, media value dashboard, article detail/evidence list. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Online Media, Print Media, TV, Radio, Blogs/Forums where configured. Fields: Article/title/content, media name/source, publish date, URL, media type, sentiment, spokesperson jika terdeteksi, ad value, PR value, page rank, monthly pageview, unique visitors, country rank, circulation/duration sesuai channel. |
| 8. Requirement / Dependency | Media source activation, keyword/company/spokesperson list, period/cadence, media tier/value rules, report template, recipient list. |
| 9. KPI yang Bisa Dijawab | Article count, ad value, PR value, pageview, unique visitors, country rank, circulation, duration, sentiment, spokesperson count, media distribution. |
| 10. Insight yang Bisa Dihasilkan | Media exposure, framing/story risk, spokesperson visibility, earned media value, PR impact, media outlet quality/distribution. |
| 11. Limitasi Produk/Fitur | - Coverage media bergantung pada source list, subscription, provider, data partnership, dan channel yang disepakati; tidak semua portal, blog, paywalled article, TV, radio, print, atau niche publisher otomatis tercakup. - Artikel paywall/restricted access dapat terbatas atau hanya sebagian metadata/content yang tersedia. - Duplicate, repost, syndicated/wire article, dan aggregator dapat menaikkan volume; article count perlu dibaca bersama story/theme, tier, sentiment, dan media quality. - Ad Value, PR Value, circulation, pageview, UV, page rank, dan country rank adalah estimasi/proxy, bukan revenue aktual atau dampak bisnis final. - Sentiment/framing media perlu validasi manusia karena headline dan body bisa memiliki tone berbeda. - Broadcast/print/radio dapat memiliki proses dan latency berbeda dari online media. - Do not claim: semua pemberitaan media pasti masuk dan media value adalah ROI aktual. |


## 25. Crisis Investigation Report
Sumber utama: S2 p.15, p.19-20; S1 p.107-123

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Crisis Investigation Report |
| 2. Deskripsi Singkat | Ad-hoc atau periodik report untuk menyelidiki isu/krisis berdasarkan data social, online media, alert, dan evidence drivers. |
| 3. Business Problem yang Diselesaikan | Manajemen perlu memahami akar isu, channel penyebaran, evidence utama, risiko reputasi, dan action point saat isu negatif naik. |
| 4. Use Case / Scenario | Crisis investigation, negative issue tracking, stakeholder update, escalation briefing, post-crisis review, issue audit. |
| 5. Kapabilitas | Issue reconstruction, timeline/trend analysis, sentiment/risk analysis, driver post/article, channel comparison, recommendation and response support. |
| 6. Output yang Dihasilkan | Crisis investigation report, issue timeline, evidence pack, executive summary, recommendation/action point. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Social and online media alert/report data. Fields: content, author/media, URL, timestamp, engagement, sentiment/risk, story/issue title, article/post details, state if from Smart Alert. |
| 8. Requirement / Dependency | Clear crisis scope, period, keyword/source setup, evidence validation, escalation question, stakeholder objective, report timeline/SLA. |
| 9. KPI yang Bisa Dijawab | Negative mentions/posts/articles, engagement, sentiment, channel state, story/article count, top drivers, media value, distribution by channel/source. |
| 10. Insight yang Bisa Dihasilkan | Root cause narrative, escalation path, key driver, stakeholder/media reaction, risk level, response priority, mitigation recommendation. |
| 11. Limitasi Produk/Fitur | - Crisis Investigation Report adalah analisis berbasis evidence, bukan vonis legal, vonis PR final, atau keputusan komunikasi resmi. - Report membutuhkan scope krisis, periode, keyword, source, evidence validation, stakeholder question, dan SLA yang jelas agar tidak melebar. - Data comment/reply/private source bisa tidak lengkap karena keterbatasan platform/provider; limitation ini harus ditulis dalam report jika memengaruhi kesimpulan. - Root cause tidak boleh dinyatakan absolut jika hanya ada korelasi data media/social tanpa konfirmasi internal atau external evidence tambahan. - Adhoc crisis report membutuhkan waktu produksi yang berbeda dari dashboard/alert; SLA harus disepakati berdasarkan tingkat urgensi dan kedalaman analisis. - Recommendation perlu review PR/legal/crisis team klien sebelum dijadikan statement atau response publik. - Do not claim: Sonar dapat memastikan penyebab krisis tanpa validasi manusia dan sumber pendukung. |


## 26. Audience Profiling & Persona Report
Sumber utama: S1 p.34-41, p.89-97; S2 p.12

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Audience Profiling & Persona Report |
| 2. Deskripsi Singkat | Report/analysis untuk memahami audience berdasarkan demographic proxies, interest, location, gender, topic, dan behavior indicators yang tersedia. |
| 3. Business Problem yang Diselesaikan | Brand tidak memahami audience segment, interest, location, atau topic yang mendorong conversation; campaign targeting perlu validasi dari social/media data. |
| 4. Use Case / Scenario | Audience listening, demographic-based summary, persona development, market research, campaign targeting, regional trend comparison. |
| 5. Kapabilitas | Profile audience by gender/location/interest/topic where available, label/topic segmentation, summarize demographic-based insights. |
| 6. Output yang Dihasilkan | Audience profiling report, persona report, demographic/interest/location breakdown, audience insight summary. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Social channel/profile/content data where available; location via geo-tags/text place mention; gender/interest via NLP on public profiles/content. Fields vary by channel. |
| 8. Requirement / Dependency | Campaign/dataset, demographic filters, channel support, label/topic taxonomy, validation methodology, persona/report objective. |
| 9. KPI yang Bisa Dijawab | Gender distribution, location buzz, interest mentions, topic distribution, sentiment/engagement by segment, demographic-based trend signals. |
| 10. Insight yang Bisa Dihasilkan | Audience segment behavior, regional perception, content/targeting opportunity, persona hypotheses, market shift signals. |
| 11. Limitasi Produk/Fitur | - Audience profiling memakai inferred signals dari public profile, content, geotag, text-based location, interest, atau NLP; bukan data identitas personal yang pasti. - Gender, interest, age, location, dan persona signal bisa incomplete, biased, atau tidak tersedia pada sebagian channel/user. - Sample audience dapat bias terhadap user yang aktif berbicara publik, bukan seluruh customer base atau market population. - Persona report adalah hypothesis/analytical segment yang perlu divalidasi dengan survey, CRM, sales, atau research tambahan jika dipakai untuk keputusan besar. - Privacy dan platform limitation harus diperhatikan; jangan menjanjikan data sensitive/individual-level yang tidak tersedia publik/terotorisasi. - Do not claim: persona yang dihasilkan adalah representasi pasti seluruh pelanggan klien. |


# E. Dashboard Widgets

## 27. Trend Analysis Widget
Sumber utama: S1 p.17-19

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Trend Analysis Widget |
| 2. Deskripsi Singkat | Widget time series untuk melihat buzz dan engagement dalam periode waktu agar spike/pattern dapat dibandingkan antar campaign/tag. |
| 3. Business Problem yang Diselesaikan | Analyst membutuhkan visual spesifik untuk membaca data lebih cepat, mengurangi manual pivot, dan mendukung report/dashboard berbasis evidence. |
| 4. Use Case / Scenario | Trend monitoring, spike detection, campaign performance, content strategy, customer service prioritization, competitor trend comparison. |
| 5. Kapabilitas | Line/stacked chart, time-series buzz/engagement, peak detail view, channel split option. |
| 6. Output yang Dihasilkan | Dashboard widget visualization and export. Metrics/options: General engagement, likes, comments, shares, views, reach, buzz, posts, channels; visualization line/stacked chart. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Channels applicable: All channels.. Data fields mengikuti source dan metric yang dipilih. |
| 8. Requirement / Dependency | Active campaign/tag/label source, date range, selected metrics/options, visualization type, and channel availability. |
| 9. KPI yang Bisa Dijawab | General engagement, likes, comments, shares, views, reach, buzz, posts, channels; visualization line/stacked chart. |
| 10. Insight yang Bisa Dihasilkan | Spike driver, growth pattern, timing opportunity, content resonance, competitor momentum, issue escalation timing. |
| 11. Limitasi Produk/Fitur | - Trend line mengikuti data yang sudah masuk ke campaign/source/filter; spike dapat berubah jika ada ingestion delay atau data backfill. - Spike tidak otomatis berarti krisis atau campaign success; perlu dicek sentiment, issue/story, author, media, dan evidence post/article. - Hourly/daily granularity dan peak detail bergantung pada konfigurasi, channel, dan field timestamp yang tersedia. - Perbandingan antar campaign/tag hanya fair jika periode, source, dan keyword setup sebanding. - Do not claim: trend chart menjelaskan penyebab spike tanpa evidence review. |


## 28. Sentiment Overview Widget
Sumber utama: S1 p.20-22, p.65-69

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Sentiment Overview Widget |
| 2. Deskripsi Singkat | Widget untuk menampilkan sentiment score per post berdasarkan campaign/tag dan channel menggunakan algoritma sentiment DXT360. |
| 3. Business Problem yang Diselesaikan | Analyst membutuhkan visual spesifik untuk membaca data lebih cepat, mengurangi manual pivot, dan mendukung report/dashboard berbasis evidence. |
| 4. Use Case / Scenario | Customer insight, competitor perception, crisis management, product feedback, marketing message evaluation. |
| 5. Kapabilitas | Sentiment by campaign/tag/channel, table/stacked chart visualization, supported sentiment languages: English, Bahasa Indonesia, Thai, Malay, Tagalog, Vietnamese. |
| 6. Output yang Dihasilkan | Dashboard widget visualization and export. Metrics/options: Buzz, mentions, comments, sentiment by campaign/tag, sentiment by channel; visualization table/stacked chart. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Channels applicable: All channels.. Data fields mengikuti source dan metric yang dipilih. |
| 8. Requirement / Dependency | Active campaign/tag/label source, date range, selected metrics/options, visualization type, and channel availability. |
| 9. KPI yang Bisa Dijawab | Buzz, mentions, comments, sentiment by campaign/tag, sentiment by channel; visualization table/stacked chart. |
| 10. Insight yang Bisa Dihasilkan | Sentiment trend, negative risk, positive driver, competitor perception gap, product/customer experience pain point. |
| 11. Limitasi Produk/Fitur | - Sentiment adalah hasil AI/NLP dan tidak 100% akurat, terutama untuk sarkasme, slang, bahasa campuran, ironi, meme, dan konteks lokal. - Sentiment post tidak selalu sama dengan sentiment terhadap brand; konten bisa negatif terhadap isu umum tetapi bukan terhadap klien. - Mixed sentiment sering disederhanakan menjadi satu label sehingga nuance dapat hilang. - Mentions dengan status Analyzing dapat sementara belum masuk perhitungan sentiment widget/filter. - Manual sentiment editing perlu governance agar report antar periode tetap konsisten. - Do not claim: sentiment negatif otomatis berarti krisis atau risk level tinggi. |


## 29. Top Authors Widget
Sumber utama: S1 p.22-23

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Top Authors Widget |
| 2. Deskripsi Singkat | Widget untuk menampilkan authors/users dengan engagement terbesar dalam campaign atau tag. |
| 3. Business Problem yang Diselesaikan | Analyst membutuhkan visual spesifik untuk membaca data lebih cepat, mengurangi manual pivot, dan mendukung report/dashboard berbasis evidence. |
| 4. Use Case / Scenario | KOL/author identification, relationship building, industry trend tracking, opportunity detection, marketing targeting. |
| 5. Kapabilitas | Rank top authors by selected metrics, table visualization. |
| 6. Output yang Dihasilkan | Dashboard widget visualization and export. Metrics/options: Engagements, views, ad value, mentions; visualization table. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Channels applicable: All channels.. Data fields mengikuti source dan metric yang dipilih. |
| 8. Requirement / Dependency | Active campaign/tag/label source, date range, selected metrics/options, visualization type, and channel availability. |
| 9. KPI yang Bisa Dijawab | Engagements, views, ad value, mentions; visualization table. |
| 10. Insight yang Bisa Dihasilkan | Influential author/KOL, high-impact media/source, potential collaborator, author-driven issue, media/author priority. |
| 11. Limitasi Produk/Fitur | - Top author berdasarkan engagement/mentions tidak otomatis berarti KOL paling relevan atau paling kredibel. - Author identity/profile dapat tidak lengkap atau ambigu karena nama mirip, handle berubah, fanbase, parody, repost account, atau bot-like account. - High engagement bisa berasal dari kontroversi, kritik, giveaway, atau outrage, bukan selalu influence positif. - Ranking top author perlu divalidasi manual sebelum dipakai untuk partnership, escalation, atau media/KOL targeting. - Do not claim: widget ini otomatis menentukan influencer terbaik tanpa brand safety review. |


## 30. Top Words Widget
Sumber utama: S1 p.23-25

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Top Words Widget |
| 2. Deskripsi Singkat | Widget word cloud/table untuk menampilkan kata/frasa paling sering atau relevan dari konten campaign/tag, termasuk tonality warna positif/netral/negatif. |
| 3. Business Problem yang Diselesaikan | Analyst membutuhkan visual spesifik untuk membaca data lebih cepat, mengurangi manual pivot, dan mendukung report/dashboard berbasis evidence. |
| 4. Use Case / Scenario | Theme identification, sentiment tracking, engagement vocabulary analysis, SEO/content keyword discovery, issue exploration. |
| 5. Kapabilitas | Top words by frequency/relevance, sentiment-colored wordcloud/table, keyword/theme extraction from collected content. |
| 6. Output yang Dihasilkan | Dashboard widget visualization and export. Metrics/options: By frequency, by relevance, mentions, buzz; visualization table/wordcloud. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Channels applicable: All channels.. Data fields mengikuti source dan metric yang dipilih. |
| 8. Requirement / Dependency | Active campaign/tag/label source, date range, selected metrics/options, visualization type, and channel availability. |
| 9. KPI yang Bisa Dijawab | By frequency, by relevance, mentions, buzz; visualization table/wordcloud. |
| 10. Insight yang Bisa Dihasilkan | Dominant theme, sentiment-laden wording, narrative shift, keyword opportunity, issue language used by public/media. |
| 11. Limitasi Produk/Fitur | - Frekuensi kata tidak selalu sama dengan kepentingan strategis; kata umum/brand mention/stopword bisa mendominasi jika cleaning kurang kuat. - Wordcloud dapat misleading jika tidak ada normalization, synonym merging, stopword removal, bahasa/slang handling, dan exclusion term. - Warna sentiment pada words adalah signal agregat, bukan bukti pasti bahwa semua konteks kata tersebut positif/negatif. - By Frequency dan By Relevance dapat menghasilkan daftar berbeda; pilih sesuai tujuan analisis. - Do not claim: wordcloud saja cukup untuk rekomendasi strategi tanpa membaca sample content. |


## 31. Top Hashtags Widget
Sumber utama: S1 p.25-28

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Top Hashtags Widget |
| 2. Deskripsi Singkat | Widget untuk melihat hashtag paling sering/relevan dari content dalam campaign/tag, termasuk growth rate comparison dengan periode sebelumnya. |
| 3. Business Problem yang Diselesaikan | Analyst membutuhkan visual spesifik untuk membaca data lebih cepat, mengurangi manual pivot, dan mendukung report/dashboard berbasis evidence. |
| 4. Use Case / Scenario | Hashtag visibility, trend tracking, content/campaign optimization, competitor/partner identification, industry conversation monitoring. |
| 5. Kapabilitas | Top hashtag extraction by frequency/relevance, growth comparison, stacked/pie chart visualization. |
| 6. Output yang Dihasilkan | Dashboard widget visualization and export. Metrics/options: By frequency, by relevance, buzz, mentions; visualization stacked chart/pie chart. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Channels applicable: All channels.. Data fields mengikuti source dan metric yang dipilih. |
| 8. Requirement / Dependency | Active campaign/tag/label source, date range, selected metrics/options, visualization type, and channel availability. |
| 9. KPI yang Bisa Dijawab | By frequency, by relevance, buzz, mentions; visualization stacked chart/pie chart. |
| 10. Insight yang Bisa Dihasilkan | Hashtag trend, campaign discoverability, topic association, competitor hashtag movement, social strategy opportunity. |
| 11. Limitasi Produk/Fitur | - Hashtag tinggi tidak selalu organic trend; bisa berasal dari campaign push, giveaway, bot, fandom, spam, atau coordinated posting. - Hashtag brand dapat dipakai untuk pujian maupun kritik, sehingga harus dibaca bersama sentiment dan sample content. - Growth comparison bergantung pada periode terpilih dan previous period availability; periode yang tidak sebanding bisa misleading. - Tidak semua channel/content memakai hashtag secara konsisten sehingga metric ini kurang relevan untuk beberapa source. - Do not claim: top hashtag otomatis menunjukkan campaign berhasil atau sentiment positif. |


## 32. Social Media Distribution Widget
Sumber utama: S1 p.28-30

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Social Media Distribution Widget |
| 2. Deskripsi Singkat | Widget untuk menganalisis buzz dan engagement across social channels dalam account, campaign, atau tag. |
| 3. Business Problem yang Diselesaikan | Analyst membutuhkan visual spesifik untuk membaca data lebih cepat, mengurangi manual pivot, dan mendukung report/dashboard berbasis evidence. |
| 4. Use Case / Scenario | Channel performance comparison, social strategy optimization, audience engagement mapping, competitor benchmark by social channel. |
| 5. Kapabilitas | Tabulates/analyzes social metrics by campaign/tag/channel; supports pie, stacked chart, and table view. |
| 6. Output yang Dihasilkan | Dashboard widget visualization and export. Metrics/options: General engagements, likes, shares, comments, views, reach, buzz, mentions, authors; visualization pie/stacked/table. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Channels applicable: All social channels.. Data fields mengikuti source dan metric yang dipilih. |
| 8. Requirement / Dependency | Active campaign/tag/label source, date range, selected metrics/options, visualization type, and channel availability. |
| 9. KPI yang Bisa Dijawab | General engagements, likes, shares, comments, views, reach, buzz, mentions, authors; visualization pie/stacked/table. |
| 10. Insight yang Bisa Dihasilkan | Best-performing channel, content-channel fit, engagement gap, social mix effectiveness, competitor social benchmark. |
| 11. Limitasi Produk/Fitur | - Perbandingan antar channel hanya valid jika campaign/source setup setara dan semua channel memiliki data yang cukup. - Metric seperti views, shares, reach, authors, atau engagement dapat berbeda definisi dan availability di setiap platform. - Channel dengan volume besar belum tentu paling penting jika sentiment, issue risk, atau engagement quality rendah. - Data distribution dapat berubah jika ada delay ingestion, source outage, atau update manual cleaning. - Do not claim: channel share sama dengan market share atau audience share aktual. |


## 33. Mainstream Media Distribution Widget
Sumber utama: S1 p.30-32

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Mainstream Media Distribution Widget |
| 2. Deskripsi Singkat | Widget untuk menganalisis distribusi non-social data seperti online media, print, broadcast, forum, dan blog berdasarkan campaign/tag. |
| 3. Business Problem yang Diselesaikan | Analyst membutuhkan visual spesifik untuk membaca data lebih cepat, mengurangi manual pivot, dan mendukung report/dashboard berbasis evidence. |
| 4. Use Case / Scenario | Media reach understanding, popular content/outlet tracking, marketing/PR impact measurement, competitor media benchmark. |
| 5. Kapabilitas | Tabulate non-social source distribution, channel/media name detail, pie/stacked/table visualization. |
| 6. Output yang Dihasilkan | Dashboard widget visualization and export. Metrics/options: Number of articles; visualization pie chart, stacked chart, table. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Channels applicable: Online Media, Print Media, TV, Radio, Forums, Blogs.. Data fields mengikuti source dan metric yang dipilih. |
| 8. Requirement / Dependency | Active campaign/tag/label source, date range, selected metrics/options, visualization type, and channel availability. |
| 9. KPI yang Bisa Dijawab | Number of articles; visualization pie chart, stacked chart, table. |
| 10. Insight yang Bisa Dihasilkan | Media outlet/channel driver, coverage concentration, PR exposure distribution, media channel opportunity. |
| 11. Limitasi Produk/Fitur | - Article count tidak otomatis menunjukkan kualitas coverage, reputasi, atau dampak PR; perlu dibaca bersama media tier, sentiment, story, dan value. - Coverage non-social bergantung pada source/subscription/provider; blog, forum, print, TV, radio, dan online media punya latency dan completeness berbeda. - Duplicate, syndication, wire, dan aggregator dapat menaikkan volume secara artifisial. - Perbandingan outlet/channel harus mempertimbangkan media size, geography, audience, dan publication type. - Do not claim: jumlah artikel tinggi selalu berarti coverage positif atau berhasil. |


## 34. Mentions Widget
Sumber utama: S1 p.32-34

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Mentions Widget |
| 2. Deskripsi Singkat | Light version of My Data mentions view yang menampilkan mention data captured dengan kemampuan sorting dan channel-specific extended dataset. |
| 3. Business Problem yang Diselesaikan | Analyst membutuhkan visual spesifik untuk membaca data lebih cepat, mengurangi manual pivot, dan mendukung report/dashboard berbasis evidence. |
| 4. Use Case / Scenario | Brand reputation monitoring, opportunity detection, content strategy, market trend analysis, customer service evidence review. |
| 5. Kapabilitas | Display captured mentions, sort/filter by options, show performance and sentiment in table form, see more by channel. |
| 6. Output yang Dihasilkan | Dashboard widget visualization and export. Metrics/options: Mention, author & source, category, performance by channel, sentiment; visualization table. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Channels applicable: All channels.. Data fields mengikuti source dan metric yang dipilih. |
| 8. Requirement / Dependency | Active campaign/tag/label source, date range, selected metrics/options, visualization type, and channel availability. |
| 9. KPI yang Bisa Dijawab | Mention, author & source, category, performance by channel, sentiment; visualization table. |
| 10. Insight yang Bisa Dihasilkan | Evidence-level analysis, customer complaint/praise, competitor mention, market trend, issue/URL sample for reporting. |
| 11. Limitasi Produk/Fitur | - Mentions Widget adalah versi ringan dari My Data; untuk audit mendalam tetap perlu membuka My Data/raw export/detail URL. - Field performance berbeda per channel, sehingga tabel mention bisa tidak memiliki semua metric untuk semua source. - Mention yang muncul bergantung pada keyword, source, filter, dan indexing; bukan seluruh percakapan publik. - Sort/filter pada widget tidak selalu cukup untuk data cleansing atau deduplication. - Do not claim: Mentions Widget adalah full raw data repository. |


## 35. Gender Widget
Sumber utama: S1 p.34-36

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Gender Widget |
| 2. Deskripsi Singkat | Widget yang menganalisis public author profiles dengan NLP untuk mengekstrak gender markers male/female dan memfilter authors berdasarkan gender. |
| 3. Business Problem yang Diselesaikan | Analyst membutuhkan visual spesifik untuk membaca data lebih cepat, mengurangi manual pivot, dan mendukung report/dashboard berbasis evidence. |
| 4. Use Case / Scenario | Audience understanding, content targeting, platform selection, inclusive communication, targeted ad/audience strategy. |
| 5. Kapabilitas | Gender marker extraction from public profiles, filter authors by gender, stacked chart/table view. |
| 6. Output yang Dihasilkan | Dashboard widget visualization and export. Metrics/options: View by mentions; visualization stacked chart/table. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Channels applicable: All social channels.. Data fields mengikuti source dan metric yang dipilih. |
| 8. Requirement / Dependency | Active campaign/tag/label source, date range, selected metrics/options, visualization type, and channel availability. |
| 9. KPI yang Bisa Dijawab | View by mentions; visualization stacked chart/table. |
| 10. Insight yang Bisa Dihasilkan | Audience gender composition, targeting implications, content fit by segment, demographic reporting input. |
| 11. Limitasi Produk/Fitur | - Gender adalah inferred signal dari public profile/NLP marker dan bisa tidak lengkap, ambigu, atau salah. - Output tidak boleh diperlakukan sebagai identitas personal pasti atau data sensitif individual-level. - Akurasi dapat menurun untuk akun brand, organisasi, anonim, fanbase, multilingual profile, atau profile tanpa marker jelas. - Analisis gender sebaiknya digunakan sebagai directional aggregate, bukan dasar targeting sensitif tanpa validasi tambahan. - Do not claim: Sonar mengetahui gender aktual semua author. |


## 36. Locations Widget
Sumber utama: S1 p.36-38

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Locations Widget |
| 2. Deskripsi Singkat | Widget map untuk mengekstrak informasi geografis dari post berdasarkan geotags dan text-based place mentions. |
| 3. Business Problem yang Diselesaikan | Analyst membutuhkan visual spesifik untuk membaca data lebih cepat, mengurangi manual pivot, dan mendukung report/dashboard berbasis evidence. |
| 4. Use Case / Scenario | Location-specific content, geo-targeting, demographic/regional analysis, new area identification, location-based campaign/issue monitoring. |
| 5. Kapabilitas | Extract and plot geo information, map visualization, geotag and text-based place matching. |
| 6. Output yang Dihasilkan | Dashboard widget visualization and export. Metrics/options: Buzz; visualization map. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Channels applicable: Geotagging information: Twitter/X, Instagram. Text-based location matches: all channels.. Data fields mengikuti source dan metric yang dipilih. |
| 8. Requirement / Dependency | Active campaign/tag/label source, date range, selected metrics/options, visualization type, and channel availability. |
| 9. KPI yang Bisa Dijawab | Buzz; visualization map. |
| 10. Insight yang Bisa Dihasilkan | Regional hotspot, local issue, city/province-level conversation, geo-specific campaign opportunity. |
| 11. Limitasi Produk/Fitur | - Geotag biasanya sparse; banyak post tidak memiliki lokasi publik yang valid. - Text-based location matching dapat ambigu, misalnya nama kota yang sama, tempat dalam konteks berita, atau lokasi yang disebut tetapi bukan lokasi author. - Location bukan precise user geolocation kecuali tersedia secara publik dari geotag/source. - Regional hotspot perlu divalidasi dengan sample content agar tidak salah membaca tempat yang hanya disebut dalam narasi. - Do not claim: widget ini melacak lokasi real-time pengguna secara akurat. |


## 37. Peak Hours Widget
Sumber utama: S1 p.38-39

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Peak Hours Widget |
| 2. Deskripsi Singkat | Widget yang mengagregasi buzz volume per jam dan meranking jam dengan buzz paling banyak. |
| 3. Business Problem yang Diselesaikan | Analyst membutuhkan visual spesifik untuk membaca data lebih cepat, mengurangi manual pivot, dan mendukung report/dashboard berbasis evidence. |
| 4. Use Case / Scenario | Posting schedule optimization, time-of-day engagement analysis, content planning, social activity monitoring. |
| 5. Kapabilitas | Aggregate buzz by hour period, rank peak hours, bar chart visualization. |
| 6. Output yang Dihasilkan | Dashboard widget visualization and export. Metrics/options: Buzz; visualization bar chart. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Channels applicable: All social channels.. Data fields mengikuti source dan metric yang dipilih. |
| 8. Requirement / Dependency | Active campaign/tag/label source, date range, selected metrics/options, visualization type, and channel availability. |
| 9. KPI yang Bisa Dijawab | Buzz; visualization bar chart. |
| 10. Insight yang Bisa Dihasilkan | Audience activity window, best posting time hypothesis, issue timing, campaign timing optimization. |
| 11. Limitasi Produk/Fitur | - Peak buzz menunjukkan jam percakapan terbanyak, bukan otomatis jam terbaik untuk conversion, reach, atau posting performance. - Hasil dipengaruhi timezone, selected period, data delay, campaign spikes, dan event tertentu. - Untuk multi-market, timezone dan cut-off harus disepakati agar tidak salah membaca jam aktif audience. - Peak hour perlu dibaca bersama engagement quality, sentiment, content type, dan channel behavior. - Do not claim: peak hour widget memberikan jadwal posting terbaik secara pasti tanpa A/B test atau konteks channel. |


## 38. Interest Widget
Sumber utama: S1 p.39-41

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Interest Widget |
| 2. Deskripsi Singkat | Widget yang menganalisis author profiles dan content dengan NLP untuk mengekstrak theme/topic interest dari public signals. |
| 3. Business Problem yang Diselesaikan | Analyst membutuhkan visual spesifik untuk membaca data lebih cepat, mengurangi manual pivot, dan mendukung report/dashboard berbasis evidence. |
| 4. Use Case / Scenario | Content tailoring, platform choice, targeted ads, market research, competitor differentiation by audience interest. |
| 5. Kapabilitas | Interest extraction from public profiles/content, filter by preset interests, bubble chart visualization. |
| 6. Output yang Dihasilkan | Dashboard widget visualization and export. Metrics/options: View by mentions; visualization bubble chart. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Channels applicable: Twitter/X and Instagram.. Data fields mengikuti source dan metric yang dipilih. |
| 8. Requirement / Dependency | Active campaign/tag/label source, date range, selected metrics/options, visualization type, and channel availability. |
| 9. KPI yang Bisa Dijawab | View by mentions; visualization bubble chart. |
| 10. Insight yang Bisa Dihasilkan | Audience interest cluster, content opportunity, audience-brand fit, competitor audience differentiation, targeting hypothesis. |
| 11. Limitasi Produk/Fitur | - Interest adalah inferred signal dari public profile/content dan hanya berlaku pada channel yang didukung; hasil dapat incomplete atau tidak mewakili seluruh audience. - Interest cluster dapat bias terhadap user yang aktif menulis di publik, bukan seluruh customer base. - Akun brand, bot, fanbase, atau akun anonim bisa mengganggu akurasi interest extraction. - Gunakan sebagai hypothesis untuk content/targeting, bukan data personal pasti. - Do not claim: Sonar mengetahui minat pribadi semua audience secara pasti. |


## 39. Spokespersons Widget
Sumber utama: S1 p.41-42

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Spokespersons Widget |
| 2. Deskripsi Singkat | Widget NLP untuk mengidentifikasi key personalities atau spokesperson yang memberi statement atau dikutip dalam artikel. |
| 3. Business Problem yang Diselesaikan | Analyst membutuhkan visual spesifik untuk membaca data lebih cepat, mengurangi manual pivot, dan mendukung report/dashboard berbasis evidence. |
| 4. Use Case / Scenario | PR team perlu melacak siapa yang dikutip, pengaruh stakeholder, media relations, public opinion, misrepresentation, dan competitor statements. |
| 5. Kapabilitas | Identify quoted personalities/spokespersons, table visualization, publication/article count. |
| 6. Output yang Dihasilkan | Dashboard widget visualization and export. Metrics/options: Publications/articles; visualization table. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Channels applicable: Online Media, Print, TV.. Data fields mengikuti source dan metric yang dipilih. |
| 8. Requirement / Dependency | Active campaign/tag/label source, date range, selected metrics/options, visualization type, and channel availability. |
| 9. KPI yang Bisa Dijawab | Publications/articles; visualization table. |
| 10. Insight yang Bisa Dihasilkan | Spokesperson visibility, executive/media impact, stakeholder framing, media relation target, competitor/public figure narrative. |
| 11. Limitasi Produk/Fitur | - NLP spokesperson extraction dapat miss nama/jabatan atau salah membaca kutipan, terutama pada artikel kompleks, OCR print/TV, atau struktur berita yang noisy. - Nama yang sama, gelar berbeda, alias, dan organisasi/person entity bisa menyebabkan ambiguity. - Kutipan langsung, tidak langsung, dan mention nama tanpa statement perlu dibedakan saat membuat report PR/executive. - Untuk executive reporting, hasil wajib divalidasi manual dengan artikel sumber. - Do not claim: semua kutipan spokesperson pasti terdeteksi sempurna. |


## 40. Topic Overview Widget
Sumber utama: S1 p.43-45

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Topic Overview Widget |
| 2. Deskripsi Singkat | NLP-based topic discovery widget untuk melihat distribusi topik dalam industry vertical berdasarkan campaign setup. |
| 3. Business Problem yang Diselesaikan | Analyst membutuhkan visual spesifik untuk membaca data lebih cepat, mengurangi manual pivot, dan mendukung report/dashboard berbasis evidence. |
| 4. Use Case / Scenario | Industry trend discovery, audience needs understanding, brand awareness/reputation, engagement opportunity, competitor tracking. |
| 5. Kapabilitas | Topic by campaign/tag, topic by sentiment, industry-dependent topic discovery, stacked chart visualization. |
| 6. Output yang Dihasilkan | Dashboard widget visualization and export. Metrics/options: Buzz, mentions, topic by campaign/tag, topic by sentiment; visualization stacked chart. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Channels applicable: All channels.. Data fields mengikuti source dan metric yang dipilih. |
| 8. Requirement / Dependency | Active campaign/tag/label source, date range, selected metrics/options, visualization type, and channel availability. |
| 9. KPI yang Bisa Dijawab | Buzz, mentions, topic by campaign/tag, topic by sentiment; visualization stacked chart. |
| 10. Insight yang Bisa Dihasilkan | Topic driver, emerging industry trend, audience need, competitor topical position, sentiment by topic. |
| 11. Limitasi Produk/Fitur | - Topic output sangat bergantung pada industry selection, taxonomy, campaign setup, dan data input. - Topic dapat overlap; satu post/artikel bisa membahas beberapa isu tetapi sistem mungkin menampilkan topic dominan. - Topik yang sering muncul belum tentu strategis; perlu dibaca bersama sentiment, engagement, author, media tier, dan trend. - Taxonomy perlu tuning per industri/klien agar tidak terlalu generic atau salah konteks. - Do not claim: topic overview otomatis memberikan final issue taxonomy tanpa sampling QA. |


## 41. Sentence Type Widget
Sumber utama: S1 p.45-47

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Sentence Type Widget |
| 2. Deskripsi Singkat | NLP widget untuk mengidentifikasi jenis speech atau underlying theme dalam post, seperti complaint, question, promotion, giveaway, request, dan lainnya. |
| 3. Business Problem yang Diselesaikan | Analyst membutuhkan visual spesifik untuk membaca data lebih cepat, mengurangi manual pivot, dan mendukung report/dashboard berbasis evidence. |
| 4. Use Case / Scenario | Brand perlu memahami pola percakapan: complaint, request, question, suggestion, promotion, announcement, CS response, etc. untuk mengarahkan response/strategy. |
| 5. Kapabilitas | Classify sentence types, show buzz/mentions by sentence type, table/bar chart visualization. |
| 6. Output yang Dihasilkan | Dashboard widget visualization and export. Metrics/options: Sentence types: wish, request, potential fraud, donation, suggestion, offering, question, apology, invitation, greeting, thanking, promotion, giveaway, complaint, customer service response, tip, appreciation, announcement, information, encouragement. Buzz, mentions; visualization table/bar chart. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Channels applicable: Social channels.. Data fields mengikuti source dan metric yang dipilih. |
| 8. Requirement / Dependency | Active campaign/tag/label source, date range, selected metrics/options, visualization type, and channel availability. |
| 9. KPI yang Bisa Dijawab | Sentence types: wish, request, potential fraud, donation, suggestion, offering, question, apology, invitation, greeting, thanking, promotion, giveaway, complaint, customer service response, tip, appreciation, announcement, information, encouragement. Buzz, mentions; visualization table/bar chart. |
| 10. Insight yang Bisa Dihasilkan | Complaint/request trend, customer service signal, campaign/promotion behavior, audience intent, fraud/issue signal. |
| 11. Limitasi Produk/Fitur | - Sentence classification sensitif terhadap bahasa informal, sarkasme, slang, typo, short text, dan mixed language. - Satu post bisa berisi beberapa intensi seperti complaint + question + request, tetapi sistem dapat memilih kategori dominan saja. - Kategori seperti potential fraud, complaint, atau customer service response perlu validasi manusia sebelum digunakan untuk keputusan operasional/eskalasi. - Taxonomy sentence type belum tentu cocok untuk semua industri tanpa penyesuaian definisi. - Do not claim: sentence type selalu membaca intensi user secara sempurna. |


## 42. Media Value Widget
Sumber utama: S1 p.47-49

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Media Value Widget |
| 2. Deskripsi Singkat | Widget untuk menghitung dan menampilkan media value seperti Ad Value dan PR Value dari selected campaigns/tags berdasarkan industry formulas. |
| 3. Business Problem yang Diselesaikan | Analyst membutuhkan visual spesifik untuk membaca data lebih cepat, mengurangi manual pivot, dan mendukung report/dashboard berbasis evidence. |
| 4. Use Case / Scenario | PR team perlu mengukur ROI/media exposure value dan membandingkan nilai earned media dengan paid advertising equivalent. |
| 5. Kapabilitas | Calculate/tabulate Ad Value and PR Value, stacked chart visualization. |
| 6. Output yang Dihasilkan | Dashboard widget visualization and export. Metrics/options: Ad Value, PR Value; visualization stacked chart. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Channels applicable: Online Media, Print, TV, Radio.. Data fields mengikuti source dan metric yang dipilih. |
| 8. Requirement / Dependency | Active campaign/tag/label source, date range, selected metrics/options, visualization type, and channel availability. |
| 9. KPI yang Bisa Dijawab | Ad Value, PR Value; visualization stacked chart. |
| 10. Insight yang Bisa Dihasilkan | Earned media value, PR ROI, channel/outlet value contribution, campaign/media impact benchmark. |
| 11. Limitasi Produk/Fitur | - Ad Value dan PR Value adalah proxy/estimasi berdasarkan formula dan media rate assumptions, bukan revenue, sales impact, atau ROI aktual. - Nilai dapat berbeda jika formula, source rate, media tier, placement, duration, circulation, atau pageview assumptions berubah. - Media value harus dibaca bersama sentiment, framing, outlet quality, story relevance, dan spokesperson, bukan angka tunggal. - Tidak semua channel/source memiliki data value yang lengkap atau comparable. - Do not claim: PR Value/Ad Value adalah nilai bisnis aktual yang pasti diterima klien. |


## 43. Competitive Analysis / Share of Voice Widget
Sumber utama: S1 p.49-51

| 11 Poin Capability | Isi |
| --- | --- |
| 1. Nama Produk/Fitur | Competitive Analysis / Share of Voice Widget |
| 2. Deskripsi Singkat | Widget untuk membandingkan berbagai metrics dari campaign/tag aktif, sering digunakan sebagai Share of Voice atau competitive benchmarking. |
| 3. Business Problem yang Diselesaikan | Analyst membutuhkan visual spesifik untuk membaca data lebih cepat, mengurangi manual pivot, dan mendukung report/dashboard berbasis evidence. |
| 4. Use Case / Scenario | Client perlu membandingkan performance brand vs competitor, menemukan opportunity, benchmark performance, dan membaca reputasi/industry position. |
| 5. Kapabilitas | Compare selected campaigns/tags, plot metric comparison in table/bar/pie, support SOV and benchmark analysis. |
| 6. Output yang Dihasilkan | Dashboard widget visualization and export. Metrics/options: Engagements, likes, comments, reach, shares, views, authors, posts, buzz; visualization table, bar chart, pie chart. |
| 7. Data Source Coverage dan Data yang Bisa Diambil | Channels applicable: All channels.. Data fields mengikuti source dan metric yang dipilih. |
| 8. Requirement / Dependency | Active campaign/tag/label source, date range, selected metrics/options, visualization type, and channel availability. |
| 9. KPI yang Bisa Dijawab | Engagements, likes, comments, reach, shares, views, authors, posts, buzz; visualization table, bar chart, pie chart. |
| 10. Insight yang Bisa Dihasilkan | Share of voice, competitor gap, brand position, content strategy benchmark, issue/opportunity vs competitor. |
| 11. Limitasi Produk/Fitur | - Comparison hanya fair jika campaign/tag, keyword quality, source coverage, selected period, dan channel scope antar brand setara. - Share of Voice adalah porsi percakapan/media exposure, bukan market share, sales share, atau pangsa pasar aktual. - Buzz/engagement tinggi pada kompetitor bisa disebabkan krisis, complaint, giveaway, fandom, atau viral negatif, bukan selalu performa lebih baik. - Kompetitor dengan fanbase besar dapat terlihat dominan jika tidak ada normalisasi seperti engagement per post, sentiment ratio, media tier, atau issue quality. - Jika keyword kompetitor tidak lengkap, campaign competitor movement bisa terlewat. - Do not claim: SOV otomatis menunjukkan brand leader di pasar atau penjualan. |


# 5. Catatan Validasi Lanjutan
- Pastikan Product/Tech melengkapi coverage source per package, negara, historical availability, data freshness, retention, dan batas API/provider per channel.
- Pastikan Sales/BD menambahkan daftar do-not-claim pada enablement internal, terutama untuk private data, reach/impression akun kompetitor, dan market share/revenue aktual.
- Pastikan CX/Insight menambahkan SOP QA untuk sentiment, topic, sentence type, gender/interest/location inference, dan Smart Alert state/risk sebelum dikirim ke klien.
- Pastikan setiap report/alert memiliki contoh output final agar LLM dapat meniru format deliverable yang benar.
- Pastikan dokumen ini dipakai sebagai reference material di semua prompt: pre-sales, sales deck, onboarding, deliverable generator, dan report generator.

# 6. Source List
- S1 - List Produk_Fitur Sonar.pdf: dokumentasi DXT360 Platform, DXT360 Analytics, library, widgets, My Data, Raw Data Export, AI Insight Summary, AI Report, Smart Alert.
- S2 - Dataxet Sonar Indonesia (1).pdf: sales deck Dataxet Sonar Indonesia yang menjelaskan offering, coverage, workflow, tailored solutions, research/service offerings, dan case studies.
