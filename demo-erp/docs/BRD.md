# BRD - Integrasi ERP

| Field | Nilai |
|---|---|
| Project | demo-erp |
| Judul | BRD - Integrasi ERP (Purchase Order & Vendor) |
| Versi Dokumen | 1.0 |
| Tanggal | 14 Oktober 2026 |
| Status | Draft - siap review tim |
| Bahasa Dokumen | Bahasa Indonesia |
| Penulis | [Asumsi: Business Analyst / Technical Writer] |
| Stack (fakta repo) | Laravel 11 + MySQL - keputusan tim tercatat di `.mcp/notes/notes.md`, 14 Okt 2026 |
| Dokumen Terkait | `docs/PRD.md` (PRD - Integrasi ERP, v1.0, 14 Okt 2026) |

> **Aturan fakta:** setiap hal yang datanya tidak tersedia di repositori atau dari stakeholder ditandai **[Asumsi]**. Sumber fakta repositori: skema tabel `purchase_orders` & `vendors`, `PurchaseOrderController`/`VendorController`, data contoh `purchase_orders.csv`, dan catatan tim `.mcp/notes/notes.md`.

---

## 1. Executive Summary

Proyek **demo-erp** adalah pembangunan aplikasi web berbahasa Indonesia untuk mengelola **Purchase Order (PO)** dan **Vendor** sebagai bagian dari rangkaian **integrasi ERP**. Saat ini kondisi repositori baru mencakup layer model & controller Laravel 11 + MySQL (CRUD PO & vendor, paginasi 25/baris, endpoint rekap total PO `approved` per vendor) beserta data contoh 5 PO dari 3 vendor. Yang belum ada: antarmuka web, autentikasi & otorisasi, validasi bisnis, workflow approval PO, impor data, dan dokumentasi API.

BRD ini mendefinisikan kebutuhan bisnis dari sisi stakeholder: (1) satu sumber data PO & vendor yang tunggal dan terpercaya, (2) workflow persetujuan PO yang jelas (draft → submitted → approved/rejected), (3) rekap nilai PO approved per vendor untuk kebutuhan keuangan tanpa hitung manual, dan (4) fondasi integrasi ERP melalui API terdokumentasi serta impor CSV.

Nilai bisnis utama: penghematan waktu pencatatan dan rekap, akurasi data pembelian, kesiapan integrasi ke modul ERP lain, dan pengendalian akses. Estimasi awal **[Asumsi]**: 8-11 minggu dengan 1-2 developer (selaras estimasi milestone di PRD v1.0, belum dikalibrasi tim).

---

## 2. Latar Belakang Bisnis (Business Background)

2.1 **Kondisi sistem saat ini (fakta repositori, 14 Okt 2026):**

- Backend **Laravel 11 + MySQL** sudah berjalan sebagai keputusan tim (tercatat di `.mcp/notes/notes.md`).
- Model & migration yang sudah ada:
  - `purchase_orders`: `id`, `kode`, `vendor`, `total` (decimal 15,2), `status`, `order_date`, `timestamps`.
  - `vendors`: `id`, `nama`, `alamat`, `kontak`, `aktif` (boolean), `timestamps`.
- Endpoint JSON hasil scaffold sudah ada:
  - `PurchaseOrderController`: list (paginasi 25), create, show, update, delete, dan endpoint rekap `approvedTotalByVendor`.
  - `VendorController`: list (paginasi 25), create, show, update, delete.
- Data contoh `purchase_orders.csv`: **5 PO dari 3 vendor** (CV Maju Jaya, PT Sinar Abadi, PT Karya Nusantara) dengan status `approved` dan `draft`.
- Terdapat **artefak scaffold ganda** (`PurchaseOrderController` + `PurchaseOrdersController`, model `PurchaseOrder` + `PurchaseOrders`) yang perlu dibersihkan.

2.2 **Masalah bisnis yang harus diselesaikan:**

