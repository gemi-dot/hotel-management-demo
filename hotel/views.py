

from datetime import datetime, timedelta

from datetime import date
from django.utils.timezone import now

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from django.utils.timezone import now
import uuid

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.views.decorators.http import require_POST

from .models import Room, Booking, Payment
from .forms import RoomForm, BookingForm, PaymentForm

from django.db.models import Prefetch
import uuid

from .models import Booking

from .forms import GuestForm
from .models import Guest
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from datetime import date  # ← make sure this line is here

from .models import Booking, Payment

from .models import MealTransaction, Booking
from .forms import MealTransactionForm

# hotel/views.py
from django.shortcuts import render, redirect, get_object_or_404
from .models import Booking, Payment
from .forms import PaymentForm

from django.utils import timezone
from django.core.paginator import Paginator





def payment_create(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)

    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.booking = booking
            payment.save()
            return redirect("booking_detail", pk=booking.pk)
    else:
        form = PaymentForm()

    return render(request, "hotel/payment_form.html", {
        "form": form,
        "booking": booking
    })

# =======================
# 🔹 DASHBOARD
# =======================
@login_required
def dashboard(request):
    # ✅ Use related_name 'payments'
    bookings = Booking.objects.prefetch_related('payments').all()

    total_bookings = bookings.count()
    total_rooms = Room.objects.count()

    # Compute revenue and payment statuses
    total_revenue = 0
    paid_bookings = 0
    partial_bookings = 0
    pending_bookings = 0

    for booking in bookings:
        total_paid = sum(p.amount for p in booking.payments.all())  # ✅ Correct usage
        if total_paid >= booking.total_price:
            paid_bookings += 1
        elif total_paid > 0:
            partial_bookings += 1
        else:
            pending_bookings += 1
        total_revenue += total_paid  # ✅ Move inside the loop

    stats = [
        {"title": "Total Bookings", "count": total_bookings, "bg": "primary"},
        {"title": "Total Rooms", "count": total_rooms, "bg": "info"},
        {"title": "Paid Bookings", "count": paid_bookings, "bg": "success"},
        {"title": "Pending Payments", "count": pending_bookings, "bg": "warning"},
        {"title": "Total Revenue", "count": f"₱{total_revenue:,.2f}", "bg": "dark"},
    ]

    # Filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    room_id = request.GET.get('room')
    customer = request.GET.get('customer')

    recent_bookings = Booking.objects.select_related('room', 'guest').order_by('-check_in')

    if start_date:
        recent_bookings = recent_bookings.filter(check_in__gte=start_date)
    if end_date:
        recent_bookings = recent_bookings.filter(check_out__lte=end_date)
    if room_id:
        recent_bookings = recent_bookings.filter(room_id=room_id)
    if customer:
        recent_bookings = recent_bookings.filter(guest__name__icontains=customer)  # ✅ Correct guest filter

    recent_bookings = recent_bookings[:10]
    rooms = Room.objects.all()

    return render(request, 'hotel/dashboard.html', {
        "stats": stats,
        "recent_bookings": recent_bookings,
        "rooms": rooms,
        "total_revenue": total_revenue,
        "today": timezone.now().date(),
    })

# =======================
# 🔹 ROOMS
# =======================
@login_required
def room_list(request):
    rooms = Room.objects.all()
    return render(request, 'hotel/room_list.html', {'rooms': rooms})

@login_required
def room_create(request):
    form = RoomForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('room_list')
    return render(request, 'hotel/room_form.html', {'form': form})

@login_required
def room_edit(request, pk):
    room = get_object_or_404(Room, pk=pk)
    form = RoomForm(request.POST or None, instance=room)
    if form.is_valid():
        form.save()
        return redirect('room_list')
    return render(request, 'hotel/room_form.html', {'form': form})

@login_required
def room_delete(request, pk):
    room = get_object_or_404(Room, pk=pk)
    room.delete()
    return redirect('room_list')

def available_rooms(request):
    rooms = Room.objects.filter(is_available=True)
    return render(request, 'hotel/available_rooms.html', {'rooms': rooms})

