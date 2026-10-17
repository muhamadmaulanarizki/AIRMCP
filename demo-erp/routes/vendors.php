<?php

use App\Http\Controllers\VendorController;
use Illuminate\Support\Facades\Route;

Route::apiResource('vendors', VendorController::class);
