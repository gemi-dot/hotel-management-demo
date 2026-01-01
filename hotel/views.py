
from datetime import datetime, timedelta
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

from .forms import GuestForm
from .models import Guest

from datetime import date  # ← make sure this line is here
from .models import Booking, Payment
from .models import MealTransaction, Booking
from .forms import MealTransactionForm
from .forms import PaymentForm

from django.utils import timezone

from datetime import datetime, time

from django.utils.timezone import now
from django.db.models import Min

from django.utils.timezone import make_aware

from openpyxl import Workbook
from django.http import HttpResponse
from .models import Room, Guest, Booking
from django.shortcuts import render



def get_room_status(room, start_datetime, end_datetime):
    """
    Return status and active booking info for a room in the given date range.
    """
    overlapping_bookings = room.bookings.filter(
        check_in__lt=end_datetime,
        check_out__gt=start_datetime,
    )

    if not overlapping_bookings.exists():
        return "Vacant", None

    booking = overlapping_bookings.first()

    if booking.status in ["Checked In", "Overdue (Needs Checkout)"]:
        return "Occupied", booking
    elif booking.status in ["Checked Out", "No Show"]:
        return "Vacant", None
    else:
        return "Vacant", None




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

from datetime import date

def dashboard(request):
    total_rooms = Room.objects.count()
    occupied_rooms = Booking.objects.filter(status="Checked In").count()
    vacant_rooms = total_rooms - occupied_rooms
    total_revenue = Payment.objects.aggregate(total=Sum("amount"))["total"] or 0
    total_bookings = Booking.objects.count()  # Add this line
    # Occupancy rate
    occupancy_rate = 0
    if total_rooms > 0:
        occupancy_rate = round((occupied_rooms / total_rooms) * 100, 2)

    # Outstanding balances (manual calculation)
    outstanding_balance = 0
    for booking in Booking.objects.all():
        meal_total = booking.meal_transactions.aggregate(total=Sum('total_price'))['total'] or 0
        grand_total = (booking.total_price or 0) + meal_total
        total_paid = booking.payments.aggregate(total=Sum('amount'))['total'] or 0
        outstanding_balance += grand_total - total_paid

    # Payments today
    today = date.today()
    payments_today = Payment.objects.filter(payment_date__date=today).count()

    # Meals ordered
    meals_ordered = MealTransaction.objects.count()

    # Recent bookings
    recent_bookings = Booking.objects.order_by("-check_in")[:5]

    # Handle guest creation form
    if request.method == 'POST':
        guest_form = GuestForm(request.POST)
        if guest_form.is_valid():
            guest_form.save()
            messages.success(request, "Guest added successfully!")
            return redirect('dashboard')
    else:
        guest_form = GuestForm()

    # Total guests
    total_guests = Guest.objects.count()
    
    return render(request, "hotel/dashboard.html", {
        "total_rooms": total_rooms,
        "occupied_rooms": occupied_rooms,
        "vacant_rooms": vacant_rooms,
        "total_revenue": total_revenue,
        "total_bookings": total_bookings,  # Pass to template
        "occupancy_rate": occupancy_rate,
        "outstanding_balance": outstanding_balance,
        "payments_today": payments_today,
        "meals_ordered": meals_ordered,
        "recent_bookings": recent_bookings,
        "guest_form": guest_form,  # Pass the form to the template
        "total_guests": total_guests,  # Pass total guests to the template
    })
# =======================
# 🔹 ROOMS
# =======================
from django.utils.timezone import now
from datetime import datetime

@login_required
def reserve_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)

    if request.method == "POST":
        # Read form inputs
        check_in_str = request.POST.get("check_in")
        check_out_str = request.POST.get("check_out")
        guest_id = request.POST.get("guest")

        # Validate inputs
        if not guest_id:
            messages.error(request, "Please select a guest.")
        elif not check_in_str or not check_out_str:
            messages.error(request, "Please provide check-in and check-out dates.")
        else:
            guest = get_object_or_404(Guest, id=guest_id)
            check_in = datetime.strptime(check_in_str, "%Y-%m-%d").date()
            check_out = datetime.strptime(check_out_str, "%Y-%m-%d").date()

            if check_out <= check_in:
                messages.error(request, "Check-out date must be after check-in date.")
            elif Booking.objects.filter(
                room=room,
                check_in__lt=check_out,
                check_out__gt=check_in,
                status__in=["Reserved", "Checked In"]
            ).exists():
                messages.error(request, "The room is already reserved for the selected dates.")
            else:
                # Create the booking
                Booking.objects.create(
                    room=room,
                    guest=guest,
                    check_in=check_in,
                    check_out=check_out,
                    status="Reserved"
                )
                messages.success(request, f"Room {room.number} reserved successfully!")
                return redirect("booking_summary")

    # Reload guests and room for GET or errors
    guests = Guest.objects.all()
    return render(request, "hotel/reserve_room.html", {
        "room": room,
        "guests": guests,
    })

