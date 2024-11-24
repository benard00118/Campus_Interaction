from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.views import View
from datetime import timedelta
from django.utils import timezone

class Forum(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(max_length=500, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField(User, through='ForumMembership', related_name='forums')
    display_picture = models.ImageField(upload_to='forum_dps/', blank=True, null=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Add the creator as an admin member
        ForumMembership.objects.get_or_create(
            user=self.created_by, 
            forum=self, 
            defaults={'role': 'admin'}
        )

    def __str__(self):
        return self.name
    def member_count(self):
        return self.members.count()
    # Check if forum is 'new' (created within the last 7 days)
    def is_new(self):
        return self.created_at >= timezone.now() - timedelta(days=7)

    # Check if forum is 'active' (has posts within the last 30 days)
    def is_active(self):
        # Assuming your Post model has a `created_at` field
        last_post = self.posts.last()
        if last_post:
            return last_post.created_at >= timezone.now() - timedelta(days=30)
        return False

class ForumMembership(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('member', 'Member'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    forum = models.ForeignKey('Forum', on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')  # New field

    class Meta:
        unique_together = ('user', 'forum')

class ForumCreateView(LoginRequiredMixin, CreateView):
    model = Forum
    template_name = 'forums/forum_form.html'
    fields = ['name', 'description']
    success_url = reverse_lazy('forum_list')  # Redirect to the forum list after creation

    def form_valid(self, form):
        # Set the current user as the creator of the forum
        form.instance.created_by = self.request.user
        return super().form_valid(form)