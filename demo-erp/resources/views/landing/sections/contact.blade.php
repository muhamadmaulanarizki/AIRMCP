<section class="section section-alt" id="kontak" aria-labelledby="contact-title">
    <div class="container contact-grid">
        <div>
            <header class="section-head section-head-left">
                <p class="eyebrow">Kontak</p>
                <h2 id="contact-title">Punya Pertanyaan atau Pesanan?</h2>
            </header>
            <p class="section-sub">Kirim pesan lewat form, atau hubungi kami langsung:</p>
            <ul class="contact-info">
                <li><strong>Telepon:</strong> {{ $contact['phone'] }}</li>
                <li><strong>Email:</strong> <a href="mailto:{{ $contact['email'] }}">{{ $contact['email'] }}</a></li>
                <li><strong>Instagram:</strong> {{ $contact['instagram'] }}</li>
            </ul>
        </div>

        <form class="contact-form" id="contact-form" method="POST" action="{{ route('contact.store') }}" novalidate>
            @csrf
            <div class="form-field">
                <label for="name">Nama <span aria-hidden="true">*</span></label>
                <input type="text" id="name" name="name" maxlength="80" required
                       value="{{ old('name') }}" autocomplete="name">
                <p class="field-error" data-error-for="name" role="alert"></p>
            </div>

            <div class="form-field">
                <label for="email">Email <span aria-hidden="true">*</span></label>
                <input type="email" id="email" name="email" maxlength="100" required
                       value="{{ old('email') }}" autocomplete="email">
                <p class="field-error" data-error-for="email" role="alert"></p>
            </div>

            <div class="form-field">
                <label for="phone">No. HP (opsional)</label>
                <input type="tel" id="phone" name="phone" maxlength="20"
                       value="{{ old('phone') }}" autocomplete="tel">
                <p class="field-error" data-error-for="phone" role="alert"></p>
            </div>

            <div class="form-field">
                <label for="message">Pesan <span aria-hidden="true">*</span></label>
                <textarea id="message" name="message" rows="5" maxlength="1000" required>{{ old('message') }}</textarea>
                <p class="field-error" data-error-for="message" role="alert"></p>
            </div>

            <button class="btn btn-primary btn-block" type="submit">Kirim Pesan</button>
            <p class="form-status" id="form-status" role="status" aria-live="polite"></p>
        </form>
    </div>
</section>

@push('scripts')
<script>
    @if (session('success'))
        document.addEventListener('DOMContentLoaded', function () {
            var status = document.getElementById('form-status');
            if (status) { status.textContent = @json(session('success')); status.classList.add('is-success'); }
        });
    @endif
</script>
@endpush
