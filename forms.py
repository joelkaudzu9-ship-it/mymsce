# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
import re


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')


# forms.py - Update the RegistrationForm phone validation

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=9, max=15)])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])

    def validate_phone(self, phone):
        """Validate Malawian phone number - more flexible validation"""
        import re

        # Remove all non-digit characters
        number = re.sub(r'\D', '', phone.data)

        # Check if it's a valid Malawian number
        # Valid formats:
        # - 9 digits starting with 8 or 9 (after removing leading codes)
        # - Can have 0, +265, or 265 prefix

        # Remove country code if present
        if number.startswith('265'):
            number = number[3:]
        elif number.startswith('0'):
            number = number[1:]

        # Now we should have 9 digits
        if len(number) != 9:
            raise ValidationError('Phone number must be 9 digits (e.g., 09832471727)')

        # Check if it starts with valid prefix (8 or 9 for Malawi)
        if not (number.startswith('8') or number.startswith('9')):
            raise ValidationError('Invalid Malawian phone number prefix')

        # Check if all characters are digits
        if not number.isdigit():
            raise ValidationError('Phone number must contain only digits')

        # If we get here, it's valid
        return True


# forms.py - Update PaymentForm phone validation

class PaymentForm(FlaskForm):
    phone_number = StringField('Mobile Money Number', validators=[DataRequired()])
    payment_method = SelectField('Payment Method', choices=[
        ('airtel', 'Airtel Money'),
        ('tnm', 'TNM Mpamba')
    ], validators=[DataRequired()])

    def validate_phone_number(self, phone):
        """Validate Malawian phone number for payments"""
        import re

        # Remove all non-digit characters
        number = re.sub(r'\D', '', phone.data)

        # Remove country code if present
        if number.startswith('265'):
            number = number[3:]
        elif number.startswith('0'):
            number = number[1:]

        # Now we should have 9 digits
        if len(number) != 9:
            raise ValidationError('Phone number must be 9 digits (e.g., 09832471727)')

        # Check if it starts with valid prefix (8 or 9 for Malawi)
        if not (number.startswith('8') or number.startswith('9')):
            raise ValidationError('Invalid Malawian phone number prefix')

        # Format the number consistently for storage
        # Store as 0 + 9 digits
        phone.data = f"0{number}"

        return True


class RequestResetForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
#    email = StringField('Email', validators=[DataRequired(), Email()])


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])