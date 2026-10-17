<?php

namespace App\Providers;

use Illuminate\Cache\RateLimiting\Limit;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\RateLimiter;
use Illuminate\Support\Str;
use Illuminate\Support\ServiceProvider;
use Illuminate\Validation\Rules\Password;

class AppServiceProvider extends ServiceProvider
{
    /**
     * Registrasi layanan aplikasi.
     */
    public function register(): void
    {
        //
    }

    /**
     * Bootstrap layanan aplikasi.
     */
    public function boot(): void
    {
        $this->configureRateLimiting();

        $this->configurePasswordDefaults();
    }

    /**
     * Limiter bernama 'login' (NFR-6, R-4).
     *
     * 5 percobaan per menit per kombinasi email + IP - bukan per-IP murni -
     * agar brute force per-akun tertahan tanpa melumpuhkan seluruh kantor
     * yang ber-IP sama (NFR-4: s.d. 50 pengguna aktif).
     *
     * Kunci ini HARUS identik dengan LoginRequest::throttleKey().
     */
    protected function configureRateLimiting(): void
    {
        RateLimiter::for('login', function (Request $request) {
            return Limit::perMinute(5)->by(
                Str::lower((string) $request->input('email')) . '|' . $request->ip()
            );
        });
    }

    /**
     * Aturan bawaan kata sandi - minimal 8 karakter (dokumen di
     * RegisterRequest lewat Password::defaults()).
     */
    protected function configurePasswordDefaults(): void
    {
        Password::defaults(fn () => Password::min(8));
    }
}
