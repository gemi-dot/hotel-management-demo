import re
import bleach
from datetime import date, datetime, timedelta
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.validators import RegexValidator, EmailValidator
from .models import Room, Booking, Payment, Guest, MealTransaction


class GuestForm(forms.ModelForm):
    """Enhanced Guest form with comprehensive validation and security."""
    
    class Meta:
        model = Guest
        fields = ['name', 'email', 'phone', 'address', 'date_of_birth', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter full name (minimum 2 characters)',
                'maxlength': 100
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter email address'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1-555-123-4567',
                'pattern': r'[\+]?[\d\-\(\)\s]+',
                'title': 'Enter a valid phone number'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter address',
                'rows': 3,
                'maxlength': 500
            }),
            'date_of_birth': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Additional notes (optional)',
                'rows': 3,
                'maxlength': 1000
            }),
        }

    def clean_name(self):
        """Validate and sanitize guest name."""
        name = self.cleaned_data.get('name')
        if not name:
            raise ValidationError("Name is required.")
        
        # Remove extra whitespace
        name = name.strip()
        
        # Check minimum length
        if len(name) < 2:
            raise ValidationError("Name must be at least 2 characters long.")
        
        # Check for invalid characters (allow letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", name):
            raise ValidationError("Name can only contain letters, spaces, hyphens, and apostrophes.")
        
        # Sanitize HTML/script injection
        name = bleach.clean(name, strip=True)
        
        return name.title()  # Capitalize properly
    
    def clean_email(self):
        """Validate email uniqueness and format."""
        email = self.cleaned_data.get('email')
        if not email:
            raise ValidationError("Email is required.")
        
        email = email.lower().strip()
        
        # Check if email already exists (excluding current instance)
        existing_guest = Guest.objects.filter(email=email)
        if self.instance.pk:
            existing_guest = existing_guest.exclude(pk=self.instance.pk)
        
        if existing_guest.exists():
            raise ValidationError("A guest with this email address already exists.")
        
        return email
    
    def clean_phone(self):
        """Validate and format phone number."""
        phone = self.cleaned_data.get('phone')
        if not phone:
            return phone  # Phone is optional
        
        # Remove all non-digit characters for validation
        phone_digits = re.sub(r'\D', '', phone)
        
        # Check minimum length
        if len(phone_digits) < 10:
            raise ValidationError("Phone number must be at least 10 digits.")
        
        # Check maximum length
        if len(phone_digits) > 15:
            raise ValidationError("Phone number cannot exceed 15 digits.")
        
        # Sanitize HTML
        phone = bleach.clean(phone.strip(), strip=True)
        
        return phone
    
    def clean_address(self):
        """Validate and sanitize address."""
        address = self.cleaned_data.get('address')
        if not address:
            return address  # Address is optional
        
        address = address.strip()
        
        # Check maximum length
        if len(address) > 500:
            raise ValidationError("Address cannot exceed 500 characters.")
        
        # Sanitize HTML/script injection
        address = bleach.clean(address, strip=True)
        
        return address
    
    def clean_date_of_birth(self):
        """Validate date of birth."""
        dob = self.cleaned_data.get('date_of_birth')
        if not dob:
            return dob  # DOB is optional
        
        today = date.today()
        
        # Check if date is in the future
        if dob > today:
            raise ValidationError("Date of birth cannot be in the future.")
        
        # Check for reasonable age limits (must be at least 1 year old, max 120 years)
        min_date = today - timedelta(days=365 * 120)  # 120 years ago
        max_date = today - timedelta(days=365)  # 1 year ago
        
        if dob < min_date:
            raise ValidationError("Please enter a valid date of birth.")
        
        if dob > max_date:
            raise ValidationError("Guest must be at least 1 year old.")
        
        return dob
    
    def clean_notes(self):
        """Validate and sanitize notes."""
        notes = self.cleaned_data.get('notes')
        if not notes:
            return notes
        
        notes = notes.strip()
        
        # Check maximum length
        if len(notes) > 1000:
            raise ValidationError("Notes cannot exceed 1000 characters.")
        
        # Sanitize HTML/script injection but allow basic formatting
        allowed_tags = ['br', 'p', 'strong', 'em']
        notes = bleach.clean(notes, tags=allowed_tags, strip=True)
        
        return notes


