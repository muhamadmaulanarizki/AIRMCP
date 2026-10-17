# ARCHITECTURE: Image Replacement — Hero & Menu Coffee Photos

## 1. Overview
Replace the 9 SVG placeholder images (`public/images/coffee/`) with real photography under CC0/Pexels/Unsplash licenses. The hero image is 1 × 640×480 landscape; the 8 menu images are 8 × 320×200 each (one per menu category). All images must be hosted locally in `public/images/coffee/`, optimized WebP/ JPEG ≤200KB, with `loading="lazy"` and `onerror` fallbacks.

---

## 2. File Structure Changes

| Current Path | New Path | Change |
|---|---|---|
| `public/images/coffee/hero.svg` | `public/images/coffee/hero.webp` | Convert/Replace → WebP format |
| `public/images/coffee/es-kopi-susu.svg` | `public/images/coffee/es-kopi-susu.webp` | Convert/Replace → WebP format |
| `public/images/coffee/kopi-tubruk.svg` | `public/images/coffee/kopi-tubruk.webp` | Convert/Replace → WebP format |
| `public/images/coffee/cappuccino.svg` | `public/images/coffee/cappuccino.webp` | Convert/Replace → WebP format |
| `public/images/coffee/cold-brew.svg` | `public/images/coffee/cold-brew.webp` | Convert/Replace → WebP format |
| `public/images/coffee/matcha-latte.svg` | `public/images/coffee/matcha-latte.webp` | Convert/Replace → WebP format |
| `public/images/coffee/cokelat-panas.svg` | `public/images/coffee/cokelat-panas.webp` | Convert/Replace → WebP format |
| `public/images/coffee/pisang-goreng.svg` | `public/images/coffee/pisang-goreng.webp` | Convert/Replace → WebP format |
| `public/images/coffee/roti-bakar.svg` | `public/images/coffee/roti-bakar.webp` | Convert/Replace → WebP format |
| `public/images/coffee/favicon.svg` | `public/images/coffee/favicon.svg` | **Leave untouched** (icon, not menu) |

> **Note:** All `.svg` source files (except `favicon.svg`) are deprecated after conversion. They may be deleted in P1 after verification, but keep a backup in `docs/` until release.

---

## 3. Data Schema (Config-Driven — No DB Changes)

The existing `config/coffee.php` schema is retained but updated with new image paths and license attribution:

```php
'hero_image' => 'images/coffee/hero.webp',
'menu' => [
    'Kopi' => [
        [
            'name' => 'Es Kopi Susu Gula Aren',
            'price' => 18000,
            'desc' => '...',
            'img' => 'images/coffee/es-kopi-susu.webp',
            'license' => 'Pexels',       // or 'CC0', 'Unsplash', 'CC-BY'
            'photographer' => 'Nama Fotografer',
            'source_url' => 'https://unsplash.com/...',
        ],
        // ... other Kopi items
    ],
    // ... Non-Kopi, Camilan
],
```

**New fields per image:**
- `img`: path relative to `public/images/coffee/` (`.webp` or `.jpg`)
- `license`: one of `CC0`, `Pexels`, `Unsplash`, `CC-BY`
- `photographer`: name of the photographer/creator
- `source_url`: direct URL where the photo was downloaded from
- `attribution_required`: boolean (`true` for CC-BY, `false` for CC0/Pexels/Unsplash)

---

## 4. API Endpoints

No new API endpoints are required. The existing endpoints serve the updated config:

| Endpoint | Purpose | Response |
|---|---|---|
| `GET /` | Landing page HTML | Renders `landing/index.blade.php` with `brand`, `menu`, `heroImage` from `config/coffee.php` |
| `GET /api/menu` | JSON menu data | `response()->json(config('coffee.menu'))` — now includes `license`, `photographer`, `source_url` |

**Optional if needed later:**
- `GET /api/image-meta?image=hero|es-kopi-susu|...` — return metadata (size, license, photographer) for caching/validation.

---

## 5. Trade-Offs & Decisions (Risiko & Mitigasi)

| Trade-Off | Decision | Reason |
|---|---|---|
| **Format: WebP vs JPEG vs PNG** | **WebP primary, JPEG fallback** | WebP gives 26–34% smaller size than JPEG at equivalent SSIM quality. All modern browsers support WebP; fallback `.jpg` via `onerror` for Safari/old Chrome. |
| **Resolution: 640×480 (hero) / 320×200 (menu)** | **Fixed dimensions in `<img>` tags** | Matches existing `width/height` attributes. Prevents layout shift (CLS). Hero landscape is wider-than-tall; menu photos should be portrait-framed at 8:5 ratio. |
| **Lazy-loading** | **Keep `loading="lazy"`** | Already in Blade templates. No extra logic needed. Only hero image may be above-the-fold; consider `loading="eager"` for hero if above fold, but keep lazy for menu cards. |
| **Image sourcing: Unsplash vs Pexels vs CC0** | **Mix: Pexels for menu (easier license), Unsplash for hero (high‑quality)** | Pexels license permits commercial use without attribution. Unsplash requires attribution (handled in footer). CC0 has no strings attached. Avoid Wikimedia Commons due to variable licenses. |
| **Batch download & compress** | **Automated script + manual review** | Use a tiny PHP/CLI script to `curl` photos → `imagemagick` or `sharp` to resize/compress ≤200KB. Final check via Lighthouse. |
| **Fallback: `.jpg` if WebP not supported** | **`onerror` → swap to `.jpg`** | `<img onerror="this.src='... .jpg'>` in the Blade template. Ensures no broken images on any browser. |

