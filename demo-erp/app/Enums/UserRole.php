<?php

namespace App\Enums;

/**
 * Peran pengguna. Dipakai sebagai cast pada User::$role (D-3).
 * Nilai string disimpan di kolom `role` (bukan DB enum) agar daftar peran
 * bisa bertambah tanpa ALTER TABLE.
 */
enum UserRole: string
{
    case Admin = 'admin';
    case ProcurementStaff = 'procurement_staff';
    case Manager = 'manager';

    /**
     * Label Bahasa Indonesia untuk ditampilkan di UI (US-13).
     */
    public function label(): string
    {
        return match ($this) {
            self::Admin => 'Administrator',
            self::ProcurementStaff => 'Staf Procurement',
            self::Manager => 'Manajer',
        };
    }

    /**
     * Peran dengan hak paling rendah - dipakai sebagai hak default registrasi
     * self-service (D-4, privilege minimum).
     */
    public static function default(): self
    {
        return self::ProcurementStaff;
    }
}
