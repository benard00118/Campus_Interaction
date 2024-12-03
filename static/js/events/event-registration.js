// document.addEventListener('DOMContentLoaded', function() {
//     // Explicitly initialize modal
//     if (document.getElementById('registrationModal')) {
//         window.registrationModal = new bootstrap.Modal(document.getElementById('registrationModal'));
//     }

//     // Add explicit modal opening function
//     window.openRegistrationModal = function() {
//         if (window.registrationModal) {
//             window.registrationModal.show();
//         } else {
//             console.error('Modal not initialized');
//         }
//     };
// });
// // event-registration.js
// document.addEventListener('DOMContentLoaded', function() {
//     const eventId = document.getElementById('event-container')?.dataset.eventId;
//     if (!eventId) return;

//     const registrationModal = new bootstrap.Modal(document.getElementById('registrationModal'));
//     const form = document.getElementById('registrationForm');
//     const alertsContainer = document.getElementById('registration-alerts');
//     const statusContainer = document.getElementById('registration-status-container');
//     const registerButton = document.getElementById('registerButton');
    
    
    
//     // Add this function to your event-registration.js
// function openRegistrationModal() {
//     if (registrationModal) {
//         registrationModal.show();
//     }
// }
//     // Registration form submission
//     document.getElementById('submitRegistration')?.addEventListener('click', handleRegistration);
    
//     // Cancel registration
//     document.getElementById('cancelRegistrationBtn')?.addEventListener('click', handleCancellation);

//     // Periodic status check
//     setInterval(() => checkEventStatus(), 30000); // Every 30 seconds
    
//     function updateRegistrationButton(event) {
//     if (!registerButton) return;

//     const maxParticipants = event.max_participants;
//     const spotsRemaining = event.spots_left;
//     const userStatus = event.userStatus;

//     registerButton.disabled = false;

//     if (userStatus && userStatus.is_registered) {
//         // User is already registered or waitlisted
//         registerButton.classList.remove('btn-success', 'btn-warning');
//         registerButton.classList.add('btn-danger');
//         registerButton.innerHTML = userStatus.status === 'registered' 
//             ? '<i class="fas fa-times"></i> Cancel Registration' 
//             : '<i class="fas fa-clock"></i> On Waiting List';
        
//         // Add click event to cancel registration
//         registerButton.onclick = openRegistrationModal;
//     } else if (maxParticipants === null || spotsRemaining > 0) {
//         // Spots available
//         registerButton.classList.remove('btn-warning', 'btn-danger');
//         registerButton.classList.add('btn-success');
//         registerButton.innerHTML = '<i class="fas fa-user-plus"></i> Register for Event';
//         registerButton.onclick = openRegistrationModal;
//     } else {
//         // Event is full
//         registerButton.classList.remove('btn-success', 'btn-danger');
//         registerButton.classList.add('btn-warning');
//         registerButton.innerHTML = '<i class="fas fa-user-plus"></i> Join Waiting List';
//         registerButton.onclick = openRegistrationModal;
//     }
// }

// function updateUI(data) {
//     // Update registration status
//     if (statusContainer) {
//         let statusHTML = '';
        
//         if (data.status === 'registered') {
//             statusHTML = `
//                 <div class="alert alert-success mb-3">
//                     <i class="fas fa-check-circle"></i> 
//                     You're registered!
//                 </div>
//                 <button type="button" 
//                         class="btn btn-danger btn-lg w-100" 
//                         id="cancelRegistrationBtn"
//                         data-event-id="${eventId}">
//                     <i class="fas fa-times"></i> Cancel Registration
//                 </button>
//             `;
//         } else if (data.status === 'waitlist') {
//             statusHTML = `
//                 <div class="alert alert-warning mb-3">
//                     <i class="fas fa-clock"></i> 
//                     You're on the waiting list (Position: ${data.waitlist_position})
//                 </div>
//                 <button type="button" 
//                         class="btn btn-danger btn-lg w-100" 
//                         id="cancelRegistrationBtn"
//                         data-event-id="${eventId}">
//                     <i class="fas fa-times"></i> Cancel Waiting List
//                 </button>
//             `;
//         }
        
