from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from .models import Forum, ForumMembership
from .forms import ForumForm
from feeds.models import Post
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class ForumListView(ListView):
    model = Forum
    template_name = "forums/forum_list.html"
    context_object_name = "forums"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Initialize total counters
        total_members = 0
        total_discussions = 0
        total_active_posts = 0
        for forum in context["forums"]:
            forum.members_count = forum.members.count()
            total_members += forum.members_count
            forum.discussions_count = forum.posts.count()
            total_discussions += forum.discussions_count
            forum.active_posts_count = forum.posts.filter(
                created_at__gte=timezone.now() - timedelta(days=30)
            ).count()

            # Add to total active posts count
            total_active_posts += forum.active_posts_count
            forum.members_count_display = self.format_count(forum.members_count)
            forum.discussions_count_display = self.format_count(forum.discussions_count)
            forum.active_posts_count_display = self.format_count(
                forum.active_posts_count
            )
        context["total_members_display"] = self.format_count(total_members)
        context["total_discussions_display"] = self.format_count(total_discussions)
        context["total_active_posts_display"] = self.format_count(total_active_posts)

        return context

    def format_count(self, count):
        """Format count as '1.2k' if over 1000."""
        if count >= 1000:
            return f"{count / 1000:.1f}k"
        return str(count)


class ForumDetailView(DetailView):
    model = Forum
    template_name = "forums/forum_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        forum = self.get_object()

        # Precompute members with their roles
        members_with_roles = [
            {
                "user": member,
                "role": ForumMembership.objects.filter(user=member, forum=forum)
                .first()
                .role,
            }
            for member in forum.members.all()
        ]

        # Precompute if the logged-in user is an admin in this forum
        user_is_admin = ForumMembership.objects.filter(
            user=self.request.user, forum=forum, role="admin"
        ).exists()

        context["members_with_roles"] = members_with_roles
        context["user_is_admin"] = user_is_admin
        return context


class JoinForumView(View):
    def post(self, request, forum_id):
        forum = get_object_or_404(Forum, id=forum_id)
        membership, created = ForumMembership.objects.get_or_create(
            user=request.user, forum=forum
        )
        return redirect("forums:forum_detail", pk=forum.id)


class ForumCreateView(LoginRequiredMixin, CreateView):
    model = Forum
    form_class = ForumForm
    template_name = "forums/forum_create.html"
    success_url = reverse_lazy("forums:forum_list")

    def form_valid(self, form):
        # Set the current user as the creator of the forum
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class ManageMembersView(LoginRequiredMixin, View):
    def post(self, request, forum_id, user_id):
        forum = get_object_or_404(Forum, id=forum_id)
        user_to_manage = get_object_or_404(User, id=user_id)
        membership = ForumMembership.objects.filter(
            user=user_to_manage, forum=forum
        ).first()

        # Check if the current user is an admin
        if not ForumMembership.objects.filter(
            user=request.user, forum=forum, role="admin"
        ).exists():
            messages.error(request, "You do not have permission to manage members.")
            return redirect("forums:forum_detail", pk=forum.id)

        action = request.POST.get("action")
        if action == "remove" and membership:
            membership.delete()
            messages.success(
                request, f"{user_to_manage.username} has been removed from the forum."
            )
        elif action == "make_admin" and membership:
            membership.role = "admin"
            membership.save()
            messages.success(request, f"{user_to_manage.username} is now an admin.")
        elif action == "revoke_admin" and membership:
            membership.role = "member"
            membership.save()
            messages.success(
                request,
                f"{user_to_manage.username}'s admin privileges have been revoked.",
            )
        else:
            messages.error(request, "Invalid action.")

        return redirect("forums:forum_detail", pk=forum.id)
