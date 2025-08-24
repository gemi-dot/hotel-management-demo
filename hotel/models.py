from django.db import models
from django.utils import timezone
from datetime import date
from django.utils.timezone import now


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

    guest = models.ForeignKey("Guest", on_delete=models.CASCADE, related_name="bookings")
    room = models.ForeignKey("Room", on_delete=models.CASCADE, related_name="bookings")

    #check_in = models.DateTimeField(auto_now_add=True)
    
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

    def __str__(self):
        return f"{self.guest.name} - Room {self.room.number}"

    # --- Price Calculation ---
    def compute_total_price(self):
        """Calculate total price based on room rate and number of days."""
        num_days = (self.check_out - self.check_in).days
        return self.room.price * num_days

    def save(self, *args, **kwargs):
        """Ensure total price is computed before saving."""
        if not self.total_price:
            self.total_price = self.compute_total_price()
        super().save(*args, **kwargs)

    # --- Payment Helpers ---
    def total_paid(self):
        """Total amount paid for this booking."""
        return sum(payment.amount for payment in self.payments.all())

    def is_fully_paid(self):
        """Check if booking is fully paid."""
        return self.total_paid() >= (self.total_price or 0)




    def update_payment_status(self, manual_override=False):
        today = now().date()  # Ensure today is a date object

        # Example comparison with proper type conversion
        if self.check_out.date() < today:  # Convert datetime to date
            self.payment_status = "overdue"
        elif self.total_paid() >= self.total_price:
            self.payment_status = "paid"
        elif self.total_paid() > 0:
            self.payment_status = "partial"
        else:
            self.payment_status = "pending"

        if manual_override:
            self.save(update_fields=["payment_status"])


    @property
    def status_display(self):
        if self.is_checked_in:
            return "Checked In"
        elif self.check_out < timezone.now().date():
            return "Checked Out"
        elif self.check_in > timezone.now().date():
            return "Upcoming"
        else:
            return "Pending"



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
        if self.booking.total_paid() + self.amount > self.booking.total_price:
            raise ValueError("Payment exceeds the total price for the booking.")
        super().save(*args, **kwargs)



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