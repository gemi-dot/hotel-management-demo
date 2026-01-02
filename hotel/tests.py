from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import datetime, timedelta
from hotel.models import Guest, Room, Booking, Payment, MealTransaction
from hotel.utils import (
    validate_payment_transaction, 
    get_booking_financial_summary,
    create_payment_with_validation,
    bulk_recalculate_booking_totals,
    get_payment_anomalies
)


class BalanceManagementTestCase(TestCase):
    def setUp(self):
        """Set up test data for balance management tests."""
        # Create test guest
        self.guest = Guest.objects.create(
            name="Test Guest",
            email="test@example.com",
            phone="1234567890"
        )
        
        # Create test room
        self.room = Room.objects.create(
            number="101",
            room_type="double",
            capacity=2,
            price=Decimal("100.00")
        )
        
        # Create test booking (3 nights = $300)
        self.check_in = timezone.now() + timedelta(days=1)
        self.check_out = self.check_in + timedelta(days=3)
        
        self.booking = Booking.objects.create(
            guest=self.guest,
            room=self.room,
            check_in=self.check_in,
            check_out=self.check_out
        )

    def test_payment_status_calculation(self):
        """Test automatic payment status calculation."""
        # Initially pending
        self.assertEqual(self.booking.payment_status, "pending")
        
        # Add partial payment
        payment1 = Payment.objects.create(
            booking=self.booking,
            amount=Decimal("150.00"),
            payment_method="credit_card",
            transaction_id="test_001"
        )
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, "partial")
        
        # Complete payment
        payment2 = Payment.objects.create(
            booking=self.booking,
            amount=Decimal("150.00"),
            payment_method="cash",
            transaction_id="test_002"
        )
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, "paid")

    def test_overpayment_prevention(self):
        """Test that overpayments are prevented."""
        # First payment of $200
        Payment.objects.create(
            booking=self.booking,
            amount=Decimal("200.00"),
            payment_method="credit_card",
            transaction_id="test_003"
        )
        
        # Try to add payment that would exceed total
        with self.assertRaises(ValueError) as context:
            Payment.objects.create(
                booking=self.booking,
                amount=Decimal("200.00"),  # This would total $400, exceeding $300
                payment_method="cash",
                transaction_id="test_004"
            )
        