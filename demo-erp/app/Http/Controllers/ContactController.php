<?php

namespace App\Http\Controllers;

use App\Models\ContactMessage;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Schema;

class ContactController extends Controller
{
    public function store(Request $request): JsonResponse|RedirectResponse
    {
        $data = $request->validate([
            'name' => ['required', 'string', 'max:80'],
            'email' => ['required', 'email', 'max:100'],
            'phone' => ['nullable', 'string', 'max:20'],
            'message' => ['required', 'string', 'max:1000'],
        ]);

        if (Schema::hasTable('contact_messages')) {
            ContactMessage::create($data);
        } else {
            // Fallback bila migration belum dijalankan
            Log::info('[contact_message] ' . json_encode($data, JSON_UNESCAPED_UNICODE));
        }

        if ($request->expectsJson()) {
            return response()->json([
                'message' => 'Terima kasih! Pesan Anda sudah kami terima.',
            ], 201);
        }

        return redirect()->route('landing')->with('success', 'Terima kasih! Pesan Anda sudah kami terima.');
    }
}
