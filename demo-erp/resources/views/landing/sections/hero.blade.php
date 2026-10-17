<section class="hero" aria-labelledby="hero-title">
    <div class="container hero-grid">
        <div class="hero-copy">
            <p class="eyebrow">Selamat datang di</p>
            <h1 id="hero-title">{{ $brand['name'] }}</h1>
            <p class="hero-tagline">{{ $brand['tagline'] }}</p>
            <p class="hero-desc">{{ $brand['description'] }}</p>
            <div class="hero-actions">
                <a class="btn btn-primary" href="#menu">Lihat Menu</a>
                <a class="btn btn-ghost" href="#lokasi">Kunjungi Kami</a>
            </div>
        </div>
        <div class="hero-media">
            {{-- Foto asli WebP (CC0) — fallback JPG otomatis bila WebP tak didukung --}}
            <img src="{{ asset($heroImage) }}"
                 alt="Suasana interior {{ $brand['name'] }}: dinding bata hangat, lampu gantung kuning, dan bar espresso kayu"
                 width="640"
                 height="480"
                 loading="eager"
                 decoding="async"
                 onerror="this.onerror=null;this.src='{{ asset(preg_replace('/\.webp$/', '.jpg', $heroImage)) }}'">
        </div>
    </div>
</section>
