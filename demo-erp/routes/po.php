<?php

use App\Http\Controllers\PurchaseOrderController;
use Illuminate\Support\Facades\Route;

Route::get('purchase_orders/approved-total-by-vendor',
    [PurchaseOrderController::class, 'approvedTotalByVendor']);

Route::apiResource('purchase_orders', PurchaseOrderController::class);
