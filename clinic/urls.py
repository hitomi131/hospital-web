from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('news/', views.news_list, name='news_list'),
    path('news/<int:pk>/', views.news_detail, name='news_detail'),
    path('doctors/<int:doctor_id>/reviews/', views.doctor_reviews, name='doctor_reviews'),
    path('avatar/<int:user_id>/', views.avatar_image, name='avatar_image'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Patient
    path('book/', views.book_appointment, name='book'),
    path('my-appointments/', views.my_appointments, name='my_appointments'),
    path('appointment/<int:pk>/review/', views.review_appointment, name='review_appointment'),
    path('appointment/<int:pk>/cancel/', views.cancel_appointment, name='cancel_appointment'),
    path('appointment/<int:pk>/reschedule/', views.reschedule_appointment, name='reschedule_appointment'),
    path('reports/', views.patient_reports, name='patient_reports'),
    path('profile/', views.profile, name='profile'),

    # Doctor
    path('doctor/schedule/', views.doctor_schedule, name='doctor_schedule'),
    path('doctor/appointment/<int:pk>/toggle/', views.toggle_visited, name='toggle_visited'),
    path('doctor/appointment/<int:pk>/report/', views.write_report, name='write_report'),
    path('doctor/reports/', views.doctor_reports, name='doctor_reports'),
    path('doctor/medical-records/', views.doctor_medical_records, name='doctor_medical_records'),
    path('doctor/medical-records/<int:patient_id>/', views.doctor_medical_record, name='doctor_medical_record'),

    # AJAX
    path('ajax/slots/', views.get_slots_ajax, name='get_slots'),
]
