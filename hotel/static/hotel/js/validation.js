/**
 * Client-side form validation for hotel management system
 * Provides real-time validation feedback and security
 */

// Validation utilities
const ValidationUtils = {
    // Email validation
    isValidEmail: (email) => {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },

    // Phone validation
    isValidPhone: (phone) => {
        const phoneDigits = phone.replace(/\D/g, '');
        return phoneDigits.length >= 10 && phoneDigits.length <= 15;
    },

    // Name validation
    isValidName: (name) => {
        const nameRegex = /^[a-zA-Z\s\-'\.]+$/;
        return name.trim().length >= 2 && nameRegex.test(name);
    },

    // Date validation
    isValidDate: (dateStr) => {
        const date = new Date(dateStr);
        return date instanceof Date && !isNaN(date);
    },

    // Future date validation
    isFutureDate: (dateStr) => {
        const date = new Date(dateStr);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        return date >= today;
    },

    // Date range validation
    isValidDateRange: (startDate, endDate) => {
        const start = new Date(startDate);
        const end = new Date(endDate);
        return end > start;
    },

    // Positive number validation
    isPositiveNumber: (value) => {
        const num = parseFloat(value);
        return !isNaN(num) && num > 0;
    },

    // Sanitize HTML input
    sanitizeHtml: (str) => {
        const temp = document.createElement('div');
        temp.textContent = str;
        return temp.innerHTML;
    },

    // Show validation error
    showError: (field, message) => {
        const errorElement = field.parentElement.querySelector('.validation-error');
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.style.display = 'block';
        } else {
            const error = document.createElement('div');
            error.className = 'validation-error text-danger small mt-1';
            error.textContent = message;
            field.parentElement.appendChild(error);
        }
        field.classList.add('is-invalid');
    },

    // Clear validation error
    clearError: (field) => {
        const errorElement = field.parentElement.querySelector('.validation-error');
        if (errorElement) {
            errorElement.style.display = 'none';
        }
        field.classList.remove('is-invalid');
        field.classList.add('is-valid');
    }
};

// Guest form validation
class GuestFormValidator {
    constructor(form) {
        this.form = form;
        this.init();
    }

    init() {
        const nameField = this.form.querySelector('[name="name"]');
        const emailField = this.form.querySelector('[name="email"]');
        const phoneField = this.form.querySelector('[name="phone"]');
        const dobField = this.form.querySelector('[name="date_of_birth"]');

        if (nameField) this.validateName(nameField);
        if (emailField) this.validateEmail(emailField);
        if (phoneField) this.validatePhone(phoneField);
        if (dobField) this.validateDateOfBirth(dobField);

        this.form.addEventListener('submit', (e) => this.validateForm(e));
    }

    validateName(field) {
        field.addEventListener('blur', () => {
            const value = field.value.trim();
            if (!value) {
                ValidationUtils.showError(field, 'Name is required');
                return false;
            }
            if (!ValidationUtils.isValidName(value)) {
                ValidationUtils.showError(field, 'Name can only contain letters, spaces, hyphens, and apostrophes');
                return false;
            }
            if (value.length < 2) {
                ValidationUtils.showError(field, 'Name must be at least 2 characters long');
                return false;
            }
            ValidationUtils.clearError(field);
            return true;
        });
    }

    validateEmail(field) {
        field.addEventListener('blur', () => {
            const value = field.value.trim();
            if (!value) {
                ValidationUtils.showError(field, 'Email is required');
                return false;
            }
            if (!ValidationUtils.isValidEmail(value)) {
                ValidationUtils.showError(field, 'Please enter a valid email address');
                return false;
            }
            ValidationUtils.clearError(field);
            return true;
        });
    }

    validatePhone(field) {
        field.addEventListener('blur', () => {
            const value = field.value.trim();
            if (value && !ValidationUtils.isValidPhone(value)) {
                ValidationUtils.showError(field, 'Phone number must be at least 10 digits');
                return false;
            }
            ValidationUtils.clearError(field);
            return true;
        });
    }