| ID | Masalah | Dampak Bisnis |
|---|---|---|
| MS-1 | Data PO & vendor belum dikelola lewat satu aplikasi web; baru berupa layer API & file CSV contoh | Pencatatan PO berisiko tersebar di spreadsheet terpisah, sulit diaudit |
| MS-2 | Belum ada autentikasi/otorisasi; endpoint API terbuka | Siapa pun yang dapat akses jaringan dapat mengubah data pembelian |
| MS-3 | Belum ada workflow approval PO | Tidak ada kontrol kualitas & jejak persetujuan atas pembelian |
| MS-4 | Rekap nilai PO approved per vendor baru berupa endpoint JSON, belum dapat dikonsumsi pengguna non-teknis | Keuangan masih berpotensi menghitung manual |
| MS-5 | Tidak ada mekanisme impor data & dokumentasi API publik | Migrasi data lama & integrasi ERP selanjutnya terhambat |
| MS-6 | Artefak kode ganda & set status PO belum tunggal (`draft`, `approved` di data; template perintah menyebut `pending`, `rejected`) | Risiko kebingungan tim & inkonsistensi data status |

2.3 **Peluang:** mengubah layer yang sudah ada menjadi aplikasi ERP yang siap dipakai tim pengadaan/keuangan dan menjadi fondasi integrasi modul ERP lain (stok/gudang, akunting) **[Asumsi: modul lanjutan menunggu keputusan bisnis - lihat Ruang Lingkup]**.

---

## 3. Tujuan Bisnis (Business Objectives)

| ID | Tujuan Bisnis | Sasaran Terukur | Prioritas |
|---|---|---|---|
| BO-1 | Menyatukan data PO & vendor dalam satu sumber data yang terpercaya | 100% PO baru tercatat di sistem (bukan CSV/spreadsheet terpisah); duplikat `kode` PO = 0 | Must |
| BO-2 | Mempercepat & mempermudah pencatatan PO dan pendataan vendor | Buat PO rata-rata < 3 menit; cari PO < 10 detik | Must |
| BO-3 | Memberi kontrol kualitas data melalui workflow approval | Setiap PO punya status jelas & jejak perubahan (audit log) | Must |
| BO-4 | Menyediakan rekap nilai PO approved per vendor bagi keuangan | Rekap tampil tanpa hitung manual; akurasi 100% vs sampling audit | Must |
| BO-5 | Menyiapkan fondasi integrasi ERP (API terdokumentasi + impor CSV) | API terdokumentasi 100% endpoint PO/Vendor; impor 5+ PO contoh tanpa error | Should |
| BO-6 | Menjaga keamanan & tata kelola akses data pembelian | 0 insiden akses tanpa otorisasi; 100% endpoint terproteksi | Must |

> Angka target (waktu, jumlah) bersifat **[Asumsi]** sampai dikalibrasi bersama stakeholder bisnis.

---

## 4. Ruang Lingkup Bisnis (Scope)

4.1 **Di dalam cakupan (In Scope) - Fase 1:**

- Manajemen data **Vendor** (tambah, lihat, ubah, nonaktifkan/hapus sesuai aturan) dengan data `nama`, `alamat`, `kontak`, `aktif`.
- Manajemen **Purchase Order**: pencatatan (`kode`, `vendor`, `total`, `status`, `order_date`), pencarian, filter (status, vendor, rentang tanggal), paginasi.
- **Workflow persetujuan PO**: `draft → submitted → approved / rejected` **[Asumsi: daftar status final menunggu konfirmasi Product Owner]**.
- **Rekap nilai PO approved per vendor** beserta ekspor laporan (format final menunggu keuangan) **[Asumsi]**.
- **Autentikasi & otorisasi** pengguna dengan peran minimal `admin`, `procurement_staff`, `manager` **[Asumsi: skema peran final menunggu konfirmasi]**.
- **Impor PO dari CSV** (format mengikuti `purchase_orders.csv`: `kode,vendor,total,status,order_date`).
- **Dokumentasi API** (OpenAPI/Swagger) untuk endpoint PO & vendor sebagai fondasi integrasi ERP.
- **Pembersihan artefak ganda** controller/model PO (fakta repositori).
- Antarmuka web **berbahasa Indonesia**.

4.2 **Di luar cakupan (Out of Scope) - Fase 1:**

