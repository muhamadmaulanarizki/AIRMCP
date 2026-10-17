# Credits: Image Sources & Licenses

*Foto landing page "Kopi Senja" — semua gambar di `public/images/coffee/` (kecuali `favicon.svg`)
bersumber dari stok bebas lisensi CC0 1.0 / Public Domain. Ditemukan via Openverse
(`api.openverse.org`, filter `license=cc0,pdm`), diverifikasi visual, lalu di-resize + dikompresi
(PHP GD: WebP kualitas 82, JPG kualitas 84 sebagai fallback) menjadi < 200 KB per file.*

**Status: semua foto TIDAK memerlukan atribusi (CC0 1.0).** Bila ingin tetap mencantumkan kredit
sebagai apresiasi, baris di bawah ini adalah sumber resminya.

| File | Source URL | License | Photographer | Attribution Required? | Notes |
|------|------------|---------|--------------|----------------------|-------|
| hero.webp / hero.jpg | https://stocksnap.io/photo/restaurant-bar-THXU08ODDE | CC0 1.0 (StockSnap License) | Afta Putta Gunawan | No | Interior bar kedai kopi: bata hangat, lampu kuning, papan menu |
| es-kopi-susu.webp / .jpg | https://www.rawpixel.com/image/5928100/photo-image-background-public-domain-glass | CC0 1.0 | rawpixel | No | Susu dituang ke gelas kopi es — visual "es kopi susu" |
| kopi-tubruk.webp / .jpg | https://www.rawpixel.com/image/5911577/image-public-domain-coffee-free | CC0 1.0 | rawpixel | No | Cangkir kopi hitam di atas dedaunan musim gugur |
| cappuccino.webp / .jpg | https://www.flickr.com/photos/132795455@N08/18281357909 | CC0 1.0 | Image Catalog | No | Cappuccino latte art di konter kayu |
| cold-brew.webp / .jpg | https://commons.wikimedia.org/wiki/File:Iced_cold_brew_coffee.jpg | CC0 1.0 | Roland Tanglao | No | Cold brew dingin dengan es batu, tampak atas |
| matcha-latte.webp / .jpg | https://wordpress.org/photos/photo/24661c2123/ | CC0 1.0 | Louie Sonugan | No | Matcha latte dengan latte art daun di cangkir hijau |
| cokelat-panas.webp / .jpg | https://stocksnap.io/photo/hot-chocolate-NOXXUWUBGJ | CC0 1.0 (StockSnap License) | Tim Sullivan | No | Cokelat panas dengan krim kocok + potongan cokelat |
| pisang-goreng.webp / .jpg | https://commons.wikimedia.org/wiki/File:Pisang_Goreng_Hangat.jpg | CC0 1.0 | AndriFB | No | Pisang goreng hangat rumahan di piring |
| roti-bakar.webp / .jpg | https://www.rawpixel.com/image/5902218/photo-image-public-domain-food-chocolate | CC0 1.0 | rawpixel | No | Roti bakar dengan olesan cokelat |

*`favicon.svg`: DIPERTAHANKAN (ikon vektor merek, bukan foto menu).*

---

## Cara verifikasi ulang lisensi (mitigasi risiko R1)

1. Buka URL sumber pada tabel di atas.
2. Pastikan lisensi tercantum **CC0 1.0 Universal Public Domain Dedication** (rawpixel: label
   "Free for commercial use / No attribution required"; StockSnap: StockSnap License berbasis CC0;
   Wikimedia/WordPress Photo Directory: field "License: CC0").
3. Hasil pencarian Openverse dapat direproduksi:
   `https://api.openverse.org/v1/images/?q=<kata kunci>&license=cc0,pdm`

## Kebijakan penggantian

- Foto hanya boleh dari CC0 / Public Domain / Pexels License / Unsplash License.
- Dilarang: NC/ND, watermark, hotlink (semua file wajib di-host lokal di `public/`).
- Setiap penggantian foto wajib memperbarui tabel ini dan metadata `config/coffee.php`
  (`license`, `photographer`, `source_url`, `attribution_required`).
