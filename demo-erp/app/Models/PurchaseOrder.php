<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class PurchaseOrder extends Model
{
    protected $fillable = ['kode', 'vendor', 'total', 'status', 'order_date'];

    protected $casts = ['total' => 'decimal:2', 'order_date' => 'date'];

    public function scopeApprovedTotalByVendor($query)
    {
        return $query->where('status', 'approved')
            ->selectRaw('vendor, SUM(total) as total_approved')
            ->groupBy('vendor')
            ->orderByDesc('total_approved')
            ->get();
    }
}