- Modul ERP selengkapnya (Gudang/Stok, Akunting/GL, HR, Sales) - tema stok gudang muncul di prompt proyek namun belum ada implementasi; masuk roadmap terpisah.
- Portal mandiri vendor (vendor login & submit sendiri) - kompleksitas akses eksternal.
- Integrasi real-time dengan sistem ERP eksternal (SAP, Odoo, Accurate, dll); nama sistem target ERP belum ditentukan **[Asumsi]**.
- Aplikasi mobile native (hanya UI web responsif).
- Perhitungan pajak, pembayaran/pelunasan PO.
- E-signature & approval berjenjang multi-level.
- Laporan BI/analitik lanjutan.

---

## 5. Stakeholder & Peran

| Stakeholder | Peran dalam Proyek | Kepentingan Utama | Keterlibatan |
|---|---|---|---|
| Product Owner / Manajemen | Sponsor & pengambil keputusan bisnis; finalisasi status PO, peran, prioritas | Nilai bisnis, kepatuhan, anggaran | Persetujuan milestone & dokumen |
| Staff Procurement (Pengadaan) | Pengguna harian: input vendor & PO, ajukan PO | Form cepat, validasi jelas, tanpa double-entry | UAT, feedback mingguan |
| Manajer Procurement | Review & approve/reject PO | Antrean approval, jejak perubahan | UAT workflow approval |
| Staf Keuangan | Konsumen rekap nilai PO approved per vendor | Rekap akurat per vendor & periode, ekspor | UAT rekap & format laporan |
| Admin Sistem | Kelola pengguna, master data, backup | Pengelolaan peran & ketersediaan | Dukungan operasional |
| Tim Pengembang (Engineering) | Bangun & uji aplikasi (backend, frontend, QA) | Spesifikasi jelas, artefak ganda dibersihkan | Eksekusi harian |
| IT / Infrastruktur | Server, hosting, backup, kredensial | SLA, keamanan lingkungan produksi | Setup & operasional **[Asumsi: belum ditunjuk]** |
| Vendor ERP eksternal (bila ada) | Pihak ketiga sistem ERP tujuan integrasi | Format API, keamanan koneksi | Belum teridentifikasi **[Asumsi]** |

> Nama persona & penunjukan PIC tiap peran bersifat **[Asumsi]** sampai dikonfirmasi oleh Product Owner.

---

## 6. Kebutuhan Bisnis (BR-1, BR-2, ...)

| ID | Kebutuhan Bisnis | Prioritas | Kaitan |
|---|---|---|---|
| BR-1 | Semua data PO & vendor harus dikelola dalam satu sistem terpusat, tidak lagi di spreadsheet/CSV terpisah (CSV hanya untuk impor awal & ekspor laporan) | Must | BO-1, MS-1 |
| BR-2 | Setiap PO harus mengikuti alur status: `draft → submitted → approved / rejected`; hanya peran `manager` yang boleh approve/reject **[Asumsi: pemegang hak approve menunggu konfirmasi]** | Must | BO-3, MS-3 |
| BR-3 | PO dengan status `submitted`/`approved` tidak dapat dihapus; hanya dapat dibatalkan/diubah status dengan alasan tercatat | Must | BO-3 |
| BR-4 | Hanya vendor berstatus `aktif` yang dapat dipilih saat membuat/mengubah PO | Must | BO-1 |
| BR-5 | `kode` PO harus unik di seluruh sistem; `total` PO harus > 0 dan tidak melebihi batas kolom (decimal 15,2) | Must | BO-1 |
| BR-6 | Semua akses aplikasi & API wajib melalui autentikasi; hak akses dibatasi per peran di setiap endpoint (bukan hanya di UI) | Must | BO-6, MS-2 |
| BR-7 | Rekap nilai PO per vendor hanya menjumlahkan PO berstatus `approved` (selaras endpoint `approvedTotalByVendor` yang sudah ada), urut dari nilai terbesar | Must | BO-4, MS-4 |
| BR-8 | Pengguna keuangan dapat melihat & mengekspor rekap per vendor/periode tanpa bantuan teknis; format ekspor final menunggu keuangan **[Asumsi: format laporan]** | Should | BO-4 |
| BR-9 | Data PO lama harus dapat dimigrasi dari CSV (format `purchase_orders.csv`) dengan validasi per baris dan laporan error yang jelas | Should | BO-5, MS-5 |
| BR-10 | API PO & vendor terdokumentasi (OpenAPI/Swagger) sebagai fondasi integrasi ERP berikutnya | Should | BO-5 |
| BR-11 | Setiap perubahan PO tercatat dalam audit log (siapa, kapan, apa yang berubah) | Should | BO-3 |
| BR-12 | Vendor yang masih memiliki PO terkait tidak dapat dihapus (hanya dinonaktifkan) | Should | BO-1 |
| BR-13 | Admin dapat mengelola pengguna & peran | Should | BO-6 |
| BR-14 | Antarmuka & pesan kesalahan berbahasa Indonesia secara konsisten | Must | BO-2 |
| BR-15 | Artefak kode ganda (controller/model PO) harus dibersihkan dan set status PO ditunggalkan sebelum pengembangan fitur lanjutan | Must | MS-6 |

