<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="csrf-token" content="{{ csrf_token() }}">

    <title>@yield('title', 'Dashboard') — {{ config('coffee.brand.name') }} ERP</title>
    <meta name="theme-color" content="{{ config('coffee.brand.palette.primary') }}">

    <link rel="icon" href="{{ asset('images/coffee/favicon.svg') }}" type="image/svg+xml">
    <link rel="stylesheet" href="{{ asset('css/app.css') }}">
</head>
<body class="app-body">
<a class="skip-link" href="#konten">Lewati ke konten</a>

<header class="app-header">
    <div class="app-container nav-wrap">
        <a class="brand" href="{{ route('landing') }}" aria-label="{{ config('coffee.brand.name') }} — beranda">
            <span class="brand-badge">ERP</span>
            <span class="brand-name">{{ config('coffee.brand.name') }}</span>
        </a>

        <nav class="app-nav" aria-label="Navigasi utama">
            @auth
                <a href="{{ route('dashboard') }}">Dashboard</a>
                <span class="nav-user">
                    {{ auth()->user()->name }}
                    <span class="badge">{{ auth()->user()->role?->label() ?? '—' }}</span>
                </span>
                <form method="POST" action="{{ route('logout') }}">
                    @csrf
                    <button type="submit" class="btn btn-ghost">Keluar</button>
                </form>
            @else
                <a href="{{ route('login') }}">Masuk</a>
                <a href="{{ route('register') }}" class="btn btn-primary">Daftar</a>
            @endauth
        </nav>
    </div>
</header>

<main id="konten" class="app-container app-main">
    @if (session('success'))
        <div class="alert alert-success" role="status">{{ session('success') }}</div>
    @endif

    @yield('content')
</main>

<footer class="app-footer">
    <div class="app-container">
        <p>&copy; <span id="tahun"></span> {{ config('coffee.brand.name') }}. Hak cipta dilindungi.</p>
        <p class="muted">Sistem ERP internal — akses terbatas untuk pengguna terdaftar.</p>
    </div>
</footer>

@stack('scripts')
<script>
    document.getElementById('tahun').textContent = new Date().getFullYear();
</script>
</body>
</html>
