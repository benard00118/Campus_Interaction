import logging
from notifications.bulk import notify_all_users
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.core.files.storage import default_storage
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_http_methods
from profiles.models import Profile
from .models import Event, EventRegistration, Comment
from .forms import EventForm, CommentForm, EventRegistrationForm
from .serializers import  CommentSerializer
import json
from django.core.paginator import EmptyPage, InvalidPage
from django.template.loader import render_to_string
from django.db.models import Count
from django.utils.html import strip_tags
from django.core.mail import send_mail
from django.db import transaction
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden
from django.conf import settings
from django.db.models import Max
from django.core.cache import cache
import logging
from django.db import transaction, DatabaseError
from django.db.models import F, Q
from django.core.exceptions import ValidationError
from django.utils import timezone
from time import sleep


# Set up logging
logger = logging.getLogger(__name__)

# events/views.py

@login_required
def event_list(request):
    status_filter = request.GET.get('status')
    campus_filter = request.GET.get('campus')

    # Fetch all events and related data
    events = Event.objects.all().order_by('-start_date').prefetch_related('comments')

    # Apply status filter if present
    if status_filter:
        now = timezone.now()
        if status_filter == 'upcoming':
            events = events.filter(start_date__gte=now)
        elif status_filter == 'ongoing':
            events = events.filter(start_date__lte=now, end_date__gte=now)
        elif status_filter == 'completed':
            events = events.filter(end_date__lt=now)
    
    # Apply campus filter if present
    if campus_filter:
        events = events.filter(campus__campus=campus_filter)

    # Get unique campus values for the filter form
    campuses = Profile.objects.values_list('campus', flat=True).distinct()

    # Pagination setup
    paginator = Paginator(events, 12)  # Show 12 events per page
    page = request.GET.get('page')
    events = paginator.get_page(page)

    # Add comments count for each event
    for event in events:
        event.comments_count = event.comments.count()

    context = {
        'events': events,
        'campuses': campuses,
    }

    # If it's an HTMX request, return only the events partial
    if request.headers.get('HX-Request'):
        return render(request, 'events/partials/event_list_content.html', context)
    
    # Otherwise return the full template
    return render(request, 'events/event_list.html', context)

@login_required
def event_detail(request, event_id):
    """Display event details and handle registration."""
    event = get_object_or_404(Event, id=event_id)
    user_profile = request.user.profile
    
    # Get current registration status
    registration = EventRegistration.objects.filter(
        event=event,
        participant=user_profile,
        status__in=['registered', 'waitlist']
    ).first()
    comments = event.comments.all()
    comment_form = CommentForm()
    user_registered = registration is not None
    
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Delegate to register_for_event view
        return register_for_event(request, event_id)
    
    context = {
        'event': event,
        'user_registered': user_registered,
        'registration': registration,
        'comment_form': comment_form,
        'comments': comments,
        'form': EventRegistrationForm(initial={
            'name': request.user.get_full_name() or request.user.username,
            'email': request.user.email
        }),
        'spots_left': event.spots_left,  # Fixed
        'is_waitlist_open': event.is_waitlist_open if hasattr(event, 'is_waitlist_open') else True  # Fixed
    }
    return render(request, 'events/event_detail.html', context)


@login_required
@transaction.atomic
def create_event(request):
    user_profile = get_object_or_404(Profile, user=request.user)
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)

        if form.is_valid():
            try:
                event = form.save(commit=False)
                event.organizer = user_profile
                event.campus = user_profile.campus
                event.save()
                isPublic = form.cleaned_data['is_public']
                if isPublic == True:
                    notify_all_users("New Event") # notify all users for upcoming event if made public
                messages.success(request, "Event created successfully!")
                return redirect('events:event_list')
            except Exception as e:
                messages.error(request, f"An error occurred while saving the event: {e}")
        else:
            messages.error(request, "Invalid form submission.")
            print(form.errors)  # Print form errors to console for debugging
    else:
        form = EventForm()

    return render(request, 'events/create_event.html', {'form': form})
