from django.contrib import admin
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Room, Booking, Payment

# ✅ Payment Inline inside Booking admin
class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ('payment_date',)
    can_delete = True


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('number', 'room_type', 'price', 'is_available')
    list_editable = ('is_available',)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'guest_name', 'room', 'check_in', 'check_out',
        'payment_status', 'total_price', 'total_paid_display', 'balance_due_display'
    )
    list_filter = ('payment_status',)
    search_fields = ('guest__name', 'room__number')
    readonly_fields = ('total_price', 'payment_status')
    inlines = [PaymentInline]

    def guest_name(self, obj):
        return obj.guest.name
    guest_name.short_description = 'Guest'

    def total_paid_display(self, obj):
        # Assumes you have a method total_paid() in Booking model
        return f'{obj.total_paid():.2f}' if hasattr(obj, 'total_paid') else '0.00'
    total_paid_display.short_description = 'Total Paid'

    def balance_due_display(self, obj):
        # Assumes you have a method or property balance_due in Booking model
        return f'{obj.balance_due:.2f}' if hasattr(obj, 'balance_due') else '0.00'
    balance_due_display.short_description = 'Balance Due'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('booking', 'amount', 'payment_method', 'payment_date')
    list_filter = ('payment_method',)
    search_fields = ('booking__guest__name', 'booking__room__number')


# ✅ Signal: Update payment status after saving a payment
@receiver(post_save, sender=Payment)
def update_booking_payment_status(sender, instance, **kwargs):
    booking = instance.booking
    booking.save()  # Triggers save method to recalculate payment_status
