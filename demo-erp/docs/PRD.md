# PRD - Integrasi ERP

| Field | Nilai |
|---|---|
| Project | demo-erp |
| Judul | Website Integrasi ERP - Manajemen Purchase Order (PO) & Vendor |
| Versi Dokumen | 1.0 |
| Tanggal | 14 Oktober 2026 |
| Status | Draft - siap review tim |
| Bahasa Produk | Bahasa Indonesia |
| Penulis | [Asumsi: Business Analyst / Technical Writer] |
| Stack (tercatat di repo) | Laravel 11 + MySQL - catatan tim tanggal 14 Okt 2026 (`.mcp/notes/notes.md`) |

> Catatan fakta: setiap kebutuhan yang datanya tidak tersedia di repositori atau dari stakeholder diberi tanda **[Asumsi]** atau dimasukkan ke **Pertanyaan Terbuka**.

---

## 1. Ringkasan Produk (Overview)

demo-erp adalah aplikasi web berbahasa Indonesia untuk mengelola **Purchase Order (PO)** dan **Vendor** sebagai bagian dari rangkaian integrasi ERP. Sistem menyediakan pendataan vendor, pencatatan PO, pengelolaan status PO, serta rekap nilai PO approved per vendor.

**Kondisi repositori saat ini (fakta):**
- Backend Laravel 11 + MySQL (keputusan tim tercatat di `.mcp/notes/notes.md`, 14 Okt 2026).
- Model & migration sudah ada:
  - `purchase_orders`: `id`, `kode`, `vendor`, `total` (decimal 15,2), `status`, `order_date`, `timestamps`.
  - `vendors`: `id`, `nama`, `alamat`, `kontak`, `aktif` (boolean), `timestamps`.
- Endpoint JSON (scaffold CRUD) sudah ada:
  - `PurchaseOrderController`: list (paginate 25), create, show, update, delete, plus endpoint rekap `approvedTotalByVendor`.
  - `VendorController`: list (paginate 25), create, show, update, delete.
- Data contoh `purchase_orders.csv`: 5 PO dari 3 vendor (CV Maju Jaya, PT Sinar Abadi, PT Karya Nusantara) dengan status `approved` dan `draft`.
- Terdapat artefak scaffold ganda (`PurchaseOrderController` + `PurchaseOrdersController`, model `PurchaseOrder` + `PurchaseOrders`) yang perlu dibersihkan.

**Gap produk yang mendorong PRD ini:** saat ini baru ada layer model/controller — belum ada UI web, autentikasi, validasi bisnis, workflow approval, dan integrasi/impor data. PRD ini mengisi gap tersebut.

**Pengguna akhir utama:** staff pengadaan (procurement), manajer/persetujuan, dan keuangan untuk rekap. **[Asumsi: kebutuhan eksternal akses vendor berada di luar fase awal - lihat Out of Scope & Open Questions.]**

---

## 2. Tujuan & Sasaran (Goals)

| ID | Tujuan | Sasaran Terukur | Prioritas |
|---|---|---|---|
| G-1 | Menyatukan data PO & vendor dalam satu sumber data | 100% PO baru tercatat di sistem (bukan CSV/spreadsheet terpisah) | Must |
| G-2 | Mempercepat pencatatan & pencarian PO | Buat PO rata-rata < 3 menit; cari PO < 10 detik | Must |
| G-3 | Memberi kontrol kualitas data via workflow approval | Setiap PO punya status yang jelas (draft/approved/dst) dan jejak perubahan | Must |
| G-4 | Menyediakan rekap nilai PO approved per vendor | Rekap dapat diekspor/ dilihat tanpa hitung manual | Should |
| G-5 | Menyiapkan fondasi integrasi ERP (API + impor data) | API terdokumentasi; impor CSV 5+ PO tanpa error | Should |
| G-6 | Menjaga keamanan akses | Semua endpoint wajib autentikasi & otorisasi peran | Must |

> Sasaran angka (waktu, jumlah) bersifat **[Asumsi]** sampai kalibrasi dengan tim.

---

## 3. Target Pengguna & Persona

| Persona | Peran | Kebutuhan Utama | Frekuensi Pakai |
|---|---|---|---|
| Staff Procurement (Rina) * | Input PO, kelola data vendor | Form cepat, validasi jelas, tidak double-entry | Harian |
| Manajer Procurement (Andi) * | Review & approve/reject PO | Antrean approval, riwayat perubahan | Harian |
| Staf Keuangan (Sari) * | Rekap nilai PO approved per vendor | Laporan/rekap per vendor & periode | Mingguan |
| Admin Sistem * | Kelola pengguna, master data, backup | Pengelolaan peran, audit log | Periodik |

