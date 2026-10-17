<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <title>@yield('title', $brand['name'] . ' — ' . $brand['tagline'])</title>
    <meta name="description" content="@yield('description', $brand['description'])">
    <meta name="theme-color" content="{{ $brand['palette']['primary'] }}">

    <meta property="og:type" content="website">
    <meta property="og:title" content="@yield('title', $brand['name'] . ' — ' . $brand['tagline'])">
    <meta property="og:description" content="@yield('description', $brand['description'])">
    <meta property="og:site_name" content="{{ $brand['name'] }}">
    <meta name="twitter:card" content="summary_large_image">

    <link rel="icon" href="{{ asset('images/coffee/favicon.svg') }}" type="image/svg+xml">
    <link rel="stylesheet" href="{{ asset('css/landing.css') }}">
</head>
<body>
<a class="skip-link" href="#konten">Lewati ke konten</a>

<header class="site-header" id="top">
    <div class="container nav-wrap">
        <a class="brand" href="{{ route('landing') }}" aria-label="{{ $brand['name'] }} — beranda">
            <span class="brand-badge">{{ $brand['logo_text'] }}</span>
            <span class="brand-name">{{ $brand['name'] }}</span>
        </a>

        <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav" aria-label="Buka menu navigasi">
            <span></span><span></span><span></span>
        </button>

        <nav class="site-nav" id="site-nav" aria-label="Navigasi utama">
            <a href="#menu">Menu</a>
            <a href="#tentang">Tentang</a>
            <a href="#lokasi">Lokasi</a>
            <a href="#kontak" class="nav-cta">Kontak</a>
        </nav>
    </div>
</header>

<main id="konten">
    @yield('content')
</main>

<footer class="site-footer">
    <div class="container footer-grid">
        <div>
            <p class="footer-brand">{{ $brand['name'] }}</p>
            <p class="footer-tagline">{{ $brand['tagline'] }}</p>
        </div>
        <div>
            <p class="footer-title">Kontak</p>
            <p>{{ $contact['address'] }}</p>
            <p>{{ $contact['phone'] }}</p>
            <p><a href="mailto:{{ $contact['email'] }}">{{ $contact['email'] }}</a></p>
        </div>
        <div>
            <p class="footer-title">Ikuti Kami</p>
            @foreach ($socials as $social)
                <p><a href="{{ $social['url'] }}" rel="noopener" target="_blank">{{ $social['label'] }}</a></p>
            @endforeach
        </div>
    </div>
    <div class="container footer-bottom">
        <p>&copy; <span id="tahun"></span> {{ $brand['name'] }}. Seluruh hak cipta dilindungi.</p>
    </div>
</footer>

<script src="{{ asset('js/landing.js') }}" defer></script>
@stack('scripts')
</body>
</html>
