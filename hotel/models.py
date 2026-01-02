from django.db import models
from django.utils import timezone
from datetime import date
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.shortcuts import redirect
from django.db.models import Sum
from django.db import transaction
from decimal import Decimal


class Guest(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)  # Allow blank for optional phone
    address = models.TextField(blank=True, null=True)  # Allow blank for optional address
    date_of_birth = models.DateField(blank=True, null=True)  # Optional date of birth
    notes = models.TextField(blank=True, null=True)  # Optional notes about the guest

    def __str__(self):
        return self.name

class Room(models.Model):
    ROOM_TYPES = (
        ('single', 'Single'),
        ('double', 'Double'),
        ('suite', 'Suite'),
    )
    number = models.CharField(max_length=10)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES)
    capacity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"Room {self.number} ({self.room_type})"


class BookingManager(models.Manager):
    """Custom manager for Booking with utility methods."""
    
    def update_all_payment_statuses(self, queryset=None):
        """Bulk update payment statuses for multiple bookings."""
        if queryset is None:
            queryset = self.all()
        
        updated_count = 0
        with transaction.atomic():
            for booking in queryset.select_related('room', 'guest'):
                old_status = booking.payment_status
                booking.update_payment_status(manual_override=True)
                if old_status != booking.payment_status:
                    booking.save(update_fields=['payment_status'])
                    updated_count += 1
        
        return updated_count