//         statusContainer.innerHTML = statusHTML;
        
//         // Reattach cancel event listener
//         document.getElementById('cancelRegistrationBtn')?.addEventListener('click', handleCancellation);
//     }
    
//     // Update spots and waitlist info
//     checkEventStatus();
// }   
// // Modify handleRegistration to update UI after successful registration
// async function handleRegistration(event) {
//     event.preventDefault();
//     clearAlerts();
    
//     try {
//         const formData = new FormData(form);
//         const response = await fetch(`/events/event/${eventId}/register/`, {
//             method: 'POST',
//             body: formData,
//             headers: {
//                 'X-Requested-With': 'XMLHttpRequest',
//                 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
//             }
//         });
        
//         const data = await response.json();
        
//         if (data.success) {
//             showAlert('success', data.message);
//             setTimeout(() => {
//                 registrationModal.hide();
//                 updateUI(data);
//                 // Force update of registration button
//                 updateRegistrationButton({
//                     max_participants: data.max_participants,
//                     spots_left: data.spots_left,
//                     userStatus: {
//                         is_registered: true,
//                         status: data.status,
//                         waitlist_position: data.waitlist_position
//                     }
//                 });
//             }, 1500);
//         } else {
//             handleErrors(data.error);
//         }
//     } catch (error) {
//         console.error('Registration error:', error);
//         showAlert('danger', 'An unexpected error occurred. Please try again.');
//     }
// }

// // Modify handleCancellation to update registration button
// async function handleCancellation() {
//     if (!confirm('Are you sure you want to cancel your registration?')) return;
    
//     try {
//         const response = await fetch(`/events/event/${eventId}/cancel/`, {
//             method: 'POST',
//             headers: {
//                 'X-Requested-With': 'XMLHttpRequest',
//                 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
//             }
//         });
        
//         const data = await response.json();
        
//         if (data.success) {
//             // Clear status container
//             const statusContainer = document.getElementById('registration-status-container');
//             if (statusContainer) {
//                 statusContainer.innerHTML = ''; 
//             }
            
//             // Check and update event status
//             await checkEventStatus();
            
//             // Show success message
//             showAlert('success', 'Registration cancelled successfully');
//         } else {
//             showAlert('danger', data.error || 'Failed to cancel registration');
//         }
//     } catch (error) {
//         showAlert('danger', 'An error occurred while cancelling registration');
//     }
// }


   

//     // More robust error handling
//     function handleErrors(errors) {
//         if (typeof errors === 'string') {
//             showAlert('danger', errors);
//             return;
//         }
        
//         // Handle both server-side and form validation errors
//         Object.entries(errors).forEach(([field, messages]) => {
//             const input = document.getElementById(`id_${field}`);
//             const feedback = document.getElementById(`${field}-error`);
//             if (input && feedback) {
//                 input.classList.add('is-invalid');
//                 feedback.textContent = Array.isArray(messages) ? messages.join(' ') : messages;
//             }
//         });
        
//         // If no specific field errors, show a general error
//         if (Object.keys(errors).length === 0) {
//             showAlert('danger', 'Registration failed. Please check your details.');
//         }
//     }

   
  
  
//     async function checkEventStatus() {
//         try {
//             const response = await fetch(`/events/api/event/${eventId}/status/`);
//             const data = await response.json();
            
//             if (data.success) {
//                 // Preserve user's registration status more carefully
//                 const userStatus = data.user_status || {};
                
//                 // Ensure all necessary properties are present
//                 const completeUserStatus = {
//                     is_registered: userStatus.is_registered || false,
//                     status: userStatus.status || null,
//                     waitlist_position: userStatus.waitlist_position || null,
//                     max_participants: data.total_spots || null,
//                     spots_left: data.spots_left || null
//                 };
    
