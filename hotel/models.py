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

    def __str__(self):
        return f"{self.guest.name} - Room {self.room.number}"

    # --- Price Calculation ---
    def compute_total_price(self):
        """Calculate total price based on room rate and number of days."""
        num_days = (self.check_out - self.check_in).days
        return self.room.price * num_days
    

    @property
    def room_total(self):
        """Always recompute from dates (room only)."""
        return self.compute_total_price()

    @property
    def meal_total(self):
        """Sum of all meals linked to this booking."""
        return self.meal_transactions.aggregate(total=Sum("total_price"))["total"] or 0

    @property
    def grand_total(self):
        """Room + Meals combined."""
        return (self.total_price or 0) + self.meal_total
    
    @property
    def total_paid(self):
        """Sum of all payments linked to booking."""
        return self.payments.aggregate(total=Sum("amount"))["total"] or 0
    
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
        

        if not self.total_price:
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
        today = now().date()

        if self.total_paid >= self.grand_total:
            self.payment_status = "paid"
        elif self.check_out.date() < today:
            if self.total_paid > 0:
                self.payment_status = "partial"
            else:
                self.payment_status = "overdue"
        elif self.total_paid > 0:
            self.payment_status = "partial"
        else:
            self.payment_status = "pending"

        if not manual_override:
            self.save(update_fields=["payment_status"])


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
        """Validate payment amount before saving."""
        if self.amount <= 0:
            raise ValueError("Payment amount must be greater than zero.")
        
        if self.booking.total_paid + self.amount > self.booking.grand_total:
            raise ValueError("Payment exceeds the total price for the booking.")
        
        super().save(*args, **kwargs)

    # ✅ always keep payment_status in sync after payment
        self.booking.update_payment_status()

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
        # Automatically calculate total price before saving
        self.total_price = self.quantity * self.price_per_unit
        super().save(*args, **kwargs)