<?php

namespace App\Http\Controllers;

use Illuminate\View\View;

class LandingController extends Controller
{
    public function index(): View
    {
        return view('landing.index', [
            'brand' => config('coffee.brand'),
            'contact' => config('coffee.contact'),
            'hours' => config('coffee.hours'),
            'socials' => config('coffee.socials'),
            'menu' => config('coffee.menu'),
            'heroImage' => config('coffee.hero_image'),
        ]);
    }

    public function menuJson()
    {
        return response()->json(config('coffee.menu'));
    }
}
