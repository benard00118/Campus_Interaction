// Comment Deletion Module
const CommentManager = {
    csrfToken: null,
    
    // Initialize the comment deletion functionality
    init() {
        // Retrieve CSRF token
        this.csrfToken = this.getCsrfToken();
        
        // Attach event listeners to all delete buttons
        this.attachDeleteListeners();
    },
    
    // Get CSRF token from the page
    getCsrfToken() {
        const csrfElement = document.querySelector('[name=csrfmiddlewaretoken]');
        if (!csrfElement) {
            console.error('CSRF token not found. Ensure it is present in the page.');
            return null;
        }
        return csrfElement.value;
    },
    
    // Attach click event listeners to delete buttons
    attachDeleteListeners() {
        const deleteButtons = document.querySelectorAll('[data-delete-comment]');
        deleteButtons.forEach(button => {
            button.addEventListener('click', (event) => {
                const commentId = button.getAttribute('data-comment-id');
                const isReply = button.hasAttribute('data-is-reply');
                
                this.deleteComment(commentId, isReply);
            });
        });
    },
    
    // Delete comment function
    async deleteComment(commentId, isReply = false) {
        // Validate inputs
        if (!commentId) {
            this.showNotification('Invalid comment ID', 'error');
            return;
        }
        
        // Confirm deletion
        if (!confirm("Are you sure you want to delete this comment? This action cannot be undone.")) {
            return;
        }
        
        try {
            // Disable button during deletion
            const button = document.querySelector(`[data-comment-id="${commentId}"]`);
            if (button) button.disabled = true;
            
            // Send delete request
            const response = await fetch(`/events/comment/${commentId}/delete/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.csrfToken || '',
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin'
            });
            
            // Handle response
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(errorText || 'Failed to delete comment');
            }
            
            // Remove comment from DOM
            this.removeCommentFromDOM(commentId, isReply);
            
            // Show success notification
            this.showNotification('Comment deleted successfully', 'success');
            
        } catch (error) {
            console.error('Comment deletion error:', error);
            this.showNotification(error.message || 'Error deleting comment', 'error');
        } finally {
            // Re-enable button
            const button = document.querySelector(`[data-comment-id="${commentId}"]`);
            if (button) button.disabled = false;
        }
    },
    
    // Remove comment from DOM
    removeCommentFromDOM(commentId, isReply) {
        const elementId = isReply ? `reply-${commentId}` : `comment-${commentId}`;
        const element = document.getElementById(elementId);
        
        if (element) {
            // If it's a reply, update parent comment's reply count
            if (isReply) {
                const parentContainer = element.closest('.replies-container');
                if (parentContainer) {
                    const parentId = parentContainer.id.split('-')[1];
                    this.updateRepliesCount(parentId, -1);
                }
            }
            
            // Remove the element
            element.remove();
        }
    },
    
    // Update replies count (placeholder - implement your specific logic)
    updateRepliesCount(parentCommentId, adjustment) {
        const replyCountElement = document.querySelector(`#comment-${parentCommentId} .reply-count`);
        if (replyCountElement) {
            let currentCount = parseInt(replyCountElement.textContent, 10) || 0;
            replyCountElement.textContent = Math.max(0, currentCount + adjustment);
        }
    },
    
    // Show notification (implement your preferred notification method)
    showNotification(message, type = 'info') {
        // Example using browser alert - replace with your preferred notification system
        if (type === 'error') {
            alert(`Error: ${message}`);
        } else {
            alert(message);
        }
    }
};

// Initialize when DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    CommentManager.init();
});