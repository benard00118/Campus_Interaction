from django.urls import path
from . import views

app_name = "forums"
urlpatterns = [
    path("", views.ForumListView.as_view(), name="forum_list"),
    path("<int:pk>/", views.ForumDetailView.as_view(), name="forum_detail"),
    path('create/', views.ForumCreateView.as_view(), name='forum_create'), 
    path("<int:forum_id>/join/", views.JoinForumView.as_view(), name="join_forum"),
    path("<int:forum_id>/manage_members/<int:user_id>/", views.ManageMembersView.as_view(), name="manage_members"), 
]