@login_required
@require_POST
@require_http_methods(["POST"])
def add_comment(request, event_id):
    """Add a new comment to an event."""
    try:
        # Get the event
        event = get_object_or_404(Event, id=event_id)

        # Create a form instance with the POST data
        form = CommentForm(request.POST)

        # Check if it's an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if form.is_valid():
            # Create comment instance but don't save yet
            comment = form.save(commit=False)
            comment.event = event
            comment.user = request.user.profile  # Assuming you have a profile relation

            # Save the comment
            comment.save()

            if is_ajax:
                # Render the comment HTML
                comment_html = render_to_string('events/partials/comment.html', {
                    'comment': comment,
                    'event': event
                }, request=request)

                return JsonResponse({
                    'status': 'success',
                    'comment_html': comment_html,
                    'comment_id': comment.id
                })
            else:
                messages.success(request, 'Comment added successfully!')
                return redirect('events:event_detail', event_id=event_id)
        else:
            if is_ajax:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid form data',
                    'errors': form.errors
                }, status=400)
            else:
                messages.error(request, 'Please correct the errors below.')
                return redirect('events:event_detail', event_id=event_id)

    except Exception:
        # Log the generic error message
        logger.error("Unexpected error occurred in add_comment view", exc_info=True)
        
        # Return a generic error message to the user
        generic_error_message = 'An unexpected error occurred. Please try again later.'
        if is_ajax:
            return JsonResponse({
                'status': 'error',
                'message': generic_error_message
            }, status=500)
        else:
            messages.error(request, generic_error_message)
            return redirect('events:event_detail', event_id=event_id)


@login_required
@require_http_methods(["DELETE"])
def delete_comment(request, comment_id):
    """Delete a comment """
    try:
        # Attempt to fetch the comment
        comment = get_object_or_404(Comment, id=comment_id)
        
        # Check if the user is the owner of the comment
        if comment.user != request.user.profile:
            return JsonResponse({
                'status': 'error',
                'message': 'You do not have permission to delete this comment'
            }, status=403)
        
        # Delete the comment
        comment.delete()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Comment deleted successfully'
        }, status=200)
        
    except Comment.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Comment does not exist'
        }, status=404)
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred while deleting the comment'
        }, status=500)

@login_required
def load_more_comments(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    page = int(request.GET.get('page', 1))
    comments_per_page = 5

    comments = Comment.objects.filter(
        event=event,
    ).select_related(
        'user__user'
    ).prefetch_related(
        'replies'
    ).order_by('-created_at')

    paginator = Paginator(comments, comments_per_page)

    try:
        comments_page = paginator.page(page)
    except (EmptyPage, InvalidPage):
        return JsonResponse({'comments_html': '', 'has_next': False})

    comments_html = render_to_string(
        'events/partials/comments_pagination.html',
        {'comments': comments_page, 'event': event},
        request=request
    )

    return JsonResponse({
        'comments_html': comments_html,
        'has_next': comments_page.has_next()
    })
@login_required
@require_POST
def toggle_comment_like(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if request.user.profile in comment.likes.all():
        comment.likes.remove(request.user.profile)
        is_liked = False
    else:
        comment.likes.add(request.user.profile)
        is_liked = True
    
    return JsonResponse({
        'status': 'success',
        'likes_count': comment.likes.count(),
        'is_liked': is_liked
        
    
    })

@login_required
@require_http_methods(["POST", "DELETE"])
@transaction.atomic
def delete_event(request, event_id):
    # Fetch the event or return 404 if it doesn't exist
    event = get_object_or_404(Event, id=event_id)

    # Permission check
    if event.organizer.user != request.user and not request.user.is_staff:
        return JsonResponse({"status": "error", "message": "Permission denied"}, status=403)

    # Attempt to delete image if exists
    image_path = event.image.path if event.image else None
    event.delete()  # Delete event from the database

    # Delete associated media file if it exists
    if image_path:
        try:
            default_storage.delete(image_path)
        except Exception as e:
            logger.error(f"Error deleting file {image_path}: {e}")
            return JsonResponse({
                "status": "success",
                "message": "Event deleted, but media file removal failed."
            }, status=500)

    # Use Django messages for UI feedback and return JSON response
    messages.success(request, "Event deleted successfully.")
    return JsonResponse({"status": "success", "message": "Event deleted successfully."})


@login_required
def campus_autocomplete(request):
    if 'term' in request.GET:
        query = request.GET.get('term')

        # Query for campus using Profile model
        campuses = Profile.objects.filter(
            Q(campus__icontains=query)
        ).values('id', 'campus').distinct()[:10]

        # Format the results to return campus data
        results = [{'id': profile['id'], 'label': profile['campus'], 'value': profile['campus']} for profile in campuses]
        return JsonResponse(results, safe=False)

    return JsonResponse([], safe=False)

# Update the registration view to handle name validation properly
# events/views.py
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError

class EventRegistrationView(View):
    """
    Handles event registration with proper concurrency control
    """
    @method_decorator(login_required)
    def post(self, request, event_id):
        try:
            event = Event.objects.get(id=event_id)
            manager = RegistrationManager(event, request.user)
            result = manager.register()
            
            return JsonResponse(result, 
                              status=200 if result['success'] else 400)
        except Event.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Event not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'An unexpected error occurred'
            }, status=500)

