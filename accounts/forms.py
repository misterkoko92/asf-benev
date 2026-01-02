from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserChangeForm, UserCreationForm

from volunteers.models import VolunteerProfile
from volunteers.utils import PHONE_COUNTRY_CHOICES, format_phone, normalize_phone_number

from .models import User


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Mail",
        widget=forms.EmailInput(attrs={"type": "email"}),
    )


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email", "first_name", "last_name")


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = ("email", "first_name", "last_name", "is_active", "is_staff")


class SignupForm(forms.Form):
    first_name = forms.CharField(label="Prenom")
    last_name = forms.CharField(label="Nom")
    email = forms.EmailField(label="Mail")
    address_line1 = forms.CharField(label="Rue")
    postal_code = forms.CharField(label="Code postal")
    city = forms.CharField(label="Ville")
    country = forms.CharField(label="Pays")
    phone_country = forms.ChoiceField(
        choices=PHONE_COUNTRY_CHOICES,
        label="Indicatif",
        initial="+33",
    )
    phone_number = forms.CharField(
        label="Numero de telephone",
        help_text="format attendu : +33 601020304",
    )
    geo_latitude = forms.DecimalField(required=False, widget=forms.HiddenInput)
    geo_longitude = forms.DecimalField(required=False, widget=forms.HiddenInput)
    password1 = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput,
    )
    password2 = forms.CharField(
        label="Confirmation mot de passe",
        widget=forms.PasswordInput,
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Un compte existe deja avec ce mail.")
        return email

    def clean_phone_number(self):
        number = normalize_phone_number(self.cleaned_data.get("phone_number"))
        if not number or not number.isdigit():
            raise forms.ValidationError("Numero invalide.")
        return number

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Les mots de passe ne correspondent pas.")
        return cleaned

    def save(self):
        email = self.cleaned_data["email"]
        user = User.objects.create_user(
            email=email,
            password=self.cleaned_data["password1"],
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
        )
        phone = format_phone(self.cleaned_data.get("phone_country"), self.cleaned_data.get("phone_number"))
        VolunteerProfile.objects.create(
            user=user,
            phone=phone,
            address_line1=self.cleaned_data["address_line1"],
            postal_code=self.cleaned_data["postal_code"],
            city=self.cleaned_data["city"],
            country=self.cleaned_data["country"],
            geo_latitude=self.cleaned_data.get("geo_latitude") or None,
            geo_longitude=self.cleaned_data.get("geo_longitude") or None,
        )
        return user