@login_required
def room_list(request):
    rooms = Room.objects.all()
    return render(request, 'hotel/room_list.html', {'rooms': rooms})

@login_required
def room_create(request):
    if request.method == "POST":
        form = RoomForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Room created successfully!")
            return redirect('room_list')  # Redirect to the room list view
        else:
            messages.error(request, "There was an error creating the room. Please check the form.")
    else:
        form = RoomForm()

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





@login_required
def vacant_rooms(request):
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    # Default: today
    start_date = date.today()
    end_date = date.today()

    if start_date_str and end_date_str:
        try:
            # Convert to date objects explicitly
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    # Get all rooms
    rooms = Room.objects.all()

    vacant_rooms = []
    for room in rooms:
        # Check if any active booking overlaps the date range
        overlapping = room.bookings.filter(
            check_in__lte=end_date,
            check_out__gte=start_date
        ).exclude(status="Checked Out")  # ignore checked-out bookings

        if not overlapping.exists():
            vacant_rooms.append(room)

    context = {
        "rooms": vacant_rooms,
        "start_date": start_date,
        "end_date": end_date,
    }

    return render(request, "hotel/vacant_rooms.html", context)









# =======================
# 🔹 BOOKINGS
@login_required
def booking_list(request):
    bookings = Booking.objects.all().order_by("-check_in")
    today = timezone.now().date()

    # ✅ Get filter dates
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if start_date:
        bookings = bookings.filter(check_in__gte=start_date)
    if end_date:
        bookings = bookings.filter(check_out__lte=end_date)

    # 🔄 Update statuses dynamically
    for booking in bookings:
        booking.update_payment_status()

        if booking.status != "Checked Out":
            if booking.is_checked_in:
                if booking.check_out.date() < today:
                    booking.status = "Overdue"
                else:
                    booking.status = "Checked In"
            else:
                if booking.check_in.date() > today:
                    booking.status = "Upcoming"
                elif booking.check_in.date() <= today <= booking.check_out.date():
                    booking.status = "Pending"
                elif booking.check_out.date() < today:
                    booking.status = "No Show"
            booking.save(update_fields=["status"])

    paginator = Paginator(bookings, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "bookings": page_obj.object_list,
        "page_obj": page_obj,
        "start_date": start_date,
        "end_date": end_date,
    }
    return render(request, "hotel/booking_list.html", context)

   

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
            if today > booking.check_out.date():
                booking.status = "Overdue (Needs Checkout)"
            else:
                booking.status = "Checked In"
          
        else:
            if booking.check_in.date() > today:
                booking.status = "Pending"
            elif booking.check_in.date() <= today <= booking.check_out.date():
                booking.status = "Pending"
            elif booking.check_out.date() < today:
                booking.status = "No Show"

    payments = Payment.objects.filter(booking=booking).order_by('-payment_date')

    # Calculate the total cost of all meal transactions
    meal_total = booking.meal_transactions.aggregate(total=Sum('total_price'))['total'] or 0

    # Calculate the grand total (room price + meal total)
    grand_total = booking.total_price + meal_total

    payments = Payment.objects.filter(booking=booking).order_by('-payment_date')

    outstanding_balance = grand_total - booking.total_paid



    return render(request, "hotel/booking_detail.html", {
        "booking": booking,
        "payments": payments,
        "meal_total": meal_total,  # Pass the meal total to the template
        "grand_total": grand_total,  # Pass the grand total to the template
        "outstanding_balance": outstanding_balance,

    })
    
