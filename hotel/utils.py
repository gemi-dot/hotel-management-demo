from datetime import datetime, time
from django.db import transaction
from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import models

def get_room_status(room, start_datetime, end_datetime):
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


def process_bulk_payment_update(bookings_queryset):
    """
    Process payment status updates for multiple bookings efficiently.
    Returns count of updated bookings.
    """
    updated_count = 0
    
    with transaction.atomic():
        # Use select_related to avoid N+1 queries
        bookings = bookings_queryset.select_related('room', 'guest').prefetch_related('payments', 'meal_transactions')
        
        for booking in bookings:
            old_status = booking.payment_status
            booking.update_payment_status(manual_override=True)
            
            if old_status != booking.payment_status:
                booking.save(update_fields=['payment_status'])
                updated_count += 1
    
    return updated_count


def validate_payment_transaction(booking, payment_amount, exclude_payment_id=None):
    """
    Validate if a payment can be processed without exceeding the total.
    Returns (is_valid, error_message, remaining_balance)
    """
    try:
        current_paid = booking.total_paid
        
        # If updating existing payment, subtract the old amount
        if exclude_payment_id:
            from hotel.models import Payment
            try:
                old_payment = Payment.objects.get(pk=exclude_payment_id)
                current_paid -= old_payment.amount
            except Payment.DoesNotExist:
                pass
        
        remaining_balance = booking.grand_total - current_paid
        
        if payment_amount <= 0:
            return False, "Payment amount must be greater than zero.", remaining_balance
        
        if payment_amount > remaining_balance:
            return False, f"Payment of ${payment_amount} exceeds remaining balance of ${remaining_balance}", remaining_balance
        
        return True, "", remaining_balance
        
    except Exception as e:
        return False, f"Validation error: {str(e)}", Decimal('0')


def get_booking_financial_summary(booking):
    """
    Get comprehensive financial summary for a booking.
    Returns dictionary with all financial details.
    """
    return {
        'room_charges': booking.total_price or Decimal('0'),
        'meal_charges': booking.meal_total,
        'grand_total': booking.grand_total,
        'total_paid': booking.total_paid,
        'outstanding_balance': booking.outstanding_balance,
        'payment_percentage': booking.payment_percentage,
        'payment_status': booking.payment_status,
        'is_fully_paid': booking.total_paid >= booking.grand_total,
        'can_add_charges': booking.can_add_charges()
    }


def sync_payment_statuses_for_date_range(start_date, end_date):
    """
    Sync payment statuses for bookings within a date range.
    Useful for daily/weekly reconciliation.
    """
    from hotel.models import Booking
    
    bookings = Booking.objects.filter(
        check_in__date__gte=start_date,
        check_out__date__lte=end_date
    )
    
    return process_bulk_payment_update(bookings)


def create_payment_with_validation(booking, amount, payment_method, transaction_id=None):
    """
    Create a payment with full validation and atomic transaction handling.
    Returns (payment_object, success, error_message)
    """
    import uuid
    from hotel.models import Payment
    
    try:
        # Validate the payment first
        is_valid, error_msg, remaining = validate_payment_transaction(booking, amount)
        if not is_valid:
            return None, False, error_msg
        
        # Generate transaction ID if not provided
        if not transaction_id:
            transaction_id = str(uuid.uuid4())
        
        # Create payment atomically
        with transaction.atomic():
            payment = Payment(
                booking=booking,
                amount=amount,
                payment_method=payment_method,
                transaction_id=transaction_id
            )
            payment.save()  # This automatically updates payment status
            
            return payment, True, ""
            
    except Exception as e:
        return None, False, f"Payment creation failed: {str(e)}"


def bulk_recalculate_booking_totals(booking_ids=None):
    """
    Recalculate all totals for multiple bookings efficiently.
    If booking_ids is None, processes all bookings.
    Returns count of processed bookings.
    """
    from hotel.models import Booking
    
    if booking_ids:
        bookings = Booking.objects.filter(id__in=booking_ids)
    else:
        bookings = Booking.objects.all()
    
    processed_count = 0
    
    with transaction.atomic():
        for booking in bookings.select_related('room', 'guest'):
            try:
                booking.recalculate_all_totals()
                processed_count += 1
            except Exception as e:
                # Log error but continue processing other bookings
                print(f"Error processing booking {booking.id}: {str(e)}")
                continue
    
    return processed_count


def get_payment_anomalies():
    """
    Identify bookings with payment anomalies for review.
    Returns list of problematic bookings with details.
    """
    from hotel.models import Booking
    from django.utils.timezone import now
    
    anomalies = []
    today = now().date()
    
    # Check all bookings for various anomalies
    for booking in Booking.objects.select_related('room', 'guest').prefetch_related('payments', 'meal_transactions'):
        issues = []
        
        # Check for overpayments
        if booking.total_paid > booking.grand_total:
            issues.append(f"Overpaid by ${booking.total_paid - booking.grand_total}")
        
        # Check for overdue payments
        if booking.check_out.date() < today and booking.outstanding_balance > 0:
            days_overdue = (today - booking.check_out.date()).days
            issues.append(f"Overdue by {days_overdue} days, balance: ${booking.outstanding_balance}")
        
        # Check for inconsistent payment status
        expected_status = booking.payment_status  # This calculates the correct status
        booking.update_payment_status(manual_override=True)
        calculated_status = booking.payment_status
        
        if expected_status != calculated_status:
            issues.append(f"Status mismatch: showing '{expected_status}', should be '{calculated_status}'")
        
        if issues:
            anomalies.append({
                'booking': booking,
                'issues': issues,
                'financial_summary': get_booking_financial_summary(booking)
            })
    
    return anomalies


