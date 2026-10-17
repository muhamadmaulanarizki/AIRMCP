(function () {
    'use strict';

    var toggle = document.querySelector('.nav-toggle');
    var nav = document.getElementById('site-nav');

    if (toggle && nav) {
        toggle.addEventListener('click', function () {
            var open = nav.classList.toggle('is-open');
            toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        });

        nav.addEventListener('click', function (e) {
            if (e.target.tagName === 'A') {
                nav.classList.remove('is-open');
                toggle.setAttribute('aria-expanded', 'false');
            }
        });
    }

    var tahun = document.getElementById('tahun');
    if (tahun) {
        tahun.textContent = new Date().getFullYear();
    }

    var form = document.getElementById('contact-form');
    var status = document.getElementById('form-status');

    if (!form) {
        return;
    }

    function clearErrors() {
        form.querySelectorAll('.field-error').forEach(function (el) {
            el.textContent = '';
        });
    }

    function showError(name, message) {
        var el = form.querySelector('[data-error-for="' + name + '"]');
        if (el) {
            el.textContent = message;
        }
    }

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        clearErrors();
        status.textContent = '';
        status.classList.remove('is-success', 'is-error');

        var submitBtn = form.querySelector('button[type="submit"]');
        submitBtn.disabled = true;

        fetch(form.action, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRF-TOKEN': form.querySelector('input[name="_token"]').value
            },
            body: new FormData(form)
        })
            .then(function (res) {
                if (res.status === 429) {
                    throw new Error('Terlalu banyak permintaan. Coba lagi dalam satu menit.');
                }
                if (!res.ok) {
                    return res.json().then(function (data) {
                        var errors = (data && data.errors) || {};
                        Object.keys(errors).forEach(function (key) {
                            showError(key, errors[key][0]);
                        });
                        throw new Error('Mohon periksa kembali isian form.');
                    });
                }
                return res.json();
            })
            .then(function (data) {
                status.textContent = data.message;
                status.classList.add('is-success');
                form.reset();
            })
            .catch(function (err) {
                status.textContent = err.message || 'Gagal mengirim pesan. Coba lagi nanti.';
                status.classList.add('is-error');
            })
            .finally(function () {
                submitBtn.disabled = false;
            });
    });
})();
