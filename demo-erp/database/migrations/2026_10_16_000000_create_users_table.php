<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Tabel pengguna (FR-1). Timestamp sengaja lebih besar dari semua
     * migration existing (lihat docs/ARCH-LOGIN.md T-4/R-11) agar urutan batch
     * deterministik.
     */
    public function up(): void
    {
        Schema::create('users', function (Blueprint $table) {
            $table->id();
            $table->string('name', 100);
            $table->string('email', 150)->unique();
            $table->string('password');
            // Bukan DB enum: daftar peran bisa berubah (PRD Q-2) - lihat D-3.
            $table->string('role', 30)->default('procurement_staff')->index();
            // Gate login pengguna nonaktif (FR-13) - lihat D-4.
            $table->boolean('is_active')->default(true);
            $table->timestamp('email_verified_at')->nullable();
            $table->rememberToken();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('users');
    }
};
