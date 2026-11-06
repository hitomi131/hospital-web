from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, Appointment, AppointmentReview


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Логин',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Введите логин',
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Введите пароль',
            'autocomplete': 'current-password',
        })
    )


class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Придумайте пароль',
        })
    )
    password_confirm = forms.CharField(
        label='Подтвердите пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Повторите пароль',
        })
    )

    class Meta:
        model = User
        fields = ['username', 'full_name', 'dob', 'phone', 'city', 'address']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Логин для входа'}),
            'full_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Фамилия Имя Отчество'}),
            'dob': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+7 (999) 000-00-00'}),
            'city': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ваш город'}),
            'address': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Улица, дом, квартира'}),
        }
        labels = {
            'username': 'Логин',
            'full_name': 'ФИО',
            'dob': 'Дата рождения',
            'phone': 'Телефон',
            'city': 'Город',
            'address': 'Адрес',
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Пароли не совпадают!')
        if password:
            try:
                validate_password(password, self.instance)
            except ValidationError as exc:
                self.add_error('password', exc)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = 'patient'
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    avatar = forms.ImageField(
        label='Аватар',
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-input', 'accept': 'image/*'}),
    )
    avatar_clear = forms.BooleanField(label='Удалить текущий аватар', required=False)

    class Meta:
        model = User
        fields = ['full_name', 'dob', 'phone', 'city', 'address', 'avatar']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-input'}),
            'dob': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
            'city': forms.TextInput(attrs={'class': 'form-input'}),
            'address': forms.TextInput(attrs={'class': 'form-input'}),
        }
        labels = {
            'full_name': 'ФИО',
            'dob': 'Дата рождения',
            'phone': 'Телефон',
            'city': 'Город',
            'address': 'Адрес',
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar and avatar.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Размер изображения не должен превышать 5 МБ.')
        return avatar

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('avatar_clear') and not cleaned_data.get('avatar'):
            cleaned_data['avatar'] = False
        return cleaned_data


class AppointmentForm(forms.ModelForm):
    doctor = forms.ModelChoiceField(
        queryset=User.objects.filter(role='doctor'),
        label='Врач',
        widget=forms.Select(attrs={'class': 'form-input', 'id': 'doctor-select'}),
        empty_label='Выберите врача...'
    )
    appt_date = forms.DateField(
        label='Дата приёма',
        widget=forms.DateInput(attrs={'class': 'form-input', 'type': 'date', 'id': 'appt-date'}),
    )
    appt_time = forms.ChoiceField(
        label='Время приёма',
        choices=[],
        widget=forms.Select(attrs={'class': 'form-input', 'id': 'appt-time'}),
    )
    snils = forms.CharField(
        label='СНИЛС',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '000-000-000 00',
            'maxlength': '14',
        })
    )

    class Meta:
        model = Appointment
        fields = ['doctor', 'appt_date', 'appt_time', 'snils']

    def __init__(self, *args, **kwargs):
        available_slots = kwargs.pop('available_slots', [])
        super().__init__(*args, **kwargs)
        slot_choices = [(s, s) for s in available_slots]
        self.fields['appt_time'].choices = [('', 'Сначала выберите врача и дату...')] + slot_choices


class AppointmentReviewForm(forms.ModelForm):
    rating = forms.ChoiceField(
        label='Оценка приёма',
        choices=AppointmentReview.RATING_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'rating-radio'}),
    )
    text = forms.CharField(
        label='Ваш отзыв',
        max_length=2000,
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 6,
            'placeholder': 'Расскажите о впечатлениях от приёма. Не указывайте диагнозы и другие личные медицинские сведения — отзыв может быть опубликован после проверки.',
        }),
    )

    class Meta:
        model = AppointmentReview
        fields = ['rating', 'text']