class Booking(models.Model):
    PAYMENT_STATUSES = [
        ('pending', 'Pending'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

##
    class Meta:
        indexes = [
            models.Index(fields=['check_in', 'check_out'], name='booking_dates_idx'),
            
            models.Index(fields=['status'], name='booking_status_idx'),
            models.Index(fields=['payment_status'], name='payment_status_idx'),
            models.Index(fields=['room', 'check_in'], name='room_checkin_idx'),
            models.Index(fields=['guest', '-created_at'], name='guest_recent_idx'),
            models.Index(fields=['-created_at'], name='recent_bookings_idx'),
        ]   
###
    guest = models.ForeignKey("Guest", on_delete=models.CASCADE, related_name="bookings")
    room = models.ForeignKey("Room", on_delete=models.CASCADE, related_name="bookings")
    
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Checked In", "Checked In"),
        ("Checked Out", "Checked Out"),
        ("No Show", "No Show"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    check_in = models.DateTimeField()
    check_out = models.DateTimeField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    payment_status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUSES,
        default="pending"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_checked_in = models.BooleanField(default=False)  # Actual check-in flag
    checked_out_at = models.DateTimeField(blank=True, null=True)  # Timestamp for check-out

    objects = BookingManager()

    def __str__(self):
        return f"{self.guest.name} - Room {self.room.number}"

    # --- Price Calculation ---
    def compute_total_price(self):
        """Calculate total price based on room rate and number of days."""
        if not self.check_in or not self.check_out or not self.room:
            return Decimal('0.00')
        
        # Convert to dates if they are datetime objects
        check_in_date = self.check_in.date() if hasattr(self.check_in, 'date') else self.check_in
        check_out_date = self.check_out.date() if hasattr(self.check_out, 'date') else self.check_out
        
        num_days = (check_out_date - check_in_date).days
        if num_days <= 0:
            return Decimal('0.00')
        
        return Decimal(str(self.room.price)) * num_days
    
    @property
    def room_total(self):
        """Always recompute from dates (room only) - ensures never null."""
        return self.compute_total_price()

    @property
    def meal_total(self):
        """Sum of all meals linked to this booking."""
        total = self.meal_transactions.aggregate(total=Sum("total_price"))["total"]
        return total if total is not None else Decimal('0.00')

    @property
    def grand_total(self):
        """Room + Meals combined - ensures never null."""
        room_price = self.total_price if self.total_price is not None else self.compute_total_price()
        return room_price + self.meal_total
    
    @property
    def total_paid(self):
        """Sum of all payments linked to booking."""
        total = self.payments.aggregate(total=Sum("amount"))["total"]
        return total if total is not None else Decimal('0.00')
    
    def clean(self):
        """Ensure no overlapping bookings for the same room, respecting early checkouts."""
        overlapping_bookings = Booking.objects.filter(
            room=self.room,
            check_in__lt=self.check_out,
            check_out__gt=self.check_in,
        ).exclude(id=self.id).exclude(status="Checked Out")  # Ignore bookings already checked out

        if overlapping_bookings.exists():
            raise ValidationError(f"Room {self.room.number} is already booked for the selected dates.")

    def save(self, *args, **kwargs):
        # Always ensure total_price is calculated and never null
        self.total_price = self.compute_total_price()

        # Mark room as unavailable when booking is created
        if self.status in ["Pending", "Checked In"]:
            self.room.is_available = False
            self.room.save(update_fields=["is_available"])

        super().save(*args, **kwargs)

    def is_fully_paid(self):
        """Check if booking is fully paid."""
        return self.total_paid >= (self.total_price or 0)

    def update_payment_status(self, manual_override=False):
        """Update payment status based on current totals and dates."""
        today = now().date()
        
        # Get current totals with database-level consistency
        grand_total = self.grand_total
        total_paid = self.total_paid
        
        # Store old status for comparison
        old_status = self.payment_status
        
        # Calculate payment status based on amounts and dates
        if total_paid >= grand_total and grand_total > 0:
            self.payment_status = "paid"
        elif self.check_out.date() < today:
            if total_paid > 0:
                self.payment_status = "partial"
            else:
                self.payment_status = "overdue"
        elif total_paid > 0:
            self.payment_status = "partial"
        else:
            self.payment_status = "pending"

        # Only save if status actually changed and not in manual override mode
        if not manual_override and old_status != self.payment_status:
            self.save(update_fields=["payment_status"])
        
        return old_status != self.payment_status  # Return whether status changed

    def recalculate_all_totals(self):
        """Recalculate and update all totals for this booking atomically."""
        with transaction.atomic():
            # Recalculate room total from dates
            self.total_price = self.compute_total_price()
            
            # Update payment status based on new totals
            self.update_payment_status(manual_override=True)
            
            # Save both fields at once
            self.save(update_fields=["total_price", "payment_status"])
    
    def add_payment(self, amount, payment_method, transaction_id=None):
        """Add a payment to this booking with automatic balance update."""
        import uuid
        
        if not transaction_id:
            transaction_id = str(uuid.uuid4())
        
        with transaction.atomic():
            payment = Payment(
                booking=self,
                amount=amount,
                payment_method=payment_method,
                transaction_id=transaction_id
            )
            payment.save()  # This will automatically update payment status
            return payment

    @property
    def outstanding_balance(self):
        """Calculate the current outstanding balance."""
        return max(self.grand_total - self.total_paid, 0)
    
    @property
    def payment_percentage(self):
        """Calculate what percentage has been paid."""
        if self.grand_total > 0:
            return min((self.total_paid / self.grand_total) * 100, 100)
        return 100 if self.total_paid == 0 else 0

    def can_add_charges(self):
        """Check if additional charges can be added to this booking."""
        # Don't allow charges to completed/checked out bookings unless still within grace period
        if self.status == "Checked Out":
            # Allow charges within 24 hours of checkout
            if self.checked_out_at:
                from datetime import timedelta
                grace_period = self.checked_out_at + timedelta(hours=24)
                return now() <= grace_period
            return False
        return self.status in ["Pending", "Checked In"]

    def add_payment_note(self, note):
        """Add a note about payment status changes for audit trail."""
        # This could be expanded to create a PaymentNote model for tracking
        pass

    def booking_checkout(request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id)

        # Mark booking as checked out
        booking.status = "Checked Out"
        booking.save(update_fields=["status"])

        # Update payment status too (in case final payment happened at checkout)
        booking.update_payment_status()

        messages.success(request, f"Booking {booking.id} has been checked out.")
        return redirect("booking_list")

    @property
    def status_display(self):
        """Compute display status consistently."""
        current_time = now()
        if self.is_checked_in:
            return "Checked In"
        elif self.check_out < current_time:
            return "Checked Out"
        elif self.check_in > current_time:
            return "Upcoming"
        elif self.status == "No Show":
            return "No Show"
        else:
            return "Pending"

    class Meta:
        # Add database indexes for better performance
        indexes = [
            # Most common query patterns
            models.Index(fields=['check_in', 'check_out'], name='booking_dates_idx'),
            models.Index(fields=['status'], name='booking_status_idx'),
            models.Index(fields=['payment_status'], name='payment_status_idx'),
            models.Index(fields=['room', 'check_in'], name='room_checkin_idx'),
            models.Index(fields=['guest', '-created_at'], name='guest_recent_idx'),
            models.Index(fields=['-created_at'], name='recent_bookings_idx'),
        ]


class Payment(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(default=timezone.now)
    payment_method = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"Payment {self.transaction_id} - {self.amount}"

    def save(self, *args, **kwargs):
        """Validate payment amount and update booking payment status atomically."""
        if self.amount <= 0:
            raise ValueError("Payment amount must be greater than zero.")
        
        # Use atomic transaction to ensure data consistency
        with transaction.atomic():
            # Check if payment exceeds remaining balance (before saving)
            current_paid = self.booking.total_paid
            if self.pk:  # If updating existing payment, subtract old amount
                try:
                    old_payment = Payment.objects.get(pk=self.pk)
                    current_paid -= old_payment.amount
                except Payment.DoesNotExist:
                    pass  # New payment
            
            remaining_balance = self.booking.grand_total - current_paid
            
            # Allow payment up to remaining balance + small tolerance for rounding
            # This prevents overpayment while allowing exact balance payments
            tolerance = Decimal('0.01')  # 1 cent tolerance for rounding differences
            if self.amount > (remaining_balance + tolerance):
                raise ValueError(
                    f"Payment of ${self.amount} exceeds remaining balance of ${remaining_balance:.2f}"
                )
            
            super().save(*args, **kwargs)
            
            # ✅ Always update booking payment status after payment is saved
            self.booking.update_payment_status()

    def delete(self, *args, **kwargs):
        """Update booking payment status when payment is deleted atomically."""
        with transaction.atomic():
            booking = self.booking
            super().delete(*args, **kwargs)
            booking.update_payment_status()

class MealTransaction(models.Model):
    CATEGORY_CHOICES = [
        ('Breakfast', 'Breakfast'),
        ('Lunch', 'Lunch'),
        ('Dinner', 'Dinner'),
        ('Snacks', 'Snacks'),
    ]
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="meal_transactions")
    meal_name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Breakfast')
    quantity = models.PositiveIntegerField(default=1)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    transaction_date = models.DateTimeField(auto_now_add=True)    

    def save(self, *args, **kwargs):
        """Calculate total price and update booking payment status atomically."""
        # Validate that we can add charges to this booking
        if not self.booking.can_add_charges():
            raise ValidationError(
                f"Cannot add charges to booking {self.booking.id} - booking is completed or past grace period"
            )
        
        # Use atomic transaction to ensure consistency
        with transaction.atomic():
            # Automatically calculate total price before saving
            self.total_price = self.quantity * self.price_per_unit
            super().save(*args, **kwargs)
            
            # ✅ Update booking payment status when meal charges change
            self.booking.update_payment_status()

    def delete(self, *args, **kwargs):
        """Update booking payment status when meal is deleted atomically."""
        with transaction.atomic():
            booking = self.booking
            super().delete(*args, **kwargs)
            booking.update_payment_status()

    def __str__(self):
        return f"{self.meal_name} - {self.quantity} x ${self.price_per_unit} = ${self.total_price}"