from datetime import datetime, time

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