class EventCancellationView(View):
    """
    Handles event registration cancellation
    """
    @method_decorator(login_required)
    def post(self, request, event_id):
        try:
            event = Event.objects.get(id=event_id)
            registration = EventRegistration.objects.get(
                event=event,
                participant=request.user.profile,
                status__in=['registered', 'waitlist']
            )
            
            manager = WaitlistManager(event)
            result = manager.process_cancellation(registration)
            
            return JsonResponse(result, 
                              status=200 if result['success'] else 400)
        except (Event.DoesNotExist, EventRegistration.DoesNotExist):
            return JsonResponse({
                'success': False,
                'error': 'Registration not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Cancellation error: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'An unexpected error occurred'
            }, status=500)

class EventStatusView(View):
    """
    Handles event status checks
    """
    @method_decorator(login_required)
    def get(self, request, event_id):
        try:
            event = Event.objects.get(id=event_id)
            
            # Try to get cached status first
            cache_key = f'event_status_{event_id}'
            status_data = cache.get(cache_key)
            
            if not status_data:
                # Get user's registration if exists
                registration = EventRegistration.objects.filter(
                    event=event,
                    participant=request.user.profile
                ).first()
                
                # Count registrations
                registered_count = EventRegistration.objects.filter(
                    event=event,
                    status='registered'
                ).count()
                
                waitlist_count = EventRegistration.objects.filter(
                    event=event,
                    status='waitlist'
                ).count()
                
                status_data = {
                    'success': True,
                    'total_spots': event.max_participants,
                    'spots_left': (event.max_participants - registered_count 
                                 if event.max_participants else None),
                    'registered_count': registered_count,
                    'waitlist_count': waitlist_count,
                    'is_full': (event.max_participants and 
                               registered_count >= event.max_participants),
                    'user_status': {
                        'is_registered': False,
                        'status': None,
                        'waitlist_position': None
                    }
                }
                
                if registration:
                    status_data['user_status'] = {
                        'is_registered': True,
                        'status': registration.status,
                        'waitlist_position': (registration.waitlist_position 
                                           if registration.status == 'waitlist' 
                                           else None)
                    }
                
                # Cache for 1 minute
                cache.set(cache_key, status_data, 60)
            
            return JsonResponse(status_data)
            
        except Event.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Event not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error getting event status: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Unable to get event status'
            }, status=500)

class WaitlistPositionView(View):
    """
    Handles waitlist position checks
    """
    @method_decorator(login_required)
    def get(self, request, event_id):
        try:
            event = get_object_or_404(Event, id=event_id)
            
            registration = EventRegistration.objects.get(
                event=event,
                participant=request.user.profile,
                status='waitlist'
            )
            
            return JsonResponse({
                'success': True,
                'position': registration.waitlist_position,
                'total_waitlist': EventRegistration.objects.filter(
                    event=event,
                    status='waitlist'
                ).count()
            })
            
        except EventRegistration.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Not on waitlist'
            }, status=404)
        except Exception as e:
            logger.error(f"Error checking waitlist position: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Unable to check waitlist position'
            }, status=500)

