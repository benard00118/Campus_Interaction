import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.db import  DatabaseError, transaction
from django.db.models import  Max, Q, F
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, DeleteView, DetailView, ListView
from django.views.generic.edit import FormMixin
from .managers import *
from notifications.bulk import notify_all_users
from profiles.models import Profile
from .forms import CommentForm, EventForm, EventRegistrationForm
from .models import Comment, Event, EventRegistration
from django.urls import reverse
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
import logging



# Set up logging
logger = logging.getLogger(__name__)


class EventListView(LoginRequiredMixin, ListView):
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'
    paginate_by = 12

    def get_queryset(self):
        queryset = Event.objects.all().order_by('-start_date').prefetch_related('comments')
        status_filter = self.request.GET.get('status')
        campus_filter = self.request.GET.get('campus')

        if status_filter:
            now = timezone.now()
            if status_filter == 'upcoming':
                queryset = queryset.filter(start_date__gte=now)
            elif status_filter == 'ongoing':
                queryset = queryset.filter(start_date__lte=now, end_date__gte=now)
            elif status_filter == 'completed':
                queryset = queryset.filter(end_date__lt=now)

        if campus_filter:
            queryset = queryset.filter(campus__campus=campus_filter)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['campuses'] = Profile.objects.values_list('campus', flat=True).distinct()
        for event in context['events']:
            event.comments_count = event.comments.count()
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('HX-Request'):
            return render(self.request, 'events/partials/event_list_content.html', context)
        return super().render_to_response(context, **response_kwargs)

class EventDetailView(LoginRequiredMixin, FormMixin, DetailView):
    model = Event
    template_name = 'events/event_detail.html'
    context_object_name = 'event'
    pk_url_kwarg = 'event_id'
    form_class = CommentForm

    def get_object(self, queryset=None):
        """Get event with prefetched registrations for efficient counting"""
        if queryset is None:
            queryset = self.get_queryset()
            
        queryset = queryset.prefetch_related('registrations')
        return get_object_or_404(queryset, id=self.kwargs.get('event_id'))

    def get_registration_status(self, event, user_profile):
        """Get cached or fresh registration status"""
        cache_key = f'registration_status_{event.id}_{user_profile.id}'
        status = cache.get(cache_key)
        
        if not status:
            registration = EventRegistration.objects.filter(
                event=event,
                participant=user_profile,
                status__in=['registered', 'waitlist']
            ).first()

            status = {
                'is_registered': registration is not None,
                'registration': registration,
                'status': getattr(registration, 'status', None),
                'waitlist_position': getattr(registration, 'waitlist_position', None)
            }
            
            # Cache for 1 minute
            cache.set(cache_key, status, 60)
            
        return status

    def get_event_stats(self, event):
        """Get cached or fresh event statistics"""
        cache_key = f'event_stats_{event.id}'
        stats = cache.get(cache_key)
        
        if not stats:
            registered_count = event.registrations.filter(
                status='registered'
            ).count()
            
            waitlist_count = event.registrations.filter(
                status='waitlist'
            ).count()
            
            spots_left = (event.max_participants - registered_count 
                         if event.max_participants else None)
            
            stats = {
                'registered_count': registered_count,
                'waitlist_count': waitlist_count,
                'spots_left': spots_left,
                'is_full': (event.max_participants and 
                           registered_count >= event.max_participants),
                'has_waitlist': waitlist_count > 0,
                'total_participants': registered_count + waitlist_count
            }
            
            # Cache for 1 minute
            cache.set(cache_key, stats, 60)
            
        return stats

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.object
        user_profile = self.request.user.profile
        
        # Get registration status and event stats
        registration_status = self.get_registration_status(event, user_profile)
        event_stats = self.get_event_stats(event)
        participant=user_profile,
        # Create initial form data
        initial_form_data = {
            'name': self.request.user.get_full_name() or self.request.user.username,
            'email': self.request.user.email
        }

        context.update({
            # Registration status
            'user_registered': registration_status['is_registered'],
            'registration': registration_status['registration'],
            'registration_status': registration_status['status'],
            'waitlist_position': registration_status['waitlist_position'],
            
            # Event statistics
            'registered_count': event_stats['registered_count'],
            'waitlist_count': event_stats['waitlist_count'],
            'spots_left': event_stats['spots_left'],
            'is_full': event_stats['is_full'],
            'has_waitlist': event_stats['has_waitlist'],
            'total_participants': event_stats['total_participants'],
            
            # Forms and additional data
            'registration_form': EventRegistrationForm(initial=initial_form_data),
            'comment_form': self.get_form(),
            
            'comments': self.object.comments.all(),
            # Waitlist settings
            'is_waitlist_open': getattr(event, 'is_waitlist_open', True),
            'can_register': not event_stats['is_full'] or event.is_waitlist_open,
            
            # Additional context for template
            'show_waitlist_button': (
                event_stats['is_full'] and 
                event.is_waitlist_open and 
                not registration_status['is_registered']
            ),
            'show_register_button': (
                not event_stats['is_full'] and 
                not registration_status['is_registered']
            )
        })
        
        return context

    def post(self, request, *args, **kwargs):
        """Handle both AJAX registration requests and comment submissions"""
        self.object = self.get_object()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                # Handle registration through RegistrationManager
                manager = RegistrationManager(self.object, request.user)
                result = manager.register()
                
                # Clear relevant caches
                cache.delete(f'registration_status_{self.object.id}_{request.user.profile.id}')
                cache.delete(f'event_stats_{self.object.id}')
                
                return JsonResponse(result, 
                                  status=200 if result['success'] else 400)
            except Exception as e:
                logger.error(f"Registration error: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'error': 'An unexpected error occurred'
                }, status=500)
        
        # Handle comment form submission
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        """Handle valid comment form submission"""
        comment = form.save(commit=False)
        comment.event = self.object
        comment.author = self.request.user
        comment.save()
        return super().form_valid(form)

    def get_success_url(self):
        """Redirect URL after successful comment submission"""
        return reverse('event_detail', kwargs={'event_id': self.object.id})

