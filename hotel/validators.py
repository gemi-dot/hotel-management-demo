"""
Validation utilities for the hotel management system.
Provides reusable validation functions and security helpers.
"""

import re
import bleach
from datetime import date, timedelta
from django.core.exceptions import ValidationError


def validate_name(name, min_length=2, max_length=100):
    """
    Validate and sanitize a name field.
    
    Args:
        name: The name to validate
        min_length: Minimum length required
        max_length: Maximum length allowed
    
    Returns:
        str: Cleaned and validated name
        
    Raises:
        ValidationError: If name is invalid
    """
    if not name:
        raise ValidationError("Name is required.")
    
    name = name.strip()
    
    if len(name) < min_length:
        raise ValidationError(f"Name must be at least {min_length} characters long.")
    
    if len(name) > max_length:
        raise ValidationError(f"Name cannot exceed {max_length} characters.")
    
    # Check for invalid characters (allow letters, spaces, hyphens, apostrophes)
    if not re.match(r"^[a-zA-Z\s\-'\.]+$", name):
        raise ValidationError("Name can only contain letters, spaces, hyphens, and apostrophes.")
    
    # Sanitize HTML/script injection
    name = bleach.clean(name, strip=True)
    
    return name.title()


def validate_phone_number(phone):
    """
    Validate and format a phone number.
    
    Args:
        phone: Phone number to validate
        
    Returns:
        str: Cleaned phone number
        
    Raises:
        ValidationError: If phone number is invalid
    """
    if not phone:
        return phone  # Phone is optional in many cases
    
    phone = phone.strip()
    
    # Remove all non-digit characters for validation
    phone_digits = re.sub(r'\D', '', phone)
    
    if len(phone_digits) < 10:
        raise ValidationError("Phone number must be at least 10 digits.")
    
    if len(phone_digits) > 15:
        raise ValidationError("Phone number cannot exceed 15 digits.")
    
    # Sanitize HTML
    phone = bleach.clean(phone, strip=True)
    
    return phone


def validate_date_range(start_date, end_date, min_days=1, max_days=90):
    """
    Validate a date range for bookings.
    
    Args:
        start_date: Start date
        end_date: End date
        min_days: Minimum number of days
        max_days: Maximum number of days
        
    Raises:
        ValidationError: If date range is invalid
    """
    if not start_date or not end_date:
        raise ValidationError("Both start and end dates are required.")
    
    if end_date <= start_date:
        raise ValidationError("End date must be after start date.")
    
    days_diff = (end_date - start_date).days
    
    if days_diff < min_days:
        raise ValidationError(f"Minimum duration is {min_days} day(s).")
    
    if days_diff > max_days:
        raise ValidationError(f"Maximum duration is {max_days} days.")


def sanitize_text_input(text, max_length=None, allow_html=False):
    """
    Sanitize text input to prevent XSS attacks.
    
    Args:
        text: Text to sanitize
        max_length: Maximum allowed length
        allow_html: Whether to allow basic HTML tags
        
    Returns:
        str: Sanitized text
        
    Raises:
        ValidationError: If text exceeds max_length
    """
    if not text:
        return text
    
    text = text.strip()
    
    if max_length and len(text) > max_length:
        raise ValidationError(f"Text cannot exceed {max_length} characters.")
    
    if allow_html:
        # Allow basic formatting tags
        allowed_tags = ['br', 'p', 'strong', 'em', 'u']
        text = bleach.clean(text, tags=allowed_tags, strip=True)
    else:
        # Strip all HTML
        text = bleach.clean(text, strip=True)
    
    return text


def validate_positive_number(value, min_value=0.01, max_value=999999):
    """
    Validate a positive number (for prices, amounts, etc.).
    
    Args:
        value: Number to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        float: Validated number
        
    Raises:
        ValidationError: If number is invalid
    """
    if value is None:
        raise ValidationError("Value is required.")
    
    if value < min_value:
        raise ValidationError(f"Value must be at least {min_value}.")
    
    if value > max_value:
        raise ValidationError(f"Value cannot exceed {max_value}.")
    
    return value


def check_room_availability(room, check_in, check_out, exclude_booking=None):
    """
    Check if a room is available for given dates.
    
    Args:
        room: Room instance
        check_in: Check-in date
        check_out: Check-out date
        exclude_booking: Booking to exclude from check (for updates)
        
    Returns:
        bool: True if available, False otherwise
        
    Raises:
        ValidationError: If room is not available with details
    """
    from .models import Booking  # Import here to avoid circular imports
    
    overlapping_bookings = Booking.objects.filter(
        room=room,
        check_in__lt=check_out,
        check_out__gt=check_in,
        status__in=['Reserved', 'Pending', 'Checked In']
    )
    
    if exclude_booking:
        overlapping_bookings = overlapping_bookings.exclude(pk=exclude_booking.pk)
    
    if overlapping_bookings.exists():
        conflicting_booking = overlapping_bookings.first()
        raise ValidationError(
            f"Room {room.number} is not available for the selected dates. "
            f"Conflict with existing booking from {conflicting_booking.check_in.date()} "
            f"to {conflicting_booking.check_out.date()}."
        )
    
    return True


# Security constants
ALLOWED_FILE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.pdf', '.doc', '.docx']
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def validate_file_upload(uploaded_file):
    """
    Validate uploaded files for security.
    
    Args:
        uploaded_file: Django uploaded file object
        
    Raises:
        ValidationError: If file is invalid or unsafe
    """
    if not uploaded_file:
        return
    
    # Check file size
    if uploaded_file.size > MAX_FILE_SIZE:
        raise ValidationError(f"File size cannot exceed {MAX_FILE_SIZE // 1024 // 1024}MB.")
    
    # Check file extension
    file_extension = uploaded_file.name.lower().split('.')[-1] if '.' in uploaded_file.name else ''
    if f'.{file_extension}' not in ALLOWED_FILE_EXTENSIONS:
        raise ValidationError(f"File type '.{file_extension}' is not allowed.")
    
    # Check for dangerous file names
    dangerous_patterns = ['../', '\\', '<script', 'javascript:', 'vbscript:']
    for pattern in dangerous_patterns:
        if pattern in uploaded_file.name.lower():
            raise ValidationError("File name contains unsafe characters.")


def validate_business_rules(booking_data):
    """
    Validate business-specific rules for bookings.
    
    Args:
        booking_data: Dictionary containing booking information
        
    Raises:
        ValidationError: If business rules are violated
    """
    guest = booking_data.get('guest')
    room = booking_data.get('room')
    check_in = booking_data.get('check_in')
    check_out = booking_data.get('check_out')
    
    # Example business rules (customize as needed)
    
    # Rule 1: Check-in must be at least 1 hour from now for same-day bookings
    if check_in and check_in == date.today():
        # You might want to add time validation here
        pass
    
    # Rule 2: Maximum advance booking period
    if check_in and check_in > date.today() + timedelta(days=365):
        raise ValidationError("Bookings cannot be made more than 1 year in advance.")
    
    # Rule 3: VIP room restrictions (example)
    if room and hasattr(room, 'room_type') and room.room_type == 'suite':
        if check_out and check_in and (check_out - check_in).days < 2:
            raise ValidationError("Suite bookings require a minimum stay of 2 nights.")
    
    # Rule 4: Capacity check (basic example)
    if room and guest:
        # This could be expanded to check actual guest count
        pass