class RoomForm(forms.ModelForm):
    """Enhanced Room form with validation."""
    
    class Meta:
        model = Room
        fields = ['number', 'room_type', 'capacity', 'price', 'is_available']
        widgets = {
            'number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 101, A-203, Suite-1',
                'maxlength': 10
            }),
            'room_type': forms.Select(attrs={'class': 'form-select'}),
            'capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Maximum guests (1-10)',
                'min': 1,
                'max': 10
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Price per night',
                'min': 0.01,
                'step': 0.01
            }),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_number(self):
        """Validate room number uniqueness."""
        number = self.cleaned_data.get('number')
        if not number:
            raise ValidationError("Room number is required.")
        
        number = number.strip().upper()
        
        # Check format (alphanumeric, hyphens, and spaces allowed)
        if not re.match(r'^[A-Z0-9\-\s]+$', number):
            raise ValidationError("Room number can only contain letters, numbers, hyphens, and spaces.")
        
        # Check uniqueness
        existing_room = Room.objects.filter(number=number)
        if self.instance.pk:
            existing_room = existing_room.exclude(pk=self.instance.pk)
        
        if existing_room.exists():
            raise ValidationError("A room with this number already exists.")
        
        return number
    
    def clean_capacity(self):
        """Validate room capacity."""
        capacity = self.cleaned_data.get('capacity')
        if capacity is None:
            raise ValidationError("Capacity is required.")
        
        if capacity < 1:
            raise ValidationError("Capacity must be at least 1.")
        
        if capacity > 10:
            raise ValidationError("Capacity cannot exceed 10 guests.")
        
        return capacity
    
    def clean_price(self):
        """Validate room price."""
        price = self.cleaned_data.get('price')
        if price is None:
            raise ValidationError("Price is required.")
        
        if price <= 0:
            raise ValidationError("Price must be greater than 0.")
        
        if price > 999999:
            raise ValidationError("Price seems unreasonably high. Please verify.")
        
        return price


class BookingForm(forms.ModelForm):
    """Enhanced Booking form with comprehensive validation."""
    
    class Meta:
        model = Booking
        fields = ['guest', 'room', 'check_in', 'check_out']
        widgets = {
            'guest': forms.Select(attrs={'class': 'form-select'}),
            'room': forms.Select(attrs={'class': 'form-select'}),
            'check_in': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'check_out': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
        }
    
    def clean_check_in(self):
        """Validate check-in date."""
        check_in = self.cleaned_data.get('check_in')
        if not check_in:
            raise ValidationError("Check-in date is required.")
        
        today = date.today()
        
        # Check if check-in is in the past (allow same day)
        if check_in < today:
            raise ValidationError("Check-in date cannot be in the past.")
        
        # Check if check-in is too far in the future (1 year max)
        max_advance = today + timedelta(days=365)
        if check_in > max_advance:
            raise ValidationError("Check-in date cannot be more than 1 year in advance.")
        
        return check_in
    
    def clean_check_out(self):
        """Validate check-out date."""
        check_out = self.cleaned_data.get('check_out')
        if not check_out:
            raise ValidationError("Check-out date is required.")
        
        today = date.today()
        
        # Check if check-out is too far in the future (1 year max)
        max_advance = today + timedelta(days=366)
        if check_out > max_advance:
            raise ValidationError("Check-out date cannot be more than 1 year in advance.")
        
        return check_out
    
    def clean(self):
        """Cross-field validation for booking dates and room availability."""
        cleaned_data = super().clean()
        guest = cleaned_data.get('guest')
        room = cleaned_data.get('room')
        check_in = cleaned_data.get('check_in')
        check_out = cleaned_data.get('check_out')
        
        # Validate date relationship
        if check_in and check_out:
            if check_out <= check_in:
                raise ValidationError("Check-out date must be after check-in date.")
            
            # Check minimum stay (at least 1 night)
            if (check_out - check_in).days < 1:
                raise ValidationError("Minimum stay is 1 night.")
            
            # Check maximum stay (90 days max)
            if (check_out - check_in).days > 90:
                raise ValidationError("Maximum stay is 90 days.")
        
        # Check room availability
        if room and check_in and check_out:
            overlapping_bookings = Booking.objects.filter(
                room=room,
                check_in__lt=check_out,
                check_out__gt=check_in,
                status__in=['Pending', 'Checked In']  # Only active bookings
            )
            
            # Exclude current booking if editing
            if self.instance.pk:
                overlapping_bookings = overlapping_bookings.exclude(pk=self.instance.pk)
            
            if overlapping_bookings.exists():
                conflicting_booking = overlapping_bookings.first()
                raise ValidationError(
                    f"Room {room.number} is not available for the selected dates. "
                    f"Conflict with booking from {conflicting_booking.check_in.date()} "
                    f"to {conflicting_booking.check_out.date()}."
                )
        
        # Check guest capacity
        if room and guest:
            # This is a basic check - you might want to add more sophisticated logic
            # based on the number of guests in a party
            pass
        
        return cleaned_data


