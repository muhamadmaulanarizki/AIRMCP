<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Vendor extends Model
{
    protected $fillable = ['nama', 'alamat', 'kontak', 'aktif'];

    protected $casts = ['aktif' => 'boolean'];
}