\* Nama persona bersifat **[Asumsi]** (placeholder untuk validasi user research).

---

## 4. User Stories

| ID | User Story | Prioritas |
|---|---|---|
| US-1 | Sebagai Staff Procurement, saya ingin menambah vendor baru agar datanya bisa dipakai saat membuat PO | Must |
| US-2 | Sebagai Staff Procurement, saya ingin mencari & memfilter vendor hanya yang aktif agar pilihan tidak salah | Must |
| US-3 | Sebagai Staff Procurement, saya ingin membuat PO (kode, vendor, total, tanggal, status draft) agar tercatat sistematis | Must |
| US-4 | Sebagai Staff Procurement, saya ingin melihat daftar PO dengan paging agar mudah dinavigasi | Must |
| US-5 | Sebagai Staff Procurement, saya ingin mengedit/menghapus PO draft | Must |
| US-6 | Sebagai Manajer Procurement, saya ingin menyetujui/menolak PO agar status data akurat | Must |
| US-7 | Sebagai Manajer Procurement, saya ingin hanya PO milik saya dapat diubah sesuai peran | Should |
| US-8 | Sebagai Staf Keuangan, saya ingin melihat rekap total PO approved per vendor untuk laporan | Must |
| US-9 | Sebagai Staf Keuangan, saya ingin mengekspor rekap ke CSV/Excel | Should |
| US-10 | Sebagai Staff Procurement, saya ingin impor PO dari CSV (format `purchase_orders.csv`) agar migrasi data lama mudah | Should |
| US-11 | Sebagai Admin, saya ingin kelola pengguna & peran | Should |
| US-12 | Sebagai pengguna, saya ingin login/logout agar data aman | Must |
| US-13 | Sebagai pengguna, saya ingin antarmuka penuh berbahasa Indonesia agar konsisten | Must |

---

## 5. Fitur & Kebutuhan Fungsional

### 5.1 Kebutuhan Fungsional (Functional Requirements)

| ID | Kebutuhan | Prioritas | Dasar |
|---|---|---|---|
| FR-1 | Registrasi/login/logout pengguna dengan sesi aman | Must | - |
| FR-2 | Role minimal: `admin`, `procurement_staff`, `manager` * | Must | [Asumsi: daftar peran final perlu konfirmasi] |
| FR-3 | CRUD Vendor (`nama`, `alamat`, `kontak`, `aktif`) dengan validasi required & unik `nama` | Must | Tabel `vendors` & `VendorController` yang ada |
| FR-4 | Daftar vendor dengan paginasi (25/baris) dan filter/search | Must | `VendorController@index` paginate(25) |
| FR-5 | CRUD PO (`kode`, `vendor`, `total`, `status`, `order_date`) | Must | Tabel `purchase_orders` & `PurchaseOrderController` |
| FR-6 | Validasi `kode` PO unik; `total` > 0 (decimal 15,2); `order_date` <= hari ini * | Must | [Asumsi: aturan unik kode dari gap analitik duplikat] |
| FR-7 | Daftar PO dengan paginasi (25/baris) + filter status, vendor, rentang tanggal, pencarian `kode` | Must | `PurchaseOrderController@index` paginate(25) |
| FR-8 | Transisi status PO: draft → submitted → approved / rejected (lihat BR-2) | Must | `status` kolom pada schema |
| FR-9 | Endpoint/halaman rekap total PO approved per vendor, urut terbesar | Must | Scope `approvedTotalByVendor` di model |
| FR-10 | Ekspor rekap per vendor (CSV) | Should | [Asumsi: format laporan belum ditentukan] |
| FR-11 | Impor PO dari CSV (kolom minimal `kode,vendor,total,status,order_date`) | Should | Format data `purchase_orders.csv` yang ada |
| FR-12 | Audit log perubahan PO (siapa, kapan, perubahan apa) | Should | Dibutuhkan untuk workflow approval |
| FR-13 | Kelola pengguna & peran oleh admin | Should | - |
| FR-14 | Halaman bantuan/glosarium singkat (PO, Vendor, status) | Could | - |
| FR-15 | REST API terdokumentasi (OpenAPI/Swagger) untuk PO & Vendor sebagai fondasi integrasi ERP | Should | Judul produk "Integrasi ERP" |

