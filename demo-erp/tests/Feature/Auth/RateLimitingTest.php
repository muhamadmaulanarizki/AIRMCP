<?php

namespace Tests\Feature\Auth;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\RateLimiter;
use Tests\TestCase;

class RateLimitingTest extends TestCase
{
    use RefreshDatabase;

    public function test_login_attempts_are_limited_to_five_per_minute(): void
    {
        User::factory()->create([
            'email' => 'target@kopisenja.test',
            'password' => 'rahasia-123',
        ]);

        $payload = [
            'email' => 'target@kopisenja.test',
            'password' => 'salah',
        ];

        // 5 percobaan pertama: ditolak sebagai gagal login biasa (422/redirect).
        foreach (range(1, 5) as $attempt) {
            $this->postJson('/login', $payload)->assertStatus(422);
        }

        // Percobaan ke-6: kena rate limit (429).
        $this->postJson('/login', $payload)->assertStatus(429);
    }

    public function test_rate_limit_is_scoped_per_email_not_per_ip(): void
    {
        RateLimiter::clear('lain@kopisenja.test|127.0.0.1');

        // Akun lain pada IP yang sama tetap bisa mencoba (tidak ikut terkunci).
        foreach (range(1, 5) as $attempt) {
            $this->postJson('/login', [
                'email' => 'lain@kopisenja.test',
                'password' => 'salah',
            ])->assertStatus(422);
        }
    }

    public function test_successful_login_resets_the_counter(): void
    {
        User::factory()->create([
            'email' => 'target@kopisenja.test',
            'password' => 'rahasia-123',
        ]);

        $wrong = ['email' => 'target@kopisenja.test', 'password' => 'salah'];

        foreach (range(1, 3) as $attempt) {
            $this->postJson('/login', $wrong)->assertStatus(422);
        }

        $this->postJson('/login', [
            'email' => 'target@kopisenja.test',
            'password' => 'rahasia-123',
        ])->assertStatus(200);

        $this->assertSame(
            0,
            RateLimiter::attempts('target@kopisenja.test|127.0.0.1')
        );
    }

    public function test_contact_form_keeps_its_own_throttle(): void
    {
        $payload = [
            'name' => 'Uji',
            'email' => 'uji@kopisenja.test',
            'message' => 'Halo, ini pesan uji.',
        ];

        foreach (range(1, 5) as $attempt) {
            $this->postJson('/contact', $payload)->assertStatus(201);
        }

        $this->postJson('/contact', $payload)->assertStatus(429);
    }
}
