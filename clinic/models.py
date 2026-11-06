from django.db import models
from django.contrib.auth.models import AbstractUser
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta


class User(AbstractUser):
    ROLE_CHOICES = [
        ('patient', 'Пациент'),
        ('doctor', 'Врач'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient')
    full_name = models.CharField(max_length=200, verbose_name='ФИО')
    dob = models.DateField(null=True, blank=True, verbose_name='Дата рождения')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    city = models.CharField(max_length=100, blank=True, verbose_name='Город')
    address = models.TextField(blank=True, verbose_name='Адрес')
    specialty = models.CharField(max_length=100, blank=True, verbose_name='Специальность')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name='Аватар')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.full_name or self.username

    @property
    def is_doctor(self):
        return self.role == 'doctor'

    @property
    def is_patient(self):
        return self.role == 'patient'

    @property
    def avatar_display_url(self):
        return reverse('avatar_image', args=[self.pk]) if self.avatar else ''


HOSPITAL_NAME = "Городская Поликлиника №1"


class NewsArticle(models.Model):
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    summary = models.CharField(max_length=400, blank=True, verbose_name='Краткое описание')
    content = models.TextField(verbose_name='Текст новости')
    published_at = models.DateTimeField(default=timezone.now, verbose_name='Дата публикации')
    is_published = models.BooleanField(default=False, verbose_name='Опубликовано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')

    class Meta:
        verbose_name = 'Новость'
        verbose_name_plural = 'Новости'
        ordering = ['-published_at', '-id']

    def __str__(self):
        return self.title


class Appointment(models.Model):
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='patient_appointments',
                                verbose_name='Пациент')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_appointments',
                               verbose_name='Врач')
    appt_date = models.DateField(verbose_name='Дата приёма')
    appt_time = models.TimeField(verbose_name='Время приёма')
    snils = models.CharField(max_length=20, verbose_name='СНИЛС')
    hospital_name = models.CharField(max_length=200, default=HOSPITAL_NAME, verbose_name='Больница')
    visited = models.BooleanField(default=False, verbose_name='Посетил')
    report = models.TextField(blank=True, null=True, verbose_name='Протокол осмотра')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Запись на приём'
        verbose_name_plural = 'Записи на приём'
        ordering = ['appt_date', 'appt_time']
        constraints = [
            models.UniqueConstraint(
                fields=['doctor', 'appt_date', 'appt_time'],
                name='unique_doctor_appointment_slot',
            ),
        ]

    def __str__(self):
        return f"{self.patient} → {self.doctor} ({self.appt_date} {self.appt_time})"

    @property
    def status_display(self):
        return 'Посетил' if self.visited else 'Ожидается'


class AppointmentReview(models.Model):
    RATING_CHOICES = [
        (1, '1 — Очень плохо'),
        (2, '2 — Плохо'),
        (3, '3 — Нормально'),
        (4, '4 — Хорошо'),
        (5, '5 — Отлично'),
    ]

    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name='review',
        verbose_name='Приём',
    )
    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='appointment_reviews',
        verbose_name='Пациент',
    )
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES, verbose_name='Оценка')
    text = models.TextField(max_length=2000, verbose_name='Отзыв')
    is_published = models.BooleanField(default=False, verbose_name='Опубликован')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Отправлен')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Изменён')

    class Meta:
        verbose_name = 'Отзыв о приёме'
        verbose_name_plural = 'Отзывы о приёмах'
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name='appointment_review_rating_1_to_5',
            ),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.appointment_id and self.patient_id:
            if self.appointment.patient_id != self.patient_id:
                raise ValidationError({'patient': 'Отзыв может оставить только пациент этой записи.'})

    def __str__(self):
        return f'{self.patient} — {self.get_rating_display()}'


def generate_time_slots():
    """Generate 15-minute time slots from 08:00 to 18:00."""
    slots = []
    start = datetime.strptime('08:00', '%H:%M')
    end = datetime.strptime('18:00', '%H:%M')
    while start <= end:
        slots.append(start.strftime('%H:%M'))
        start += timedelta(minutes=15)
    return slots


def get_available_slots(doctor_id, date_str, exclude_appt_id=None):
    """Return list of available time slots for a doctor on a given date."""
    all_slots = generate_time_slots()
    qs = Appointment.objects.filter(doctor_id=doctor_id, appt_date=date_str)
    if exclude_appt_id:
        qs = qs.exclude(id=exclude_appt_id)
    booked = set(qs.values_list('appt_time', flat=True))
    booked_str = {t.strftime('%H:%M') if hasattr(t, 'strftime') else str(t)[:5] for t in booked}
    return [s for s in all_slots if s not in booked_str]