def vacant_rooms(request):
    today = timezone.now().date()
    start_date = request.GET.get('start_date', today)
    end_date = request.GET.get('end_date', today)

    booked = Booking.objects.filter(
        Q(check_in__lte=end_date) & Q(check_out__gte=start_date)
    ).values_list('room_id', flat=True)

    available_rooms = Room.objects.exclude(id__in=booked)

    return render(request, 'hotel/vacant_rooms.html', {
        'rooms': available_rooms,
        'start_date': start_date,
        'end_date': end_date,
    })

# =======================
# 🔹 BOOKINGS
# =======================


@login_required
def booking_list(request):
    bookings = Booking.objects.select_related('guest', 'room').all().order_by('-check_in')

    today = date.today()
    for booking in bookings:
        # Update payment status dynamically
        booking.update_payment_status()


       # Determine booking status (do not overwrite "Checked Out")
        if booking.status != "Checked Out":
            if booking.is_checked_in:
                booking.status = "Checked In"
            elif booking.check_out.date() < today:
                booking.status = "No Show"
            elif booking.check_in == today and not booking.is_checked_in:
                booking.status = "Pending"
            else:
                booking.status = "Upcoming"

            # Save the updated status to the database
            booking.save(update_fields=["status"]) 

     

    paginator = Paginator(bookings, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'hotel/booking_list.html', {'bookings': page_obj})

@login_required
def booking_detail(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    today = date.today()

    if request.method == "POST":
        # Update check-in status
        booking.is_checked_in = bool(request.POST.get("is_checked_in"))

        # Update payment status (manual override)
        new_payment_status = request.POST.get("payment_status", booking.payment_status)
        booking.payment_status = new_payment_status
        booking.update_payment_status(manual_override=True)

        # Save the updated status
        booking.save()
        messages.success(request, f"Booking #{booking.pk} updated successfully!")
        return redirect("booking_detail", pk=booking.pk)

    # Dynamically compute status only if it's not already "Checked Out"
    if booking.status != "Checked Out":
        if booking.is_checked_in:
            if booking.check_out.date() > today:
                booking.status = "Checked In"
            else:
                booking.status = "Checked Out"
        else:
            if booking.check_in.date() > today:
                booking.status = "Pending"
            elif booking.check_in.date() <= today <= booking.check_out.date():
                booking.status = "Pending"
            elif booking.check_out.date() < today:
                booking.status = "No Show"

    payments = Payment.objects.filter(booking=booking).order_by('-payment_date')

    return render(request, "hotel/booking_detail.html", {
        "booking": booking,
        "payments": payments,
    })

@login_required
def booking_create(request):
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)

            # compute total price (make sure your model has this method)
            booking.total_price = booking.compute_total_price()  
            booking.save()

            messages.success(request, "Booking created successfully!")
            return redirect('booking_detail', pk=booking.pk)
        else:
            messages.error(request, "There was a problem with the booking form. Please check the fields.")
    else:
        form = BookingForm()

    # Always load guests and available rooms for dropdowns
    guests = Guest.objects.all()
    rooms = Room.objects.filter(is_available=True)

    return render(request, 'hotel/booking_form.html', {
        'form': form,
        'guests': guests,
        'rooms': rooms,
    })