---

## 6. Concrete File Paths (Relevant to This Task)

| Category | File Path | Role |
|---|---|---|
| **Config (source of truth)** | `config/coffee.php:51-103` | Menu items with `img` paths; `hero_image` at line 103 |
| **Controller (data feeder)** | `app/Http/Controllers/LandingController.php:17` | `'heroImage' => config('coffee.hero_image')` |
| **Hero view** | `resources/views/landing/sections/hero.blade.php:14` | `<img src="{{ asset($heroImage) }}" ...>` |
| **Menu view** | `resources/views/landing/sections/menu.blade.php:15-16` | `<img class="menu-card-img" src="{{ asset($item['img']) }}" ...>` |
| **Placeholder images** | `public/images/coffee/{hero,es-kopi-susu,kopi-tubruk,cappuccino,cold-brew,matcha-latte,cokelat-panas,pisang-goreng,roti-baker}.svg` | **Replace with `.webp`** |
| **Favicon (untouched)** | `public/images/coffee/favicon.svg` | **Do not touch** |
| **Credits doc** | `docs/credits-images.md` | **Generate after image replacement** — list URL + license + photographer for each image |
| **MCP notes (risk log)** | `.mcp/notes/notes.md` | Update after merge to close risk "foto placeholder" |

---

## 7. Workflow (End-to-End)

### P0 – Researcher (Step 1–3)
1. Search Unsplash/Pexels/Pixabay for:
   - 1 hero photo: 640×480 landscape, coffee‑shop vibe, warm tones (coffee sunset)
   - 8 menu photos: 320×200, each representing a menu category (es susu, tubruk, cappuccino, cold brew, matcha latte, cokelat panas, pisang goreng, roti bakar)
2. Filter by license: CC0 / Pexels License / Unsplash License / CC-BY only.
3. Reject NC/ND, watermark, hotlink-only, no-clear-license.
4. Output table to `docs/credits-images.md`:
   ```
   | File | Source URL | License | Photographer | Attribution? |
   |------|------------|---------|--------------|------------|
   | hero.webp | unsplash.com/photos/... | CC0 | Ansel Adams | No |
   | es-kopi-susu.webp | pexels.com/photo/... | Pexels | ... | No |
   ...

### P0 – Coder-1 (Step 4–6)
5. Download each photo to `public/images/coffee/` as `.webp` (or `.jpg` fallback).
   - Resize: hero max‑width 1280px, menu max‑width 800px.
   - Compress: <200KB target (use `cwebp` or `imagemagick -quality 75`).
   - Keep `loading="lazy"` on `<img>` tags.
   - Delete original `.svg` files **after** paths updated (keep `favicon.svg`).
6. Update `config/coffee.php:51-103`:
   - `'hero_image' => 'images/coffee/hero.webp'`
   - Each `'img' => 'images/coffee/<name>.webp'`
   - Add `'license'`, `'photographer'`, `'source_url'`, `'attribution_required'`.

### P1 – Coder-2 (Step 7–8)
7. Update `hero.blade.php:14`:
   - Add descriptive `alt` (e.g., "Suasana kafe hangat pagi dengan meja kayu dan tanaman hijau").
   - Add `width="640" height="480"` (keep existing).
   - Add `onerror` fallback: `onerror="this.src='{{ asset('images/coffee/hero.jpg') }}'; this.loading='eager'"`.
   - Keep `loading="lazy"` (or change to `"eager"` if hero is above-the-fold — decide case-by-case).
8. Update `menu.blade.php:15-16`:
   - `alt` deskriptif per kategori (e.g., "Es Kopi Susu — espresso dengan susu segar").
   - Keep `width="320" height="200"`.
   - Keep `loading="lazy"`.
9. `menu.blade.php:6` — hapus teks "masih placeholder" dari `<p class="section-sub">`.

### P1 – Tester (Step 9–10)
10. Verifikasi:
    - Tidak ada 404 di Console Network.
    - Tidak ada referensi `.svg` tersisa kecuali `favicon.svg`.
    - Lighthouse image OK (score ≥90, CLS 0).
    - Mobile aspect di `landing.css:249` tidak pecah (gambar tidak lebar/tebal).
    - Validasi lisensi ulang: semua file ada atribusi di footer/about jika CC-BY mewajibkan.

### P2 – Review & Docs (Step 11)
11. Review diff + merge. Update `.mcp/notes/notes.md` tutup risiko "foto placeholder".

---

## 8. Risiko & Mitigasi (Ringkasan)

| Kode | Risiko | Mitigasi |
|------|--------|----------|
| R1 | Lisensi salah klaim free → sengketa | Hanya CC0/Pexels/Unsplash, simpan bukti URL+lisensi di `docs/credits-images.md` |
| R2 | Hotlink langsung (bukan file lokal) → broken/lemot | Wajib hosting lokal di `public/images/coffee/` — jangan gunakan URL luar |
| R3 | Ukuran file besar → LCP jebol | Batas 200KB + WebP + lazy-load. Kompres dengan `cwebp -q 80` atau alat serupa. |
| R4 | Gaya foto tidak konsisten | 1 sumber seri / tone warna kopi senja. Semua foto diambil dengan kamera/kondisi serupa atau edit warna konsisten dalam post-processing. |

---