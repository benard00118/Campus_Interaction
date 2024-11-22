# events/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from . import api_views
from .views import (
    EventListView,
    EventDetailView,
    EventCreateView,
    CommentCreateView,
    CommentLikeToggleView,
    EventDeleteView,
    CampusAutocompleteView,
    LoadMoreCommentsView,
    CommentDeleteView,
    EventRegistrationView,
    EventCancellationView,
    EventStatusView,
    WaitlistPositionView,
)

# Create a router for the main viewset
router = routers.DefaultRouter()
router.register(r'events', api_views.EventViewSet, basename='event')

# Create a nested router for comments
event_router = routers.NestedDefaultRouter(router, r'events', lookup='event')
event_router.register(r'comments', api_views.CommentViewSet, basename='event-comments')

app_name = 'events'

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    path('api/', include(event_router.urls)),
    path('api/events/<int:pk>/update/', 
         api_views.EventViewSet.as_view({'patch': 'partial_update'}), 
         name='event-update'),
    path('api/events/<int:pk>/status/', 
         api_views.EventViewSet.as_view({'post': 'update_event_status'}), 
         name='event-status-update'),
    path('api/event/<int:event_id>/status/', 
         EventStatusView.as_view(), 
         name='event_status'),
    path('api/event/<int:event_id>/waitlist/', 
         WaitlistPositionView.as_view(), 
         name='waitlist_position'),

    # Main event URLs
    path('', EventListView.as_view(), name='event_list'),
    path('<int:event_id>/', EventDetailView.as_view(), name='event_detail'),
    path('create/', EventCreateView.as_view(), name='create_event'),
    path('<int:event_id>/delete/', EventDeleteView.as_view(), name='delete_event'),
    
    # Registration URLs
    path('event/<int:event_id>/register/', 
         EventRegistrationView.as_view(), 
         name='register'),
    path('event/<int:event_id>/cancel/', 
         EventCancellationView.as_view(), 
         name='cancel'),

    # Comment URLs
    path('<int:event_id>/comment/', CommentCreateView.as_view(), name='add_comment'),
    path('comment/<int:comment_id>/like/', CommentLikeToggleView.as_view(), name='toggle_comment_like'),
    path('<int:event_id>/comments/', LoadMoreCommentsView.as_view(), name='load_more_comments'),
    path('comment/<int:comment_id>/delete/', CommentDeleteView.as_view(), name='delete_comment'),

    # Utility URLs
    path('university/autocomplete/', CampusAutocompleteView.as_view(), name='university_autocomplete'),
    path('select2/', include('django_select2.urls')),
]