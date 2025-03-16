from django import forms
from django.contrib.auth.models import User
from .models import Profile
from .models import Address

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email"]

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["mobile_number"]

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['first_name', 'last_name', 'postcode', 'mobile', 'house_no', 'street_address']


class CustomPasswordResetForm(forms.Form):
    email = forms.EmailField(
        label="Enter your email",
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Enter your email"}),
    )

    def clean_email(self):
        email = self.cleaned_data["email"]
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError("No account is associated with this email.")
        return email
    

