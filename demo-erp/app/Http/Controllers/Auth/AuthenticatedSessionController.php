<?php

namespace App\Http\Controllers\Auth;

use App\Http\Controllers\Controller;
use App\Http\Requests\Auth\LoginRequest;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\View\View;

class AuthenticatedSessionController extends Controller
{
    /**
     * Tampilkan form login (GET /login).
     */
    public function create(): View
    {
        return view('auth.login');
    }

    /**
     * Proses login (POST /login) - session + CSRF (D-1).
     */
    public function store(LoginRequest $request): JsonResponse|RedirectResponse
    {
        $request->authenticate();

        // Cegah session fixation (NFR-6).
        $request->session()->regenerate();

        $user = Auth::user();

        if ($request->expectsJson()) {
            return response()->json([
                'message' => __('auth.welcome', ['name' => $user->name]),
                'user' => $user,
            ]);
        }

        return redirect()->intended(route('dashboard', absolute: false))
            ->with('success', __('auth.welcome', ['name' => $user->name]));
    }

    /**
     * Proses logout (POST /logout).
     */
    public function destroy(Request $request): JsonResponse|RedirectResponse
    {
        Auth::guard('web')->logout();

        // Buang seluruh data sesi dan CSRF token lama (NFR-6).
        $request->session()->invalidate();
        $request->session()->regenerateToken();

        if ($request->expectsJson()) {
            return response()->json(['message' => __('auth.logged_out')]);
        }

        return redirect()->route('login')->with('success', __('auth.logged_out'));
    }
}
