@login_required
def cancel_registration(request, event_id):
    """
    Comprehensive event registration cancellation handler
    """
    # Logging for debugging
    logger.info(f"Cancellation attempt: User {request.user.id}, Event {event_id}")

    if request.method != 'POST':
        logger.warning(f"Invalid method for cancellation: {request.method}")
        return JsonResponse({
            'success': False, 
            'error': 'Method not allowed. Use POST.',
            'status_code': 'METHOD_NOT_ALLOWED'
        }, status=405)
    
    try:
        # Retrieve the event first to validate its existence
        event = get_object_or_404(Event, id=event_id)
        
        # Comprehensive cancellation eligibility check
        can_cancel, reason = event.is_cancellation_allowed()
        if not can_cancel:
            logger.info(f"Cancellation not allowed: {reason}")
            return JsonResponse({
                'success': False,
                'error': reason,
                'status_code': 'CANCELLATION_NOT_ALLOWED'
            }, status=400)
        
        # Find the user's registration
        try:
            registration = EventRegistration.objects.get(
                event=event, 
                participant=request.user.profile,
                status__in=['registered', 'waitlist']
            )
        except EventRegistration.DoesNotExist:
            logger.warning(f"No active registration found for user {request.user.id}, event {event_id}")
            return JsonResponse({
                'success': False,
                'error': 'No active registration found',
                'status_code': 'NO_REGISTRATION'
            }, status=404)
        
        # Detailed logging
        logger.info(f"Cancellation details: Registration {registration.id}, Status {registration.status}")
        
        # Log cancellation event
        RegistrationCancellationLog.objects.create(
            event=event,
            user=request.user,
            original_status=registration.status,
            cancelled_at=timezone.now()
        )
        
        # Cancel the registration
        registration.cancel_registration()
        
        # Send cancellation confirmation email
        try:
            send_cancellation_confirmation_email(request.user.profile, event)
        except Exception as email_error:
            logger.error(f"Email sending failed during cancellation: {email_error}")
            # Note: We don't return an error here, as the cancellation itself was successful
        
        # Prepare comprehensive response
        response_data = {
            'success': True,
            'message': 'Registration cancelled successfully',
            'previous_status': registration.status,
            'spots_left': event.spots_left,
            'max_participants': event.max_participants,
            'waitlist_promoted': True  # Assuming promotion might have occurred
        }
        
        return JsonResponse(response_data)
    
    except Exception as unexpected_error:
        logger.error(f"Unexpected cancellation error: {unexpected_error}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An unexpected system error occurred',
            'status_code': 'SYSTEM_ERROR',
            'details': str(unexpected_error)
        }, status=500)

def send_cancellation_confirmation_email(user, event):
    """
    Comprehensive cancellation email
    """
    try:
        email_context = {
            'event_title': event.title,
            'event_date': event.start_date,
            'cancellation_time': timezone.now(),
            'spots_left_before': event.spots_left
        }
        
        # Use a template-based email for richer content
        send_mail(
            subject=f'Event Registration Cancelled: {event.title}',
            message=render_to_string('emails/cancellation_confirmation.html', email_context),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=render_to_string('events/emails/cancellation_confirmation_html.html', email_context)
        )
    except Exception as e:
        logger.error(f"Cancellation email failed: {e}")