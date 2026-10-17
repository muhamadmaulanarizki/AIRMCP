<?php

namespace Database\Seeders;

use App\Enums\UserRole;
use App\Models\User;
use Illuminate\Database\Seeder;

/**
 * Seeder akun administrator (F1).
 *
 * Kredensial diambil dari konfigurasi yang bersumber dari .env
 * (ADMIN_EMAIL / ADMIN_PASSWORD / ADMIN_NAME) - tidak pernah di-hardcode di
 * repo (NFR-10, R-5). Jika tidak di-set, seeder melewati pembuatan admin
 * dengan peringatan, bukan gagal.
 */
class AdminUserSeeder extends Seeder
{
    public function run(): void
    {
        $email = (string) config('auth.admin.email');
        $password = (string) config('auth.admin.password');

        if ($email === '' || $password === '') {
            $this->command?->warn(
                'ADMIN_EMAIL / ADMIN_PASSWORD belum di-set di .env - akun admin dilewati.'
            );

            return;
        }

        User::updateOrCreate(
            ['email' => $email],
            [
                'name' => config('auth.admin.name') ?: 'Administrator',
                'password' => $password,
                'role' => UserRole::Admin,
                'is_active' => true,
            ],
        );

        $this->command?->info("Akun admin siap: {$email}");
    }
}