---

## 7. Kebutuhan Fungsional Tingkat Tinggi (FR)

| ID | Kebutuhan Fungsional | Prioritas | Dasar/Sumber |
|---|---|---|---|
| FR-1 | Autentikasi pengguna: login/logout dengan sesi aman (password hashing, proteksi CSRF, rate limit login) | Must | Gap MS-2 |
| FR-2 | Otorisasi berbasis peran minimal `admin`, `procurement_staff`, `manager` di setiap endpoint **[Asumsi: skema peran final menunggu konfirmasi]** | Must | Gap MS-2 |
| FR-3 | CRUD Vendor (`nama`, `alamat`, `kontak`, `aktif`) dengan validasi required & keunikan `nama` | Must | Tabel `vendors` & `VendorController` ada |
| FR-4 | Daftar vendor dengan paginasi (25/baris), pencarian & filter hanya-aktif | Must | `VendorController@index` paginate(25) |
| FR-5 | CRUD PO (`kode`, `vendor`, `total`, `status`, `order_date`) dengan status awal `draft` | Must | Tabel `purchase_orders` & `PurchaseOrderController` |
| FR-6 | Validasi PO: `kode` unik, `total` > 0 (decimal 15,2), `order_date` <= hari ini **[Asumsi: pola kode PO menunggu keputusan]** | Must | Gap analitik duplikat |
| FR-7 | Daftar PO dengan paginasi (25/baris) + filter status, vendor, rentang tanggal, pencarian `kode` | Must | `PurchaseOrderController@index` paginate(25) |
| FR-8 | Transisi status PO: `draft → submitted → approved / rejected` sesuai BR-2 | Must | Kolom `status` pada schema |
| FR-9 | Halaman/endpoint rekap total PO approved per vendor, urut terbesar (dipublikasikan ke UI web, bukan hanya JSON) | Must | Scope `approvedTotalByVendor` di model |
| FR-10 | Ekspor rekap per vendor ke CSV/Excel | Should | **[Asumsi: format laporan belum ditentukan keuangan]** |
| FR-11 | Impor PO dari CSV (kolom minimal `kode,vendor,total,status,order_date`) dengan validasi & laporan error per baris | Should | Format `purchase_orders.csv` |
| FR-12 | Audit log perubahan PO (siapa, kapan, perubahan apa) | Should | Dukungan workflow approval |
| FR-13 | Admin kelola pengguna & peran | Should | BR-13 |
| FR-14 | Halaman bantuan/glosarium singkat (PO, Vendor, status) | Could | Kebutuhan usability |
| FR-15 | REST API terdokumentasi (OpenAPI/Swagger) untuk PO & vendor sebagai fondasi integrasi ERP | Should | Judul produk "Integrasi ERP" |
| FR-16 | Pembersihan artefak ganda: satukan `PurchaseOrdersController`↔`PurchaseOrderController`, model `PurchaseOrders`↔`PurchaseOrder`; tunggalkan set status PO; hubungkan PO ke tabel `vendors` (relasi/pemilihan vendor, bukan string bebas) **[Asumsi: keputusan normalisasi menunggu konfirmasi]** | Must | Fakta repositori (artefak ganda) |

---

## 8. Asumsi

