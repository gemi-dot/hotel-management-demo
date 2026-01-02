from django.core.management.base import BaseCommand
from django.db import transaction
from hotel.models import Booking

class Command(BaseCommand):
    help = 'Fix booking total_price values that are null or incorrect'

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
        issues = []
        
        for booking in bookings:
            old_total = booking.total_price
            computed_total = booking.compute_total_price()
            
            # Check if total_price is null or incorrect
            needs_update = (
                booking.total_price is None or 
                booking.total_price == 0 or
                booking.total_price != computed_total
            )
            
            if needs_update:
                days = (booking.check_out - booking.check_in).days
                issues.append({
                    'booking_id': booking.id,
                    'guest': booking.guest.name,
                    'room': booking.room.number,
                    'check_in': booking.check_in.date(),
                    'check_out': booking.check_out.date(),
                    'days': days,
                    'room_price': booking.room.price,
                    'old_total': old_total,
                    'new_total': computed_total
                })
                
                if not dry_run:
                    with transaction.atomic():
                        booking.total_price = computed_total
                        booking.save(update_fields=['total_price'])
                        # Also update payment status based on new total
                        booking.update_payment_status()
                        updated_count += 1
        
        if issues:
            self.stdout.write(f"\nFound {len(issues)} bookings with incorrect total_price:")
            for item in issues:
                self.stdout.write(
                    f"Booking {item['booking_id']} ({item['guest']}, Room {item['room']}): "
                    f"{item['days']} days × ₱{item['room_price']} = ₱{item['new_total']} "
                    f"(was: {item['old_total']})"
                )
            
            if not dry_run:
                self.stdout.write(
                    self.style.SUCCESS(f"\n✅ Updated {updated_count} booking totals successfully!")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"\n⚠️ Would update {len(issues)} bookings. Run without --dry-run to apply changes.")
                )
        else:
            self.stdout.write(self.style.SUCCESS("✅ All booking totals are correct."))
        
        # Show summary of what each booking should have
        self.stdout.write(f"\n📊 SUMMARY OF ALL BOOKINGS:")
        all_bookings = Booking.objects.all().select_related('guest', 'room')
        for booking in all_bookings:
            days = (booking.check_out - booking.check_in).days
            computed = booking.compute_total_price()
            current = booking.total_price or 0
            status = "✅" if current == computed else "❌"
            
            self.stdout.write(
                f"{status} Booking {booking.id}: {booking.guest.name}, Room {booking.room.number}, "
                f"{days} nights × ₱{booking.room.price} = ₱{computed} (stored: ₱{current})"
            )