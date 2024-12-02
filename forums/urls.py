from django.urls import path
from . import views

app_name = "forums"
urlpatterns = [
    path("", views.ForumListView.as_view(), name="forum_list"),
    path("<int:pk>/", views.ForumDetailView.as_view(), name="forum_detail"),
    path("create/", views.ForumCreateView.as_view(), name="forum_create"),
    path("<int:forum_id>/join/", views.JoinForumView.as_view(), name="join_forum"),
    path("<int:forum_id>/leave/", views.JoinForumView.as_view(), name="leave_forum"),
    path(
        "<int:forum_id>/manage_members/<int:user_id>/",
        views.ManageMembersView.as_view(),
        name="manage_members",
    ),
    path(
        "post/<int:post_id>/delete/", views.PostDeleteView.as_view(), name="post_delete"
    ),
    path("post/<int:post_id>/like/", views.LikePostView.as_view(), name="like_post"),
    path(
        "<int:forum_id>/create-post/",
        views.CreatePostView.as_view(),
        name="create_post",
    ),
    path(
        "forum/<int:forum_id>/post/<int:post_id>/",
        views.post_detail,
        name="post_detail",
    ),
    path("search/posts/", views.search_posts, name="search_posts"),
    path(
        "post/<int:post_id>/add_comment/",
        views.add_comment_to_post,
        name="add_comment_to_post",
    ),
    path(
        "comments/<int:comment_id>/reply/",
        views.reply_to_comment,
        name="reply_to_comment",
    ),
    path("comments/<int:comment_id>/like/", views.like_comment, name="like_comment"),
    path(
        "post/<int:post_id>/check_updates/",
        views.check_post_updates,
        name="check_post_updates",
    ),
    path(
        "toggle-post-approval/<int:post_id>/",
        views.toggle_post_approval,
        name="toggle_post_approval",
    ),
    path('comments/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    path("forum/<int:forum_id>/drafts/", views.drafts_page, name="drafts_page"),
]