class PaymentForm(forms.ModelForm):
    """Enhanced Payment form with validation."""
    
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('online', 'Online Payment'),
    ]
    
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHODS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Payment
        fields = ['amount', 'payment_method', 'transaction_id']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter payment amount',
                'min': 0.01,
                'step': 0.01
            }),
            'transaction_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter transaction ID',
                'maxlength': 100
            }),
        }
    
    def clean_amount(self):
        """Validate payment amount."""
        amount = self.cleaned_data.get('amount')
        if amount is None:
            raise ValidationError("Payment amount is required.")
        
        if amount <= 0:
            raise ValidationError("Payment amount must be greater than 0.")
        
        if amount > 999999:
            raise ValidationError("Payment amount seems too high. Please verify.")
        
        return amount
    
    def clean_transaction_id(self):
        """Validate transaction ID uniqueness."""
        transaction_id = self.cleaned_data.get('transaction_id')
        if not transaction_id:
            raise ValidationError("Transaction ID is required.")
        
        transaction_id = transaction_id.strip()
        
        # Sanitize input
        transaction_id = bleach.clean(transaction_id, strip=True)
        
        # Check uniqueness
        existing_payment = Payment.objects.filter(transaction_id=transaction_id)
        if self.instance.pk:
            existing_payment = existing_payment.exclude(pk=self.instance.pk)
        
        if existing_payment.exists():
            raise ValidationError("A payment with this transaction ID already exists.")
        
        return transaction_id


class MealTransactionForm(forms.ModelForm):
    """Enhanced Meal Transaction form with validation."""
    
    class Meta:
        model = MealTransaction
        fields = ['meal_name', 'category', 'quantity', 'price_per_unit']
        widgets = {
            'meal_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter meal/item name',
                'maxlength': 255
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Quantity (1-50)',
                'min': 1,
                'max': 50
            }),
            'price_per_unit': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Price per unit',
                'min': 0.01,
                'step': 0.01
            }),
        }
    
    def clean_meal_name(self):
        """Validate and sanitize meal name."""
        meal_name = self.cleaned_data.get('meal_name')
        if not meal_name:
            raise ValidationError("Meal name is required.")
        
        meal_name = meal_name.strip()
        
        if len(meal_name) < 2:
            raise ValidationError("Meal name must be at least 2 characters long.")
        
        # Sanitize HTML
        meal_name = bleach.clean(meal_name, strip=True)
        
        return meal_name
    
    def clean_quantity(self):
        """Validate meal quantity."""
        quantity = self.cleaned_data.get('quantity')
        if quantity is None:
            raise ValidationError("Quantity is required.")
        
        if quantity < 1:
            raise ValidationError("Quantity must be at least 1.")
        
        if quantity > 50:
            raise ValidationError("Quantity cannot exceed 50 items.")
        
        return quantity
    
    def clean_price_per_unit(self):
        """Validate price per unit."""
        price = self.cleaned_data.get('price_per_unit')
        if price is None:
            raise ValidationError("Price per unit is required.")
        
        if price <= 0:
            raise ValidationError("Price per unit must be greater than 0.")
        
        if price > 9999:
            raise ValidationError("Price per unit seems too high. Please verify.")
        
        return price