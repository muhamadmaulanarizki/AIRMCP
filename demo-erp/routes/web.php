<?php

use App\Http\Controllers\ContactController;
use App\Http\Controllers\LandingController;
use Illuminate\Support\Facades\Route;

Route::get('/', [LandingController::class, 'index'])->name('landing');

Route::get('/api/menu', [LandingController::class, 'menuJson'])->name('landing.menu.json');

Route::post('/contact', [ContactController::class, 'store'])
    ->middleware('throttle:5,1')
    ->name('contact.store');

require __DIR__ . '/auth.php';

/*
|--------------------------------------------------------------------------
| Grup terautentikasi (F4 - docs/ARCH-LOGIN.md §7 Opsi A)
|--------------------------------------------------------------------------
| Route PO & Vendor dahulu berupa snippet yang tidak pernah terdaftar dan
| memakai apiResource stateless (tanpa CSRF). Kini di-wire di dalam grup
| 'auth' sehingga tamu diarahkan ke /login (MS-2 tertutup sebagian).
*/
Route::middleware(['auth', 'active'])->group(function () {
    require __DIR__ . '/po.php';
    require __DIR__ . '/vendors.php';
});
