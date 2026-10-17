<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Symfony\Component\HttpFoundation\Response;

/**
 * Menolak pengguna yang dinonaktifkan (is_active = false) di tengah sesi.
 * Pelengkap gate `Auth::attempt(..., 'is_active' => true)` saat login.
 *
 * Tidak dipasang pada route /logout agar pengguna nonaktif tetap bisa keluar.
 */
class EnsureUserIsActive
{
    public function handle(Request $request, Closure $next): Response
    {
        if (! Auth::check()) {
            return redirect()->route('login');
        }

        if (! Auth::user()->is_active) {
            Auth::guard('web')->logout();

            $request->session()->invalidate();
            $request->session()->regenerateToken();

            return redirect()->route('login')->withErrors([
                'email' => __('auth.inactive'),
            ]);
        }

        return $next($request);
    }
}
