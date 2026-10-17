<?php

return [

    'brand' => [
        'name' => 'Kopi Senja',
        'tagline' => 'Kopi hangat untuk setiap cerita',
        'description' => 'Coffee shop dengan biji kopi pilihan Nusantara, disajikan untuk teman curhat, kerja, dan berkumpul.',
        'logo_text' => 'KS',
        'palette' => [
            'primary' => '#6f4e37',
            'accent' => '#c9a227',
            'cream' => '#f7f1e8',
        ],
    ],

    'contact' => [
        'address' => 'Jl. Kopi Senja No. 12, Kota Senja, Indonesia',
        'phone' => '0812-0000-0000',
        'whatsapp' => '6281200000000',
        'email' => 'halo@kopisenja.example',
        'instagram' => '@kopisenja',
        'maps_url' => 'https://www.google.com/maps',
    ],

    'hours' => [
        ['day' => 'Senin - Jumat', 'time' => '07.00 - 22.00'],
        ['day' => 'Sabtu', 'time' => '08.00 - 23.00'],
        ['day' => 'Minggu', 'time' => '08.00 - 21.00'],
    ],

    'socials' => [
        ['label' => 'Instagram', 'url' => 'https://instagram.com'],
        ['label' => 'Facebook', 'url' => 'https://facebook.com'],
        ['label' => 'TikTok', 'url' => 'https://tiktok.com'],
    ],

    /*
    |--------------------------------------------------------------------------
    | MENU — single source of truth (fase-1 config-driven, tanpa DB)
    |--------------------------------------------------------------------------
    | Untuk ubah konten menu: edit bagian ini saja, tidak perlu sentuh view.
    | 'price' dalam Rupiah tanpa titik/koma.
    */
    'menu' => [
        'Kopi' => [
            [
                'name' => 'Es Kopi Susu Gula Aren',
                'price' => 18000,
                'desc' => 'Espresso, susu segar, dan gula aren asli — favorit pelanggan.',
                'img' => 'images/coffee/es-kopi-susu.webp',
                'license' => 'CC0 1.0',
                'photographer' => 'rawpixel',
                'source_url' => 'https://www.rawpixel.com/image/5928100/photo-image-background-public-domain-glass',
                'attribution_required' => false,
            ],
            [
                'name' => 'Kopi Tubruk',
                'price' => 15000,
                'desc' => 'Kopi hitam klasik diseduh manual, pahit pekat khas Nusantara.',
                'img' => 'images/coffee/kopi-tubruk.webp',
                'license' => 'CC0 1.0',
                'photographer' => 'rawpixel',
                'source_url' => 'https://www.rawpixel.com/image/5911577/image-public-domain-coffee-free',
                'attribution_required' => false,
            ],
            [
                'name' => 'Cappuccino',
                'price' => 25000,
                'desc' => 'Espresso dengan foam susu lembut dan taburan kakao.',
                'img' => 'images/coffee/cappuccino.webp',
                'license' => 'CC0 1.0',
                'photographer' => 'Image Catalog (Flickr)',
                'source_url' => 'https://www.flickr.com/photos/132795455@N08/18281357909',
                'attribution_required' => false,
            ],
            [
                'name' => 'Cold Brew',
                'price' => 24000,
                'desc' => 'Diseduh dingin 12 jam, rasa smooth dan rendah asam.',
                'img' => 'images/coffee/cold-brew.webp',
                'license' => 'CC0 1.0',
                'photographer' => 'Roland Tanglao (Wikimedia Commons)',
                'source_url' => 'https://commons.wikimedia.org/wiki/File:Iced_cold_brew_coffee.jpg',
                'attribution_required' => false,
            ],
        ],
        'Non-Kopi' => [
            [
                'name' => 'Matcha Latte',
                'price' => 24000,
                'desc' => 'Matcha premium dengan susu hangat, manis seimbang.',
                'img' => 'images/coffee/matcha-latte.webp',
                'license' => 'CC0 1.0',
                'photographer' => 'Louie Sonugan (WordPress Photo Directory)',
                'source_url' => 'https://wordpress.org/photos/photo/24661c2123/',
                'attribution_required' => false,
            ],
            [
                'name' => 'Cokelat Panas',
                'price' => 20000,
                'desc' => 'Cokelat asli leleh, cocok untuk cuaca dingin.',
                'img' => 'images/coffee/cokelat-panas.webp',
                'license' => 'CC0 1.0',
                'photographer' => 'Tim Sullivan (StockSnap)',
                'source_url' => 'https://stocksnap.io/photo/hot-chocolate-NOXXUWUBGJ',
                'attribution_required' => false,
            ],
        ],
        'Camilan' => [
            [
                'name' => 'Pisang Goreng Keju',
                'price' => 18000,
                'desc' => 'Pisang kriuk dengan keju parut melimpah.',
                'img' => 'images/coffee/pisang-goreng.webp',
                'license' => 'CC0 1.0',
                'photographer' => 'AndriFB (Wikimedia Commons)',
                'source_url' => 'https://commons.wikimedia.org/wiki/File:Pisang_Goreng_Hangat.jpg',
                'attribution_required' => false,
            ],
            [
                'name' => 'Roti Bakar Cokelat',
                'price' => 22000,
                'desc' => 'Roti bakar isi cokelat dan keju, hangat dan mengenyangkan.',
                'img' => 'images/coffee/roti-bakar.webp',
                'license' => 'CC0 1.0',
                'photographer' => 'rawpixel',
                'source_url' => 'https://www.rawpixel.com/image/5902218/photo-image-public-domain-food-chocolate',
                'attribution_required' => false,
            ],
        ],
    ],

    // Foto hero asli (WebP + fallback JPG, kompres < 200KB) — lihat docs/credits-images.md
    'hero_image' => 'images/coffee/hero.webp',
    'hero_image_meta' => [
        'license' => 'CC0 1.0 (StockSnap License)',
        'photographer' => 'Afta Putta Gunawan (StockSnap)',
        'source_url' => 'https://stocksnap.io/photo/restaurant-bar-THXU08ODDE',
        'attribution_required' => false,
    ],

];