class MultiStepEventCreateView(LoginRequiredMixin, CreateView):
    model = Event
    template_name = 'events/create_event.html'
    form_class = EventForm
    success_url = reverse_lazy('events:event_list')

    @transaction.atomic
    def form_valid(self, form):
        # Additional processing for multi-step form submission
        form.instance.organizer = self.request.user.profile
        form.instance.campus = self.request.user.profile.campus
        
        response = super().form_valid(form)
        
        # Optionally send notifications
        if form.cleaned_data.get('is_public'):
            notify_all_users("New Event Created")
        
        messages.success(self.request, "Event created successfully!")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Please check the form and try again.")
        print(form.errors)
        return super().form_invalid(form)

class CommentCreateView(LoginRequiredMixin, View):
    @transaction.atomic
    def post(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)
        form = CommentForm(request.POST)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if form.is_valid():
            comment = form.save(commit=False)
            comment.event = event
            comment.user = request.user.profile
            comment.save()

            if is_ajax:
                comment_html = render_to_string('events/partials/comment.html', {
                    'comment': comment,
                    'event': event
                }, request=request)
                return JsonResponse({
                    'status': 'success',
                    'comment_html': comment_html,
                    'comment_id': comment.id
                })
            
            messages.success(request, 'Comment added successfully!')
            return redirect('events:event_detail', event_id=event_id)
        
        if is_ajax:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid form data',
                'errors': form.errors
            }, status=400)
        
        messages.error(request, 'Please correct the errors below.')
        return redirect('events:event_detail', event_id=event_id)

        

