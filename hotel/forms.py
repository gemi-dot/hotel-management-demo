from django import forms
from .models import Room, Booking

from .models import Payment
from .models import Guest

from .models import MealTransaction


class GuestForm(forms.ModelForm):
    class Meta:
        model = Guest
        fields = ['name', 'email', 'phone', 'address', 'date_of_birth', 'notes']
class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['number', 'room_type', 'capacity', 'price', 'is_available']
        widgets = {
            'number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter room number'}),
            'room_type': forms.Select(attrs={'class': 'form-select'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter capacity'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter price'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['guest', 'check_in', 'check_out']
        widgets = {
            'check_in': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'check_out': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'guest': forms.Select(attrs={'class': 'form-select'}),
        }

               
class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'payment_method', 'transaction_id']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter payment amount'}),
            'payment_method': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter payment method'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter transaction ID'}),
        }


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['guest', 'room', 'check_in', 'check_out']
        widgets = {
            'check_in': forms.DateInput(attrs={'type': 'date'}),
            'check_out': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        """Validate check-in and check-out dates."""
        cleaned_data = super().clean()
        check_in = cleaned_data.get('check_in')
        check_out = cleaned_data.get('check_out')

        if check_in and check_out and check_in >= check_out:
            raise forms.ValidationError("Check-out date must be after check-in date.")
        return cleaned_data



class MealTransactionForm(forms.ModelForm):
    class Meta:
        model = MealTransaction
        #fields = ['meal_name', 'quantity', 'price_per_unit']
        fields = ['meal_name', 'category', 'quantity', 'price_per_unit']