@extends('layouts.app')

@section('title', 'Daftar')

@section('content')
<div class="auth-wrap">
    <div class="card auth-card">
        <h1 class="auth-title">Daftar Akun</h1>
        <p class="muted">Akun baru otomatis memperoleh peran <strong>Staf Procurement</strong> (hak paling rendah).</p>

        <form method="POST" action="{{ route('register') }}" novalidate>
            @csrf

            <div class="field">
                <label for="name">Nama Lengkap</label>
                <input id="name" type="text" name="name" value="{{ old('name') }}"
                       autocomplete="name" autofocus required maxlength="100"
                       placeholder="Contoh: Siti Rahayu"
                       class="@error('name') is-invalid @enderror">
                @error('name')
                    <p class="error" role="alert">{{ $message }}</p>
                @enderror
            </div>

            <div class="field">
                <label for="email">Email</label>
                <input id="email" type="email" name="email" value="{{ old('email') }}"
                       autocomplete="username" required maxlength="150"
                       placeholder="nama@perusahaan.com"
                       class="@error('email') is-invalid @enderror">
                @error('email')
                    <p class="error" role="alert">{{ $message }}</p>
                @enderror
            </div>

            <div class="field">
                <label for="password">Kata Sandi</label>
                <input id="password" type="password" name="password"
                       autocomplete="new-password" required
                       aria-describedby="password-hint"
                       class="@error('password') is-invalid @enderror">
                <p id="password-hint" class="hint">Minimal 8 karakter.</p>
                @error('password')
                    <p class="error" role="alert">{{ $message }}</p>
                @enderror
            </div>

            <div class="field">
                <label for="password_confirmation">Ulangi Kata Sandi</label>
                <input id="password_confirmation" type="password" name="password_confirmation"
                       autocomplete="new-password" required>
            </div>

            <button type="submit" class="btn btn-primary btn-block">Buat Akun</button>
        </form>

        <p class="auth-alt">Sudah punya akun? <a href="{{ route('login') }}">Masuk di sini</a></p>
    </div>
</div>
@endsection
