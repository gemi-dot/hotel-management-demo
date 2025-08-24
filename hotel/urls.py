from django.urls import path
from . import views

urlpatterns = [
    # =======================
    # 🔹 Dashboard
    # =======================
    path('', views.dashboard, name='dashboard'),

    # =======================
    # 🔹 Rooms
    # =======================
    path('rooms/', views.room_list, name='room_list'),
    path('rooms/create/', views.room_create, name='room_create'),
    path('rooms/<int:pk>/edit/', views.room_edit, name='room_edit'),
    path('rooms/<int:pk>/delete/', views.room_delete, name='room_delete'),
    path('rooms/available/', views.available_rooms, name='available_rooms'),
    path('rooms/vacant/', views.vacant_rooms, name='vacant_rooms'),

    # =======================
    # 🔹 Guests
    # =======================
    path('guests/', views.guest_list, name='guest_list'),
    path('guests/create/', views.guest_create, name='guest_create'),
    path('guests/<int:pk>/edit/', views.guest_edit, name='guest_edit'),
    path('guests/<int:pk>/delete/', views.guest_delete, name='guest_delete'),

    # =======================
    # 🔹 Bookings
    # =======================
    path('bookings/', views.booking_list, name='booking_list'),
    path('bookings/create/', views.booking_create, name='booking_create'),
    path('bookings/<int:pk>/', views.booking_detail, name='booking_detail'),
    path('bookings/<int:booking_id>/edit/', views.booking_edit, name='booking_edit'),
    path('bookings/<int:pk>/delete/', views.booking_delete, name='booking_delete'),
    path('bookings/<int:pk>/toggle-checkin/', views.toggle_check_in, name='toggle_check_in'),
    path('bookings/<int:booking_id>/mark-paid/', views.mark_as_paid, name='mark_as_paid'),
    path('bookings/history/', views.booking_history, name='booking_history'),
    path('bookings/summary/', views.booking_summary, name='booking_summary'),

    path('bookings/<int:booking_id>/mark_as_checked_out/', views.mark_as_checked_out, name='mark_as_checked_out'),
    path('bookings/<int:booking_id>/add-meal/', views.add_meal_transaction, name='add_meal_transaction'),
    path('bookings/<int:booking_id>/meal/<int:meal_id>/edit/', views.edit_meal_transaction, name='edit_meal_transaction'),
    path('bookings/<int:booking_id>/meal/<int:meal_id>/delete/', views.delete_meal_transaction, name='delete_meal_transaction'),

    # =======================
    # 🔹 Payments
    # =======================
    path('bookings/<int:booking_id>/payment/', views.create_or_update_payment, name='create_or_update_payment'),
    path('bookings/<int:booking_id>/payment/create/', views.create_payment, name='create_payment'),

    # hotel/urls.py

    path('payments/create/<int:booking_id>/', views.payment_create, name='payment_create'),



    # =======================
    # 🔹 Reports
    # =======================
    path('reports/occupancy/', views.occupancy_report, name='occupancy_report'),
    path('reports/revenue/', views.revenue_report, name='revenue_report'),
]