    validateDateOfBirth(field) {
        field.addEventListener('blur', () => {
            const value = field.value;
            if (value) {
                const date = new Date(value);
                const today = new Date();
                const oneYearAgo = new Date(today.getFullYear() - 1, today.getMonth(), today.getDate());
                const maxAge = new Date(today.getFullYear() - 120, today.getMonth(), today.getDate());

                if (date > today) {
                    ValidationUtils.showError(field, 'Date of birth cannot be in the future');
                    return false;
                }
                if (date > oneYearAgo) {
                    ValidationUtils.showError(field, 'Guest must be at least 1 year old');
                    return false;
                }
                if (date < maxAge) {
                    ValidationUtils.showError(field, 'Please enter a valid date of birth');
                    return false;
                }
            }
            ValidationUtils.clearError(field);
            return true;
        });
    }

    validateForm(e) {
        let isValid = true;
        const nameField = this.form.querySelector('[name="name"]');
        const emailField = this.form.querySelector('[name="email"]');

        // Trigger validation for required fields
        nameField.dispatchEvent(new Event('blur'));
        emailField.dispatchEvent(new Event('blur'));

        // Check if any validation errors exist
        const errors = this.form.querySelectorAll('.validation-error[style*="block"]');
        if (errors.length > 0) {
            e.preventDefault();
            isValid = false;
        }

        return isValid;
    }
}

// Room form validation
class RoomFormValidator {
    constructor(form) {
        this.form = form;
        this.init();
    }

    init() {
        const numberField = this.form.querySelector('[name="number"]');
        const capacityField = this.form.querySelector('[name="capacity"]');
        const priceField = this.form.querySelector('[name="price"]');

        if (numberField) this.validateRoomNumber(numberField);
        if (capacityField) this.validateCapacity(capacityField);
        if (priceField) this.validatePrice(priceField);

        this.form.addEventListener('submit', (e) => this.validateForm(e));
    }

    validateRoomNumber(field) {
        field.addEventListener('blur', () => {
            const value = field.value.trim().toUpperCase();
            if (!value) {
                ValidationUtils.showError(field, 'Room number is required');
                return false;
            }
            if (!/^[A-Z0-9\-\s]+$/.test(value)) {
                ValidationUtils.showError(field, 'Room number can only contain letters, numbers, hyphens, and spaces');
                return false;
            }
            field.value = value; // Update to uppercase
            ValidationUtils.clearError(field);
            return true;
        });
    }

    validateCapacity(field) {
        field.addEventListener('blur', () => {
            const value = parseInt(field.value);
            if (!value) {
                ValidationUtils.showError(field, 'Capacity is required');
                return false;
            }
            if (value < 1) {
                ValidationUtils.showError(field, 'Capacity must be at least 1');
                return false;
            }
            if (value > 10) {
                ValidationUtils.showError(field, 'Capacity cannot exceed 10 guests');
                return false;
            }
            ValidationUtils.clearError(field);
            return true;
        });
    }

    validatePrice(field) {
        field.addEventListener('blur', () => {
            const value = parseFloat(field.value);
            if (!value) {
                ValidationUtils.showError(field, 'Price is required');
                return false;
            }
            if (value <= 0) {
                ValidationUtils.showError(field, 'Price must be greater than 0');
                return false;
            }
            if (value > 999999) {
                ValidationUtils.showError(field, 'Price seems unreasonably high');
                return false;
            }
            ValidationUtils.clearError(field);
            return true;
        });
    }

    validateForm(e) {
        let isValid = true;
        const requiredFields = this.form.querySelectorAll('[name="number"], [name="capacity"], [name="price"]');

        requiredFields.forEach(field => {
            field.dispatchEvent(new Event('blur'));
        });

        const errors = this.form.querySelectorAll('.validation-error[style*="block"]');
        if (errors.length > 0) {
            e.preventDefault();
            isValid = false;
        }

        return isValid;
    }
}

// Booking form validation
class BookingFormValidator {
    constructor(form) {
        this.form = form;
        this.init();
    }