//                 // Update registration button with comprehensive status
//                 updateRegistrationButton({
//                     max_participants: completeUserStatus.max_participants,
//                     spots_left: completeUserStatus.spots_left,
//                     userStatus: completeUserStatus
//                 });
    
//                 // If user has an active registration, update UI
//                 if (completeUserStatus.is_registered) {
//                     updateUI({
//                         status: completeUserStatus.status,
//                         waitlist_position: completeUserStatus.waitlist_position,
//                         max_participants: completeUserStatus.max_participants
//                     });
//                 }
//             }
//         } catch (error) {
//             console.error('Error checking event status:', error);
//         }
//     }
    
//     // Modify the DOMContentLoaded to ensure initial status check
//     document.addEventListener('DOMContentLoaded', function() {
//         const eventId = document.getElementById('event-container')?.dataset.eventId;
//         if (!eventId) return;
    
//         // Immediate status check on page load
//         checkEventStatus();
    
//         // Rest of your existing initialization code...
//     });
    
//     function clearAlerts() {
//         if (alertsContainer) alertsContainer.innerHTML = '';
//         document.querySelectorAll('.invalid-feedback').forEach(el => el.textContent = '');
//         document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
//     }
    
//     function showAlert(type, message) {
//         if (!alertsContainer) return;
        
//         const alert = document.createElement('div');
//         alert.className = `alert alert-${type}`;
//         alert.innerHTML = `<i class="fas fa-${type === 'success' ? 'check' : 'exclamation'}-circle"></i> ${message}`;
//         alertsContainer.appendChild(alert);
//     }
    
//     function handleErrors(errors) {
//         if (typeof errors === 'string') {
//             showAlert('danger', errors);
//             return;
//         }
        
//         for (const [field, messages] of Object.entries(errors)) {
//             const input = document.getElementById(`id_${field}`);
//             const feedback = document.getElementById(`${field}-error`);
//             if (input && feedback) {
//                 input.classList.add('is-invalid');
//                 feedback.textContent = messages.join(' ');
//             }
//         }
//     }
//      // Attach event listener to form submission
//     form.addEventListener('submit', handleRegistration);
// });



