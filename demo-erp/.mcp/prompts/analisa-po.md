---
title: Analisa Purchase Order
description: Ringkas data PO dari CSV, hitung total per vendor + status
required: path
argument: path = path file CSV purchase order
---
Baca file CSV berikut lalu buat ringkasan analitis:

File: {{path}}

Yang harus kamu laporkan:
1. Total nilai PO per vendor (hanya yang statusnya approved).
2. Vendor dengan total terbesar.
3. Jumlah PO per status (approved / pending / rejected).
4. Sajikan sebagai tabel, lalu satu paragraf kesimpulan singkat.