def generate_payment_reconciliation_report(start_date=None, end_date=None):
    """
    Generate a comprehensive payment reconciliation report.
    Returns dictionary with summary statistics and details.
    """
    from hotel.models import Booking, Payment
    from django.db.models import Sum, Count
    
    # Default to current month if no dates provided
    if not start_date or not end_date:
        today = timezone.now().date()
        start_date = today.replace(day=1)
        if today.month == 12:
            end_date = today.replace(year=today.year + 1, month=1, day=1) - timezone.timedelta(days=1)
        else:
            end_date = today.replace(month=today.month + 1, day=1) - timezone.timedelta(days=1)
    
    # Get bookings in date range
    bookings = Booking.objects.filter(
        check_in__date__gte=start_date,
        check_out__date__lte=end_date
    ).select_related('room', 'guest').prefetch_related('payments', 'meal_transactions')
    
    # Calculate summary statistics
    summary = {
        'period': f"{start_date} to {end_date}",
        'total_bookings': bookings.count(),
        'total_revenue': sum(b.grand_total for b in bookings),
        'total_collected': sum(b.total_paid for b in bookings),
        'outstanding_balance': sum(b.outstanding_balance for b in bookings),
        'payment_status_breakdown': {},
        'anomalies': []
    }
    
    # Payment status breakdown
    for status, _ in Booking.PAYMENT_STATUSES:
        count = bookings.filter(payment_status=status).count()
        if count > 0:
            summary['payment_status_breakdown'][status] = count
    
    # Find anomalies in this period
    summary['anomalies'] = [a for a in get_payment_anomalies() if a['booking'] in bookings]
    
    return summary


class BalanceValidator:
    """Utility class to validate and fix balance inconsistencies."""
    
    @staticmethod
    def check_booking_balance(booking):
        """Check if a booking's payment status matches its actual balance."""
        grand_total = booking.grand_total
        total_paid = booking.total_paid
        outstanding = booking.outstanding_balance
        current_status = booking.payment_status
        
        # Calculate what the status should be
        temp_booking = booking
        temp_booking.update_payment_status(manual_override=True)
        expected_status = temp_booking.payment_status
        
        is_consistent = current_status == expected_status
        
        return {
            'booking_id': booking.id,
            'is_consistent': is_consistent,
            'current_status': current_status,
            'expected_status': expected_status,
            'grand_total': grand_total,
            'total_paid': total_paid,
            'outstanding_balance': outstanding,
            'payment_percentage': booking.payment_percentage
        }
    
    @staticmethod
    def bulk_validate_all_bookings():
        """Validate all bookings and return inconsistencies."""
        from hotel.models import Booking
        
        inconsistencies = []
        total_bookings = 0
        
        for booking in Booking.objects.all():
            total_bookings += 1
            result = BalanceValidator.check_booking_balance(booking)
            
            if not result['is_consistent']:
                inconsistencies.append(result)
        
        return {
            'total_bookings': total_bookings,
            'inconsistent_count': len(inconsistencies),
            'inconsistencies': inconsistencies,
            'consistency_rate': ((total_bookings - len(inconsistencies)) / total_bookings * 100) if total_bookings > 0 else 100
        }
    
    @staticmethod
    def fix_all_inconsistencies(dry_run=False):
        """Fix all payment status inconsistencies."""
        from hotel.models import Booking
        
        fixed_count = 0
        errors = []
        
        with transaction.atomic():
            for booking in Booking.objects.all():
                try:
                    old_status = booking.payment_status
                    booking.update_payment_status(manual_override=True)
                    
                    if old_status != booking.payment_status:
                        if not dry_run:
                            booking.save(update_fields=['payment_status'])
                        fixed_count += 1
                        
                except Exception as e:
                    errors.append({
                        'booking_id': booking.id,
                        'error': str(e)
                    })
            
            if dry_run:
                transaction.set_rollback(True)
        
        return {
            'fixed_count': fixed_count,
            'errors': errors
        }


def validate_payment_amount(booking, amount):
    """Validate that a payment amount doesn't exceed the outstanding balance."""
    outstanding = booking.outstanding_balance
    if amount > outstanding:
        raise ValidationError(
            f"Payment amount ${amount} exceeds outstanding balance ${outstanding}"
        )
    return True


def recalculate_booking_totals(booking):
    """Recalculate all totals for a booking to ensure consistency."""
    # Recalculate room total
    booking.total_price = booking.compute_total_price()
    
    # Meal total is calculated via property, no need to store
    # Payment status will be updated automatically
    booking.update_payment_status()
    booking.save()
    
    return {
        'room_total': booking.total_price,
        'meal_total': booking.meal_total,
        'grand_total': booking.grand_total,
        'total_paid': booking.total_paid,
        'outstanding': booking.outstanding_balance,
        'payment_status': booking.payment_status
    }
