<?php

namespace App\Http\Requests\Auth;

use Illuminate\Auth\Events\Lockout;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\RateLimiter;
use Illuminate\Support\Str;
use Illuminate\Validation\ValidationException;

class LoginRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    /**
     * Aturan validasi selaras dengan gaya ContactController (array of rules).
     */
    public function rules(): array
    {
        return [
            'email' => ['required', 'string', 'email', 'max:150'],
            'password' => ['required', 'string'],
            'remember' => ['nullable', 'boolean'],
        ];
    }

    /**
     * Autentikasi kredensial + gate akun nonaktif + reset rate limiter saat
     * berhasil (NFR-6).
     */
    public function authenticate(): void
    {
        $this->ensureIsNotRateLimited();

        // is_active = true ikut jadi syarat: pengguna nonaktif ditolak dengan
        // pesan yang sama sehingga status akun tidak dibocorkan.
        $credentials = $this->only('email', 'password') + ['is_active' => true];

        if (! Auth::attempt($credentials, $this->boolean('remember'))) {
            event(new Lockout($this));

            throw ValidationException::withMessages([
                'email' => __('auth.failed'),
            ]);
        }

        RateLimiter::clear($this->throttleKey());
    }

    /**
     * Kunci rate limit: per kombinasi email + IP, agar brute force per-akun
     * tertahan tanpa melumpuhkan seluruh kantor yang ber-IP sama.
     * HARUS identik dengan limiter 'login' di AppServiceProvider.
     */
    public function throttleKey(): string
    {
        return Str::lower((string) $this->input('email')) . '|' . $this->ip();
    }

    protected function ensureIsNotRateLimited(): void
    {
        if (! RateLimiter::tooManyAttempts($this->throttleKey(), 5)) {
            return;
        }

        event(new Lockout($this));

        $seconds = RateLimiter::availableIn($this->throttleKey());

        throw ValidationException::withMessages([
            'email' => __('auth.throttle', [
                'seconds' => $seconds,
                'minutes' => ceil($seconds / 60),
            ]),
        ]);
    }
}
