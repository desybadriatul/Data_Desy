// ============================================================
//  Dataxet:Sonar  ·  Master Deck Engine
//  Usage:  node build_deck.js <client>      (default: leminerale)
//  Theme + logos come from ./theme.js. Slide CONTENT below is
//  Le Minerale's; copy this file per deck and swap the content,
//  keeping the same components for a consistent house style.
// ============================================================
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const FA = require("react-icons/fa");

const ROOT = path.join(__dirname, "..");
const THEME = require("./theme");
const CLIENT = process.argv[2] || "leminerale";
const client = THEME.clients[CLIENT];
if (!client) { console.error("Unknown client '" + CLIENT + "'. Options: " + Object.keys(THEME.clients).join(", ")); process.exit(1); }

// Palette: client tokens + safe defaults
const C = Object.assign({ white: "FFFFFF", ink: "16203A", slate: "5C6A86", line: "DCE7F4" }, client.colors);
const FONT_H = THEME.fonts.header;
const FONT_B = THEME.fonts.body;

const LOGO = {
  dxt: { p: path.join(ROOT, THEME.logoAgency), w: 1.7, h: 0.214 },
  lm:  { p: path.join(ROOT, client.logoClient), w: 0.66, h: 0.66 },
};
async function prepLogos() {
  const d = await sharp(LOGO.dxt.p).metadata(), l = await sharp(LOGO.lm.p).metadata();
  LOGO.dxt.h = LOGO.dxt.w * d.height / d.width;
  LOGO.lm.w  = LOGO.lm.h  * l.width  / l.height;
}

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
const PW = 13.33, PH = 7.5, M = 0.7;

const iconCache = {};
async function icon(Comp, color, size = 256) {
  const key = Comp.name + color + size;
  if (iconCache[key]) return iconCache[key];
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color, size: String(size) }));
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  const d = "image/png;base64," + png.toString("base64");
  iconCache[key] = d; return d;
}
const shadow = () => ({ type: "outer", color: "0E2A6B", blur: 9, offset: 3, angle: 90, opacity: 0.12 });
const softShadow = () => ({ type: "outer", color: "000000", blur: 7, offset: 2, angle: 90, opacity: 0.10 });

function logoLeft(slide) {
  slide.addImage({ path: LOGO.dxt.p, x: M, y: 0.55 - LOGO.dxt.h / 2, w: LOGO.dxt.w, h: LOGO.dxt.h });
}
function logoRight(slide) {
  slide.addImage({ path: LOGO.lm.p, x: PW - M - LOGO.lm.w, y: 0.55 - LOGO.lm.h / 2, w: LOGO.lm.w, h: LOGO.lm.h });
}
function header(slide, eyebrow, eyebrowColor) {
  logoLeft(slide); logoRight(slide);
  if (eyebrow) {
    slide.addText(eyebrow.toUpperCase(), { x: M, y: 1.02, w: 7, h: 0.34, fontFace: FONT_B, fontSize: 12.5, bold: true, color: eyebrowColor || C.blueMid, charSpacing: 3, align: "left", valign: "middle", margin: 0 });
  }
}
function footer(slide, n) {
  slide.addText("CONFIDENTIAL · Le Minerale × dataxet:sonar", { x: M, y: PH - 0.5, w: 7, h: 0.3, fontFace: FONT_B, fontSize: 8.5, color: C.slate, align: "left", valign: "middle", margin: 0 });
  slide.addText(`${n} / 11`, { x: PW - M - 1.2, y: PH - 0.5, w: 1.2, h: 0.3, fontFace: FONT_B, fontSize: 9, color: C.slate, align: "right", valign: "middle", margin: 0 });
}
function title(slide, txt, y = 1.42, w = PW - 2 * M, color = C.navy) {
  slide.addText(txt, { x: M, y, w, h: 1.12, fontFace: FONT_H, fontSize: 23.5, bold: true, color, align: "left", valign: "top", lineSpacingMultiple: 1.0, margin: 0 });
}
function subtitle(slide, txt, y, w = PW - 2 * M) {
  slide.addText(txt, { x: M, y, w, h: 0.7, fontFace: FONT_B, fontSize: 13.5, color: C.slate, align: "left", valign: "top", lineSpacingMultiple: 1.05, margin: 0 });
}
function iconChip(slide, x, y, data, size = 0.46, bg = C.blue) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: size, h: size, rectRadius: 0.08, fill: { color: bg }, shadow: softShadow() });
  const pad = size * 0.24;
  slide.addImage({ data, x: x + pad / 2, y: y + pad / 2, w: size - pad, h: size - pad });
}
function kicker(slide, txt, y) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y, w: PW - 2 * M, h: 0.62, rectRadius: 0.06, fill: { color: C.navy } });
  slide.addText(txt, { x: M + 0.3, y, w: PW - 2 * M - 0.6, h: 0.62, fontFace: FONT_B, fontSize: 12.5, italic: true, color: C.white, align: "left", valign: "middle", margin: 0 });
}
// dashed placeholder; if promptText given -> diagram illustration placeholder with GPT Image prompt
async function placeholder(slide, x, y, w, h, label, promptText) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.06, fill: { color: C.blueSoft }, line: { color: C.blue, width: 1.25, dashType: "dash" } });
  const ic = await icon(promptText ? FA.FaProjectDiagram : FA.FaImage, "#2E86C8");
  slide.addImage({ data: ic, x: x + w / 2 - 0.22, y: y + 0.2, w: 0.44, h: 0.44 });
  slide.addText(label, { x: x + 0.2, y: y + 0.66, w: w - 0.4, h: 0.3, fontFace: FONT_B, fontSize: 10.5, bold: true, color: C.blue, align: "center", valign: "middle", charSpacing: 1, margin: 0 });
  if (promptText) {
    slide.addText(promptText, { x: x + 0.28, y: y + 1.0, w: w - 0.56, h: h - 1.18, fontFace: "Courier New", fontSize: 8.6, italic: true, color: C.slate, align: "left", valign: "top", lineSpacingMultiple: 1.04, margin: 0 });
  }
}

