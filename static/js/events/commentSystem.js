// comment-system.js

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the comment system
    initializeCommentSystem();
});

function initializeCommentSystem() {
    // Main comment form submission
    const commentForm = document.getElementById('commentForm');
    if (commentForm) {
        commentForm.addEventListener('submit', handleCommentSubmission);
    }

    // Initialize all reply forms
    document.addEventListener('click', function(e) {
     

       
        // Other click handlers remain the same...
       

        if (e.target.matches('.like-button') || e.target.closest('.like-button')) {
            handleLikeToggle(e);
        }

        if (e.target.matches('.delete-comment') || e.target.closest('.delete-comment')) {
            handleCommentDeletion(e);
        }

        
    });

   
}
async function handleCommentSubmission(e) {
    e.preventDefault();
    const form = e.target;
    const url = form.getAttribute('action');
    const formData = new FormData(form);

    try {
        const response = await fetch(url, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        const data = await response.json();

        if (response.ok) {
            // Insert the new comment at the top of the comments section
            const commentsSection = document.getElementById('main-comments');
            commentsSection.insertAdjacentHTML('afterbegin', data.comment_html);
            
            // Clear the form
            form.reset();
            
            // Show success message
            showNotification('Comment posted successfully!', 'success');
        } else {
            throw new Error(data.message || 'Error posting comment');
        }
    } catch (error) {
        showNotification(error.message, 'error');
    }
}


async function handleLikeToggle(e) {
    const button = e.target.closest('.like-button');
    const url = button.dataset.url;
    const isLiked = button.dataset.liked === 'true';

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });

        const data = await response.json();

        if (response.ok) {
            // Update like button appearance and count
            button.dataset.liked = (!isLiked).toString();
            button.classList.toggle('btn-danger', !isLiked);
            button.classList.toggle('btn-outline-danger', isLiked);
            
            const likesCount = button.querySelector('.likes-count');
            likesCount.textContent = data.likes_count;
        } else {
            throw new Error(data.message || 'Error toggling like');
        }
    } catch (error) {
        showNotification(error.message, 'error');
    }
}


function showNotification(message, type = 'success') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} position-fixed top-0 end-0 m-3`;
    notification.style.zIndex = '1050';
    notification.textContent = message;

    // Add to document
    document.body.appendChild(notification);

    // Remove after 3 seconds
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}