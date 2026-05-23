'use strict';

/* ===================================================
   ملف JavaScript الرئيسي - مكتب خدمات ترجمة وتصديق
   =================================================== */

// ── CSRF Helper ──────────────────────────────────────
function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

// إضافة CSRF token تلقائياً لجميع طلبات fetch
const originalFetch = window.fetch;
window.fetch = function(url, options = {}) {
    if (!options.method || options.method.toUpperCase() === 'GET') {
        return originalFetch(url, options);
    }
    const headers = new Headers(options.headers || {});
    if (!headers.has('X-CSRFToken')) {
        headers.set('X-CSRFToken', getCsrfToken());
    }
    options.headers = headers;
    return originalFetch(url, options);
};

// ── تهيئة عند تحميل الصفحة ───────────────────────────
document.addEventListener('DOMContentLoaded', function () {

    initServiceFields();
    initPaymentFields();
    initPasswordToggle();
    initFileValidation();
    initFormConfirm();
    initAutoHideAlerts();
    initNotificationRead();
    initPriceCalculator();
});

// ── إظهار/إخفاء حقل الجامعة بناءً على الخدمة ─────────
function initServiceFields() {
    const serviceSelect = document.getElementById('service');
    if (!serviceSelect) return;

    serviceSelect.addEventListener('change', function () {
        const universityField = document.getElementById('university_field');
        if (universityField) {
            universityField.style.display =
                this.value === 'التسجيل على الجامعة' ? 'block' : 'none';
        }
    });
}

// ── إظهار/إخفاء حقل رقم المستلم بناءً على طريقة الدفع ──
function initPaymentFields() {
    const paymentMethodSelect = document.getElementById('payment_method');
    const paymentStatusSelect = document.getElementById('payment_status');

    if (paymentMethodSelect) {
        paymentMethodSelect.addEventListener('change', function () {
            const receiverField = document.getElementById('receiver_field');
            if (receiverField) {
                receiverField.style.display =
                    this.value === 'أونلاين' ? 'block' : 'none';
            }
        });
    }

    if (paymentStatusSelect) {
        paymentStatusSelect.addEventListener('change', function () {
            const installmentField = document.getElementById('installment_field');
            if (installmentField) {
                installmentField.style.display =
                    this.value === 'تقسيط' ? 'block' : 'none';
            }
        });
    }
}

// ── إظهار/إخفاء كلمة المرور ──────────────────────────
function initPasswordToggle() {
    document.querySelectorAll('[data-toggle-password]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            const targetId = this.getAttribute('data-toggle-password');
            const input = document.getElementById(targetId);
            if (!input) return;
            const isPassword = input.type === 'password';
            input.type = isPassword ? 'text' : 'password';
            const icon = this.querySelector('i');
            if (icon) {
                icon.className = isPassword ? 'bi bi-eye-slash' : 'bi bi-eye';
            }
        });
    });

    // دعم أزرار toggle بـ ID محدد
    [['togglePassword', 'password'], ['toggleCustomerPassword', 'customer_password']].forEach(function([btnId, inputId]) {
        const btn = document.getElementById(btnId);
        if (!btn) return;
        btn.addEventListener('click', function () {
            const input = document.getElementById(inputId);
            if (!input) return;
            const isPassword = input.type === 'password';
            input.type = isPassword ? 'text' : 'password';
            this.innerHTML = isPassword
                ? '<i class="bi bi-eye-slash"></i>'
                : '<i class="bi bi-eye"></i>';
        });
    });
}

// ── التحقق من الملفات قبل الرفع ─────────────────────
function initFileValidation() {
    const MAX_SIZE_MB = 16;
    const ALLOWED_TYPES = [
        'image/png', 'image/jpeg', 'image/gif',
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain'
    ];

    document.querySelectorAll('input[type="file"]').forEach(function (input) {
        input.addEventListener('change', function () {
            const files = Array.from(this.files);
            for (const file of files) {
                if (file.size > MAX_SIZE_MB * 1024 * 1024) {
                    alert(`الملف "${file.name}" يتجاوز الحد الأقصى ${MAX_SIZE_MB} ميجابايت`);
                    this.value = '';
                    return;
                }
                if (!ALLOWED_TYPES.includes(file.type)) {
                    alert(`نوع الملف "${file.name}" غير مسموح به`);
                    this.value = '';
                    return;
                }
            }
        });
    });
}

// ── تأكيد الإجراءات الخطرة ───────────────────────────
function initFormConfirm() {
    document.querySelectorAll('[data-confirm]').forEach(function (el) {
        el.addEventListener('click', function (e) {
            const message = this.getAttribute('data-confirm') || 'هل أنت متأكد؟';
            if (!confirm(message)) {
                e.preventDefault();
                e.stopPropagation();
            }
        });
    });
}

// ── إخفاء التنبيهات تلقائياً بعد 5 ثوانٍ ────────────
function initAutoHideAlerts() {
    document.querySelectorAll('.alert:not(.alert-danger)').forEach(function (alert) {
        setTimeout(function () {
            alert.classList.remove('show');
            alert.classList.add('fade');
            setTimeout(function () { alert.remove(); }, 500);
        }, 5000);
    });
}

// ── تحديد الإشعارات كمقروءة ──────────────────────────
function initNotificationRead() {
    document.querySelectorAll('.notification-item[data-id]').forEach(function (item) {
        item.addEventListener('click', function () {
            const id = this.getAttribute('data-id');
            fetch(`/mark_notification_read/${id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            }).catch(console.error);
        });
    });
}

// ── حساب الإجمالي تلقائياً ───────────────────────────
function initPriceCalculator() {
    function recalcTotal() {
        let total = 0;
        document.querySelectorAll('.service-price-input').forEach(function (input) {
            const checkbox = document.getElementById('check_' + input.dataset.service);
            if (checkbox && checkbox.checked) {
                total += parseFloat(input.value) || 0;
            }
        });

        const quantityInput = document.getElementById('quantity');
        const quantity = quantityInput ? (parseInt(quantityInput.value) || 1) : 1;
        total *= quantity;

        const totalDisplay = document.getElementById('total_display');
        if (totalDisplay) {
            totalDisplay.textContent = total.toFixed(2) + ' روبل';
        }

        const totalInput = document.getElementById('total_hidden');
        if (totalInput) {
            totalInput.value = total.toFixed(2);
        }
    }

    document.querySelectorAll('.service-price-input, .service-checkbox').forEach(function (el) {
        el.addEventListener('change', recalcTotal);
        el.addEventListener('input', recalcTotal);
    });

    const qtyInput = document.getElementById('quantity');
    if (qtyInput) {
        qtyInput.addEventListener('input', recalcTotal);
    }
}

// ── دالة مساعدة لطلبات AJAX ──────────────────────────
function ajaxPost(url, data, onSuccess, onError) {
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify(data),
    })
    .then(function(res) { return res.json(); })
    .then(onSuccess)
    .catch(onError || console.error);
}