@login_required
def booking_checkout(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    # Mark booking as checked out
    booking.status = "Checked Out"
    booking.save(update_fields=["status"])

    # Update payment status too (in case final payment happened at checkout)
    booking.update_payment_status()

    messages.success(request, f"Booking {booking.id} has been checked out.")
    return redirect("booking_list")


@login_required
def booking_create(request, pk=None):
    # If pk is provided, edit existing booking
    if pk:
        booking = get_object_or_404(Booking, pk=pk)
    else:
        booking = None

    if request.method == 'POST':
        form = BookingForm(request.POST, instance=booking)
        if form.is_valid():
            booking = form.save(commit=False)

            # Apply fixed check-in/check-out times
            check_in_date = form.cleaned_data['check_in']
            check_out_date = form.cleaned_data['check_out']
            booking.check_in = timezone.make_aware(datetime.combine(check_in_date, time(14, 0)))  # 2 PM
            booking.check_out = timezone.make_aware(datetime.combine(check_out_date, time(12, 0))) # 12 PM

            # Compute total price
            booking.total_price = booking.compute_total_price()
            booking.save()

            messages.success(request, "Booking saved successfully!")
            return redirect('booking_detail', pk=booking.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = BookingForm(instance=booking)

    guests = Guest.objects.all()
    rooms = Room.objects.filter(is_available=True)

    return render(request, 'hotel/booking_form.html', {
        'form': form,
        'booking': booking,
        'guests': guests,
        'rooms': rooms,
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

from django.core.paginator import Paginator

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

    # 🔑 Sync status filter with booking.status field
    if status:
        bookings = bookings.filter(status=status)

    if room_id:
        bookings = bookings.filter(room__id=room_id)

    # ✅ Enhance each booking with calculated status
    today = now()
    for booking in bookings:
        check_in = booking.check_in
        check_out = booking.check_out

        if today < booking.check_in:
            booking.display_status = "Reserved"
        elif booking.check_in <= today < booking.check_out and booking.status == "Checked In":
            booking.display_status = "Checked In"
        elif today >= booking.check_out and booking.status == "Checked In":
            booking.display_status = "Checked Out"
        elif today > booking.check_in and booking.status == "Not Checked In":
            booking.display_status = "No Show"
        else:
            booking.display_status = booking.status  # fallback

    # ✅ Compute Next Available Date for each room
    room_next_available = (
        Booking.objects.filter(check_out__gte=today)
        .values("room__id", "room__number")
        .annotate(next_available=Min("check_out"))
    )

    next_available_map = {
        r["room__id"]: r["next_available"] for r in room_next_available
    }

    # ✅ Add pagination (e.g., 10 bookings per page)
    paginator = Paginator(bookings.order_by('-check_in'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'hotel/booking_summary.html', {
        'page_obj': page_obj,  # Pass paginated bookings to the template
        'rooms': Room.objects.all(),
        'start_date': start_date,
        'end_date': end_date,
        'status': status,
        'room_id': room_id,
        "next_available_map": next_available_map,  # 🆕 use this in template
    })

# =======================
# 🔹 REPORTS
# =======================
from datetime import datetime, time
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Room, Booking


import csv
from django.http import HttpResponse

@login_required
def export_booking_list_csv(request):
    bookings = Booking.objects.all()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="booking_list.csv"'

    writer = csv.writer(response)
    writer.writerow(['Guest Name', 'Room Number', 'Check-in', 'Check-out', 'Status'])
    for booking in bookings:
        writer.writerow([booking.guest.name, booking.room.number, booking.check_in, booking.check_out, booking.status])

    return response



@login_required
def export_booking_list_excel(request):
    bookings = Booking.objects.all()
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="booking_list.xlsx"'

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Booking List'

    # Add headers
    sheet.append(['Guest Name', 'Room Number', 'Check-in', 'Check-out', 'Status'])

    # Add booking data
    for booking in bookings:
        sheet.append([
            booking.guest.name,
            booking.room.number,
            booking.check_in.strftime('%Y-%m-%d'),
            booking.check_out.strftime('%Y-%m-%d'),
            booking.status
        ])

    # Save workbook to response
    workbook.save(response)
    return response


@login_required
def occupancy_report(request):
    """
    Display occupancy report for all rooms within a date range.
    Determines room status based on active bookings.
    """

    # --- Parse date filters from GET parameters ---
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    today = date.today()
    start_date = today
    end_date = today

    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass  # fallback to today if invalid

    # --- Get all rooms ---
    rooms = Room.objects.all()
    room_occupancy = []

    for room in rooms:
        # --- Find bookings overlapping the date range ---
        overlapping_bookings = room.bookings.filter(
            check_in__lte=end_date,
            check_out__gte=start_date
        ).order_by("check_in")

        # Determine status
        status = "Vacant"
        booking_info = None

        for booking in overlapping_bookings:
            # Ignore bookings that are already Checked Out
            if booking.status not in ["Checked Out", "No Show"]:
                status = "Occupied"
                booking_info = booking
                break  # first active booking is enough

        room_occupancy.append({
            "room": room,
            "status": status,
            "booking": booking_info,
        })

    context = {
        "room_occupancy": room_occupancy,
        "start_date": start_date,
        "end_date": end_date,
    }

    return render(request, "hotel/occupancy_report.html", context)




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

import logging

logger = logging.getLogger(__name__)



@login_required
def toggle_check_out(request, pk):
    booking = get_object_or_404(Booking, pk=pk)

    # Set checked out timestamp
    booking.checked_out_at = timezone.now()
    booking.is_checked_in = False
    booking.status = "Checked Out"  # Explicitly set status
    booking.save(update_fields=["checked_out_at", "is_checked_in", "status"])

    # Mark room as available
    room = booking.room
    room.is_available = True
    room.save()

    messages.success(request, f"Booking #{booking.pk} marked as Checked Out.")
    return redirect('booking_detail', pk=booking.pk)


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