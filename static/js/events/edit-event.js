// static/js/events/editEvent.js
document.addEventListener('DOMContentLoaded', function() {
    const editEventForm = document.getElementById('editEventForm');
    const saveEventChangesBtn = document.getElementById('saveEventChangesBtn');
    
    if (editEventForm) {
        editEventForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Get the event ID from the page
            const eventId = document.getElementById('event-container').getAttribute('data-event-id');
            
            // Create FormData object
            const formData = new FormData(this);
            
            // Disable submit button and show loading state
            saveEventChangesBtn.disabled = true;
            saveEventChangesBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
            
            // Send AJAX request
            fetch(`/events/api/events/${eventId}/update/`, {
                method: 'PATCH',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                },
                body: formData
            })
            .then(response => {
                // Check if response is ok
                if (!response.ok) {
                    // Try to parse error response
                    return response.json().then(errorData => {
                        throw new Error(errorData.error || 'Update failed');
                    });
                }
                return response.json();
            })
            .then(data => {
                // Success handling
                Swal.fire({
                    icon: 'success',
                    title: 'Event Updated',
                    text: data.message || 'Event updated successfully',
                    confirmButtonColor: '#3085d6'
                }).then(() => {
                    // Reload the page or update specific elements
                    location.reload();
                });
            })
            .catch(error => {
                // Error handling
                Swal.fire({
                    icon: 'error',
                    title: 'Update Failed',
                    text: error.message || 'There was an error updating the event. Please try again.',
                    confirmButtonColor: '#d33'
                });
                console.error('Error:', error);
            })
            .finally(() => {
                // Re-enable submit button
                saveEventChangesBtn.disabled = false;
                saveEventChangesBtn.innerHTML = 'Save Changes';
            });
        });
    }
});