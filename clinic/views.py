from functools import wraps
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import FileResponse, JsonResponse, HttpResponseForbidden, Http404
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, Q
from django.utils.dateparse import parse_date, parse_time
from django.utils import timezone
from PIL import Image
from .models import User, Appointment, AppointmentReview, NewsArticle, get_available_slots, HOSPITAL_NAME
from .forms import LoginForm, RegisterForm, ProfileForm, AppointmentReviewForm


def role_required(*roles):
    """Enforce role permissions on the server for every protected view."""
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if request.user.role not in roles:
                return HttpResponseForbidden('Недостаточно прав для этого действия.')
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


def get_bookable_slots(doctor_id, selected_date, exclude_appt_id=None):
    slots = get_available_slots(doctor_id, selected_date, exclude_appt_id)
    if selected_date == timezone.localdate():
        now = timezone.localtime().time().replace(second=0, microsecond=0)
        slots = [slot for slot in slots if parse_time(slot) > now]
    return slots


def appointment_has_passed(appointment):
    today = timezone.localdate()
    if appointment.appt_date < today:
        return True
    if appointment.appt_date > today:
        return False
    return appointment.appt_time <= timezone.localtime().time().replace(second=0, microsecond=0)


def public_doctors(limit=None):
    approved_review = Q(doctor_appointments__review__is_published=True)
    doctors = User.objects.filter(role='doctor', is_active=True).annotate(
        average_rating=Avg('doctor_appointments__review__rating', filter=approved_review),
        review_count=Count('doctor_appointments__review', filter=approved_review, distinct=True),
    ).order_by('full_name')
    return doctors[:limit] if limit else doctors


def avatar_image(request, user_id):
    user = get_object_or_404(User, pk=user_id, is_active=True)
    if user.is_patient and (not request.user.is_authenticated or request.user.pk != user.pk):
        return HttpResponseForbidden('Аватар доступен только владельцу профиля.')
    if not user.avatar:
        raise Http404('Аватар не загружен.')

    try:
        with Image.open(user.avatar) as image:
            content_type = image.get_format_mimetype()
        user.avatar.open('rb')
    except (OSError, ValueError):
        raise Http404('Не удалось прочитать изображение.')

    response = FileResponse(user.avatar.file, content_type=content_type)
    response['Cache-Control'] = 'private, max-age=300' if user.is_patient else 'public, max-age=3600'
    return response


# ==========================================
# HOME & AUTH VIEWS
# ==========================================

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    news = NewsArticle.objects.filter(
        is_published=True,
        published_at__lte=timezone.now(),
    )[:3]
    doctors = public_doctors(limit=6)
    return render(request, 'clinic/home.html', {'news': news, 'doctors': doctors})


def about(request):
    doctors = public_doctors()
    return render(request, 'clinic/about.html', {'doctors': doctors})


def news_list(request):
    news = NewsArticle.objects.filter(
        is_published=True,
        published_at__lte=timezone.now(),
    )
    return render(request, 'clinic/news_list.html', {'news': news})


def news_detail(request, pk):
    article = get_object_or_404(
        NewsArticle,
        pk=pk,
        is_published=True,
        published_at__lte=timezone.now(),
    )
    return render(request, 'clinic/news_detail.html', {'article': article})