    init() {
        const guestField = this.form.querySelector('[name="guest"]');
        const roomField = this.form.querySelector('[name="room"]');
        const checkInField = this.form.querySelector('[name="check_in"]');
        const checkOutField = this.form.querySelector('[name="check_out"]');

        if (guestField) this.validateGuest(guestField);
        if (roomField) this.validateRoom(roomField);
        if (checkInField) this.validateCheckIn(checkInField);
        if (checkOutField) this.validateCheckOut(checkOutField);

        // Cross-field validation
        if (checkInField && checkOutField) {
            this.validateDateRange(checkInField, checkOutField);
        }

        this.form.addEventListener('submit', (e) => this.validateForm(e));
    }

    validateGuest(field) {
        field.addEventListener('change', () => {
            if (!field.value) {
                ValidationUtils.showError(field, 'Please select a guest');
                return false;
            }
            ValidationUtils.clearError(field);
            return true;
        });
    }

    validateRoom(field) {
        field.addEventListener('change', () => {
            if (!field.value) {
                ValidationUtils.showError(field, 'Please select a room');
                return false;
            }
            ValidationUtils.clearError(field);
            this.checkAvailability();
            return true;
        });
    }

    validateCheckIn(field) {
        field.addEventListener('change', () => {
            const value = field.value;
            if (!value) {
                ValidationUtils.showError(field, 'Check-in date is required');
                return false;
            }
            if (!ValidationUtils.isFutureDate(value)) {
                ValidationUtils.showError(field, 'Check-in date cannot be in the past');
                return false;
            }
            
            const checkIn = new Date(value);
            const maxAdvance = new Date();
            maxAdvance.setFullYear(maxAdvance.getFullYear() + 1);
            
            if (checkIn > maxAdvance) {
                ValidationUtils.showError(field, 'Check-in date cannot be more than 1 year in advance');
                return false;
            }
            
            ValidationUtils.clearError(field);
            this.validateDateRangeOnChange();
            return true;
        });
    }

    validateCheckOut(field) {
        field.addEventListener('change', () => {
            const value = field.value;
            if (!value) {
                ValidationUtils.showError(field, 'Check-out date is required');
                return false;
            }
            
            ValidationUtils.clearError(field);
            this.validateDateRangeOnChange();
            return true;
        });
    }

    validateDateRange(checkInField, checkOutField) {
        // This method is called during form submission
        const checkIn = checkInField.value;
        const checkOut = checkOutField.value;

        if (checkIn && checkOut) {
            if (!ValidationUtils.isValidDateRange(checkIn, checkOut)) {
                ValidationUtils.showError(checkOutField, 'Check-out date must be after check-in date');
                return false;
            }

            const start = new Date(checkIn);
            const end = new Date(checkOut);
            const daysDiff = Math.ceil((end - start) / (1000 * 60 * 60 * 24));

            if (daysDiff < 1) {
                ValidationUtils.showError(checkOutField, 'Minimum stay is 1 night');
                return false;
            }

            if (daysDiff > 90) {
                ValidationUtils.showError(checkOutField, 'Maximum stay is 90 days');
                return false;
            }

            ValidationUtils.clearError(checkOutField);
        }
        return true;
    }

    validateDateRangeOnChange() {
        const checkInField = this.form.querySelector('[name="check_in"]');
        const checkOutField = this.form.querySelector('[name="check_out"]');
        this.validateDateRange(checkInField, checkOutField);
    }

    checkAvailability() {
        const roomField = this.form.querySelector('[name="room"]');
        const checkInField = this.form.querySelector('[name="check_in"]');
        const checkOutField = this.form.querySelector('[name="check_out"]');

        if (roomField.value && checkInField.value && checkOutField.value) {
            // You could add AJAX call here to check real-time availability
            // For now, we'll just clear any previous availability errors
            const availabilityError = roomField.parentElement.querySelector('.availability-error');
            if (availabilityError) {
                availabilityError.remove();
            }
        }
    }

    validateForm(e) {
        let isValid = true;
        const requiredFields = this.form.querySelectorAll('[name="guest"], [name="room"], [name="check_in"], [name="check_out"]');

        requiredFields.forEach(field => {
            field.dispatchEvent(new Event('change'));
        });

        // Validate date range
        const checkInField = this.form.querySelector('[name="check_in"]');
        const checkOutField = this.form.querySelector('[name="check_out"]');
        if (!this.validateDateRange(checkInField, checkOutField)) {
            isValid = false;
        }

        const errors = this.form.querySelectorAll('.validation-error[style*="block"]');
        if (errors.length > 0) {
            e.preventDefault();
            isValid = false;
        }

        return isValid;
    }
}