document.addEventListener('DOMContentLoaded', function() {
    const eventContainer = document.getElementById('event-container');
    if (!eventContainer) return;

    const eventId = eventContainer.dataset.eventId;
    const redirectUrl = eventContainer.dataset.redirectUrl || `/events/event/${eventId}/`;

    const registrationModal = new bootstrap.Modal(document.getElementById('registrationModal'));
    const form = document.getElementById('registrationForm');
    const alertsContainer = document.getElementById('registration-alerts');
    const statusContainer = document.getElementById('registration-status-container');
    const registerButton = document.getElementById('registerButton');
    const submitRegistrationBtn = document.getElementById('submitRegistration');

    // Centralized error handling
    function showAlert(type, message) {
        if (!alertsContainer) return;
        
        alertsContainer.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                <i class="fas fa-${type === 'success' ? 'check' : 'exclamation'}-circle me-2"></i> 
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
    }

    // Clear form errors
    function clearFormErrors() {
        document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
        document.querySelectorAll('.invalid-feedback').forEach(el => el.textContent = '');
    }

    // Handle form submission with improved error handling
    async function handleRegistration(event) {
        event.preventDefault();
        const maxRetries = 3;
        let retryCount = 0;
    
        while (retryCount < maxRetries) {
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
                    setTimeout(() => {
                        registrationModal.hide();
                        window.location.href = redirectUrl;
                    }, 1500);
                    return; // Exit the function on success
                } else {
                    // Check for specific lock error
                    if (data.error.includes('currently being processed')) {
                        retryCount++;
                        await new Promise(resolve => setTimeout(resolve, 1000 * retryCount)); // Exponential backoff
                        continue;
                    }
                    
                    handleErrors(data.errors || data.error);
                    return;
                }
            } catch (error) {
                console.error('Registration error:', error);
                
                if (retryCount < maxRetries - 1) {
                    retryCount++;
                    await new Promise(resolve => setTimeout(resolve, 1000 * retryCount));
                } else {
                    showAlert('danger', 'An unexpected error occurred. Please try again.');
                    return;
                }
            }
        }
    }
    // Enhanced error handling
    function handleErrors(errors) {
        if (typeof errors === 'string') {
            showAlert('danger', errors);
            return;
        }
        
        // Handle both server-side and form validation errors
        Object.entries(errors).forEach(([field, messages]) => {
            const input = document.getElementById(`id_${field}`);
            const feedback = document.getElementById(`${field}-error`);
            
            if (input && feedback) {
                input.classList.add('is-invalid');
                feedback.textContent = Array.isArray(messages) ? messages.join(' ') : messages;
            }
        });
        
        // If no specific field errors, show a general error
        if (Object.keys(errors).length === 0) {
            showAlert('danger', 'Registration failed. Please check your details.');
        }
    }

    // Update registration button state
    function updateRegistrationButton(event) {
        if (!registerButton) return;

        const maxParticipants = event.max_participants;
        const spotsRemaining = event.spots_left;
        const userStatus = event.userStatus || {};

        registerButton.disabled = false;

        if (userStatus.is_registered) {
            // User is already registered or waitlisted
            registerButton.classList.remove('btn-success', 'btn-warning');
            registerButton.classList.add('btn-danger');
            registerButton.innerHTML = userStatus.status === 'registered' 
                ? '<i class="fas fa-times"></i> Cancel Registration' 
                : '<i class="fas fa-clock"></i> On Waiting List';
        } else if (maxParticipants === null || spotsRemaining > 0) {
            // Spots available
            registerButton.classList.remove('btn-warning', 'btn-danger');
            registerButton.classList.add('btn-success');
            registerButton.innerHTML = '<i class="fas fa-user-plus"></i> Register for Event';
        } else {
            // Event is full
            registerButton.classList.remove('btn-success', 'btn-danger');
            registerButton.classList.add('btn-warning');
            registerButton.innerHTML = '<i class="fas fa-user-plus"></i> Join Waiting List';
        }
    }

    // Check event status periodically
    async function checkEventStatus() {
        try {
            const response = await fetch(`/events/api/event/${eventId}/status/`);
            const data = await response.json();
            
            if (data.success) {
                const userStatus = data.user_status || {};
                
                updateRegistrationButton({
                    max_participants: data.total_spots || null,
                    spots_left: data.spots_left || null,
                    userStatus: {
                        is_registered: userStatus.is_registered || false,
                        status: userStatus.status || null
                    }
                });
            }
        } catch (error) {
            console.error('Error checking event status:', error);
        }
    }

    // Cancel registration functionality
    async function handleCancellation() {
        if (!confirm('Are you sure you want to cancel your registration?')) return;
        
        try {
            const response = await fetch(`/events/event/${eventId}/cancel/`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Clear status container
                if (statusContainer) {
                    statusContainer.innerHTML = ''; 
                }
                
                // Check and update event status
                await checkEventStatus();
                
                // Show success message and redirect
                showAlert('success', 'Registration cancelled successfully');
                setTimeout(() => {
                    window.location.href = redirectUrl;
                }, 1500);
            } else {
                showAlert('danger', data.error || 'Failed to cancel registration');
            }
        } catch (error) {
            showAlert('danger', 'An error occurred while cancelling registration');
        }
    }

    // Event Listeners
    if (form) {
        form.addEventListener('submit', handleRegistration);
    }

    if (submitRegistrationBtn) {
        submitRegistrationBtn.addEventListener('click', handleRegistration);
    }

    const cancelRegistrationBtn = document.getElementById('cancelRegistrationBtn');
    if (cancelRegistrationBtn) {
        cancelRegistrationBtn.addEventListener('click', handleCancellation);
    }

    // Initial event status check
    checkEventStatus();

    // Periodic status check
    setInterval(checkEventStatus, 50000); // Every 30 seconds

    // Expose functions globally if needed
    window.openRegistrationModal = function() {
        if (registrationModal) {
            registrationModal.show();
        }
    };
});