def doctor_reviews(request, doctor_id):
    doctor = get_object_or_404(User, pk=doctor_id, role='doctor', is_active=True)
    reviews = AppointmentReview.objects.filter(
        appointment__doctor=doctor,
        is_published=True,
    ).select_related('appointment').order_by('-created_at')
    rating_summary = reviews.aggregate(average=Avg('rating'), count=Count('id'))
    return render(request, 'clinic/doctor_public_reviews.html', {
        'doctor': doctor,
        'reviews': reviews,
        'average_rating': rating_summary['average'],
        'review_count': rating_summary['count'],
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.full_name or user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Неверный логин или пароль.')

    return render(request, 'clinic/login.html', {'form': form})


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, 'Вы успешно вышли из системы.')
    return redirect('login')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно! Добро пожаловать!')
            return redirect('dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')

    return render(request, 'clinic/register.html', {'form': form})


# ==========================================
# DASHBOARD
# ==========================================

@login_required
def dashboard(request):
    user = request.user
    if user.is_staff:
        return redirect('admin:index')
    if user.is_doctor:
        return redirect('doctor_schedule')

    # Patient dashboard
    today = timezone.localdate()
    upcoming = Appointment.objects.filter(patient=user).filter(
        Q(appt_date__gt=today) | Q(appt_date=today, appt_time__gt=timezone.localtime().time())
    ).select_related('doctor').order_by('appt_date', 'appt_time')[:3]

    total = Appointment.objects.filter(patient=user).count()
    visited = Appointment.objects.filter(patient=user, visited=True).count()
    pending = Appointment.objects.filter(patient=user, visited=False).filter(
        Q(appt_date__gt=today) | Q(appt_date=today, appt_time__gt=timezone.localtime().time())
    ).count()

    context = {
        'upcoming': upcoming,
        'total': total,
        'visited': visited,
        'pending': pending,
    }
    return render(request, 'clinic/patient/dashboard.html', context)


# ==========================================
# PATIENT VIEWS
# ==========================================

@role_required('patient')
def book_appointment(request):
    today = timezone.localdate()
    today_str = today.isoformat()
    doctors = User.objects.filter(role='doctor')

    if request.method == 'POST':
        doctor_id = request.POST.get('doctor')
        appt_date = request.POST.get('appt_date')
        appt_time = request.POST.get('appt_time')
        snils = request.POST.get('snils', '').strip()

        appt_day = parse_date(appt_date or '')
        appt_clock = parse_time(appt_time or '')
        try:
            doctor_pk = int(doctor_id)
        except (TypeError, ValueError):
            doctor_pk = None
        doctor = User.objects.filter(id=doctor_pk, role='doctor').first() if doctor_pk else None
        digits_only = re.sub(r'[^0-9]', '', snils)
        errors = []
        if not doctor:
            errors.append('Выберите врача из списка.')
        if not appt_day or appt_day < today:
            errors.append('Выберите корректную дату не раньше сегодняшнего дня.')
        available = get_bookable_slots(doctor.id, appt_day) if doctor and appt_day and appt_day >= today else []
        if not appt_clock or appt_time not in available:
            errors.append('Выберите свободное время из списка.')
        if len(digits_only) != 11:
            errors.append('СНИЛС должен содержать 11 цифр.')

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            try:
                with transaction.atomic():
                    # Recheck the slot inside the write transaction; the DB constraint
                    # also prevents two requests claiming the same doctor/time.
                    if appt_time not in get_bookable_slots(doctor.id, appt_day):
                        raise ValueError('Это время уже занято. Выберите другой слот.')
                    Appointment.objects.create(
                        patient=request.user,
                        doctor=doctor,
                        appt_date=appt_day,
                        appt_time=appt_clock,
                        snils=f'{digits_only[:3]}-{digits_only[3:6]}-{digits_only[6:9]} {digits_only[9:]}',
                        hospital_name=HOSPITAL_NAME,
                    )
            except (IntegrityError, ValueError):
                messages.error(request, 'Это время уже занято. Выберите другой слот.')
            else:
                messages.success(request, f'Вы записаны к врачу {doctor.full_name} на {appt_day:%d.%m.%Y} в {appt_clock:%H:%M}.')
                return redirect('my_appointments')

    context = {
        'doctors': doctors,
        'today': today_str,
    }
    return render(request, 'clinic/patient/book.html', context)


@role_required('patient')
def my_appointments(request):
    today = timezone.localdate()
    upcoming = Appointment.objects.filter(patient=request.user).filter(
        Q(appt_date__gt=today) | Q(appt_date=today, appt_time__gt=timezone.localtime().time())
    ).select_related('doctor').order_by('appt_date', 'appt_time')

    past = Appointment.objects.filter(
        patient=request.user,
    ).select_related('doctor', 'review').order_by('-appt_date', '-appt_time')
    past = past.filter(Q(appt_date__lt=today) | Q(appt_date=today, appt_time__lte=timezone.localtime().time()))

    return render(request, 'clinic/patient/my_appointments.html', {
        'upcoming': upcoming,
        'past': past,
        'today': today,
    })


@role_required('patient')
def review_appointment(request, pk):
    appointment = get_object_or_404(
        Appointment.objects.select_related('doctor'),
        pk=pk,
        patient=request.user,
    )
    if not appointment.visited or not appointment_has_passed(appointment):
        messages.error(request, 'Оценить можно только завершённый приём, отмеченный врачом как состоявшийся.')
        return redirect('my_appointments')

    review = AppointmentReview.objects.filter(appointment=appointment).first()
    if review and review.patient_id != request.user.id:
        return HttpResponseForbidden('Недостаточно прав для этого действия.')

    form = AppointmentReviewForm(request.POST or None, instance=review)
    if request.method == 'POST' and form.is_valid():
        review = form.save(commit=False)
        review.appointment = appointment
        review.patient = request.user
        # New and edited reviews require administrator approval before public display.
        review.is_published = False
        review.save()
        messages.success(request, 'Спасибо! Отзыв отправлен на проверку перед публикацией.')
        return redirect('my_appointments')

    return render(request, 'clinic/patient/review_appointment.html', {
        'appointment': appointment,
        'form': form,
        'has_existing_review': bool(review),
    })


@role_required('patient')
@require_POST
def cancel_appointment(request, pk):
    appt = get_object_or_404(Appointment, pk=pk, patient=request.user)
    if appointment_has_passed(appt) or appt.visited:
        messages.error(request, 'Прошедший или завершённый приём нельзя отменить.')
        return redirect('my_appointments')
    appt.delete()
    messages.success(request, 'Запись успешно отменена.')
    return redirect('my_appointments')


@role_required('patient')
def reschedule_appointment(request, pk):
    appt = get_object_or_404(Appointment, pk=pk, patient=request.user)
    if appointment_has_passed(appt) or appt.visited:
        messages.error(request, 'Прошедший или завершённый приём нельзя перенести.')
        return redirect('my_appointments')

    if request.method == 'POST':
        new_date = request.POST.get('appt_date')
        new_time = request.POST.get('appt_time')

        parsed_day = parse_date(new_date or '')
        parsed_time = parse_time(new_time or '')
        if parsed_day and parsed_day >= timezone.localdate() and parsed_time and new_time in get_bookable_slots(
            appt.doctor_id, parsed_day, exclude_appt_id=pk
        ):
            appt.appt_date = parsed_day
            appt.appt_time = parsed_time
            try:
                appt.save(update_fields=['appt_date', 'appt_time'])
            except IntegrityError:
                messages.error(request, 'Это время уже занято. Выберите другой слот.')
            else:
                messages.success(request, f'Запись перенесена на {parsed_day:%d.%m.%Y} в {parsed_time:%H:%M}.')
                return redirect('my_appointments')
        else:
            messages.error(request, 'Выберите корректную будущую дату и свободное время.')

    return render(request, 'clinic/patient/reschedule.html', {
        'appt': appt,
        'today': timezone.localdate().isoformat(),
    })


@role_required('patient')
def patient_reports(request):
    reports = Appointment.objects.filter(
        patient=request.user,
        report__isnull=False,
    ).exclude(report='').select_related('doctor').order_by('-appt_date')

    return render(request, 'clinic/patient/reports.html', {'reports': reports})


@role_required('patient', 'doctor')
def profile(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == 'POST':
        if form.is_valid():
            previous_avatar = request.user.avatar.name
            user = form.save()
            if previous_avatar and previous_avatar != user.avatar.name:
                user.avatar.storage.delete(previous_avatar)
            messages.success(request, 'Данные профиля обновлены!')
            return redirect('profile')

    return render(request, 'clinic/patient/profile.html', {'form': form})


# ==========================================
# DOCTOR VIEWS
# ==========================================

@role_required('doctor')
def doctor_schedule(request):
    requested_date = parse_date(request.GET.get('date', ''))
    selected_date = requested_date or timezone.localdate()

    appointments = Appointment.objects.filter(
        doctor=request.user, appt_date=selected_date
    ).select_related('patient').order_by('appt_time')

    return render(request, 'clinic/doctor/schedule.html', {
        'appointments': appointments,
        'selected_date': selected_date,
        'today': timezone.localdate().isoformat(),
    })


@role_required('doctor')
@require_POST
def toggle_visited(request, pk):
    appt = get_object_or_404(Appointment, pk=pk, doctor=request.user)
    appt.visited = not appt.visited
    appt.save()

    return JsonResponse({'visited': appt.visited, 'id': appt.id})


@role_required('doctor')
def write_report(request, pk):
    appt = get_object_or_404(Appointment, pk=pk, doctor=request.user)

    if request.method == 'POST':
        report_text = request.POST.get('report', '').strip()
        if not report_text:
            messages.error(request, 'Заполните текст протокола.')
            return render(request, 'clinic/doctor/write_report.html', {'appt': appt})
        if len(report_text) > 20000:
            messages.error(request, 'Протокол слишком длинный (максимум 20 000 символов).')
            return render(request, 'clinic/doctor/write_report.html', {'appt': appt})
        appt.report = report_text
        appt.visited = True
        appt.save()
        messages.success(request, 'Протокол осмотра сохранён.')
        return redirect('doctor_schedule')

    return render(request, 'clinic/doctor/write_report.html', {'appt': appt})


@role_required('doctor')
def doctor_reports(request):
    reports = Appointment.objects.filter(
        doctor=request.user,
        report__isnull=False,
    ).exclude(report='').select_related('patient').order_by('-appt_date', '-appt_time')
    return render(request, 'clinic/doctor/reports.html', {'reports': reports})


@role_required('doctor')
def doctor_medical_records(request):
    patients = User.objects.filter(
        role='patient',
        patient_appointments__doctor=request.user,
    ).distinct().order_by('full_name')

    search_query = request.GET.get('q', '').strip()
    if search_query:
        patients = patients.filter(full_name__icontains=search_query)

    return render(request, 'clinic/doctor/medical_records.html', {
        'patients': patients,
        'search_query': search_query,
    })


@role_required('doctor')
def doctor_medical_record(request, patient_id):
    patient = get_object_or_404(
        User,
        pk=patient_id,
        role='patient',
        patient_appointments__doctor=request.user,
    )
    appointments = Appointment.objects.filter(
        patient=patient,
    ).select_related('doctor').order_by('-appt_date', '-appt_time')

    return render(request, 'clinic/doctor/medical_record.html', {
        'patient': patient,
        'appointments': appointments,
    })


# ==========================================
# AJAX VIEWS
# ==========================================

@role_required('patient')
def get_slots_ajax(request):
    doctor_id = request.GET.get('doctor_id')
    date_str = request.GET.get('date')
    exclude_id = request.GET.get('exclude_id')

    selected_date = parse_date(date_str or '')
    try:
        doctor_pk = int(doctor_id)
    except (TypeError, ValueError):
        doctor_pk = None
    if not doctor_pk or not selected_date or selected_date < timezone.localdate():
        return JsonResponse({'slots': []})
    if not User.objects.filter(id=doctor_pk, role='doctor').exists():
        return JsonResponse({'slots': []})
    if exclude_id:
        try:
            exclude_pk = int(exclude_id)
        except (TypeError, ValueError):
            return JsonResponse({'slots': []})
        owns_excluded = Appointment.objects.filter(
            id=exclude_pk, patient=request.user, doctor_id=doctor_pk
        ).exists()
        if not owns_excluded:
            return JsonResponse({'slots': []})
    slots = get_bookable_slots(doctor_pk, selected_date, exclude_appt_id=exclude_id or None)
    return JsonResponse({'slots': slots})
