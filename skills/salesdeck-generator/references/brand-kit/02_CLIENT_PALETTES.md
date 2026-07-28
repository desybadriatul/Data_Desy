# 02 · Client Palettes

Color tokens per client. Hex values use NO leading `#` (pptxgenjs requirement).
These live in code at `template/theme.js`; this file is the human-readable reference.

> **Lock the hex.** Le Minerale is finalized from its real logo. GoPay and Kementan are
> sensible starters — verify against each client's official brand guideline before sending.

## Agency — Dataxet:Sonar

Used only for the agency mark + tiny accents, never as the deck's main color.

| Token | Hex | Use |
|---|---|---|
| Green | `2BA32B` | "dataxet" in the wordmark |
| Periwinkle | `7C86E8` | "sonar" in the wordmark |
| Grey | `B5B5B5` | colon glyph |

## Le Minerale — FINALIZED ✅

Brand: deep royal blue + bright red cap, fresh "mountain water" feel (light backgrounds).
Logo colors observed: red `E2231A`, drop blue `29ABE2`, mountain green `3AAA35`.

| Token | Hex | Role |
|---|---|---|
| navy | `0E2A6B` | dominant — titles, dark cards, kicker |
| blue | `1E78C8` | secondary |
| blueMid | `2E86C8` | accents, chart bars, eyebrows |
| blueSoft | `E4F1FB` | tints, number ovals |
| red | `E1251B` | 10% sharp accent |
| redSoft | `FBE7E5` | warning callout fill |
| ink | `16203A` | body text |
| slate | `5C6A86` | muted text |
| cloud | `F2F8FD` | slide background |
| line | `DCE7F4` | card borders |

## GoPay — STARTER ⚠️ (verify)

Brand: GoPay blue + Gojek green. Add official `assets/logos/gopay.png`.

| Token | Hex | Role |
|---|---|---|
| navy | `052B4E` | dominant deep blue |
| blue | `1FA7E8` | secondary |
| blueMid | `00AAE4` | GoPay blue accent / chart bars |
| blueSoft | `E2F4FC` | tints |
| red (accent slot) | `00AA13` | Gojek green — the 10% accent |
| redSoft | `E3F6E5` | accent fill |
| cloud | `F2F9FD` | background |
| line | `D8E7F2` | borders |

## Kementerian Pertanian (Kementan) — STARTER ⚠️ (verify)

Brand: formal government green + gold + red, from the ministry emblem. Add official
`assets/logos/kementan.png`. Tone is institutional, not consumer — keep it restrained.

| Token | Hex | Role |
|---|---|---|
| navy (deep green slot) | `0F4F28` | dominant deep green |
| blue (green slot) | `1B7A3D` | secondary green |
| blueMid | `2E8B4E` | accents / chart bars |
| blueSoft | `E5F2E8` | tints |
| gold | `F2B807` | ministry gold accent |
| red | `D32F2F` | ministry red, sparing |
| cloud | `F4F8F3` | background |
| line | `DCEADD` | borders |

> Note: the engine reads generic token names (`navy`, `blue`, `red`...). For green-led
> brands like Kementan, those slots simply hold green/gold values — no code changes needed.
