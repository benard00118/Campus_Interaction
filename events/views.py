import logging
from notifications.bulk import notify_all_users
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
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
from time import sleep
from django.db import transaction, DatabaseError
from django.db.models import F, Q, Max
from django.views import View
from django.utils.decorators import method_decorator




# Set up logging
logger = logging.getLogger(__name__)

# views.py
from django.views.generic import ListView, DetailView, CreateView, DeleteView
from django.views.generic.edit import FormMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.db import transaction
from django.contrib import messages

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_profile = self.request.user.profile
        registration = EventRegistration.objects.filter(
            event=self.object,
            participant=user_profile,
            status__in=['registered', 'waitlist']
        ).first()

        context.update({
            'user_registered': registration is not None,
            'registration': registration,
            'comments': self.object.comments.all(),
            'form': EventRegistrationForm(initial={
                'name': self.request.user.get_full_name() or self.request.user.username,
                'email': self.request.user.email
            }),
            'spots_left': self.object.spots_left,
            'is_waitlist_open': getattr(self.object, 'is_waitlist_open', True)
        })
        return context

    def post(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return register_for_event(request, self.get_object().id)
        return super().post(request, *args, **kwargs)

class EventCreateView(LoginRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = 'events/create_event.html'
    success_url = reverse_lazy('events:event_list')

    @transaction.atomic
    def form_valid(self, form):
        form.instance.organizer = self.request.user.profile
        form.instance.campus = self.request.user.profile.campus
        response = super().form_valid(form)
        
        if form.cleaned_data.get('is_public'):
            notify_all_users("New Event")
        
        messages.success(self.request, "Event created successfully!")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Invalid form submission.")
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

class CommentDeleteView(LoginRequiredMixin, DeleteView):
    model = Comment
    pk_url_kwarg = 'comment_id'

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.user != request.user.profile:
            return JsonResponse({
                'status': 'error',
                'message': 'You do not have permission to delete this comment'
            }, status=403)

        self.object.delete()
        return JsonResponse({
            'status': 'success',
            'message': 'Comment deleted successfully'
        })

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
# Update the registration view to handle name validation properly




class RegistrationManager:
    """
    Handles event registration operations with proper concurrency control
    """
    LOCK_TIMEOUT = 3  # seconds
    MAX_RETRIES = 3
    RETRY_DELAY = 0.5  # seconds

    def __init__(self, event, user):
        self.event = event
        self.user = user
        self.cache_key = f'registration_lock_{event.id}'

    def register(self):
        """
        Handle registration with proper locking and retry mechanism
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                with transaction.atomic():
                    # Get event with select_for_update with a short timeout
                    event = Event.objects.select_for_update(
                        nowait=True,
                        skip_locked=True
                    ).get(id=self.event.id)

                    # Check for existing registration
                    if self._check_existing_registration():
                        return {
                            'success': False,
                            'error': 'Already registered for this event'
                        }

                    # Validate event status
                    self._validate_event(event)

                    # Get current counts atomically
                    registration_info = self._get_registration_counts(event)
                    
                    # Create registration
                    registration = self._create_registration(
                        event, 
                        registration_info['is_full']
                    )

                    # Clear relevant cache
                    self._clear_cache(event)

                    return {
                        'success': True,
                        'status': registration.status,
                        'message': ('Added to waitlist' if registration_info['is_full'] 
                                  else 'Registration successful'),
                        'waitlist_position': registration.waitlist_position
                    }

            except DatabaseError as e:
                if attempt == self.MAX_RETRIES - 1:
                    logger.error(f"Final retry failed: {str(e)}")
                    return {
                        'success': False,
                        'error': 'Registration system temporarily unavailable'
                    }
                sleep(self.RETRY_DELAY * (2 ** attempt))  # Exponential backoff

    def _check_existing_registration(self):
        """Check if user is already registered"""
        return EventRegistration.objects.filter(
            participant=self.user.profile,
            event_id=self.event.id,
            status__in=['registered', 'waitlist']
        ).exists()

    def _validate_event(self, event):
        """Validate event registration conditions"""
        if event.registration_closed or (
            event.start_date and event.end_date < timezone.now()
        ):
            raise ValidationError("Registration for this event has closed.")

    def _get_registration_counts(self, event):
        """Get current registration counts atomically"""
        registered_count = EventRegistration.objects.filter(
            event=event,
            status='registered'
        ).count()

        return {
            'registered_count': registered_count,
            'is_full': event.max_participants and registered_count >= event.max_participants
        }

    def _create_registration(self, event, is_full):
        """Create new registration with proper status"""
        registration = EventRegistration(
            event=event,
            participant=self.user.profile,
            name=self.user.profile.name,
            email=self.user.email,
            status='waitlist' if is_full else 'registered'
        )

        if is_full:
            # Get next waitlist position atomically
            last_position = EventRegistration.objects.filter(
                event=event,
                status='waitlist'
            ).aggregate(Max('waitlist_position'))['waitlist_position__max'] or 0
            registration.waitlist_position = last_position + 1

        registration.save()
        return registration

    def _clear_cache(self, event):
        """Clear relevant cache keys"""
        cache.delete_many([
            f'event_status_{event.id}',
            f'registration_count_{event.id}',
            f'waitlist_count_{event.id}'
        ])

class WaitlistManager:
    """
    Handles waitlist operations with proper concurrency control
    """
    def __init__(self, event):
        self.event = event
        self.cache_key = f'waitlist_lock_{event.id}'

    def process_cancellation(self, registration):
        """
        Handle registration cancellation and waitlist promotion
        """
        try:
            with transaction.atomic():
                # Lock the event for updating
                event = Event.objects.select_for_update(
                    nowait=True
                ).get(id=self.event.id)

                was_registered = registration.status == 'registered'
                
                # Store position for reordering
                old_position = registration.waitlist_position
                
                # Cancel registration
                registration.delete()

                # If it was a registered spot, try to promote from waitlist
                if was_registered:
                    self._promote_next_in_line(event)
                elif old_position:
                    # Reorder waitlist after cancellation
                    self._reorder_waitlist(event, old_position)

                # Clear cache
                self._clear_cache(event)

                return {
                    'success': True,
                    'message': 'Registration cancelled successfully'
                }

        except DatabaseError as e:
            logger.error(f"Error in cancellation: {str(e)}")
            return {
                'success': False,
                'error': 'Unable to process cancellation'
            }

    def _promote_next_in_line(self, event):
        """
        Promote the next person from waitlist to registered
        """
        next_in_line = EventRegistration.objects.filter(
            event=event,
            status='waitlist'
        ).order_by('waitlist_position').select_for_update().first()

        if next_in_line:
            next_in_line.status = 'registered'
            next_in_line.waitlist_position = None
            next_in_line.save()

            # Send notification
            self._send_promotion_notification(next_in_line)
            
            # Reorder remaining waitlist
            self._reorder_waitlist(event, next_in_line.waitlist_position)

    def _reorder_waitlist(self, event, start_position):
        """
        Reorder waitlist positions starting from given position
        """
        with transaction.atomic():
            waitlist_entries = EventRegistration.objects.filter(
                event=event,
                status='waitlist',
                waitlist_position__gt=start_position
            ).order_by('waitlist_position').select_for_update()

            for i, entry in enumerate(waitlist_entries, start_position):
                entry.waitlist_position = i
                entry.save(update_fields=['waitlist_position'])

    def _clear_cache(self, event):
        """Clear relevant cache keys"""
        cache.delete_many([
            f'event_status_{event.id}',
            f'registration_count_{event.id}',
            f'waitlist_count_{event.id}'
        ])

# Updated view function using the managers
@login_required
@require_http_methods(["POST"])
def register_for_event(request, event_id):
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

@login_required
@require_http_methods(["POST"])
def cancel_registration(request, event_id):
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

# Update the email sending function to handle name properly
def send_registration_email(registration):
    """Send registration confirmation or waitlist email to participant."""
    try:
        if not registration.name or not registration.email:
            raise ValueError("Registration must have both name and email")

        subject = f"Registration Update - {registration.event.title}"
        
        context = {
            'registration': registration,
            'event': registration.event,
            'name': registration.name,
            'status': registration.get_status_display(),
            'waitlist_position': registration.waitlist_position if registration.status == 'waitlist' else None
        }

        template = ('events/emails/registration_confirmation.html' 
                   if registration.status == 'registered' 
                   else 'events/emails/waitlist_confirmation.html')
        
        html_message = render_to_string(template, context)
        plain_message = strip_tags(html_message)

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[registration.email],
            html_message=html_message,
            fail_silently=False
        )

        logger.info(f"Registration email sent successfully to {registration.email} for event {registration.event.title}")

    except Exception as e:
        logger.error(f"Error sending registration email to {registration.email} for event {registration.event.title}: {e}")
        raise