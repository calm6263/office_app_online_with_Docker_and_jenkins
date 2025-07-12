// التحكم في ظهور الحقول بناءً على الخدمة وطريقة الدفع
document.addEventListener('DOMContentLoaded', function() {
    const serviceSelect = document.getElementById('service');
    const paymentMethodSelect = document.getElementById('payment_method');
    
    if (serviceSelect) {
        serviceSelect.addEventListener('change', function() {
            const universityField = document.getElementById('university_field');
            if (this.value === 'التسجيل على الجامعة') {
                universityField.style.display = 'block';
            } else {
                universityField.style.display = 'none';
            }
        });
    }
    
    if (paymentMethodSelect) {
        paymentMethodSelect.addEventListener('change', function() {
            const receiverField = document.getElementById('receiver_field');
            if (this.value === 'أونلاين') {
                receiverField.style.display = 'block';
            } else {
                receiverField.style.display = 'none';
            }
        });
    }
    
    // إظهار/إخفاء كلمة المرور
    const togglePassword = document.getElementById('togglePassword');
    if (togglePassword) {
        togglePassword.addEventListener('click', function() {
            const passwordInput = document.getElementById('password');
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);
            this.innerHTML = type === 'password' ? '<i class="bi bi-eye"></i>' : '<i class="bi bi-eye-slash"></i>';
        });
    }
});