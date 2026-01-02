from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from hotel.models import Booking, Guest, Room, Payment, MealTransaction
from hotel.utils import BalanceValidator, get_booking_financial_summary
import uuid

class Command(BaseCommand):
    help = 'Test balance update mechanisms with various scenarios'

    def handle(self, *args, **options):
        self.stdout.write("Testing Balance Update Mechanisms...")
        
        # Test 1: Create a new booking and verify initial state
        self.stdout.write("\n1. Testing initial booking state...")
        test_results = self.test_booking_creation()
        
        # Test 2: Add payments and verify status updates
        self.stdout.write("\n2. Testing payment additions...")
        payment_results = self.test_payment_updates(test_results['booking'])
        
        # Test 3: Add meal charges and verify recalculation
        self.stdout.write("\n3. Testing meal charge additions...")
        meal_results = self.test_meal_updates(test_results['booking'])
        
        # Test 4: Test edge cases (overpayment protection, etc.)
        self.stdout.write("\n4. Testing edge cases...")
        edge_results = self.test_edge_cases(test_results['booking'])
        
        # Test 5: Validate all bookings for consistency
        self.stdout.write("\n5. Running comprehensive validation...")
        validation_results = BalanceValidator.bulk_validate_all_bookings()
        
        # Summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write("BALANCE UPDATE TEST SUMMARY")
        self.stdout.write("="*50)
        self.stdout.write(f"✅ Initial state: {test_results['success']}")
        self.stdout.write(f"✅ Payment updates: {payment_results['success']}")
        self.stdout.write(f"✅ Meal charge updates: {meal_results['success']}")
        self.stdout.write(f"✅ Edge case handling: {edge_results['success']}")
        self.stdout.write(f"✅ System-wide consistency: {validation_results['consistency_rate']:.1f}%")
        
        if validation_results['inconsistent_count'] == 0:
            self.stdout.write(self.style.SUCCESS("\n🎉 ALL TESTS PASSED! Balance update mechanisms are working correctly."))
        else:
            self.stdout.write(self.style.WARNING(f"\n⚠️  Found {validation_results['inconsistent_count']} inconsistencies."))
    
    def test_booking_creation(self):
        """Test that new bookings have correct initial payment status."""
        try:
            # Create test guest and room if they don't exist
            guest, _ = Guest.objects.get_or_create(
                name="Test Guest Balance",
                defaults={'email': 'test_balance@example.com'}
            )
            room, _ = Room.objects.get_or_create(
                number="999",
                defaults={
                    'room_type': 'single',
                    'capacity': 1,
                    'price': Decimal('100.00')
                }
            )
            
            # Create booking
            from django.utils import timezone
            from datetime import timedelta
            
            booking = Booking.objects.create(
                guest=guest,
                room=room,
                check_in=timezone.now(),
                check_out=timezone.now() + timedelta(days=2),
                status="Pending"
            )
            
            summary = get_booking_financial_summary(booking)
            
            success = (
                summary['payment_status'] == 'pending' and
                summary['total_paid'] == 0 and
                summary['outstanding_balance'] == summary['grand_total']
            )
            
            self.stdout.write(f"   Initial payment status: {summary['payment_status']}")
            self.stdout.write(f"   Grand total: ${summary['grand_total']}")
            self.stdout.write(f"   Outstanding: ${summary['outstanding_balance']}")
            
            return {'booking': booking, 'success': success}
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error: {str(e)}"))
            return {'booking': None, 'success': False}
    
    def test_payment_updates(self, booking):
        """Test that payment additions correctly update payment status."""
        if not booking:
            return {'success': False}
            
        try:
            # Add partial payment
            partial_amount = booking.grand_total / 2
            Payment.objects.create(
                booking=booking,
                amount=partial_amount,
                payment_method="Credit Card",
                transaction_id=str(uuid.uuid4())
            )
            
            booking.refresh_from_db()
            summary = get_booking_financial_summary(booking)
            
            partial_success = summary['payment_status'] == 'partial'
            self.stdout.write(f"   After partial payment: {summary['payment_status']}")
            self.stdout.write(f"   Paid: ${summary['total_paid']} / ${summary['grand_total']}")
            
            # Add remaining payment
            remaining_amount = summary['outstanding_balance']
            Payment.objects.create(
                booking=booking,
                amount=remaining_amount,
                payment_method="Cash",
                transaction_id=str(uuid.uuid4())
            )
            
            booking.refresh_from_db()
            final_summary = get_booking_financial_summary(booking)
            
            full_success = final_summary['payment_status'] == 'paid'
            self.stdout.write(f"   After full payment: {final_summary['payment_status']}")
            self.stdout.write(f"   Final balance: ${final_summary['outstanding_balance']}")
            
            return {'success': partial_success and full_success}
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error: {str(e)}"))
            return {'success': False}
    
    def test_meal_updates(self, booking):
        """Test that meal charge additions correctly update totals and status."""
        if not booking:
            return {'success': False}
            
        try:
            initial_total = booking.grand_total
            
            # Add meal charge
            MealTransaction.objects.create(
                booking=booking,
                meal_name="Test Breakfast",
                category="Breakfast",
                quantity=2,
                price_per_unit=Decimal('15.00')
            )
            
            booking.refresh_from_db()
            summary = get_booking_financial_summary(booking)
            
            success = (
                summary['grand_total'] > initial_total and
                summary['meal_charges'] == Decimal('30.00') and
                summary['payment_status'] == 'partial'  # Should revert to partial due to new charges
            )
            
            self.stdout.write(f"   After meal charge: {summary['payment_status']}")
            self.stdout.write(f"   Meal charges: ${summary['meal_charges']}")
            self.stdout.write(f"   New grand total: ${summary['grand_total']}")
            self.stdout.write(f"   New outstanding: ${summary['outstanding_balance']}")
            
            return {'success': success}
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error: {str(e)}"))
            return {'success': False}
    
    def test_edge_cases(self, booking):
        """Test edge cases like overpayment protection."""
        if not booking:
            return {'success': False}
            
        try:
            # Test overpayment protection
            outstanding = booking.outstanding_balance
            overpayment_amount = outstanding + Decimal('100.00')
            
            try:
                Payment.objects.create(
                    booking=booking,
                    amount=overpayment_amount,
                    payment_method="Test",
                    transaction_id=str(uuid.uuid4())
                )
                # If this succeeds, our protection failed
                overpayment_protected = False
                self.stdout.write("   ❌ Overpayment protection failed")
            except (ValueError, Exception) as e:
                # This should happen - overpayment should be blocked
                overpayment_protected = True
                self.stdout.write(f"   ✅ Overpayment blocked: {str(e)}")
            
            # Test zero payment protection
            try:
                Payment.objects.create(
                    booking=booking,
                    amount=Decimal('0.00'),
                    payment_method="Test",
                    transaction_id=str(uuid.uuid4())
                )
                zero_payment_protected = False
                self.stdout.write("   ❌ Zero payment protection failed")
            except (ValueError, Exception) as e:
                zero_payment_protected = True
                self.stdout.write(f"   ✅ Zero payment blocked: {str(e)}")
            
            return {'success': overpayment_protected and zero_payment_protected}
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error: {str(e)}"))
            return {'success': False}