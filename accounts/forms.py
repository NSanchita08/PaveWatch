from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

User = get_user_model()

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Create a password"}),
        label="Password",
        help_text="Choose a strong password."
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm your password"}),
        label="Confirm Password"
    )

    class Meta:
        model = User
        fields = ("username", "email", "phone")
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter username"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "name@example.com"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 9876543210"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email:
            raise ValidationError("Email address is required.")
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with that email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm:
            if password != password_confirm:
                self.add_error("password_confirm", "Passwords do not match.")
            else:
                validate_password(password)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.role = User.Role.CITIZEN  # Registration is always CITIZEN
        if commit:
            user.save()
        return user

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("email", "phone")
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
        }
