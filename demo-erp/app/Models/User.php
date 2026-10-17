<?php

namespace App\Models;

use App\Enums\UserRole;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Foundation\Auth\User as Authenticatable;
use Illuminate\Notifications\Notifiable;

/**
 * Model pengguna (FR-1).
 *
 * Wajib extends Authenticatable - bukan Model - agar terhubung ke guard `web`
 * (Auth::attempt, session, hashing). Lihat docs/ARCH-LOGIN.md §5.
 */
class User extends Authenticatable
{
    use HasFactory, Notifiable;

    /** @var list<string> */
    protected $fillable = ['name', 'email', 'password', 'role', 'is_active'];

    /** @var list<string> */
    protected $hidden = ['password', 'remember_token'];

    /** @var array<string, string> */
    protected $casts = [
        'password' => 'hashed',
        'role' => UserRole::class,
        'is_active' => 'boolean',
        'email_verified_at' => 'datetime',
    ];

    /**
     * Akun masih dapat dipakai masuk (gate FR-13).
     */
    public function isActive(): bool
    {
        return (bool) $this->is_active;
    }
}
