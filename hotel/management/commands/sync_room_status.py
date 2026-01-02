from django.core.management.base import BaseCommand
from django.db import transaction
from hotel.models import Room, Booking
from django.utils import timezone

class Command(BaseCommand):
    help = 'Synchronize room availability status with actual booking data'

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
        
        today = timezone.now().date()
        updated_count = 0
        issues = []
        
        for room in Room.objects.all():
            current_availability = room.is_available
            
            # Check if room has any active bookings
            active_bookings = room.bookings.filter(
                check_in__date__lte=today,
                check_out__date__gt=today,
                status__in=["Pending", "Checked In"]
            )
            
            should_be_occupied = active_bookings.exists()
            should_be_available = not should_be_occupied
            
            # Check for data inconsistency
            needs_update = current_availability != should_be_available
            
            if needs_update or active_bookings.exists():
                active_booking = active_bookings.first() if active_bookings.exists() else None
                
                issues.append({
                    'room_number': room.number,
                    'current_status': 'Available' if current_availability else 'Occupied',
                    'should_be': 'Available' if should_be_available else 'Occupied',
                    'needs_update': needs_update,
                    'active_booking': active_booking,
                    'guest_name': active_booking.guest.name if active_booking else None,
                })
                
                if needs_update and not dry_run:
                    with transaction.atomic():
                        room.is_available = should_be_available
                        room.save(update_fields=['is_available'])
                        updated_count += 1
        
        # Display results
        if issues:
            self.stdout.write(f"\nRoom Status Analysis:")
            for item in issues:
                status_icon = "✅" if not item['needs_update'] else "❌"
                self.stdout.write(
                    f"{status_icon} Room {item['room_number']}: "
                    f"Currently {item['current_status']}, Should be {item['should_be']}"
                )
                if item['active_booking']:
                    self.stdout.write(
                        f"    └── Active booking: {item['guest_name']} "
                        f"({item['active_booking'].check_in.date()} to {item['active_booking'].check_out.date()})"
                    )
                else:
                    self.stdout.write("    └── No active bookings found")
            
            if not dry_run and updated_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f"\n✅ Updated {updated_count} room statuses successfully!")
                )
            elif dry_run:
                needs_update_count = sum(1 for item in issues if item['needs_update'])
                if needs_update_count > 0:
                    self.stdout.write(
                        self.style.WARNING(f"\n⚠️ Would update {needs_update_count} rooms. Run without --dry-run to apply changes.")
                    )
                else:
                    self.stdout.write(self.style.SUCCESS("\n✅ All room statuses are correct!"))
        else:
            self.stdout.write(self.style.SUCCESS("✅ All room statuses are correct!"))