// Payment form validation
class PaymentFormValidator {
    constructor(form) {
        this.form = form;
        this.init();
    }

    init() {
        const amountField = this.form.querySelector('[name="amount"]');
        const methodField = this.form.querySelector('[name="payment_method"]');
        const transactionField = this.form.querySelector('[name="transaction_id"]');

        if (amountField) this.validateAmount(amountField);
        if (methodField) this.validatePaymentMethod(methodField);
        if (transactionField) this.validateTransactionId(transactionField);

        this.form.addEventListener('submit', (e) => this.validateForm(e));
    }

    validateAmount(field) {
        field.addEventListener('blur', () => {
            const value = parseFloat(field.value);
            if (!value) {
                ValidationUtils.showError(field, 'Payment amount is required');
                return false;
            }
            if (value <= 0) {
                ValidationUtils.showError(field, 'Payment amount must be greater than 0');
                return false;
            }
            if (value > 999999) {
                ValidationUtils.showError(field, 'Payment amount seems too high');
                return false;
            }
            ValidationUtils.clearError(field);
            return true;
        });
    }

    validatePaymentMethod(field) {
        field.addEventListener('change', () => {
            if (!field.value) {
                ValidationUtils.showError(field, 'Please select a payment method');
                return false;
            }
            ValidationUtils.clearError(field);
            return true;
        });
    }

    validateTransactionId(field) {
        field.addEventListener('blur', () => {
            const value = field.value.trim();
            if (!value) {
                ValidationUtils.showError(field, 'Transaction ID is required');
                return false;
            }
            ValidationUtils.clearError(field);
            return true;
        });
    }

    validateForm(e) {
        let isValid = true;
        const requiredFields = this.form.querySelectorAll('[name="amount"], [name="payment_method"], [name="transaction_id"]');

        requiredFields.forEach(field => {
            field.dispatchEvent(new Event(field.type === 'select-one' ? 'change' : 'blur'));
        });

        const errors = this.form.querySelectorAll('.validation-error[style*="block"]');
        if (errors.length > 0) {
            e.preventDefault();
            isValid = false;
        }

        return isValid;
    }
}

// Initialize validators when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize form validators based on form type
    const guestForms = document.querySelectorAll('form[action*="guest"]');
    guestForms.forEach(form => new GuestFormValidator(form));

    const roomForms = document.querySelectorAll('form[action*="room"]');
    roomForms.forEach(form => new RoomFormValidator(form));

    const bookingForms = document.querySelectorAll('form[action*="booking"]');
    bookingForms.forEach(form => new BookingFormValidator(form));

    const paymentForms = document.querySelectorAll('form[action*="payment"]');
    paymentForms.forEach(form => new PaymentFormValidator(form));

    // General form security
    document.querySelectorAll('input[type="text"], textarea').forEach(field => {
        field.addEventListener('input', function() {
            // Basic XSS prevention
            if (this.value.includes('<script') || this.value.includes('javascript:')) {
                this.value = ValidationUtils.sanitizeHtml(this.value);
                ValidationUtils.showError(this, 'Invalid characters detected');
            }
        });
    });

    // Auto-format phone numbers
    document.querySelectorAll('input[name="phone"]').forEach(field => {
        field.addEventListener('input', function() {
            let value = this.value.replace(/\D/g, '');
            if (value.length >= 6) {
                value = value.replace(/(\d{3})(\d{3})(\d+)/, '($1) $2-$3');
            } else if (value.length >= 3) {
                value = value.replace(/(\d{3})(\d+)/, '($1) $2');
            }
            this.value = value;
        });
    });

    // Auto-capitalize names
    document.querySelectorAll('input[name="name"]').forEach(field => {
        field.addEventListener('blur', function() {
            this.value = this.value.trim().replace(/\b\w+/g, function(word) {
                return word.charAt(0).toUpperCase() + word.substr(1).toLowerCase();
            });
        });
    });

    console.log('Hotel Management Form Validation Initialized');
});