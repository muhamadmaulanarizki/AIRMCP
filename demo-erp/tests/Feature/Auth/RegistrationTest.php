<?php

namespace Tests\Feature\Auth;

use App\Enums\UserRole;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class RegistrationTest extends TestCase
{
    use RefreshDatabase;

    public function test_registration_screen_can_be_rendered(): void
    {
        $response = $this->get('/register');

        $response->assertStatus(200);
        $response->assertSee('Daftar Akun');
    }

    public function test_new_users_can_register_and_are_logged_in(): void
    {
        $response = $this->post('/register', [
            'name' => 'Siti Rahayu',
            'email' => 'siti@kopisenja.test',
            'password' => 'rahasia-123',
            'password_confirmation' => 'rahasia-123',
        ]);

        $user = User::query()->where('email', 'siti@kopisenja.test')->firstOrFail();

        $this->assertAuthenticatedAs($user);
        $response->assertRedirect(route('dashboard'));
    }

    public function test_registered_users_receive_minimum_privilege_role(): void
    {
        $this->post('/register', [
            'name' => 'Siti Rahayu',
            'email' => 'siti@kopisenja.test',
            'password' => 'rahasia-123',
            'password_confirmation' => 'rahasia-123',
        ]);

        $user = User::query()->where('email', 'siti@kopisenja.test')->firstOrFail();

        $this->assertSame(UserRole::ProcurementStaff, $user->role);
        $this->assertTrue($user->is_active);
    }

    public function test_duplicate_email_cannot_register(): void
    {
        User::factory()->create(['email' => 'siti@kopisenja.test']);

        $response = $this->post('/register', [
            'name' => 'Siti Rahayu',
            'email' => 'siti@kopisenja.test',
            'password' => 'rahasia-123',
            'password_confirmation' => 'rahasia-123',
        ]);

        $response->assertSessionHasErrors('email');
        $this->assertSame(1, User::query()->count());
    }

    public function test_password_confirmation_must_match(): void
    {
        $response = $this->post('/register', [
            'name' => 'Siti Rahayu',
            'email' => 'siti@kopisenja.test',
            'password' => 'rahasia-123',
            'password_confirmation' => 'berbeda',
        ]);

        $response->assertSessionHasErrors('password');
        $this->assertGuest();
        $this->assertSame(0, User::query()->count());
    }

    public function test_password_requires_at_least_eight_characters(): void
    {
        $response = $this->post('/register', [
            'name' => 'Siti Rahayu',
            'email' => 'siti@kopisenja.test',
            'password' => 'pendek',
            'password_confirmation' => 'pendek',
        ]);

        $response->assertSessionHasErrors('password');
        $this->assertGuest();
    }

    public function test_authenticated_user_is_redirected_away_from_login_page(): void
    {
        $user = User::factory()->create();

        $response = $this->actingAs($user)->get('/login');

        $response->assertRedirect(route('dashboard'));
    }
}
