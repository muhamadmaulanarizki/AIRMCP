---
title: Buat Migration ERP
description: Generate migration Laravel + model untuk tabel baru di project ini
required: table, fields
argument: table = nama tabel (snake_case), mis. purchase_orders
argument: fields = daftar field name:type, mis. nama:string,total:decimal
---
Kamu engineer Laravel di project ERP ini. Buatkan migration dan Eloquent model
untuk tabel `{{table}}` dengan field berikut:

{{fields}}

Aturan:
- Gunakan tipe kolom Laravel yang tepat (string, decimal(15,2), boolean, foreignId).
- Tambahkan $fillable dan $casts pada model.
- Tulis nama file migration dengan timestamp terbaru.
- Setelah selesai, tampilkan ringkasan kolom yang dibuat.