| ID | Asumsi | Status Verifikasi |
|---|---|---|
| A-1 | Pengguna akhir internal (staff pengadaan, manajer, keuangan, admin); tidak ada pengguna eksternal di Fase 1 | Perlu konfirmasi Product Owner |
| A-2 | Daftar status PO final: `draft`, `submitted`, `approved`, `rejected` (data saat ini hanya memuat `approved` & `draft`; template perintah menyebut `pending`) | Perlu keputusan M1 |
| A-3 | Hanya peran `manager` yang boleh approve/reject PO | Perlu konfirmasi |
| A-4 | Skema peran final: `admin`, `procurement_staff`, `manager` | Perlu konfirmasi |
| A-5 | Volume tahun pertama s.d. 50.000 PO & 5.000 vendor; s.d. 50 pengguna aktif bersamaan | Perlu validasi kapasitas |
| A-6 | Format ekspor laporan keuangan: CSV (menunggu keputusan keuangan; bisa berubah ke Excel) | Perlu konfirmasi Keuangan |
| A-7 | Sistem ERP eksternal tujuan integrasi belum ditentukan; Fase 1 hanya fondasi API | Perlu konfirmasi IT/Product Owner |
| A-8 | Lingkungan produksi & SLA hosting belum ditentukan; uptime target jam kerja 08.00-17.00 | Perlu konfirmasi IT/Infra |
| A-9 | Kapasitas tim 1-2 developer; estimasi durasi 8-11 minggu | Perlu kalibrasi tim |
| A-10 | Pola `kode` PO bebas (tidak ada format wajib) selama unik | Perlu konfirmasi Manajemen Procurement |
| A-11 | Data historis CSV contoh valid dan dapat diimpor ulang setelah validasi | Diverifikasi saat staging impor |
| A-12 | Bahasa antarmuka tunggal: Bahasa Indonesia | Perlu konfirmasi Product Owner |

---

## 9. Batasan (Constraints)

| ID | Batasan | Jenis | Dampak |
|---|---|---|---|
| C-1 | Stack teknologi terikat keputusan tim: **Laravel 11 + MySQL** (catatan `.mcp/notes/notes.md`) - tidak boleh berganti framework fase ini | Teknis | Seluruh implementasi mengikuti ekosistem Laravel/Eloquent/Blade |
| C-2 | Struktur data existing harus dihormati: kolom `purchase_orders` (`kode`, `vendor` sebagai string, `total` decimal 15,2, `status`, `order_date`) & `vendors` (`nama`, `alamat`, `kontak`, `aktif`) | Teknis | Perubahan skema (mis. FK vendor) butuh migrasi tersendiri (FR-16) |
| C-3 | Paginasi 25 baris/halaman sudah menjadi konvensi controller | Teknis | Desain UI mengikuti konvensi ini |
| C-4 | Artefak ganda controller/model harus dibersihkan tanpa memutus endpoint yang sudah berjalan | Teknis | Gate milestone awal (lihat Timeline) |
| C-5 | Akses vendor eksternal/portal mandiri tidak tersedia di Fase 1 | Bisnis | Fitur ditunda ke fase berikutnya |
| C-6 | Integrasi ERP eksternal real-time di luar Fase 1 (hanya fondasi API + impor CSV) | Bisnis | Batasan BO-5 |
| C-7 | Aplikasi harus berbahasa Indonesia penuh (UI, pesan error, laporan) | Bisnis | FR-14, BR-14 |
| C-8 | Anggaran & tenaga belum ditetapkan resmi; asumsi sementara 1-2 developer **[Asumsi]** | Sumber daya | Estimasi biaya di Bagian 12 berformat parameter, bukan angka final |
| C-9 | Lingkungan produksi/SLA/backup belum tersedia atau belum ditunjuk **[Asumsi]** | Infrastruktur | Rencana rilis menunggu konfirmasi IT |
| C-10 | Tidak ada perhitungan pajak/pembayaran/e-signature di Fase 1 | Bisnis | Out of scope |

---

## 10. Kriteria Sukses & KPI

