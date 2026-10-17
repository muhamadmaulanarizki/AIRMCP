@extends('layouts.app')

@section('title', 'Masuk')

@section('content')
<div class="auth-wrap">
    <div class="card auth-card">
        <h1 class="auth-title">Masuk</h1>
        <p class="muted">Gunakan akun Anda untuk mengakses sistem {{ config('coffee.brand.name') }} ERP.</p>

        <form method="POST" action="{{ route('login') }}" novalidate>
            @csrf

            <div class="field">
                <label for="email">Email</label>
                <input id="email" type="email" name="email" value="{{ old('email') }}"
                       autocomplete="username" autofocus required
                       placeholder="nama@perusahaan.com"
                       aria-describedby="email-hint"
                       class="@error('email') is-invalid @enderror">
                <p id="email-hint" class="hint">Gunakan email terdaftar. Percobaan dibatasi 5 kali per menit.</p>
                @error('email')
                    <p class="error" role="alert">{{ $message }}</p>
                @enderror
            </div>

            <div class="field">
                <label for="password">Kata Sandi</label>
                <input id="password" type="password" name="password"
                       autocomplete="current-password" required
                       class="@error('password') is-invalid @enderror">
                @error('password')
                    <p class="error" role="alert">{{ $message }}</p>
                @enderror
            </div>

            <button type="submit" class="btn btn-primary btn-block">Masuk</button>
        </form>

        <p class="auth-alt">Belum punya akun? <a href="{{ route('register') }}">Daftar di sini</a></p>
        <p class="auth-alt"><a href="{{ route('landing') }}">← Kembali ke beranda</a></p>
    </div>
</div>
@endsection
