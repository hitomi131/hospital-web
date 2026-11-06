// ============================================
// HOSPITAL WEB — Main JavaScript
// ============================================

document.addEventListener('DOMContentLoaded', function () {

    // ---------- Date display ----------
    const dateEl = document.getElementById('current-date');
    if (dateEl) {
        const now = new Date();
        const options = { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' };
        dateEl.textContent = now.toLocaleDateString('ru-RU', options);
    }

    // ---------- Sidebar toggle (mobile) ----------
    const sidebar = document.getElementById('sidebar');
    const overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    document.body.appendChild(overlay);

    function openSidebar() {
        sidebar.classList.add('open');
        overlay.classList.add('show');
    }

    function closeSidebar() {
        sidebar.classList.remove('open');
        overlay.classList.remove('show');
    }

    document.getElementById('topbarToggle')?.addEventListener('click', openSidebar);
    document.getElementById('sidebarToggle')?.addEventListener('click', closeSidebar);
    overlay.addEventListener('click', closeSidebar);

    // ---------- Auto-dismiss alerts ----------
    setTimeout(function () {
        document.querySelectorAll('.alert--dismissible').forEach(function (el) {
            el.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            el.style.opacity = '0';
            el.style.transform = 'translateY(-10px)';
            setTimeout(() => el.remove(), 400);
        });
    }, 5000);

    // ---------- SNILS auto-format ----------
    const snilsInput = document.getElementById('id_snils') || document.querySelector('input[name="snils"]');
    if (snilsInput) {
        snilsInput.addEventListener('input', function () {
            let value = this.value.replace(/\D/g, '');
            let formatted = '';
            if (value.length > 0) formatted += value.substring(0, 3);
            if (value.length > 3) formatted += '-' + value.substring(3, 6);
            if (value.length > 6) formatted += '-' + value.substring(6, 9);
            if (value.length > 9) formatted += ' ' + value.substring(9, 11);
            this.value = formatted;
        });
    }

    // ---------- Booking: dynamic slot loading ----------
    const doctorSelect = document.getElementById('doctor-select');
    const dateInput    = document.getElementById('appt-date');
    const timeSelect   = document.getElementById('appt-time');

    function loadSlots() {
        const doctorId = doctorSelect ? doctorSelect.value : null;
        const date     = dateInput    ? dateInput.value    : null;

        if (!doctorId || !date) {
            if (timeSelect) {
                timeSelect.innerHTML = '<option value="">Сначала выберите врача и дату...</option>';
                timeSelect.disabled = true;
            }
            return;
        }

        if (timeSelect) {
            timeSelect.innerHTML = '<option value="">⏳ Загрузка слотов...</option>';
            timeSelect.disabled = true;
        }

        const params = new URLSearchParams({ doctor_id: doctorId, date });
        fetch(`/ajax/slots/?${params}`)
            .then(r => {
                if (!r.ok) throw new Error('Не удалось получить список времени');
                return r.json();
            })
            .then(data => {
                if (!timeSelect) return;
                timeSelect.innerHTML = '';
                if (data.slots && data.slots.length > 0) {
                    const placeholder = document.createElement('option');
                    placeholder.value = '';
                    placeholder.textContent = 'Выберите время...';
                    timeSelect.appendChild(placeholder);
                    data.slots.forEach(slot => {
                        const opt = document.createElement('option');
                        opt.value = slot;
                        opt.textContent = slot;
                        timeSelect.appendChild(opt);
                    });
                } else {
                    const opt = document.createElement('option');
                    opt.value = '';
                    opt.textContent = '❌ Нет доступных слотов';
                    timeSelect.appendChild(opt);
                }
                timeSelect.disabled = false;
            })
            .catch(() => {
                if (timeSelect) {
                    timeSelect.innerHTML = '<option value="">Ошибка загрузки. Попробуйте снова.</option>';
                    timeSelect.disabled = false;
                }
            });
    }

    if (doctorSelect) doctorSelect.addEventListener('change', loadSlots);
    if (dateInput)    dateInput.addEventListener('change', loadSlots);

    // ---------- Reschedule: dynamic slot loading ----------
    const rescheduleDateInput = document.getElementById('reschedule-date');
    const rescheduleTimeSelect = document.getElementById('reschedule-time');
    const doctorIdHidden = document.getElementById('reschedule-doctor-id');
    const excludeIdHidden = document.getElementById('reschedule-exclude-id');

    function loadRescheduleSlots() {
        if (!rescheduleDateInput || !rescheduleTimeSelect) return;
        const doctorId = doctorIdHidden ? doctorIdHidden.value : null;
        const date = rescheduleDateInput.value;
        const excludeId = excludeIdHidden ? excludeIdHidden.value : null;
        if (!doctorId || !date) {
            rescheduleTimeSelect.innerHTML = '<option value="">Сначала выберите дату...</option>';
            rescheduleTimeSelect.disabled = true;
            return;
        }

        rescheduleTimeSelect.innerHTML = '<option value="">⏳ Загрузка...</option>';
        rescheduleTimeSelect.disabled = true;

        const params = new URLSearchParams({ doctor_id: doctorId, date });
        if (excludeId) params.set('exclude_id', excludeId);

        fetch(`/ajax/slots/?${params}`)
            .then(r => {
                if (!r.ok) throw new Error('Не удалось получить список времени');
                return r.json();
            })
            .then(data => {
                rescheduleTimeSelect.innerHTML = '';
                if (data.slots && data.slots.length > 0) {
                    const placeholder = document.createElement('option');
                    placeholder.value = '';
                    placeholder.textContent = 'Выберите новое время...';
                    rescheduleTimeSelect.appendChild(placeholder);
                    data.slots.forEach(slot => {
                        const opt = document.createElement('option');
                        opt.value = slot;
                        opt.textContent = slot;
                        rescheduleTimeSelect.appendChild(opt);
                    });
                } else {
                    rescheduleTimeSelect.innerHTML = '<option value="">Нет свободных слотов</option>';
                }
                rescheduleTimeSelect.disabled = false;
            })
            .catch(() => {
                rescheduleTimeSelect.innerHTML = '<option value="">Ошибка загрузки. Попробуйте снова.</option>';
                rescheduleTimeSelect.disabled = false;
            });
    }

    if (rescheduleDateInput) rescheduleDateInput.addEventListener('change', loadRescheduleSlots);

    // ---------- Toggle visited (doctor) ----------
    document.querySelectorAll('.toggle-visited-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            if (this.disabled) return;
            this.disabled = true;
            const apptId = this.dataset.apptId;
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
                              || getCookie('csrftoken');

            fetch(`/doctor/appointment/${apptId}/toggle/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json',
                }
            })
            .then(r => {
                if (!r.ok) throw new Error('Не удалось сохранить статус');
                return r.json();
            })
            .then(data => {
                const row = this.closest('tr') || this.closest('.appt-row');
                const badge = row ? row.querySelector('.status-badge') : null;
                if (data.visited) {
                    this.textContent = 'Отметить отсутствие';
                    this.classList.remove('btn-success');
                    this.classList.add('btn-secondary');
                    if (badge) {
                        badge.className = 'badge badge-success status-badge';
                        badge.innerHTML = '<i class="fas fa-check-circle"></i> Посетил';
                    }
                } else {
                    this.textContent = 'Отметить присутствие';
                    this.classList.remove('btn-secondary');
                    this.classList.add('btn-success');
                    if (badge) {
                        badge.className = 'badge badge-warning status-badge';
                        badge.innerHTML = '<i class="fas fa-clock"></i> Ожидается';
                    }
                }
            })
            .catch(() => window.alert('Не удалось обновить статус. Обновите страницу и попробуйте ещё раз.'))
            .finally(() => { this.disabled = false; });
        });
    });

    // ---------- Confirm modals ----------
    document.querySelectorAll('[data-confirm]').forEach(el => {
        el.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirm)) {
                e.preventDefault();
            }
        });
    });

});

// CSRF helper
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