| ID | Kriteria Sukses / KPI | Cara Ukur | Target * | Prioritas |
|---|---|---|---|---|
| KPI-1 | Adopsi: PO baru tercatat di sistem (bukan spreadsheet) | Count PO via aplikasi vs total PO tim | >= 95% pada bulan ke-2 setelah rilis | Must |
| KPI-2 | Kecepatan: waktu rata-rata membuat PO | Instrumentasi timestamp form start → submit | <= 3 menit | Must |
| KPI-3 | Kecepatan: pencarian PO | Pengukuran waktu respon daftar/filter | < 10 detik | Must |
| KPI-4 | Kualitas data: duplikat `kode` PO | Query audit | 0 duplikat | Must |
| KPI-5 | Kualitas approval: PO approved tanpa revisi data | PO approved / PO submitted | >= 90% | Should |
| KPI-6 | Akurasi rekap per vendor vs laporan manual | Audit sampling 10 vendor/bulan | Selisih = 0 | Must |
| KPI-7 | Kualitas impor: baris gagal validasi CSV | Baris gagal / total baris | <= 5% | Should |
| KPI-8 | Kesiapan integrasi: endpoint PO/Vendor terdokumentasi & lulus smoke test API | Cek dokumentasi OpenAPI + test | 100% endpoint | Should |
| KPI-9 | Keamanan: insiden akses tanpa otorisasi | Log insiden per bulan | 0 | Must |
| KPI-10 | Keamanan: endpoint terproteksi autentikasi/otorisasi | Audit kode & penetration checklist | 100% endpoint | Must |
| KPI-11 | Keandalan: uptime jam kerja (Senin-Sabtu 08.00-17.00) | Monitoring ketersediaan | >= 99% per bulan | Should |
| KPI-12 | Adopsi pengguna aktif bulanan | Login aktif > 4x/bulan / total pengguna | >= 80% | Should |

\* Semua angka target bersifat **[Asumsi]** sampai disepakati stakeholder bisnis.

---

## 11. Analisis Risiko

| ID | Risiko | Dampak | Probabilitas * | Mitigasi |
|---|---|---|---|---|
| R-1 | Set status PO belum tunggal & artefak ganda controller/model membingungkan tim | Sedang-Tinggi | Sedang | Jadikan pembersihan (FR-16) gate milestone awal; dokumentasikan finalisasi status di repo |
| R-2 | Kolom `vendor` pada PO masih string, bukan relasi - data vendor tidak konsisten | Tinggi | Sedang | Relasi/FK + form pemilihan vendor aktif (BR-4); migrasi data contoh CSV |
| R-3 | Aturan approval & hak akses belum final dari bisnis | Sedang | Sedang | Finalisasi di M1 (A-2, A-3); default sementara `manager` approve, tandai [Asumsi] |
| R-4 | Lingkungan produksi & koneksi ERP eksternal belum ditentukan | Sedang | Sedang | Fase 1 hanya fondasi API + CSV; integrasi eksternal ditunda sampai requirement jelas |
| R-5 | Data historis CSV tidak bersih (status/format tanggal) saat impor | Sedang | Sedang | Validasi per baris + laporan error (FR-11); staging impor sebelum go-live |
| R-6 | Performa belum teruji (data contoh baru 5 baris) | Sedang | Sedang | Uji beban dengan seed data ~10.000 baris; indeks kolom filter (`kode`, `status`, `vendor`) |
| R-7 | Keamanan akses dilewatkan demi kecepatan demo | Tinggi | Rendah | KPI-9/KPI-10 wajib lolos sebelum rilis; checklist code review |
| R-8 | Kredensial/env bocor ke repo | Tinggi | Rendah | `.env` gitignored; rotasi kredensial; hindari verbose error di produksi |
| R-9 | Timeline melar karena kapasitas tim belum pasti | Sedang | Sedang | Milestone bertahap; rilis inti M1-M5 lebih dulu, M6-M7 menyusul |
| R-10 | Kebutuhan keuangan (format laporan) berubah di tengah jalan | Rendah-Sedang | Sedang | Format ekspor di-desain pluggable (CSV dulu, Excel belakangan) |

\* Penilaian dampak & probabilitas bersifat **[Asumsi]** penilaian awal reviewer.

---

## 12. Estimasi Biaya & Timeline

