<?php

namespace App\Http\Controllers;

use App\Models\Vendor;
use Illuminate\Http\Request;

class VendorController extends Controller
{
    public function index()
    {
        return response()->json(Vendor::latest()->paginate(25));
    }

    public function store(Request $request)
    {
        $data = $request->validate([ /* rules untuk: 'nama', 'alamat', 'kontak', 'aktif' */ ]);
        return response()->json(Vendor::create($data), 201);
    }

    public function show(Vendor $po)
    {
        return response()->json($po);
    }

    public function update(Request $request, Vendor $po)
    {
        $data = $request->validate([ /* rules untuk: 'nama', 'alamat', 'kontak', 'aktif' */ ]);
        $po->update($data);
        return response()->json($po);
    }

    public function destroy(Vendor $po)
    {
        $po->delete();
        return response()->noContent();
    }
}