### 5.2 Peraturan Bisnis (Business Rules)

| ID | Aturan | Prioritas |
|---|---|---|
| BR-1 | PO tidak dapat dihapus setelah status `approved`/`submitted`; hanya dibatalkan dengan alasan (soft status) * | Must |
| BR-2 | Alur status: `draft → submitted → approved | rejected`; hanya role `manager` yang boleh approve/reject * | Must |
| BR-3 | Hanya vendor dengan `aktif = true` yang bisa dipilih saat membuat/mengubah PO | Must |
| BR-4 | Total PO harus > 0 dan maksimal sesuai batas kolom (decimal 15,2) | Must |
| BR-5 | Rekap per vendor hanya menjumlahkan PO berstatus `approved` (selaras scope `approvedTotalByVendor`) | Must |
| BR-6 | Vendor tidak dapat dihapus jika masih punya PO terkait * | Should |

\* Nilai konvensi (label status, hak approve, soft-delete policy) bersifat **[Asumsi]** sampai dikonfirmasi.

### 5.3 Catatan Konsistensi Data Wajib Dibersihkan

| ID | Kebutuhan | Prioritas |
|---|---|---|
| TD-1 | Hapus/satukan artefak ganda: `PurchaseOrdersController` vs `PurchaseOrderController`, model `PurchaseOrders` vs `PurchaseOrder` | Must |
| TD-2 | Tetapkan satu set status PO (data saat ini memuat `approved`, `draft`; template perintah menyebut `pending`, `rejected`) | Must |
| TD-3 | Hubungkan PO ke tabel `vendors` (foreign key / pemilihan vendor), bukan string bebas * | Should |

\* **[Asumsi: keputusan normalisasi tersedia setelah dikonfirmasi].**

---

## 6. Kebutuhan Non-Fungsional (performa, keamanan, skala)

| ID | Kategori | Kebutuhan | Target/Ukuran * | Prioritas |
|---|---|---|---|---|
| NFR-1 | Performa | Waktu muat halaman daftar (25 baris) | < 1,5 detik pada koneksi internal | Must |
| NFR-2 | Performa | Respons API CRUD PO/Vendor (95th percentile) | < 500 ms | Must |
| NFR-3 | Performa | Waktu render rekap per vendor (1000 PO) | < 3 detik | Should |
| NFR-4 | Skala | Jumlah pengguna bersamaan saat rilis | s.d. 50 pengguna aktif, tanpa degradasi NFR-2 | Must |
| NFR-5 | Skala | Volume data PO/vendor tahun pertama | s.d. 50.000 PO & 5.000 vendor tanpa migration ulang; indeks `kode`, `status`, `vendor` | Should |
| NFR-6 | Keamanan | Password hashing (bcrypt/argon2), proteksi CSRF pada form web, rate limit login | Laravel default + konfigurasi eksplisit | Must |
| NFR-7 | Keamanan | Otorisasi per role di setiap endpoint (policy/gate), tidak hanya di UI | 100% endpoint terproteksi | Must |
| NFR-8 | Keamanan | Data `total` & nominal tidak bocor via error message verbose di produksi | Debug off di prod | Must |
| NFR-9 | Keamanan | Backup DB harian & retensi 30 hari * | RTO < 4 jam, RPO < 24 jam | Should |
| NFR-10 | Keamanan | Env/secret tidak masuk repo (.env gitignored) | 0 kebocoran kredensial | Must |
| NFR-11 | Ketersediaan | Uptime jam kerja (Senin-Sabtu 08.00-17.00) | >= 99% per bulan * | Should |
| NFR-12 | Kualitas | Cakupan automated test untuk CRUD + approval flow | >= 70% jalur kritis | Should |
| NFR-13 | Aksesibilitas | UI bisa dipakai di resolusi 1366x768, teks bahasa Indonesia konsisten | Pass pemeriksaan manual | Could |
| NFR-14 | Keamanan | Proteksi SQL injection & XSS memakai Eloquent/Blade escaping | Code review checklist | Must |

\* Semua angka target bersifat **[Asumsi]** sampai disepakati tim/infra.

---

## 7. Alur Pengguna (User Flow)

**A. Manajemen Vendor**
1. Pengguna login -> menu Vendor -> "Tambah Vendor"
2. Isi form (nama, alamat, kontak, aktif) -> simpan
3. Validasi gagal -> tampilkan pesan error Bahasa Indonesia -> kembali ke form (data terisi)
4. Validasi sukses -> vendor muncul di daftar (paginasi 25/baris)