12.1 **Timeline (berbasis milestone PRD v1.0 - durasi relatif, tanggal kalender menunggu konfirmasi kapasitas tim):**

| Milestone | Deliverable | Estimasi Durasi * | Ketergantungan |
|---|---|---|---|
| M1 - Finalisasi Kebutuhan | BRD/PRD disetujui; status PO, peran, format laporan difinalkan; pertanyaan terbuka terjawab | 1 minggu | Stakeholder (PO, Keuangan, IT) |
| M2 - Fondasi Backend | Bersihkan artefak ganda (FR-16), tunggalkan status, relasi/FK vendor, validasi BR-1 s/d BR-5 | 1-2 minggu | M1 |
| M3 - UI Web Bahasa Indonesia | Halaman Vendor & PO (CRUD, paginasi, filter, pesan error) | 2-3 minggu | M2 |
| M4 - Autentikasi & Otorisasi | Login/logout, peran, policy per endpoint, audit log | 1 minggu | M2 |
| M5 - Approval & Rekap | Workflow status (BR-2), UI rekap per vendor, ekspor | 1-2 minggu | M3, M4 |
| M6 - Impor CSV & API Docs | Impor CSV, OpenAPI/Swagger, test skenario kritis | 1 minggu | M2 |
| M7 - QA, Hardening & Rilis | UAT, uji performa, backup, go-live | 1 minggu | M3-M6 |

**Total estimasi: 8-11 minggu dengan 1-2 developer (termasuk buffer).**

12.2 **Estimasi biaya (parameter - angka final menunggu keputusan manajemen):**

| Komponen Biaya | Basis Perhitungan | Estimasi * |
|---|---|---|
| Pengembangan | Durasi x jumlah developer x rate tim | 8-11 minggu x 1-2 developer; rate belum ada data **[Asumsi: isi setelah manajemen menetapkan rate]** |
| Infrastruktur produksi | Server/hosting, domain, SSL | Belum ada data; menunggu IT (A-8) **[Asumsi]** |
| Lisensi/tools | Laravel & stack utama open-source (fakta repo); tools tambahan TBD | Minimal di Fase 1 **[Asumsi]** |
| QA & uji beban | Termasuk di M7; tools uji TBD | **[Asumsi]** |
| Buffer risiko | ~10-20% dari total | **[Asumsi]** |

\* Seluruh angka biaya **belum dapat ditetapkan** karena data rate & infrastruktur belum tersedia; bagian ini wajib di-update setelah konfirmasi manajemen (lihat Pertanyaan Terbuka PRD Q-6).

---

## 13. Persetujuan (Approval)

| Peran | Nama | Tanggung Jawab Persetujuan | Tanda Tangan | Tanggal |
|---|---|---|---|---|
| Product Owner / Sponsor | *(belum ditunjuk)* **[Asumsi]** | Menyetujui ruang lingkup, tujuan bisnis, & prioritas | ______ | ______ |
| Manajer Procurement | *(belum ditunjuk)* **[Asumsi]** | Menyetujui workflow approval & aturan status PO | ______ | ______ |
| Perwakilan Keuangan | *(belum ditunjuk)* **[Asumsi]** | Menyetujui format rekap & ekspor laporan | ______ | ______ |
| IT / Infrastruktur | *(belum ditunjuk)* **[Asumsi]** | Menyetujui lingkungan produksi, SLA, & backup | ______ | ______ |
| Tech Lead / Pengembang | *(belum ditunjuk)**[Asumsi]** | Menyetujui kelayakan teknis & estimasi timeline | ______ | ______ |

**Riwayat Versi:**

| Versi | Tanggal | Perubahan | Penulis |
|---|---|---|---|
| 1.0 | 14 Okt 2026 | Draf awal BRD berbahasa Indonesia (13 bagian) | [Asumsi: Business Analyst] |

**Tinjauan berikutnya:** setelah Pertanyaan Terbuka PRD (Q-1 status PO & hak approve, Q-2 skema peran, Q-4 format ekspor keuangan, Q-6 lingkungan produksi) terjawab, BRD naik ke Versi 1.1 dengan angka target final, timeline kalender, dan estimasi biaya konkret.
