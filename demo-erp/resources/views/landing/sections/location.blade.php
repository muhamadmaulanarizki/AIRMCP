<section class="section" id="lokasi" aria-labelledby="location-title">
    <div class="container location-grid">
        <div>
            <header class="section-head section-head-left">
                <p class="eyebrow">Lokasi &amp; Jam Buka</p>
                <h2 id="location-title">Mampir ke Kami</h2>
            </header>
            <p class="location-address">{{ $contact['address'] }}</p>
            <dl class="hours-list">
                @foreach ($hours as $row)
                    <div>
                        <dt>{{ $row['day'] }}</dt>
                        <dd>{{ $row['time'] }}</dd>
                    </div>
                @endforeach
            </dl>
            <a class="btn btn-primary" href="{{ $contact['maps_url'] }}" target="_blank" rel="noopener">Buka di Google Maps</a>
        </div>
        <div class="location-map" role="img" aria-label="Peta lokasi {{ $brand['name'] }}">
            <iframe
                src="{{ $contact['maps_url'] }}"
                title="Peta lokasi {{ $brand['name'] }}"
                loading="lazy"
                referrerpolicy="no-referrer-when-downgrade"
                allowfullscreen></iframe>
        </div>
    </div>
</section>