**B. Membuat & Menyetujui PO**
1. Staff Procurement -> menu Purchase Order -> "Buat PO"
2. Isi `kode`, pilih vendor (hanya aktif), `total`, `order_date`, status awal `draft` -> simpan
3. Sistem validasi (kode unik, total > 0) -> gagal: tampil error; sukses: tersimpan
4. Staff tekan "Ajukan" -> status `submitted`
5. Manager buka antrean approval -> review detail PO -> "Setujui" -> status `approved`; atau "Tolak" -> status `rejected`
6. PO approved masuk ke basis rekap; setiap perubahan tercatat di audit log

**C. Rekap & Analitik**
1. Staf Keuangan -> menu Rekap -> filter periode/vendor
2. Sistem menghitung SUM(total) untuk status `approved`, grup per vendor, urut menurun
3. Pengguna melihat tabel rekap -> (Should) ekspor CSV

**D. Impor Data CSV (Should)**
1. Pengguna -> menu Import -> unggah CSV kolom `kode,vendor,total,status,order_date`
2. Sistem validasi tiap baris & laporan error per baris -> data valid tersimpan; baris invalid ditolak dilaporkan

---

## 8. Metrik Keberhasilan (Success Metrics)

| ID | Metrik | Cara Ukur | Target * | Prioritas |
|---|---|---|---|---|
| SM-1 | 100% PO baru tercatat di sistem | Count PO masuk via app vs total PO tim | >= 95% bulan ke-2 setelah rilis | Must |
| SM-2 | Waktu rata-rata buat PO | Instrumentasi timestamp form start->submit | <= 3 menit | Must |
| SM-3 | Rasio PO approved tanpa revisi data | PO approved / PO submitted | >= 90% | Should |
| SM-4 | Akurasi rekap per vendor vs laporan manual | Audit sampling 10 vendor/bulan | Selisih = 0 | Must |
| SM-5 | Error validasi pada impor CSV | Jumlah baris gagal / total baris | <= 5% | Should |
| SM-6 | Kesiapan integrasi | Endpoint terdokumentasi & lulus smoke test API | 100% endpoint PO/Vendor terdokumentasi | Should |
| SM-7 | Retensi pengguna aktif bulanan | Login aktif > 4x sebulan / total pengguna | >= 80% | Should |
| SM-8 | Insiden keamanan terkait akses | Jumlah insiden unauthorized access per bulan | 0 | Must |

\* Target angka bersifat **[Asumsi]**, kalibrasi bersama stakeholder bisnis.

---

## 9. Di Luar Cakupan (Out of Scope)

Fase 1 **tidak** mencakup:
- Modul selengkapnya (Gudang/Stok, Akunting/GL, HR, Sales) - catatan: prompt `cek-stok` menunjukkan tema stok gudang, namun belum ada implementasi; masuk roadmap terpisah.
- Portal mandiri vendor (vendor submit PO sendiri) - kompleksitas auth eksternal & keamanan.
- Integrasi real-time/API dengan sistem ERP eksternal (SAP, Odoo, Accurate, dll) - integrasi baru fondasi di FR-15. Nama sistem target ERP belum ditentukan. *[Asumsi]*
- Mobile app native (UI web responsif saja).
- Perhitungan pajak/pelunasan/pembayaran PO.
- E-signature & antar-modul workflow (multi-approval berjenjang).
- Laporan BI/analitik lanjutan.
- Migrasi klasifikasi COA/gudang/produk.

---

## 10. Milestone & Timeline

| Milestone | Deliverable | Estimasi Durasi * | Status |
|---|---|---|---|
| M1 - Riset & Finalisasi Kebutuhan | PRD disetujui, daftar status PO & peran difinalkan, skema mendetail | 1 minggu | Draft |
| M2 - Fondasi Backend | Bersihkan artefak ganda (TD-1), finalkan status (TD-2), tambah FK vendor (TD-3), validasi BR-1 s/d BR-5 | 1-2 minggu | Belum mulai |
| M3 - UI Web Bahasa Indonesia | Halaman Vendor CRUD + PO CRUD + paginasi + filter + pesan error | 2-3 minggu | Belum mulai |
| M4 - Auth & Otorisasi | Login/logout, peran, policy per endpoint, audit log | 1 minggu | Belum mulai |
| M5 - Approval & Rekap | Workflow status (BR-2), rekap per vendor, ekspor CSV | 1-2 minggu | Belum mulai |
| M6 - Impor CSV & API Docs | Impor `purchase_orders.csv`, OpenAPI/Swagger, test skenario kritis | 1 minggu | Belum mulai |
| M7 - QA, Hardening & Rilis | UAT, uji performa NFR-1/2, backup/retensi, go-live | 1 minggu | Belum mulai |

