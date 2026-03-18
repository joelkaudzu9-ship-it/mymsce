// static/js/main.js
// Show loading spinner on form submissions
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            showSpinner();
        });
    });

    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });

    // Payment method selection
    const paymentMethods = document.querySelectorAll('.payment-method-card');
    paymentMethods.forEach(method => {
        method.addEventListener('click', function() {
            paymentMethods.forEach(m => m.classList.remove('selected'));
            this.classList.add('selected');
            const radio = this.querySelector('input[type="radio"]');
            if (radio) radio.checked = true;
        });
    });

    // Phone number formatting for Malawi
    const phoneInput = document.getElementById('phone');
    if (phoneInput) {
        phoneInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length > 0) {
                if (value.startsWith('265')) {
                    value = '+' + value;
                } else if (value.startsWith('0')) {
                    value = value.substring(1);
                    if (value.length > 0) {
                        value = '+265' + value;
                    }
                }
            }
            e.target.value = value;
        });
    }

    // Subject card click
    const subjectCards = document.querySelectorAll('.subject-card');
    subjectCards.forEach(card => {
        card.addEventListener('click', function() {
            const subjectId = this.dataset.subjectId;
            if (subjectId) {
                window.location.href = `/subject/${subjectId}`;
            }
        });
    });

    // Confirm delete actions
    const deleteButtons = document.querySelectorAll('.delete-confirm');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });
});

function showSpinner() {
    const spinner = document.getElementById('spinner');
    if (spinner) {
        spinner.classList.add('show');
    }
}

function hideSpinner() {
    const spinner = document.getElementById('spinner');
    if (spinner) {
        spinner.classList.remove('show');
    }
}

// Payment status checker
function checkPaymentStatus(paymentId) {
    const checkInterval = setInterval(function() {
        fetch(`/api/payment-status/${paymentId}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'completed') {
                    clearInterval(checkInterval);
                    window.location.href = '/payment-success';
                } else if (data.status === 'failed') {
                    clearInterval(checkInterval);
                    window.location.href = '/payment-failed';
                }
            })
            .catch(error => console.error('Error:', error));
    }, 3000); // Check every 3 seconds
}

// Copy text to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        alert('Copied to clipboard!');
    }, function(err) {
        console.error('Could not copy text: ', err);
    });
}