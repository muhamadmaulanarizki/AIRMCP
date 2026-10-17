<?php

namespace App\Http\Controllers\Auth;

use App\Http\Controllers\Controller;
use App\Http\Requests\Auth\RegisterRequest;
use App\Models\User;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Support\Facades\Auth;

class RegisteredUserController extends Controller
{
    /**
     * Tampilkan form registrasi (GET /register).
     */
    public function create()
    {
        return view('auth.register');
    }

    /**
     * Proses registrasi self-service (POST /register).
     *
     * Hak akses mengikuti default kolom `role` / `is_active` pada migration
     * (privilege minimum, D-4) sehingga keputusan PO soal registrasi ketat
     * cukup diubah di migration/seeder tanpa menyentuh controller ini.
     */
    public function store(RegisterRequest $request): JsonResponse|RedirectResponse
    {
        $data = $request->validated();
        unset($data['password_confirmation']);

        $user = User::create($data);

        // Kolom default (role, is_active) tidak ikut terisi saat insert;
        // refresh agar objek in-memory konsisten dengan nilai di database.
        $user->refresh();

        Auth::login($user);

        $request->session()->regenerate();

        if ($request->expectsJson()) {
            return response()->json([
                'message' => __('auth.registered'),
                'user' => $user,
            ], 201);
        }

        return redirect()->route('dashboard')
            ->with('success', __('auth.registered'));
    }
}