async function build() {
  await prepLogos();
  // ============ SLIDE 1 — COVER (light, fresh) ============
  {
    const s = pres.addSlide();
    s.background = { color: "F7FBFF" };
    s.addShape(pres.shapes.OVAL, { x: PW - 4.6, y: -2.9, w: 6.6, h: 6.6, fill: { color: C.blueSoft } });
    s.addShape(pres.shapes.OVAL, { x: PW - 2.6, y: PH - 2.4, w: 4.4, h: 4.4, fill: { color: "EAF3FC" } });
    logoLeft(s); logoRight(s);

    s.addText("SALES DECK · NARRATIVE EFFECTIVENESS INTELLIGENCE", { x: M, y: 1.62, w: 10.5, h: 0.4, fontFace: FONT_B, fontSize: 12.5, bold: true, color: C.blueMid, charSpacing: 3, margin: 0 });
    s.addText("Anda Menang Lebih Cepat\nDari Yang Bisa Anda Ukur", { x: M, y: 2.1, w: 11.5, h: 1.7, fontFace: FONT_H, fontSize: 41, bold: true, color: C.navy, lineSpacingMultiple: 1.02, margin: 0 });
    s.addText("Dari lima narasi yang Anda jalankan, mana yang benar-benar menggerakkan preferensi, bukan sekadar paling ramai?", { x: M, y: 3.85, w: 9.3, h: 0.8, fontFace: FONT_B, fontSize: 14.5, color: C.slate, italic: true, lineSpacingMultiple: 1.08, margin: 0 });
    s.addText("Le Minerale · Tim Marketing & Digital · Juni 2026", { x: M, y: 4.66, w: 9, h: 0.35, fontFace: FONT_B, fontSize: 12, color: C.slate, margin: 0 });

    const stats = [
      { big: "4,6% → 18,8%", lab: "Top Brand Index Le Minerale (2021–2024)", c: C.blueMid },
      { big: "62,5% → 46,9%", lab: "Pangsa Aqua melemah di periode yang sama", c: C.navy },
      { big: "Gold", lab: "Marketeers Youth Choice 2025, pilihan Gen Z", c: C.red },
    ];
    const cw = 3.74, gap = 0.34, x0 = M, cy = 5.35, ch = 1.35;
    stats.forEach((st, i) => {
      const x = x0 + i * (cw + gap);
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: cy, w: cw, h: ch, rectRadius: 0.1, fill: { color: C.white }, line: { color: C.line, width: 1 }, shadow: softShadow() });
      s.addText(st.big, { x: x + 0.25, y: cy + 0.18, w: cw - 0.5, h: 0.55, fontFace: FONT_H, fontSize: 23, bold: true, color: st.c, align: "left", valign: "middle", margin: 0 });
      s.addText(st.lab, { x: x + 0.25, y: cy + 0.72, w: cw - 0.5, h: 0.5, fontFace: FONT_B, fontSize: 10.5, color: C.slate, align: "left", valign: "top", lineSpacingMultiple: 1.0, margin: 0 });
    });
    s.addText("DRAFT · SIMULATION ONLY · NOT CLIENT CONFIRMED", { x: PW - M - 5, y: PH - 0.5, w: 5, h: 0.3, fontFace: FONT_B, fontSize: 8.5, color: "9AA9C2", align: "right", margin: 0 });
  }

  // ============ SLIDE 2 — MASALAH ============
  {
    const s = pres.addSlide();
    s.background = { color: C.cloud };
    header(s, "Masalah", C.red);
    title(s, "Lima Narasi Berjalan Serentak, Tapi Narasi Pemenang Masih Ditebak");
    subtitle(s, "Narasi yang paling ramai belum tentu yang menggerakkan preferensi. Tanpa ukuran efektivitas per narasi, 'ramai' mudah keliru dibaca sebagai 'menang'.", 2.55);
    const items = [
      { ic: FA.FaTint, t: "Mineral Alami", d: "“Kaya ada manis-manisnya”, diferensiasi rasa dan kandungan" },
      { ic: FA.FaShieldAlt, t: "BPA Free", d: "Galon PET vs polikarbonat: paling membedakan, paling sensitif" },
      { ic: FA.FaRunning, t: "Active Lifestyle", d: "JRF & JAKIM, Running Squad, endorsement atlet" },
      { ic: FA.FaHeart, t: "Keluarga Sehat", d: "Positioning sehat untuk konsumsi harian keluarga" },
      { ic: FA.FaTrophy, t: "Sponsorship Event", d: "Official Mineral Water event berstandar internasional" },
    ];
    const cw = 2.27, gap = 0.16, x0 = M, cy = 3.15, ch = 2.3;
    for (let i = 0; i < items.length; i++) {
      const it = items[i]; const x = x0 + i * (cw + gap);
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: cy, w: cw, h: ch, rectRadius: 0.09, fill: { color: C.white }, line: { color: C.line, width: 1 }, shadow: softShadow() });
      iconChip(s, x + 0.26, cy + 0.28, await icon(it.ic, "#FFFFFF"), 0.5, C.navy);
      s.addText("?", { x: x + cw - 0.74, y: cy + 0.2, w: 0.5, h: 0.5, fontFace: FONT_H, fontSize: 24, bold: true, color: C.redSoft, align: "right", valign: "top", margin: 0 });
      s.addText(it.t, { x: x + 0.26, y: cy + 0.95, w: cw - 0.5, h: 0.4, fontFace: FONT_B, fontSize: 13.5, bold: true, color: C.ink, margin: 0 });
      s.addText(it.d, { x: x + 0.26, y: cy + 1.32, w: cw - 0.5, h: 0.9, fontFace: FONT_B, fontSize: 10.5, color: C.slate, lineSpacingMultiple: 1.03, margin: 0 });
    }
    kicker(s, "Tanpa ukuran efektivitas per narasi, setiap rupiah campaign berikutnya bertaruh pada tebakan.", 5.8);
    footer(s, 2);
  }

  // ============ SLIDE 3 — BIAYA DIAM ============
  {
    const s = pres.addSlide();
    s.background = { color: C.cloud };
    header(s, "Biaya Diam", C.red);
    title(s, "Tiga Hal Sudah Terjadi, Berjalan Tanpa Terukur");
    subtitle(s, "Pendatang baru sudah menyasar audiens inti Anda, eksposur sponsorship besar sudah berlalu, dan medan narasi paling sensitif sedang aktif, semuanya tanpa ukuran untuk membacanya.", 2.5);
    const items = [
      { ic: FA.FaChartLine, t: "Pesaing baru sudah bergerak", d: "Aquviva (Wings) masuk 25 Feb 2025 dengan target eksplisit Gen Z, audiens inti Anda. Share-nya tumbuh tanpa terpantau." },
      { ic: FA.FaCalendarTimes, t: "Eksposur besar sudah berlalu", d: "JRF 27.300 pelari dan JAKIM 31.000+ peserta sudah lewat. Eksposurnya tak bisa ditarik ulang menjadi ukuran preferensi." },
      { ic: FA.FaExclamationTriangle, t: "Medan narasi sensitif aktif", d: "Regulasi BPA BPOM 6/2024 dalam masa transisi. Narasi BPA Free Anda berpolemik tanpa early-warning sentimen." },
    ];
    const cw = 3.84, gap = 0.27, x0 = M, cy = 3.2, ch = 2.45;
    for (let i = 0; i < items.length; i++) {
      const it = items[i]; const x = x0 + i * (cw + gap);
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: cy, w: cw, h: ch, rectRadius: 0.1, fill: { color: C.white }, line: { color: C.line, width: 1 }, shadow: softShadow() });
      iconChip(s, x + 0.3, cy + 0.32, await icon(it.ic, "#FFFFFF"), 0.56, i === 2 ? C.red : C.navy);
      s.addText(it.t, { x: x + 0.3, y: cy + 1.08, w: cw - 0.6, h: 0.5, fontFace: FONT_B, fontSize: 15, bold: true, color: C.ink, lineSpacingMultiple: 1.0, margin: 0 });
      s.addText(it.d, { x: x + 0.3, y: cy + 1.55, w: cw - 0.6, h: 0.85, fontFace: FONT_B, fontSize: 11, color: C.slate, lineSpacingMultiple: 1.05, margin: 0 });
    }
    kicker(s, "Yang sudah terjadi menciptakan urgensi nyata. Yang mungkin terjadi hanya menciptakan kecemasan abstrak.", 5.95);
    footer(s, 3);
  }

  // ============ SLIDE 4 — BUKTI MOMENTUM ============
  {
    const s = pres.addSlide();
    s.background = { color: C.cloud };
    header(s, "Bukti Momentum", C.blueMid);
    title(s, "Momentum Sebesar Ini Terlalu Mahal Untuk Ditebak");
    subtitle(s, "Pertumbuhan yang menggeser dominasi puluhan tahun layak diarahkan dengan data. Ruang rebutan pangsa masih terbuka lebar.", 2.4);
    const stats = [
      { n: "↗ +14,2 pt", l: "Top Brand Index Le Minerale naik sekitar 4× lipat (2021–2024)", c: C.blueMid },
      { n: "↘ –15,6 pt", l: "Aqua, sang market leader, melemah di periode yang sama", c: C.red },
      { n: "USD ~3,9 M", l: "Nilai pasar AMDK 2024, ruang rebutan masih terbuka", c: C.navy },
    ];
    const sx = M, sw = 5.2; let sy = 3.0;
    stats.forEach((st) => {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: sx, y: sy, w: sw, h: 0.92, rectRadius: 0.09, fill: { color: C.white }, line: { color: C.line, width: 1 }, shadow: softShadow() });
      s.addText(st.n, { x: sx + 0.28, y: sy + 0.05, w: 2.1, h: 0.82, fontFace: FONT_H, fontSize: 21, bold: true, color: st.c, align: "left", valign: "middle", margin: 0 });
      s.addText(st.l, { x: sx + 2.45, y: sy + 0.05, w: sw - 2.7, h: 0.82, fontFace: FONT_B, fontSize: 10.5, color: C.slate, align: "left", valign: "middle", lineSpacingMultiple: 1.0, margin: 0 });
      sy += 1.04;
    });
    s.addText("Top Brand Index: Le Minerale vs Aqua", { x: 6.5, y: 2.95, w: 6, h: 0.35, fontFace: FONT_B, fontSize: 12.5, bold: true, color: C.ink, margin: 0 });
    s.addChart(pres.charts.BAR, [
      { name: "Le Minerale", labels: ["2021", "2024"], values: [4.6, 18.8] },
      { name: "Aqua", labels: ["2021", "2024"], values: [62.5, 46.9] },
    ], {
      x: 6.45, y: 3.32, w: 6.15, h: 2.6, barDir: "col",
      chartColors: [C.blueMid, C.slate], chartArea: { fill: { color: C.cloud } },
      catAxisLabelColor: C.slate, catAxisLabelFontSize: 11, catAxisLabelFontFace: FONT_B,
      valAxisHidden: true, valGridLine: { style: "none" },
      showValue: true, dataLabelPosition: "outEnd", dataLabelColor: C.ink, dataLabelFontSize: 10, dataLabelFontBold: true, dataLabelFormatCode: '0.0"%"',
      showLegend: true, legendPos: "b", legendColor: C.slate, legendFontSize: 10, legendFontFace: FONT_B, barGapWidthPct: 60,
    });
    s.addText("Sumber: enciety.co (2024–2025)", { x: 6.45, y: 6.0, w: 6, h: 0.25, fontFace: FONT_B, fontSize: 8.5, italic: true, color: C.slate, margin: 0 });
    kicker(s, "Pasar AMDK Indonesia sekitar USD 3,9 miliar (2024). Setiap poin preferensi punya nilai nyata.", 6.3);
    footer(s, 4);
  }

  // ============ SLIDE 5 — WAWASAN STRATEGIS ============
  {
    const s = pres.addSlide();
    s.background = { color: C.cloud };
    header(s, "Wawasan Strategis", C.blueMid);
    title(s, "Volume Mengukur Seberapa Ramai. Efektivitas Mengukur Apa Yang Mengubah Preferensi.");
    subtitle(s, "Efektivitas narasi adalah perpaduan tiga lapis yang bersama-sama memisahkan 'ramai' dari 'menggerakkan'.", 2.55);
    const comps = [
      { n: "1", ic: FA.FaComments, t: "Share of Conversation", d: "Seberapa besar ruang percakapan yang ditempati tiap narasi, bukan sekadar volume mentah." },
      { n: "2", ic: FA.FaSmile, t: "Sentimen per Narasi", d: "Apakah narasi diterima positif, atau berisiko berbalik (mis. BPA Free)." },
      { n: "3", ic: FA.FaBolt, t: "Engagement Quality", d: "Kedalaman interaksi nyata, bukan reach pasif yang tak menggerakkan preferensi." },
    ];
    const cw = 3.18, cy = 3.25, ch = 2.4, gap = 0.55, x0 = M;
    for (let i = 0; i < comps.length; i++) {
      const it = comps[i]; const x = x0 + i * (cw + gap);
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: cy, w: cw, h: ch, rectRadius: 0.1, fill: { color: C.white }, line: { color: C.line, width: 1 }, shadow: softShadow() });
      s.addShape(pres.shapes.OVAL, { x: x + 0.28, y: cy + 0.3, w: 0.56, h: 0.56, fill: { color: C.blueSoft } });
      s.addText(it.n, { x: x + 0.28, y: cy + 0.3, w: 0.56, h: 0.56, fontFace: FONT_H, fontSize: 20, bold: true, color: C.blue, align: "center", valign: "middle", margin: 0 });
      iconChip(s, x + cw - 0.82, cy + 0.32, await icon(it.ic, "#FFFFFF"), 0.5, C.navy);
      s.addText(it.t, { x: x + 0.28, y: cy + 1.02, w: cw - 0.56, h: 0.5, fontFace: FONT_B, fontSize: 13.5, bold: true, color: C.ink, lineSpacingMultiple: 1.0, margin: 0 });
      s.addText(it.d, { x: x + 0.28, y: cy + 1.46, w: cw - 0.56, h: 0.85, fontFace: FONT_B, fontSize: 10.5, color: C.slate, lineSpacingMultiple: 1.05, margin: 0 });
      if (i < comps.length - 1) s.addText("+", { x: x + cw + 0.02, y: cy + 0.85, w: gap - 0.04, h: 0.7, fontFace: FONT_H, fontSize: 26, bold: true, color: C.slate, align: "center", valign: "middle", margin: 0 });
    }
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 6.0, w: PW - 2 * M, h: 0.78, rectRadius: 0.1, fill: { color: C.navy } });
    s.addText([
      { text: "=  ", options: { color: C.red, bold: true } },
      { text: "Skor Efektivitas Narasi", options: { color: C.white, bold: true } },
      { text: "      →   Peringkat narasi yang bisa langsung ditindaklanjuti.", options: { color: "C8D5EE" } },
    ], { x: M + 0.35, y: 6.0, w: PW - 2 * M - 0.7, h: 0.78, fontFace: FONT_B, fontSize: 14, align: "left", valign: "middle", margin: 0 });
    footer(s, 5);
  }

  // ============ SLIDE 6 — SOLUSI (deliverables + dashboard illustration placeholder) ============
  {
    const s = pres.addSlide();
    s.background = { color: C.cloud };
    header(s, "Solusi", C.blueMid);
    title(s, "Sonar Mengubah Percakapan Publik Menjadi Peringkat Narasi Siap Pakai");
    subtitle(s, "Tiga hasil yang langsung menjawab pertanyaan inti Anda: narasi mana yang menang, resonansi sejati vs dorongan brand, dan posisi Anda vs kompetitor.", 2.5);
    // left: deliverable rows
    const rows = [
      { ic: FA.FaListOl, t: "Peringkat Lima Narasi", d: "Diurutkan by SoV, sentimen, dan engagement quality." },
      { ic: FA.FaUserCheck, t: "Resonansi Sejati vs Dorongan Brand", d: "Memisahkan percakapan official account dari organik." },
      { ic: FA.FaCrosshairs, t: "Posisi vs Kompetitor, Real-Time", d: "Benchmark vs Aqua, Aquviva, Nestlé Pure Life, enam platform." },
    ];
    const lx = M, lw = 5.5; let ly = 3.25; const rh = 0.86, rgap = 0.12;
    for (let i = 0; i < rows.length; i++) {
      const it = rows[i];
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: lx, y: ly, w: lw, h: rh, rectRadius: 0.09, fill: { color: C.white }, line: { color: C.line, width: 1 }, shadow: softShadow() });
      iconChip(s, lx + 0.22, ly + 0.19, await icon(it.ic, "#FFFFFF"), 0.48, C.navy);
      s.addText(it.t, { x: lx + 0.92, y: ly + 0.12, w: lw - 1.1, h: 0.34, fontFace: FONT_B, fontSize: 13, bold: true, color: C.ink, valign: "middle", margin: 0 });
      s.addText(it.d, { x: lx + 0.92, y: ly + 0.44, w: lw - 1.1, h: 0.36, fontFace: FONT_B, fontSize: 10.5, color: C.slate, valign: "top", lineSpacingMultiple: 1.0, margin: 0 });
      ly += rh + rgap;
    }
    // right: dashboard illustration placeholder with GPT Image prompt (ratio ~2:1)
    const prompt = "PROMPT → GPT Image: Mockup dashboard SaaS modern platform media-intelligence 'dataxet:sonar': panel 'Narrative Effectiveness Ranking' berisi 5 narasi dengan bar chart, gauge sentimen, dan panel share-of-voice kompetitor. Palet WAJIB konsisten brand: navy #0E2A6B, biru azure #2E86C8, putih, aksen merah #E1251B seperlunya. Gaya flat UI, kartu rounded, tipografi sans bersih, selaras desain slide. Rasio 2:1 (landscape), resolusi tinggi, tanpa teks acak, tanpa logo asli.";
    await placeholder(s, 6.55, 3.25, 6.1, 3.0, "ILUSTRASI DIAGRAM · DASHBOARD (PLACEHOLDER)", prompt);
    kicker(s, "Dari percakapan, ke peringkat narasi, ke keputusan komunikasi campaign berikutnya.", 6.35);
    footer(s, 6);
  }

  // ============ SLIDE 7 — PREVIEW DEMO (social post placeholders) ============
  {
    const s = pres.addSlide();
    s.background = { color: C.cloud };
    header(s, "Preview Demo", C.blueMid);
    title(s, "Buktinya Memakai Brand, Kompetitor, dan Event Anda. Bukan Simulasi.");
    subtitle(s, "Tiga momen yang akan Anda kenali langsung: narasi yang membedakan sekaligus rawan, sponsorship yang bisa diangkakan, dan pesaing baru yang diam-diam tumbuh.", 2.5);
    const items = [
      { t: "BPA Free: Pedang Bermata Dua", d: "Paling membedakan dari Aqua sekaligus paling perlu dijaga. Lihat sentiment breakdown real-time." },
      { t: "Sponsorship Bisa Diangkakan", d: "Lonjakan percakapan active lifestyle seputar JRF/JAKIM. Eksposur event akhirnya punya angka dampak." },
      { t: "Pendatang Yang Diam-Diam Tumbuh", d: "Share of voice Aquviva vs Le Minerale di platform audiens muda Anda, sebelum kecolongan." },
    ];
    const cw = 3.84, gap = 0.27, x0 = M, cy = 3.05, ch = 3.15;
    for (let i = 0; i < items.length; i++) {
      const it = items[i]; const x = x0 + i * (cw + gap);
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: cy, w: cw, h: ch, rectRadius: 0.1, fill: { color: C.white }, line: { color: C.line, width: 1 }, shadow: softShadow() });
      await placeholder(s, x + 0.22, cy + 0.22, cw - 0.44, 1.4, "SCREENSHOT POST SOSMED");
      s.addText(it.t, { x: x + 0.3, y: cy + 1.74, w: cw - 0.6, h: 0.42, fontFace: FONT_B, fontSize: 13.5, bold: true, color: C.ink, lineSpacingMultiple: 1.0, margin: 0 });
      s.addText(it.d, { x: x + 0.3, y: cy + 2.18, w: cw - 0.6, h: 0.85, fontFace: FONT_B, fontSize: 10.5, color: C.slate, lineSpacingMultiple: 1.04, margin: 0 });
    }
    kicker(s, "Setiap insight punya post dan isu konkret pendukungnya. Evidence siap pakai, bukan angka kosong.", 6.35);
    footer(s, 7);
  }

  // ============ SLIDE 8 — KENAPA SONAR ============
  {
    const s = pres.addSlide();
    s.background = { color: C.cloud };
    header(s, "Kenapa Sonar", C.blueMid);
    title(s, "Engine Global Membaca Bahasa. Sonar Membaca 'Eneg', 'Seger', dan TikTok Lokal Anda.");
    subtitle(s, "Ketika sentimen penentu tersembunyi di slang Gen Z dan lahir lebih dulu di TikTok, mesin global meleset, dan laporan agency mingguan datang terlambat.", 2.55);
    const cols = [
      { ic: FA.FaGlobe, t: "Tools Global", s2: "(Brandwatch / Meltwater)", d: "Coverage luas, tapi sering meleset pada slang Indonesia ('eneg', 'seger', 'racun') yang justru menentukan sentimen narasi air mineral.", hl: false },
      { ic: FA.FaClock, t: "Agency / Monitoring Manual", s2: "", d: "Laporan biasanya mingguan dan reaktif. Terlambat untuk narasi BPA Free yang bisa memanas dalam hitungan jam.", hl: false },
      { ic: FA.FaCheckCircle, t: "Dataxet:Sonar", s2: "", d: "Kedalaman bahasa dan slang lokal, coverage TikTok tempat narasi lahir, alert real-time WA/email, dan AI report siap-readout.", hl: true },
    ];
    const cw = 3.84, gap = 0.27, x0 = M, cy = 3.25, ch = 2.4;
    for (let i = 0; i < cols.length; i++) {
      const it = cols[i]; const x = x0 + i * (cw + gap);
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: cy, w: cw, h: ch, rectRadius: 0.1, fill: { color: it.hl ? C.navy : C.white }, line: { color: it.hl ? C.navy : C.line, width: 1 }, shadow: it.hl ? shadow() : softShadow() });
      iconChip(s, x + 0.3, cy + 0.3, await icon(it.ic, "#FFFFFF"), 0.56, it.hl ? C.blueMid : C.slate);
      s.addText([
        { text: it.t, options: { bold: true, color: it.hl ? C.white : C.ink } },
        ...(it.s2 ? [{ text: "  " + it.s2, options: { color: it.hl ? "C8D5EE" : C.slate, italic: true } }] : []),
      ], { x: x + 0.3, y: cy + 1.02, w: cw - 0.6, h: 0.5, fontFace: FONT_B, fontSize: 14, lineSpacingMultiple: 1.0, margin: 0 });
      s.addText(it.d, { x: x + 0.3, y: cy + 1.5, w: cw - 0.6, h: 0.82, fontFace: FONT_B, fontSize: 10.5, color: it.hl ? "C8D5EE" : C.slate, lineSpacingMultiple: 1.05, margin: 0 });
    }
    kicker(s, "Kedalaman bahasa lokal, coverage TikTok, alert real-time, dan report siap-readout.", 5.95);
    footer(s, 8);
  }

  // ============ SLIDE 9 — RISIKO RENDAH ============
  {
    const s = pres.addSlide();
    s.background = { color: C.cloud };
    header(s, "Risiko Rendah", C.blueMid);
    title(s, "Pilot 30 Hari Memberi Baseline Yang Tetap Berguna, Apa Pun Keputusan Setelahnya");
    subtitle(s, "Yang Anda bawa pulang adalah peta efektivitas lima narasi dan benchmark kompetitor, aset untuk merancang campaign berikutnya, terlepas dari kelanjutan.", 2.5);
    const items = [
      { ic: FA.FaMapMarkedAlt, t: "Yang Anda Simpan", d: "Peta efektivitas lima narasi dan benchmark Aqua, Aquviva, Nestlé Pure Life. Baseline yang tetap dipakai untuk campaign berikutnya." },
      { ic: FA.FaLightbulb, t: "Yang Anda Pelajari", d: "Platform dan format pemenang per narasi, plus akun ambigu yang sudah ditandai untuk validasi. Berguna meski tanpa lanjutan." },
      { ic: FA.FaHandshake, t: "Komitmen Minimal", d: "Diawali keyword validation dan sample dashboard. Tidak ada kewajiban annual sampai Anda melihat hasilnya." },
    ];
    const cw = 3.84, gap = 0.27, x0 = M, cy = 3.2, ch = 2.45;
    for (let i = 0; i < items.length; i++) {
      const it = items[i]; const x = x0 + i * (cw + gap);
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: cy, w: cw, h: ch, rectRadius: 0.1, fill: { color: C.white }, line: { color: C.line, width: 1 }, shadow: softShadow() });
      iconChip(s, x + 0.3, cy + 0.32, await icon(it.ic, "#FFFFFF"), 0.56, C.navy);
      s.addText(it.t, { x: x + 0.3, y: cy + 1.08, w: cw - 0.6, h: 0.5, fontFace: FONT_B, fontSize: 15, bold: true, color: C.ink, margin: 0 });
      s.addText(it.d, { x: x + 0.3, y: cy + 1.52, w: cw - 0.6, h: 0.9, fontFace: FONT_B, fontSize: 11, color: C.slate, lineSpacingMultiple: 1.05, margin: 0 });
    }
    kicker(s, "Komitmen kecil, deliverable yang Anda simpan, keputusan tetap di tangan Anda.", 5.95);
    footer(s, 9);
  }

  // ============ SLIDE 10 — LANGKAH BERIKUTNYA ============
  {
    const s = pres.addSlide();
    s.background = { color: C.cloud };
    header(s, "Langkah Berikutnya", C.blueMid);
    title(s, "Mulai Dari Satu Pertanyaan: Dari Lima Narasi Anda, Mana Yang Menang?");
    subtitle(s, "Satu pertanyaan bisnis, satu baseline, satu peringkat narasi yang Anda bawa ke meja keputusan campaign berikutnya.", 2.5);
    const phases = [
      { p: "PHASE 1", t: "Validasi & Sample", d: "Keyword taxonomy lima narasi divalidasi, sample dashboard, dan penandaan official account ambigu." },
      { p: "PHASE 2", t: "Pilot Baseline 30 Hari", d: "Baseline AMDK, peringkat narasi, dan benchmark Aqua/Aquviva/Nestlé Pure Life. Enam platform plus online media." },
      { p: "PHASE 3", t: "Executive Readout", d: "Pembacaan hasil ke Marketing Director sebagai dasar arah campaign berikutnya." },
    ];
    const cw = 3.7, gap = 0.5, x0 = M, cy = 3.3, ch = 1.8;
    for (let i = 0; i < phases.length; i++) {
      const it = phases[i]; const x = x0 + i * (cw + gap);
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: cy, w: cw, h: ch, rectRadius: 0.1, fill: { color: C.white }, line: { color: C.line, width: 1 }, shadow: softShadow() });
      s.addText(it.p, { x: x + 0.3, y: cy + 0.24, w: cw - 0.6, h: 0.32, fontFace: FONT_B, fontSize: 11, bold: true, color: C.blue, charSpacing: 2, margin: 0 });
      s.addText(it.t, { x: x + 0.3, y: cy + 0.54, w: cw - 0.6, h: 0.45, fontFace: FONT_H, fontSize: 16, bold: true, color: C.navy, margin: 0 });
      s.addText(it.d, { x: x + 0.3, y: cy + 1.0, w: cw - 0.6, h: 0.75, fontFace: FONT_B, fontSize: 10.5, color: C.slate, lineSpacingMultiple: 1.05, margin: 0 });
      if (i < phases.length - 1) s.addText("→", { x: x + cw + 0.02, y: cy + 0.55, w: gap - 0.04, h: 0.7, fontFace: FONT_B, fontSize: 22, bold: true, color: C.red, align: "center", valign: "middle", margin: 0 });
    }
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 5.3, w: PW - 2 * M, h: 1.05, rectRadius: 0.1, fill: { color: C.redSoft } });
    s.addText([
      { text: "⚡ Kenapa sekarang:  ", options: { bold: true, color: C.red } },
      { text: "Baseline harus berdiri sebelum musim aktivasi lari 2026 dan campaign berikutnya dirancang, agar dampaknya punya pembanding, bukan ditebak ulang. Sementara itu Aquviva sudah bergerak di audiens muda Anda sejak Februari 2025.", options: { color: C.ink } },
    ], { x: M + 0.35, y: 5.3, w: PW - 2 * M - 0.7, h: 1.05, fontFace: FONT_B, fontSize: 12, align: "left", valign: "middle", lineSpacingMultiple: 1.05, margin: 0 });
    s.addText([
      { text: "Langkah pertama: sepakati jadwal keyword validation dan sample dashboard.", options: { bold: true, color: C.navy } },
      { text: "      dataxet:sonar · info@sonar.id · www.sonarplatform.com", options: { color: C.slate } },
    ], { x: M, y: 6.55, w: PW - 2 * M, h: 0.35, fontFace: FONT_B, fontSize: 11.5, align: "left", valign: "middle", margin: 0 });
    footer(s, 10);
  }

  // ============ SLIDE 11 — REFERENSI ============
  {
    const s = pres.addSlide();
    s.background = { color: C.cloud };
    header(s, "Referensi", C.slate);
    title(s, "Sumber & Referensi");
    subtitle(s, "Evidence yang memperkuat argumen, bukan pajangan.", 2.4);
    const head = ["Sumber", "Tanggal", "Data / Klaim yang Dipakai", "Slide"].map((t) => ({
      text: t, options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 10.5, align: "left", valign: "middle", fontFace: FONT_B },
    }));
    const rows = [
      ["enciety.co", "Jan 2026", "TBI Le Minerale 4,6%→18,8%; Aqua 62,5%→46,9%; pasar ~USD 3,9 M", "1, 4"],
      ["Kompas: Pemilik Aquviva", "Jun 2025", "Aquviva (Wings) launch 25 Feb 2025; target eksplisit Gen Z", "3"],
      ["Wartakota / Tribunnews", "Feb 2025", "Peluncuran Aquviva; 7 tahap nano-purifikasi", "3"],
      ["IDN Times: JRF 2025", "2025", "JRF Official Mineral Water; 27.300 pelari, 48 negara", "3"],
      ["Le Minerale Newsroom: JAKIM", "Jun 2025", "JAKIM Official Mineral Water; 31.000+ peserta", "3"],
      ["Tempo: Aturan BPOM soal BPA", "2024", "PerBPOM No. 6/2024; regulasi BPA aktif, transisi 4 tahun", "3"],
      ["Ekuatorial: Pelabelan BPA", "Des 2024", "Polemik narasi BPA Free vs kompetitor", "7"],
      ["Bisnis.com: Le Minerale", "Agu 2025", "Gold Marketeers Youth Choice 2025 (Gen Z)", "1, 4"],
      ["Liputan6: Mayora 2024", "2025", "Penjualan MYOR Rp36,07 T (+14,57% YoY)", "4"],
      ["TikTok: @leminerale_id", "2025", "~312K followers; narasi active lifestyle (perlu validasi)", "7, 8"],
    ];
    const body = rows.map((r, idx) => r.map((c, ci) => ({
      text: c, options: { color: ci === 0 ? C.navy : C.ink, bold: ci === 0, fontSize: 9.5, align: "left", valign: "middle", fontFace: FONT_B, fill: { color: idx % 2 === 0 ? C.white : "EAF2FB" } },
    })));
    s.addTable([head, ...body], { x: M, y: 2.75, w: PW - 2 * M, colW: [3.1, 1.3, 6.0, 1.5], border: { type: "solid", pt: 0.5, color: C.line }, rowH: 0.34, valign: "middle", margin: [2, 4, 2, 4] });
    footer(s, 11);
  }

  const out = "Deck_" + CLIENT + ".pptx";
  await pres.writeFile({ fileName: out });
  console.log("WROTE " + out + "  (client: " + client.name + ")");
}
build().catch((e) => { console.error(e); process.exit(1); });