class LoadMoreCommentsView(LoginRequiredMixin, View):
    def get(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)
        page = int(request.GET.get('page', 1))
        comments_per_page = 5

        comments = Comment.objects.filter(
            event=event
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

class CommentLikeToggleView(LoginRequiredMixin, View):
    def post(self, request, comment_id):
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

class EventDeleteView(LoginRequiredMixin, DeleteView):
    model = Event
    pk_url_kwarg = 'event_id'
    success_url = reverse_lazy('events:event_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.organizer.user != request.user and not request.user.is_staff:
            return JsonResponse({"status": "error", "message": "Permission denied"}, status=403)

        image_path = self.object.image.path if self.object.image else None
        self.object.delete()

        if image_path:
            try:
                default_storage.delete(image_path)
            except Exception as e:
                logger.error(f"Error deleting file {image_path}: {e}")
                return JsonResponse({
                    "status": "success",
                    "message": "Event deleted, but media file removal failed."
                }, status=500)

        messages.success(request, "Event deleted successfully.")
        return JsonResponse({"status": "success", "message": "Event deleted successfully."})

class CampusAutocompleteView(LoginRequiredMixin, View):
    def get(self, request):
        if 'term' in request.GET:
            query = request.GET.get('term')
            campuses = Profile.objects.filter(
                Q(campus__icontains=query)
            ).values('id', 'campus').distinct()[:10]

            results = [{
                'id': profile['id'],
                'label': profile['campus'],
                'value': profile['campus']
            } for profile in campuses]
            return JsonResponse(results, safe=False)

        return JsonResponse([], safe=False)
    
@login_required
def cancel_registration(request, event_id):
    """
    Handle comprehensive registration cancellation with advanced logic
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    try:
        # First get the event to ensure it exists
        event = get_object_or_404(Event, id=event_id)
        
        # Find the active registration
        registration = EventRegistration.objects.filter(
            event_id=event_id,
            participant=request.user.profile,
            status__in=['registered', 'waitlist']
        ).first()
        
        if not registration:
            return JsonResponse({
                'success': False,
                'error': 'No active registration found for this event'
            }, status=404)
        
        with transaction.atomic():
            # Store previous status for logging/response
            previous_status = registration.status
            
            # Completely delete the registration instead of just changing status
            registration.delete()
            
            # Trigger waitlist promotion logic
            _promote_from_waitlist(event)
            
            # Get updated spots count
            spots_remaining = event.spots_left or 0
            
            return JsonResponse({
                'success': True,
                'message': 'Registration cancelled and removed successfully',
                'previous_status': previous_status,
                'spots_left': spots_remaining,
                'max_participants': event.max_participants,
            })
            
    except Exception as e:
        logger.error(f"Registration cancellation error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred while cancelling registration'
        }, status=500)

def _promote_from_waitlist(event):
    """
    Promote participants from waitlist to registered status
    """
    # Get waitlisted registrations ordered by waitlist position
    waitlist_registrations = EventRegistration.objects.filter(
        event=event, 
        status='waitlist'
    ).order_by('waitlist_position')
    
    # Iterate through waitlist and promote if spots are available
    for registration in waitlist_registrations:
        # Check if there are spots left
        if event.spots_left and event.spots_left > 0:
            # Change status to registered
            registration.status = 'registered'
            registration.waitlist_position = None
            registration.save()
            
            # Send promotion notification (optional)
            _send_waitlist_promotion_email(registration)
        else:
            # No more spots available, stop promoting
            break

def _send_waitlist_promotion_email(registration):
    """
    Send email to promote from waitlist to registered
    """
    try:
        send_mail(
            subject=f"Waitlist Promotion - {registration.event.title}",
            message=render_to_string('events/emails/waitlist_promotion.html', {
                'registration': registration,
                'event': registration.event,
                'name': registration.name,
            }),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[registration.email],
            html_message=render_to_string('events/emails/waitlist_promotion.html', {
                'registration': registration,
                'event': registration.event,
                'name': registration.name,
            }),
        )
    except Exception as email_error:
        logger.error(f"Failed to send waitlist promotion email: {email_error}", exc_info=True)

@login_required
def register_event(request, event_id):
    """
    Enhanced event registration with improved error handling and flexibility
    """
    try:
        # Use select_for_update with nowait to prevent long-running locks
        with transaction.atomic():
            try:
                event = Event.objects.select_for_update(nowait=True).get(id=event_id)
            except DatabaseError:
                return JsonResponse({
                    'success': False,
                    'error': 'Event is currently being processed. Please try again in a moment.'
                }, status=409)
            
            user_profile = request.user.profile
            
            # Remove any existing registrations to allow re-registration
            EventRegistration.objects.filter(
                event=event, 
                participant=user_profile
            ).delete()
            
            # Create and validate form
            form = EventRegistrationForm(
                request.POST,
                event=event,
                user=request.user
            )
            
            if not form.is_valid():
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)
            
            # Determine registration status with atomic transaction
            try:
                with transaction.atomic():
                    # Refresh the event to get the most current state
                    event.refresh_from_db()
                    
                    # Count registered participants
                    registered_count = event.registrations.filter(status='registered').count()
                    
                    # Prepare registration
                    registration = form.save(commit=False)
                    registration.event = event
                    registration.participant = user_profile
                    registration.name = form.cleaned_data['name']
                    registration.email = form.cleaned_data['email']
                    
                    # Determine registration status
                    if event.max_participants is None:
                        registration.status = 'registered'
                    elif registered_count < event.max_participants:
                        registration.status = 'registered'
                    else:
                        registration.status = 'waitlist'
                        # Calculate waitlist position
                        registration.waitlist_position = (
                            event.registrations.filter(status='waitlist')
                            .aggregate(Max('waitlist_position'))['waitlist_position__max'] or 0
                        ) + 1
                    
                    # Save the registration
                    registration.save()
                    
                    # Send appropriate email
                    try:
                        if registration.status == 'registered':
                            send_mail(
                                subject=f"Registration Confirmed - {event.title}",
                                message=render_to_string('events/emails/registration_confirmation.html', {
                                    'registration': registration,
                                    'event': event,
                                    'name': registration.name,
                                }),
                                from_email=settings.DEFAULT_FROM_EMAIL,
                                recipient_list=[registration.email],
                                html_message=render_to_string('events/emails/registration_confirmation.html', {
                                    'registration': registration,
                                    'event': event,
                                    'name': registration.name,
                                }),
                            )
                        elif registration.status == 'waitlist':
                            send_mail(
                                subject=f"Waitlist Confirmation - {event.title}",
                                message=render_to_string('events/emails/waitlist_confirmation.html', {
                                    'registration': registration,
                                    'event': event,
                                    'name': registration.name,
                                    'waitlist_position': registration.waitlist_position,
                                }),
                                from_email=settings.DEFAULT_FROM_EMAIL,
                                recipient_list=[registration.email],
                                html_message=render_to_string('events/emails/waitlist_confirmation.html', {
                                    'registration': registration,
                                    'event': event,
                                    'name': registration.name,
                                    'waitlist_position': registration.waitlist_position,
                                }),
                            )
                    except Exception as email_error:
                        logger.error(f"Failed to send registration email: {email_error}", exc_info=True)
                    
                    # Return response
                    return JsonResponse({
                        'success': True,
                        'status': registration.status,
                        'message': ('Successfully registered' if registration.status == 'registered' 
                                    else f'Added to waitlist (Position: {registration.waitlist_position})'),
                        'waitlist_position': registration.waitlist_position,
                        'spots_left': event.spots_left
                    })
            
            except Exception as inner_error:
                logger.error(f"Registration processing error: {inner_error}", exc_info=True)
                return JsonResponse({
                    'success': False,
                    'error': 'Registration processing failed. Please try again.'
                }, status=500)
    
    except Exception as outer_error:
        logger.error(f"Registration error: {outer_error}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Registration failed. Please try again.'
        }, status=500)

