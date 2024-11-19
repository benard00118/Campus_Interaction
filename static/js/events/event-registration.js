document.addEventListener('DOMContentLoaded', function() {
    const eventId = document.getElementById('event-container')?.dataset.eventId;
    if (!eventId) return;

    const registrationModal = new bootstrap.Modal(document.getElementById('registrationModal'));
    const form = document.getElementById('registrationForm');
    const alertsContainer = document.getElementById('registration-alerts');
    const statusContainer = document.getElementById('registration-status-container');
    const registerButton = document.getElementById('registerButton');
    
    // Track registration state
    let isRegistrationInProgress = false;

    async function checkEventStatus() {
        try {
            const response = await fetch(`/events/api/event/${eventId}/status/`);
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            const data = await response.json();
            
            if (data.success) {
                updateStatusDisplay(data);
                if (registerButton) {
                    updateRegistrationButton(data);
                }
            }
        } catch (error) {
            console.error('Error checking event status:', error);
        }
    }

    function updateRegistrationButton(data) {
        if (!registerButton) return;
    
        const maxParticipants = data.max_participants;
        const spotsLeft = data.spots_left;
    
        registerButton.disabled = false;
    
        if (maxParticipants === null || spotsLeft > 0) {
            registerButton.classList.remove('btn-warning');
            registerButton.classList.add('btn-success');
            registerButton.innerHTML = '<i class="fas fa-user-plus"></i> Register for Event';
        } else {
            registerButton.classList.remove('btn-success');
            registerButton.classList.add('btn-warning');
            registerButton.innerHTML = '<i class="fas fa-user-plus"></i> Join Waiting List';
        }
    }

    function updateStatusDisplay(data) {
        try {
            const spotsCounter = document.getElementById('spots-counter');
            const waitlistCounter = document.getElementById('waitlist-counter');
            
            if (spotsCounter) {
                spotsCounter.textContent = data.spots_left === null ? 'Unlimited' : data.spots_left;
            }
            
            // Only update waitlist if the data exists
            if (waitlistCounter && typeof data.waitlist_count !== 'undefined') {
                waitlistCounter.textContent = `${data.waitlist_count} people`;
                if (waitlistCounter.parentElement) {
                    waitlistCounter.parentElement.style.display = 
                        data.waitlist_count > 0 ? 'flex' : 'none';
                }
            }
        } catch (error) {
            console.error('Error updating status display:', error);
        }
    }

    async function handleRegistration(e) {
        e.preventDefault();
        if (isRegistrationInProgress) return;
        
        clearAlerts();
        isRegistrationInProgress = true;
        
        const submitButton = document.getElementById('submitRegistration');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        }
        
        try {
            const formData = new FormData(form);
            const response = await fetch(`/events/event/${eventId}/register/`, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                showAlert('success', data.message);
                await updateUI(data);
                setTimeout(() => {
                    registrationModal.hide();
                }, 1500);
            } else {
                handleErrors(data.error);
            }
        } catch (error) {
            showAlert('danger', 'An error occurred. Please try again.');
        } finally {
            isRegistrationInProgress = false;
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.innerHTML = 'Register';
            }
        }
    }

    async function handleCancellation(e) {
        e.preventDefault();
        if (!confirm('Are you sure you want to cancel your registration?')) return;
        
        const cancelButton = e.target.closest('#cancelRegistrationBtn');
        if (!cancelButton) return;
        
        cancelButton.disabled = true;
        cancelButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Cancelling...';
        
        try {
            const response = await fetch(`/events/event/${eventId}/cancel/`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                showAlert('success', 'Registration cancelled successfully');
                setTimeout(() => {
                    location.reload();
                }, 1500);
            } else {
                throw new Error(data.error || 'Failed to cancel registration');
            }
        } catch (error) {
            console.error('Cancellation error:', error);
            showAlert('danger', error.message || 'An error occurred while cancelling registration');
            cancelButton.disabled = false;
            cancelButton.innerHTML = '<i class="fas fa-times"></i> Cancel Registration';
        }
    }

    function showAlert(type, message) {
        if (!alertsContainer) return;
        
        alertsContainer.innerHTML = '';
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.innerHTML = `<i class="fas fa-${type === 'success' ? 'check' : 'exclamation'}-circle"></i> ${message}`;
        alertsContainer.appendChild(alert);
    }

    function clearAlerts() {
        if (alertsContainer) {
            alertsContainer.innerHTML = '';
        }
        document.querySelectorAll('.invalid-feedback').forEach(el => el.textContent = '');
        document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
    }

    function handleErrors(errors) {
        if (typeof errors === 'string') {
            showAlert('danger', errors);
            return;
        }
        
        for (const [field, messages] of Object.entries(errors)) {
            const input = document.getElementById(`id_${field}`);
            const feedback = document.getElementById(`${field}-error`);
            if (input && feedback) {
                input.classList.add('is-invalid');
                feedback.textContent = messages.join(' ');
            }
        }
    }

    // Event Listeners
    form?.addEventListener('submit', handleRegistration);
    
    // Attach cancel button listener
    const cancelButton = document.getElementById('cancelRegistrationBtn');
    if (cancelButton) {
        cancelButton.addEventListener('click', handleCancellation);
    }
    
    // Initial status check
    checkEventStatus();
    // Periodic status check
    setInterval(checkEventStatus, 30000);
});