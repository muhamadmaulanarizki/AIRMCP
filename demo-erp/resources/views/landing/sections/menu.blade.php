<section class="section" id="menu" aria-labelledby="menu-title">
    <div class="container">
        <header class="section-head">
            <p class="eyebrow">Menu Favorit</p>
            <h2 id="menu-title">Disajikan Segar Setiap Hari</h2>
            <p class="section-sub">Semua foto diambil langsung dari sajian asli kedai kami.</p>
        </header>

        @foreach ($menu as $category => $items)
            <div class="menu-group">
                <h3 class="menu-category">{{ $category }}</h3>
                <div class="menu-grid">
                    @foreach ($items as $item)
                        <article class="menu-card">
                            {{-- Foto asli WebP (CC0) — alt deskriptif + fallback JPG bila WebP tak didukung --}}
                            <img class="menu-card-img"
                                 src="{{ asset($item['img']) }}"
                                 alt="Foto {{ $item['name'] }} — {{ $item['desc'] }}"
                                 width="320"
                                 height="200"
                                 loading="lazy"
                                 decoding="async"
                                 onerror="this.onerror=null;this.src='{{ asset(preg_replace('/\.webp$/', '.jpg', $item['img'])) }}'">
                            <div class="menu-card-body">
                                <div class="menu-card-head">
                                    <h4>{{ $item['name'] }}</h4>
                                    <span class="menu-price">Rp{{ number_format($item['price'], 0, ',', '.') }}</span>
                                </div>
                                <p>{{ $item['desc'] }}</p>
                            </div>
                        </article>
                    @endforeach
                </div>
            </div>
        @endforeach
    </div>
</section>
