@extends('layouts.app')

@section('title', 'Dashboard')

@section('content')
<div class="page-head">
    <h1>Dashboard</h1>
    <p class="muted">Ringkasan akun dan modul yang tersedia.</p>
</div>

<div class="grid">
    <section class="card" aria-labelledby="profil-title">
        <h2 id="profil-title">Profil Akun</h2>
        <dl class="dl">
            <dt>Nama</dt>
            <dd>{{ auth()->user()->name }}</dd>

            <dt>Email</dt>
            <dd>{{ auth()->user()->email }}</dd>

            <dt>Peran</dt>
            <dd>
                <span class="badge badge-lg">
                    {{ auth()->user()->role?->label() ?? '—' }}
                </span>
            </dd>

            <dt>Status</dt>
            <dd>
                @if (auth()->user()->is_active)
                    <span class="badge badge-ok">Aktif</span>
                @else
                    <span class="badge badge-warn">Nonaktif</span>
                @endif
            </dd>

            <dt>Terdaftar</dt>
            <dd>{{ auth()->user()->created_at?->translatedFormat('d F Y H:i') ?? '—' }}</dd>
        </dl>
    </section>

    <section class="card" aria-labelledby="modul-title">
        <h2 id="modul-title">Modul</h2>
        <p class="muted">Modul berikut dilindungi sesi login (kelompok route <code>auth</code>).</p>
        <ul class="module-list">
            <li>
                <a href="{{ url('/purchase_orders') }}">Purchase Order</a>
                <span class="muted">Daftar PO dalam format JSON.</span>
            </li>
            <li>
                <a href="{{ url('/vendors') }}">Vendor</a>
                <span class="muted">Daftar vendor dalam format JSON.</span>
            </li>
        </ul>
        <p class="hint">
            Antarmuka halaman PO/Vendor (Blade) dijadwalkan pada tahap M3 berikutnya;
            saat ini endpoint datanya sudah dapat diakses setelah masuk.
        </p>
    </section>
</div>
@endsection
