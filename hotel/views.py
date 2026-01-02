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
from django.db import models
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
    # ✅ PERFORMANCE FIX: Use efficient aggregations instead of multiple queries
    from django.db.models import Count, Sum, Q, Case, When, IntegerField, DecimalField
    
    # Single query to get room statistics
    room_stats = Room.objects.aggregate(
        total_rooms=Count('id'),
        occupied_rooms=Count('id', filter=Q(bookings__status="Checked In"))
    )
    
    total_rooms = room_stats['total_rooms']
    occupied_rooms = room_stats['occupied_rooms'] 
    vacant_rooms = total_rooms - occupied_rooms
    
    # ✅ FIX: Use simple count to avoid duplication from JOINs
    total_bookings = Booking.objects.count()
    
    # ✅ Calculate pending check-ins count
    pending_checkins = Booking.objects.filter(status="Pending").count()
    
    # ✅ Calculate pending check-outs count (guests currently checked in)
    pending_checkouts = Booking.objects.filter(status="Checked In").count()
    
    # Efficient revenue calculations
    total_revenue = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate outstanding balance more accurately
    total_booking_value = Booking.objects.aggregate(
        total=Sum('total_price')
    )['total'] or 0
    
    total_meal_value = MealTransaction.objects.aggregate(
        total=Sum('total_price')
    )['total'] or 0
    
    total_grand_value = total_booking_value + total_meal_value
    outstanding_balance = max(total_grand_value - total_revenue, 0)
    
    # Occupancy rate
    occupancy_rate = 0
    if total_rooms > 0:
        occupancy_rate = round((occupied_rooms / total_rooms) * 100, 2)

    # Payments today - single query
    today = date.today()
    payments_today = Payment.objects.filter(payment_date__date=today).count()

    # Meals ordered - single query
    meals_ordered = MealTransaction.objects.count()

    # Recent bookings with optimized query
    recent_bookings = Booking.objects.select_related('guest', 'room').order_by("-check_in")[:5]

    # Handle guest creation form
    if request.method == 'POST':
        guest_form = GuestForm(request.POST)
        if guest_form.is_valid():
            guest_form.save()
            messages.success(request, "Guest added successfully!")
            return redirect('dashboard')
    else:
        guest_form = GuestForm()

    # Total guests - single query
    total_guests = Guest.objects.count()
    
    return render(request, "hotel/dashboard.html", {
        "total_rooms": total_rooms,
        "occupied_rooms": occupied_rooms,
        "vacant_rooms": vacant_rooms,
        "total_revenue": total_revenue,
        "total_bookings": total_bookings,
        "occupancy_rate": occupancy_rate,
        "outstanding_balance": outstanding_balance,
        "payments_today": payments_today,
        "meals_ordered": meals_ordered,
        "recent_bookings": recent_bookings,
        "guest_form": guest_form,
        "total_guests": total_guests,
        "pending_checkins": pending_checkins,  # ✅ Add pending check-ins to context
        "pending_checkouts": pending_checkouts,  # ✅ Add pending check-outs to context
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
    # ✅ PERFORMANCE FIX: Get all rooms and calculate statistics efficiently
    rooms = Room.objects.all()
    
    # Calculate accurate room statistics
    total_rooms = rooms.count()
    available_rooms = rooms.filter(is_available=True).count()
    occupied_rooms = rooms.filter(is_available=False).count()
    
    # Calculate active revenue from occupied rooms
    active_revenue = rooms.filter(is_available=False).aggregate(
        total_revenue=Sum('price')
    )['total_revenue'] or 0
    
    # Add statistics to context
    room_stats = {
        'total_rooms': total_rooms,
        'available_rooms': available_rooms,
        'occupied_rooms': occupied_rooms,
        'active_revenue': active_revenue,
    }
    
    return render(request, 'hotel/room_list.html', {
        'rooms': rooms,
        'room_stats': room_stats,
    })

@login_required
def room_create(request):
    if request.method == "POST":
        form = RoomForm(request.POST)
        if form.is_valid():
            try:
                room = form.save()
                messages.success(request, f"Room '{room.number}' created successfully!")
                return redirect('room_list')
            except Exception as e:
                messages.error(request, f"Error creating room: {str(e)}")
        else:
            # Form has validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
    else:
        form = RoomForm()

    return render(request, 'hotel/room_form.html', {'form': form})

@login_required
def room_edit(request, pk):
    room = get_object_or_404(Room, pk=pk)
    if request.method == 'POST':
        form = RoomForm(request.POST, instance=room)
        if form.is_valid():
            try:
                updated_room = form.save()
                messages.success(request, f"Room '{updated_room.number}' updated successfully!")
                return redirect('room_list')
            except Exception as e:
                messages.error(request, f"Error updating room: {str(e)}")
        else:
            # Form has validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
    else:
        form = RoomForm(instance=room)
    
    return render(request, 'hotel/room_form.html', {'form': form, 'room': room})

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
    # ✅ PERFORMANCE FIX: Properly optimized query with filtering
    bookings = Booking.objects.select_related('guest', 'room').prefetch_related('payments', 'meal_transactions').order_by("-check_in")
    
    today = timezone.now().date()

    # ✅ Apply date filters to the optimized queryset
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if start_date:
        bookings = bookings.filter(check_in__gte=start_date)
    if end_date:
        bookings = bookings.filter(check_out__lte=end_date)

    # 🔄 Update statuses dynamically (but avoid saving in loops for better performance)
    bookings_to_update = []
    for booking in bookings:
        booking.update_payment_status()

        if booking.status != "Checked Out":
            old_status = booking.status
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
            
            # Only save if status actually changed
            if old_status != booking.status:
                bookings_to_update.append(booking)
    
    # Bulk update changed statuses for better performance
    if bookings_to_update:
        Booking.objects.bulk_update(bookings_to_update, ['status'])

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
    # ✅ PERFORMANCE FIX: Use select_related and prefetch_related to avoid N+1 queries
    booking = get_object_or_404(
        Booking.objects.select_related('guest', 'room').prefetch_related('payments', 'meal_transactions'), 
        pk=pk
    )
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

    # ✅ Use prefetched data instead of separate queries
    payments = booking.payments.all().order_by('-payment_date')

    # Calculate meal total using prefetched data
    meal_total = sum(meal.total_price or 0 for meal in booking.meal_transactions.all())

    # Calculate the grand total (room price + meal total)
    grand_total = booking.total_price + meal_total

    # Calculate outstanding balance using prefetched payment data
    total_paid = sum(payment.amount for payment in payments)
    outstanding_balance = grand_total - total_paid

    return render(request, "hotel/booking_detail.html", {
        "booking": booking,
        "payments": payments,
        "meal_total": meal_total,
        "grand_total": grand_total,
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
            try:
                booking = form.save(commit=False)
                
                # Apply fixed check-in/check-out times if needed
                check_in_date = form.cleaned_data['check_in']
                check_out_date = form.cleaned_data['check_out']
                
                # Set specific times (2 PM check-in, 12 PM check-out)
                from datetime import time
                booking.check_in = timezone.make_aware(datetime.combine(check_in_date, time(14, 0)))
                booking.check_out = timezone.make_aware(datetime.combine(check_out_date, time(12, 0)))
                
                # Compute total price
                booking.total_price = booking.compute_total_price()
                booking.save()

                messages.success(request, f"Booking #{booking.pk} created successfully!")
                return redirect('booking_detail', pk=booking.pk)
            except Exception as e:
                messages.error(request, f"Error creating booking: {str(e)}")
        else:
            # Form has validation errors
            if form.non_field_errors():
                for error in form.non_field_errors():
                    messages.error(request, error)
            
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
    else:
        form = BookingForm()

    # Always load fresh data for dropdowns
    guests = Guest.objects.all().order_by('name')
    rooms = Room.objects.filter(is_available=True).order_by('number')

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
            try:
                updated_booking = form.save(commit=False)
                
                # Recompute total price
                updated_booking.total_price = updated_booking.compute_total_price()
                updated_booking.save()
                
                # Check if payment status was manually changed
                manual_override = 'payment_status' in form.changed_data
                updated_booking.update_payment_status(manual_override=manual_override)
                
                messages.success(request, f"Booking #{updated_booking.pk} updated successfully!")
                return redirect('booking_detail', pk=updated_booking.pk)
            except Exception as e:
                messages.error(request, f"Error updating booking: {str(e)}")
        else:
            # Form has validation errors
            if form.non_field_errors():
                for error in form.non_field_errors():
                    messages.error(request, error)
            
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
    else:
        form = BookingForm(instance=booking)
    
    # Load fresh data for dropdowns
    guests = Guest.objects.all().order_by('name')
    rooms = Room.objects.filter(
        models.Q(is_available=True) | models.Q(id=booking.room.id)
    ).order_by('number')
    
    return render(request, 'hotel/booking_form.html', {
        'form': form, 
        'booking': booking,
        'guests': guests,
        'rooms': rooms,
    })

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
    payments = Payment.objects.select_related('booking', 'booking__guest', 'booking__room').all()

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

    # Order payments by date (most recent first)
    payments = payments.order_by('-payment_date')

    # Calculate summary statistics
    total_revenue = payments.aggregate(total=Sum('amount'))['total'] or 0
    total_payments = payments.count()
    avg_revenue = total_revenue / total_payments if total_payments > 0 else 0
    
    # Get unique bookings count from the filtered payments
    unique_bookings = payments.values('booking').distinct().count()

    return render(request, 'hotel/revenue_report.html', {
        'payments': payments,  # ✅ Add missing payments data
        'start_date': start_date_str,
        'end_date': end_date_str,
        'total_bookings': unique_bookings,
        'total_payments': total_payments,
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
            try:
                payment = form.save(commit=False)
                payment.booking = booking
                payment.save()
                
                # Update booking payment status
                booking.update_payment_status()
                
                messages.success(request, f"Payment of ${payment.amount} successfully added for booking #{booking.id}.")
                return redirect('booking_detail', pk=booking.id)
            except Exception as e:
                messages.error(request, f"Error processing payment: {str(e)}")
        else:
            # Form has validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
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
            try:
                guest = form.save()
                messages.success(request, f"Guest '{guest.name}' added successfully!")
                return redirect('guest_list')
            except Exception as e:
                messages.error(request, f"Error creating guest: {str(e)}")
        else:
            # Form has validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
    else:
        form = GuestForm()
    
    return render(request, 'hotel/guest_form.html', {'form': form})

@login_required
def guest_list(request):
    # ✅ PERFORMANCE FIX: Use prefetch_related to avoid N+1 queries
    # This loads all guest bookings in just 2 queries instead of N+1
    guests = Guest.objects.prefetch_related('bookings').all()
    
    # Calculate additional stats efficiently
    recent_guests_count = Guest.objects.filter(
        bookings__created_at__gte=timezone.now() - timedelta(days=30)
    ).distinct().count()
    
    # Calculate total guest bookings efficiently
    total_guest_bookings = Booking.objects.count()
    
    context = {
        'guests': guests,
        'recent_guests_count': recent_guests_count,
        'total_guest_bookings': total_guest_bookings,
    }
    
    return render(request, 'hotel/guest_list.html', context)

@login_required
def guest_detail(request, pk):
    guest = get_object_or_404(Guest, pk=pk)
    
    # Get all bookings for this guest
    guest_bookings = Booking.objects.filter(guest=guest).order_by('-check_in')
    
    # Calculate guest statistics
    total_bookings = guest_bookings.count()
    total_spent = 0
    
    for booking in guest_bookings:
        # Calculate total spent including meals
        meal_total = booking.meal_transactions.aggregate(total=Sum('total_price'))['total'] or 0
        booking_total = (booking.total_price or 0) + meal_total
        total_spent += booking_total
    
    # Calculate average spending per booking
    average_per_booking = total_spent / total_bookings if total_bookings > 0 else 0
    
    context = {
        'guest': guest,
        'guest_bookings': guest_bookings,
        'total_bookings': total_bookings,
        'total_spent': total_spent,
        'average_per_booking': average_per_booking,  # Add this line
    }
    
    return render(request, 'hotel/guest_detail.html', context)

@login_required
def guest_edit(request, pk):
    guest = get_object_or_404(Guest, pk=pk)
    if request.method == 'POST':
        form = GuestForm(request.POST, instance=guest)
        if form.is_valid():
            try:
                updated_guest = form.save()
                messages.success(request, f"Guest '{updated_guest.name}' updated successfully!")
                return redirect('guest_list')
            except Exception as e:
                messages.error(request, f"Error updating guest: {str(e)}")
        else:
            # Form has validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
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
            try:
                meal_transaction = form.save(commit=False)
                meal_transaction.booking = booking
                meal_transaction.save()
                messages.success(request, f"Meal '{meal_transaction.meal_name}' added successfully!")
                return redirect('booking_detail', pk=booking.id)
            except Exception as e:
                messages.error(request, f"Error adding meal transaction: {str(e)}")
        else:
            # Form has validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
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
            try:
                updated_meal = form.save()
                messages.success(request, f"Meal '{updated_meal.meal_name}' updated successfully!")
                return redirect('booking_detail', pk=booking.id)
            except Exception as e:
                messages.error(request, f"Error updating meal transaction: {str(e)}")
        else:
            # Form has validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
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