**Total estimasi: 8-11 minggu dengan 1-2 developer** (termasuk buffer). \* **[Asumsi: estimasi belum dikalibrasi tim; tanggal kalender bergantung juga pada kapasitas tim.]**

---

## 11. Risiko & Mitigasi

| ID | Risiko | Dampak | Probabilitas * | Mitigasi |
|---|---|---|---|---|
| R-1 | Status PO belum tunggal (draft/submitted/approved/rejected/pending) dan artefak ganda controller/model membingungkan tim | Sedang-Tinggi | Sedang | TD-1 & TD-2 dijadikan gate M2; dokumentasikan finalisasi di repo |
| R-2 | Schema PO menyimpan vendor sebagai string, bukan relasi - data vendor tidak konsisten | Tinggi | Sedang | TD-3 FK + form pemilihan vendor aktif (BR-3); migrasi data CSV awal |
| R-3 | Aturan approval & hak akses tidak eksplisit dari bisnis | Sedang | Sedang | Kunci di M1 sebagai BR-2; default sementara `manager` approves, tandai [Asumsi] |
| R-4 | Lingkungan hosting/koneksi ERP eksternal belum ditentukan | Sedang | Sedang | Fase 1 hanya fondasi API + CSV; integrasi ERP eksternal ditunda sampai requirement jelas |
| R-5 | Data historis dari CSV tidak bersih (status/format tanggal) saat impor | Sedang | Sedang | Validasi per-baris + laporan error; staging import sebelum go-live |
| R-6 | Skala/performanya belum teruji (data 5 baris saja hari ini) | Sedang | Sedang | Seed data 10.000 baris untuk uji beban; indeks kolom filter |
| R-7 | Keamanan akses dilewatkan karena fitur demo kejar cepat | Tinggi | Rendah | NFR-6,7,8,10 wajib lolos sebelum rilis; checklist code review |
| R-8 | Ketergantungan satu kredensial/env (*.env) bocor | Tinggi | Rendah | Rotasi kredensial, .env gitignored, gunakan secrets manager (jika tersedia) * |
| R-9 | Timeline berubah karena kapasitas tim | Sedang | Sedang | Milestone bertahap; fase 1 bisa dirilis M1-M5, sisanya M6-M7 |

\* **Probabilitas & dampak bersifat [Asumsi] penilaian awal reviewer.**

---

## 12. Pertanyaan Terbuka (Open Questions)

| ID | Pertanyaan | Diperlukan Dari | Dampak Jika Terlambat |
|---|---|---|---|
| Q-1 | Daftar final status PO & siapa yang boleh approve/reject? | Product Owner / Manajemen | Workflow (FR-8, BR-2) |
| Q-2 | Skema peran final (admin/staff/manager/lainnya)? | Product Owner | FR-2, NFR-7 |
| Q-3 | Aplikasi harus terhubung ke sistem ERP mana saja (nama produk/API/format)? | IT / Vendor ERP | Integrasi & Out of Scope |
| Q-4 | Standar format ekspor yang diharinkan keuangan (CSV/Excel, kolom apa saja)? | Keuangan | FR-10, SM-4 |
| Q-5 | Apakah vendor akses mandiri masuk cakupan? Jika ya, berapa user eksternal? | Product Owner | Out of Scope & NFR-4 |
| Q-6 | Environment produksi: server mana, SLA, backup tersedia? | IT/Infra | NFR-9, NFR-11 |
| Q-7 | Apakah kode PO harus ikut pola tertentu (mis. PO-YYYYMM-###)? | Manajemen Procurement | FR-6 |
| Q-8 | Bahasa antarmuka selain Bahasa Indonesia diperlukan? | Product Owner | NFR-13, US-13 |
| Q-9 | Metode verifikasi data impor (staging dulu atau langsung)? | Tim Eng. | FR-11 |

---

**Dokumen terkait:** `CHANGELOG.md` (opsional), `.mcp/notes/notes.md` (keputusan), `purchase_orders.csv` (data contoh), `docs/BRD.md` (jika diperlukan).

*Tinjauan berikutnya: setelah Q-1, Q-2, dan Q-4 terjawab, PRD naik ke Versi 1.1 dengan angka target final & timeline kalender.*
