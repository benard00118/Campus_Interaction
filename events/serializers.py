# events/serializers.py
from rest_framework import serializers
from django.utils import timezone
from .models import Event, EventCategory, EventRegistration, Comment


class EventCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = EventCategory
        fields = ['id', 'name', 'description']

    

# Update CommentSerializer to use ReplySerializer
class CommentSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    is_liked_by_user = serializers.SerializerMethodField()
    

    class Meta:
        model = Comment
        fields = ['id', 'content', 'user', 'created_at', 'updated_at',
                 'likes_count', 'is_liked_by_user', 'replies', 'level',
                 'is_edited', 'path']
        read_only_fields = ['user', 'created_at', 'updated_at', 'path',
                           'level', 'is_edited']

    def get_user(self, obj):
        return {
            'id': obj.user.id,
            'username': obj.user.user.username,
            'avatar': obj.user.avatar.url if obj.user.avatar else None
        }

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_is_liked_by_user(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.profile.id).exists()
        return False

class EventSerializer(serializers.ModelSerializer):
    category = EventCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=EventCategory.objects.all(),
        source='category',
        write_only=True,
        required=False
    )
    campus = serializers.SerializerMethodField()
    comments = CommentSerializer(many=True, read_only=True)
    reactions_count = serializers.SerializerMethodField()
    is_registered = serializers.SerializerMethodField()
    remaining_slots = serializers.SerializerMethodField()
    organizer_details = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ['id', 'category', 'category_id', 'title', 'description',
                 'event_type', 'start_date', 'end_date', 'location', 'image',
                 'max_participants', 'is_public', 'campus', 'content',
                 'attachments', 'comments', 'reactions_count', 'is_registered',
                 'remaining_slots', 'organizer_details']
        read_only_fields = ['organizer', 'reactions_count', 'is_registered', 'campus']
    
    def get_campus(self, obj):
        if obj.campus:
            return {
                'id': obj.campus.id,
                'name': obj.campus.campus.name if hasattr(obj.campus, 'campus') else None
            }
        return None
    
  
    def get_is_registered(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return EventRegistration.objects.filter(
                event=obj,
                participant=request.user.profile
            ).exists()
        return False

    def get_remaining_slots(self, obj):
        if obj.max_participants:
            registered = EventRegistration.objects.filter(event=obj).count()
            return max(0, obj.max_participants - registered)
        return None

    def get_organizer_details(self, obj):
        return {
            'id': obj.organizer.id,
            'username': obj.organizer.user.username,
            'avatar': obj.organizer.avatar.url if obj.organizer.avatar else None
        }

    def validate(self, data):
        # Validate dates
        if data.get('start_date') and data.get('end_date'):
            if data['start_date'] >= data['end_date']:
                raise serializers.ValidationError({
                    "end_date": "End date must be after start date."
                })
            if data['start_date'] < timezone.now():
                raise serializers.ValidationError({
                    "start_date": "Start date cannot be in the past."
                })

        # Validate event type specific fields
        event_type = data.get('event_type')
        if event_type == 'physical' and not data.get('location'):
            raise serializers.ValidationError({
                "location": "Location is required for physical events."
            })
        if event_type == 'text' and not data.get('content'):
            raise serializers.ValidationError({
                "content": "Content is required for text-based events."
            })

        # Validate max_participants
        if data.get('max_participants'):
            if data['max_participants'] < 1:
                raise serializers.ValidationError({
                    "max_participants": "Maximum participants must be at least 1."
                })

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['organizer'] = request.user.profile
        return super().create(validated_data)

class EventRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventRegistration
        fields = ['id', 'event', 'registration_date', 'attended']
        read_only_fields = ['registration_date', 'attended']

    def validate(self, data):
        event = data['event']
        request = self.context.get('request')
        
        # Check if registration is still open
        if event.start_date <= timezone.now():
            raise serializers.ValidationError("Registration is closed for this event.")

        # Check maximum participants
        if event.max_participants:
            current_registrations = EventRegistration.objects.filter(event=event).count()
            if current_registrations >= event.max_participants:
                raise serializers.ValidationError("Event has reached maximum participants.")

        # Check if user is already registered
        if EventRegistration.objects.filter(
            event=event,
            participant=request.user.profile
        ).exists():
            raise serializers.ValidationError("You are already registered for this event.")

        return data
    


class EventUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer specifically for updating events with controlled fields
    """
    # Add a status field if not already in the model
    status = serializers.ChoiceField(
        choices=['draft', 'published', 'canceled'], 
        required=False
    )

    # Add a special field to handle image explicitly
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Event
        fields = [
            'title', 
            'description', 
            'start_date', 
            'end_date', 
            'location', 
            'max_participants', 
            'is_public', 
            'status',  # Include status
            'event_type',
            'content',
            'image'
        ]
        extra_kwargs = {
            'image': {'required': False},
            'title': {'required': False},
            'description': {'required': False},
            # Allow partial updates
        }

    def update(self, instance, validated_data):
        """
        Custom update method to handle potential missing fields and preserve existing image
        """
        # Remove status if not in the model or validated_data
        if 'status' in validated_data:
            validated_data.pop('status')
        
        # Explicitly handle the image field
        if 'image' not in validated_data:
            # If no image is provided in the update, keep the existing image
            validated_data['image'] = instance.image
        elif validated_data['image'] is None:
            # If image is explicitly set to None, remove the image
            validated_data['image'] = ''
        
        return super().update(instance, validated_data)

    def to_internal_value(self, data):
        """
        Custom method to handle image preservation
        """
        # If image is not in the data, it means no image update is intended
        if 'image' not in data:
            # Temporarily add the existing image to preserve it
            data['image'] = self.instance.image if self.instance and self.instance.image else None
        
        return super().to_internal_value(data)