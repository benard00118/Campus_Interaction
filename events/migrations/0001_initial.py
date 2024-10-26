# Generated by Django 5.1.2 on 2024-10-26 14:00

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(help_text='Enter the event title.', max_length=200)),
                ('description', models.TextField(help_text='Include the university details in this description.')),
                ('event_type', models.CharField(choices=[('physical', 'Physical Event'), ('text', 'Text-Based Event')], default='physical', max_length=10)),
                ('start_date', models.DateTimeField()),
                ('end_date', models.DateTimeField()),
                ('location', models.CharField(blank=True, help_text='Event location (optional for text-based events).', max_length=200, null=True)),
                ('image', models.ImageField(blank=True, null=True, upload_to='event_images/')),
                ('max_participants', models.PositiveIntegerField(blank=True, help_text='Maximum number of participants.', null=True)),
                ('is_public', models.BooleanField(default=True)),
                ('content', models.TextField(blank=True, help_text='Content for text-based events', null=True)),
                ('attachments', models.FileField(blank=True, help_text='Optional attachments for text-based events', null=True, upload_to='event_attachments/')),
            ],
        ),
        migrations.CreateModel(
            name='EventCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Enter the event category name.', max_length=100)),
                ('description', models.TextField(blank=True, help_text='Brief description of the category.')),
            ],
            options={
                'verbose_name_plural': 'Event Categories',
            },
        ),
        migrations.CreateModel(
            name='University',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('code', models.CharField(default='default_code', max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('level', models.PositiveIntegerField(default=0)),
                ('is_edited', models.BooleanField(default=False)),
                ('path', models.TextField(db_index=True, default='', editable=False)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='replies', to='events.comment')),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='events.event')),
            ],
            options={
                'ordering': ['path'],
            },
        ),
        migrations.AddField(
            model_name='event',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='events', to='events.eventcategory'),
        ),
        migrations.AddField(
            model_name='event',
            name='university',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='events.university'),
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_event_organizer', models.BooleanField(default=False)),
                ('university', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='events.university')),
                ('user', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('object_id', models.PositiveIntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('read', models.BooleanField(default=False)),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='events.userprofile')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CommentLike',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('comment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='events.comment')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='events.userprofile')),
            ],
            options={
                'unique_together': {('user', 'comment')},
            },
        ),
        migrations.AddField(
            model_name='comment',
            name='likes',
            field=models.ManyToManyField(related_name='liked_comments', through='events.CommentLike', to='events.userprofile'),
        ),
        migrations.AddField(
            model_name='comment',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_comments', to='events.userprofile'),
        ),
        migrations.CreateModel(
            name='EventRegistration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('registration_date', models.DateTimeField(auto_now_add=True)),
                ('attended', models.BooleanField(default=False)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='events.event')),
                ('participant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='events.userprofile')),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('event', 'participant'), name='unique_event_participant')],
            },
        ),
        migrations.CreateModel(
            name='EventReaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reaction_type', models.CharField(choices=[('like', '👍'), ('love', '❤️'), ('laugh', '😄'), ('wow', '😮'), ('sad', '😢')], max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reactions', to='events.event')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='events.userprofile')),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('event', 'user', 'reaction_type'), name='unique_event_user_reaction')],
            },
        ),
    ]
