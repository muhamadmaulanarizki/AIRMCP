<?php

namespace Tests\Feature\Auth;

use App\Enums\UserRole;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Hash;
use Tests\TestCase;

class AuthenticationTest extends TestCase
{
    use RefreshDatabase;

    public function test_login_screen_can_be_rendered(): void
    {
        $response = $this->get('/login');

        $response->assertStatus(200);
        $response->assertSee('Masuk');
        $response->assertSee('Email');
    }

    public function test_users_can_authenticate_with_valid_credentials(): void
    {
        $user = User::factory()->create([
            'email' => 'staf@kopisenja.test',
            'password' => 'rahasia-123',
        ]);

        $response = $this->post('/login', [
            'email' => 'staf@kopisenja.test',
            'password' => 'rahasia-123',
        ]);

        $this->assertAuthenticatedAs($user);
        $response->assertRedirect(route('dashboard'));
    }

    public function test_users_cannot_authenticate_with_invalid_password(): void
    {
        User::factory()->create([
            'email' => 'staf@kopisenja.test',
            'password' => 'rahasia-123',
        ]);

        $response = $this->from('/login')->post('/login', [
            'email' => 'staf@kopisenja.test',
            'password' => 'salah',
        ]);

        $this->assertGuest();
        $response->assertRedirect('/login');
        $response->assertSessionHasErrors('email');
    }

    public function test_inactive_users_cannot_authenticate(): void
    {
        User::factory()->create([
            'email' => 'nonaktif@kopisenja.test',
            'password' => 'rahasia-123',
            'is_active' => false,
        ]);

        $response = $this->post('/login', [
            'email' => 'nonaktif@kopisenja.test',
            'password' => 'rahasia-123',
        ]);

        $this->assertGuest();
        $response->assertSessionHasErrors('email');
    }

    public function test_login_failure_message_is_in_indonesian(): void
    {
        $response = $this->post('/login', [
            'email' => 'tidak-ada@kopisenja.test',
            'password' => 'salah-saja',
        ]);

        $this->assertGuest();
        $response->assertSessionHasErrors('email');
        $response->assertSee('Email atau kata sandi yang Anda masukkan tidak sesuai.');
    }

    public function test_passwords_are_hashed_in_database(): void
    {
        $user = User::factory()->create([
            'email' => 'staf@kopisenja.test',
            'password' => 'rahasia-123',
        ]);

        $stored = User::query()->findOrFail($user->id)->password;

        $this->assertNotSame('rahasia-123', $stored);
        $this->assertTrue(Hash::check('rahasia-123', $stored));
    }

    public function test_users_can_logout(): void
    {
        $user = User::factory()->create();

        $response = $this->actingAs($user)->post('/logout');

        $this->assertGuest();
        $response->assertRedirect(route('login'));
    }

    public function test_guest_is_redirected_to_login_from_protected_routes(): void
    {
        $this->get('/dashboard')->assertRedirect(route('login'));
        $this->post('/logout')->assertRedirect(route('login'));
    }

    public function test_authenticated_user_can_view_dashboard(): void
    {
        $user = User::factory()->create(['name' => 'Siti Rahayu']);

        $response = $this->actingAs($user)->get('/dashboard');

        $response->assertStatus(200);
        $response->assertSee('Siti Rahayu');
    }

    public function test_guest_cannot_access_purchase_order_and_vendor_endpoints(): void
    {
        $this->getJson('/purchase_orders')->assertStatus(401);
        $this->getJson('/vendors')->assertStatus(401);
    }

    public function test_authenticated_user_can_access_purchase_order_and_vendor_endpoints(): void
    {
        $this->actingAs(User::factory()->create())
            ->getJson('/purchase_orders')
            ->assertStatus(200);
    }

    public function test_authenticated_user_is_logged_out_when_account_is_deactivated(): void
    {
        $user = User::factory()->create(['is_active' => false]);

        $response = $this->actingAs($user)->get('/dashboard');

        $this->assertGuest();
        $response->assertRedirect(route('login'));
    }
}
