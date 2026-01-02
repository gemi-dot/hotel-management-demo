from django.core.management.base import BaseCommand
from django.db import transaction
from hotel.models import Booking

class Command(BaseCommand):
    help = 'Fix inconsistent payment statuses for all bookings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write("DRY RUN MODE - No changes will be made")
        
        bookings = Booking.objects.all()
        updated_count = 0
        inconsistencies = []
        
        for booking in bookings:
            old_status = booking.payment_status
            
            # Calculate what the status should be
            booking.update_payment_status(manual_override=True)
            new_status = booking.payment_status
            
            if old_status != new_status:
                inconsistencies.append({
                    'booking_id': booking.id,
                    'guest': booking.guest.name,
                    'room': booking.room.number,
                    'old_status': old_status,
                    'new_status': new_status,
                    'grand_total': booking.grand_total,
                    'total_paid': booking.total_paid,
                    'outstanding': booking.outstanding_balance
                })
                
                if not dry_run:
                    booking.save(update_fields=['payment_status'])
                    updated_count += 1
        
        if inconsistencies:
            self.stdout.write(f"\nFound {len(inconsistencies)} payment status inconsistencies:")
            for item in inconsistencies:
                self.stdout.write(
                    f"Booking {item['booking_id']} ({item['guest']}, Room {item['room']}): "
                    f"{item['old_status']} → {item['new_status']} "
                    f"(${item['total_paid']}/${item['grand_total']}, Outstanding: ${item['outstanding']})"
                )
            
            if not dry_run:
                self.stdout.write(
                    self.style.SUCCESS(f"\nUpdated {updated_count} booking payment statuses.")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"\nWould update {len(inconsistencies)} bookings. Run without --dry-run to apply changes.")
                )
        else:
            self.stdout.write(self.style.SUCCESS("All payment statuses are consistent."))