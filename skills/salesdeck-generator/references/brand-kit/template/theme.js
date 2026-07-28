// ============================================================
//  Dataxet:Sonar  ·  Master Deck Theme Config
//  One file = the brand kit in code. Add a client = add a block.
//  Hex tokens use NO leading "#", per pptxgenjs.
// ============================================================

module.exports = {
  // ---- Agency identity (Dataxet:Sonar). Used sparingly as accent. ----
  dataxet: { green: "2BA32B", periwinkle: "7C86E8", grey: "B5B5B5" },

  // ---- Typography (safe-list fonts that ship with Office) ----
  fonts: { header: "Cambria", body: "Calibri" },

  // ---- Agency logo (top-left on every slide) ----
  logoAgency: "assets/logos/dataxet-sonar.png",

  // ---- Per-client themes. The CLIENT palette drives the deck. ----
  clients: {
    // ---------------------------------------------------------
    // LE MINERALE  — FINALIZED (matches real brand)
    // ---------------------------------------------------------
    leminerale: {
      name: "Le Minerale",
      logoClient: "assets/logos/le-minerale.png",
      colors: {
        navy: "0E2A6B", navy2: "16357F",
        blue: "1E78C8", blueMid: "2E86C8", blueSoft: "E4F1FB",
        red: "E1251B", redSoft: "FBE7E5",
        ink: "16203A", slate: "5C6A86",
        cloud: "F2F8FD", line: "DCE7F4", white: "FFFFFF",
      },
    },

    // ---------------------------------------------------------
    // GOPAY  — STARTER (verify hex against GoPay brand guideline)
    // GoPay blue + Gojek green. Drop the official logo into assets/logos/gopay.png
    // ---------------------------------------------------------
    gopay: {
      name: "GoPay",
      logoClient: "assets/logos/gopay.png", // TODO: add official PNG
      colors: {
        navy: "052B4E", navy2: "0A3A63",
        blue: "1FA7E8", blueMid: "00AAE4", blueSoft: "E2F4FC",
        red: "00AA13", redSoft: "E3F6E5",   // "red" slot reused as Gojek-green accent
        ink: "13233A", slate: "5B6B82",
        cloud: "F2F9FD", line: "D8E7F2", white: "FFFFFF",
      },
    },

    // ---------------------------------------------------------
    // KEMENTAN (Kementerian Pertanian) — STARTER (verify hex)
    // Formal government green + gold + red, from the ministry emblem.
    // ---------------------------------------------------------
    kementan: {
      name: "Kementerian Pertanian",
      logoClient: "assets/logos/kementan.png", // TODO: add official PNG
      colors: {
        navy: "0F4F28", navy2: "166436",      // "navy" slot = deep green
        blue: "1B7A3D", blueMid: "2E8B4E", blueSoft: "E5F2E8",
        red: "D32F2F", redSoft: "FBE7E5",      // ministry red outline
        gold: "F2B807",                        // ministry gold accent
        ink: "1A2A1E", slate: "5C6E60",
        cloud: "F4F8F3", line: "DCEADD", white: "FFFFFF",
      },
    },
  },
};