@login_required
def booking_edit(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    if request.method == 'POST':
        form = BookingForm(request.POST, instance=booking)
        if form.is_valid():
            form.save()
            # Check if the payment status was manually changed
            manual_override = 'payment_status' in form.changed_data
            booking.update_payment_status(manual_override=manual_override)
            return redirect('booking_list')  # Redirect back to the booking list
    else:
        form = BookingForm(instance=booking)
    return render(request, 'hotel/booking_edit.html', {'form': form, 'booking': booking})

@login_required
def booking_delete(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    booking.delete()
    return redirect('dashboard')

@login_required
def toggle_check_in(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    booking.is_checked_in = not booking.is_checked_in
    booking.save()
    return redirect('booking_list')

@login_required
def mark_as_paid(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    booking.payment_status = 'paid'
    booking.payment_date = timezone.now()
    booking.save()
    messages.success(request, f'Payment marked as paid for booking #{booking_id}')
    return redirect('booking_list')

@login_required
def booking_history(request):
    bookings = Booking.objects.select_related('room').all()
    rooms = Room.objects.all()

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    room_id = request.GET.get('room_id')

    if start_date:
        bookings = bookings.filter(check_in__gte=start_date)
    if end_date:
        bookings = bookings.filter(check_out__lte=end_date)
    if room_id:
        bookings = bookings.filter(room_id=room_id)

    paginator = Paginator(bookings.order_by('-check_in'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'hotel/booking_history.html', {
        'page_obj': page_obj,
        'rooms': rooms,
        'start_date': start_date,
        'end_date': end_date,
        'selected_room': int(room_id) if room_id else None,
    })

@login_required
def booking_summary(request):
    bookings = Booking.objects.select_related('room').all()

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status = request.GET.get('status')
    room_id = request.GET.get('room')

    if start_date:
        bookings = bookings.filter(check_in__gte=start_date)
    if end_date:
        bookings = bookings.filter(check_out__lte=end_date)
    if status == 'checked_in':
        bookings = bookings.filter(is_checked_in=True)
    elif status == 'not_checked_in':
        bookings = bookings.filter(is_checked_in=False)
    if room_id:
        bookings = bookings.filter(room__id=room_id)

    return render(request, 'hotel/booking_summary.html', {
        'bookings': bookings,
        'rooms': Room.objects.all(),
        'start_date': start_date,
        'end_date': end_date,
        'status': status,
        'room_id': room_id,
    })

# =======================
# 🔹 REPORTS
# =======================
@login_required
def occupancy_report(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if not start_date or not end_date:
        today = datetime.today().date()
        start_date = today.replace(day=1)
        end_date = today
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    total_days = (end_date - start_date).days + 1
    total_rooms = Room.objects.count()
    available_room_nights = total_rooms * total_days

    bookings = Booking.objects.filter(check_in__lte=end_date, check_out__gte=start_date)

    occupied_nights = 0
    for booking in bookings:
        overlap_start = max(booking.check_in, start_date)
        overlap_end = min(booking.check_out, end_date)
        nights = (overlap_end - overlap_start).days
        occupied_nights += max(nights, 0)

    occupancy_rate = (occupied_nights / available_room_nights) * 100 if available_room_nights else 0

    return render(request, 'hotel/occupancy_report.html', {
        'start_date': start_date,
        'end_date': end_date,
        'total_rooms': total_rooms,
        'available_nights': available_room_nights,
        'occupied_nights': occupied_nights,
        'occupancy_rate': round(occupancy_rate, 2),
    })

@login_required

def revenue_report(request):
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    start_date = end_date = None
    payments = Payment.objects.filter(booking__payment_status='paid').select_related('booking')

    # Filter by date range on payment date
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            payments = payments.filter(payment_date__date__gte=start_date)
        if end_date_str:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            payments = payments.filter(payment_date__date__lte=end_date)
    except ValueError:
        pass  # Invalid date strings are ignored

    total_revenue = payments.aggregate(total=Sum('amount'))['total'] or 0
    total_bookings = payments.count()
    avg_revenue = total_revenue / total_bookings if total_bookings > 0 else 0

    return render(request, 'hotel/revenue_report.html', {
        'start_date': start_date_str,
        'end_date': end_date_str,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'avg_revenue': avg_revenue,
    })

# =======================
# 🔹 PAYMENTS
# =======================
@login_required
def create_or_update_payment(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)
    payment = getattr(booking, 'payment', None)

    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.booking = booking
            payment.save()
            return redirect('booking_detail', pk=booking.id)
    else:
        form = PaymentForm(instance=payment)

    return render(request, 'hotel/payment_form.html', {'form': form, 'booking': booking})


@login_required
def create_payment(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.booking = booking  # Associate the payment with the booking
            payment.save()
            booking.update_payment_status()  # Update payment status after adding payment
            messages.success(request, f"Payment successfully added for booking #{booking.id}.")
            return redirect('booking_detail', pk=booking.id)
    else:
        form = PaymentForm()

    return render(request, 'hotel/create_payment.html', {'form': form, 'booking': booking})

@login_required
def toggle_check_in(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    today = now().date()

    # Restrict check-in toggle to valid dates
    if today >= booking.check_in and today <= booking.check_out:
        booking.is_checked_in = not booking.is_checked_in  # Toggle the check-in status
        booking.save()
        messages.success(request, f"Booking #{booking.id} check-in status updated.")
    else:
        messages.error(request, f"Booking #{booking.id} cannot be checked in. Invalid date range.")

    return redirect('booking_list')  # Redirect back to the booking list

@login_required
def guest_create(request):
    if request.method == 'POST':
        form = GuestForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Guest added successfully!")
            return redirect('guest_list')  # Redirect to guest list
    else:
        form = GuestForm()
    return render(request, 'hotel/guest_form.html', {'form': form})

@login_required
def guest_list(request):
    guests = Guest.objects.all()
    return render(request, 'hotel/guest_list.html', {'guests': guests})

@login_required
def guest_edit(request, pk):
    guest = get_object_or_404(Guest, pk=pk)
    if request.method == 'POST':
        form = GuestForm(request.POST, instance=guest)
        if form.is_valid():
            form.save()
            messages.success(request, "Guest updated successfully!")
            return redirect('guest_list')
    else:
        form = GuestForm(instance=guest)
    return render(request, 'hotel/guest_form.html', {'form': form, 'guest': guest})

@login_required
def guest_delete(request, pk):
    guest = get_object_or_404(Guest, pk=pk)
    if request.method == 'POST':
        guest.delete()
        messages.success(request, "Guest deleted successfully!")
        return redirect('guest_list')
    return render(request, 'hotel/guest_confirm_delete.html', {'guest': guest})

@login_required
def mark_as_checked_out(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    # Check if the booking is already marked as "Checked Out"
    if booking.status == "Checked Out":
        messages.warning(request, f"Booking #{booking_id} is already marked as Checked Out.")
        return redirect('booking_list')

    # Ensure the check-out date has passed
    if booking.check_out > now():  # Compare full datetime objects
        messages.error(request, f"Booking #{booking_id} cannot be marked as Checked Out before the check-out date.")
        return redirect('booking_list')

    # Mark the booking as "Checked Out"
    booking.status = "Checked Out"
    booking.is_checked_in = False  # Ensure check-in status is updated
    booking.save(update_fields=["status", "is_checked_in"])

    # Success message
    messages.success(request, f"Booking #{booking_id} marked as Checked Out successfully.")
    return redirect('booking_list')


@login_required
def add_meal_transaction(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if request.method == "POST":
        form = MealTransactionForm(request.POST)
        if form.is_valid():
            meal_transaction = form.save(commit=False)
            meal_transaction.booking = booking
            meal_transaction.save()
            messages.success(request, "Meal transaction added successfully!")
            return redirect('booking_detail', pk=booking.id)
    else:
        form = MealTransactionForm()

    return render(request, 'hotel/add_meal_transaction.html', {
        'form': form,
        'booking': booking,
    })

@login_required
def edit_meal_transaction(request, booking_id, meal_id):
    booking = get_object_or_404(Booking, id=booking_id)
    meal_transaction = get_object_or_404(MealTransaction, id=meal_id, booking=booking)

    if request.method == "POST":
        form = MealTransactionForm(request.POST, instance=meal_transaction)
        if form.is_valid():
            form.save()
            messages.success(request, "Meal transaction updated successfully!")
            return redirect('booking_detail', pk=booking.id)
    else:
        form = MealTransactionForm(instance=meal_transaction)

    return render(request, 'hotel/edit_meal_transaction.html', {
        'form': form,
        'booking': booking,
        'meal_transaction': meal_transaction,
    })




@login_required
def delete_meal_transaction(request, booking_id, meal_id):
    booking = get_object_or_404(Booking, id=booking_id)
    meal_transaction = get_object_or_404(MealTransaction, id=meal_id, booking=booking)

    if request.method == "POST":
        meal_transaction.delete()
        messages.success(request, "Meal transaction deleted successfully!")
        return redirect('booking_detail', pk=booking.id)

    return render(request, 'hotel/delete_meal_transaction.html', {
        'booking': booking,
        'meal_transaction': meal_transaction,
    })