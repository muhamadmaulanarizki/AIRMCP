<?php

namespace App\Http\Controllers;

use App\Models\PurchaseOrder;
use Illuminate\Http\Request;

class PurchaseOrderController extends Controller
{
    public function index()
    {
        return response()->json(PurchaseOrder::latest()->paginate(25));
    }

    public function store(Request $request)
    {
        $data = $request->validate([ /* rules untuk: 'kode', 'vendor', 'total', 'status', 'order_date' */ ]);
        return response()->json(PurchaseOrder::create($data), 201);
    }

    public function show(PurchaseOrder $po)
    {
        return response()->json($po);
    }

    public function update(Request $request, PurchaseOrder $po)
    {
        $data = $request->validate([ /* rules untuk: 'kode', 'vendor', 'total', 'status', 'order_date' */ ]);
        $po->update($data);
        return response()->json($po);
    }

    public function destroy(PurchaseOrder $po)
    {
        $po->delete();
        return response()->noContent();
    }

    public function approvedTotalByVendor()
    {
        return response()->json(PurchaseOrder::approvedTotalByVendor());
    }
}
