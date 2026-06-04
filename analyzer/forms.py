from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


class SimpleSignupForm(UserCreationForm):
    """
    Signup form that uses a valid email address as the username.
    The email is stored in both username and email fields on the User model.
    """
    username = forms.EmailField(
        max_length=150,
        label="Email Address",
        widget=forms.EmailInput(attrs={
            "placeholder": "yourname@gmail.com",
            "autocomplete": "email",
        }),
        help_text="Enter a valid email address (e.g. student@gmail.com)",
    )
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"placeholder": "Create password"}),
        help_text="Use at least 8 characters.",
    )
    password2 = forms.CharField(
        label="Confirm Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm password"}),
        help_text="Enter the same password again.",
    )

    class Meta:
        model = User
        fields = ("username", "password1", "password2")

    def clean_username(self):
        """Validate that the username is a valid email and not already taken."""
        email = self.cleaned_data.get("username", "").strip().lower()
        try:
            validate_email(email)
        except ValidationError:
            raise forms.ValidationError(
                "Please enter a valid email address (e.g. student@gmail.com)."
            )
        
        # Strict prefix verification: reject purely numeric/short email prefixes
        import re
        if '@' in email:
            local_part = email.split('@')[0]
            if len(local_part) < 3:
                raise forms.ValidationError(
                    "Email prefix (the part before @) must be at least 3 characters long."
                )
            if local_part.isdigit():
                raise forms.ValidationError(
                    "Email prefix cannot be purely numeric (e.g. '1234'). Please use a valid personal email."
                )
            if not re.search(r'[a-zA-Z]', local_part):
                raise forms.ValidationError(
                    "Email prefix must contain at least one alphabetical letter (a-z)."
                )

        if User.objects.filter(username=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists. Please login instead."
            )
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2:
            if password1 != password2:
                self.add_error("password2", "The two password fields didn't match.")
            
            if len(password1) < 8:
                self.add_error("password1", "Password must be at least 8 characters long.")
            if not any(c.isupper() for c in password1):
                self.add_error("password1", "Password must contain at least one uppercase letter.")
            if not any(c.islower() for c in password1):
                self.add_error("password1", "Password must contain at least one lowercase letter.")
            if not any(c.isdigit() for c in password1):
                self.add_error("password1", "Password must contain at least one digit.")
            
            import re
            special_chars = r"[!@#$%^&*(),.?\":{}|<>]"
            if not re.search(special_chars, password1):
                self.add_error("password1", "Password must contain at least one special character.")
        
        return cleaned_data

    def save(self, commit=True):
        """Save email into both username and email fields."""
        user = super().save(commit=False)
        user.email = user.username   # mirror email → email field
        if commit:
            user.save()
        return user

