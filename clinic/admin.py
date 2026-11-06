from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Appointment, AppointmentReview, NewsArticle


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Доп. информация', {'fields': ('role', 'full_name', 'dob', 'phone', 'city', 'address', 'specialty', 'avatar')}),
    )
    list_display = ['username', 'full_name', 'role', 'phone', 'city']
    list_filter = ['role']
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'full_name', 'role', 'specialty', 'password1', 'password2'),
        }),
    )


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'appt_date', 'appt_time', 'visited']
    list_filter = ['visited', 'appt_date', 'doctor']
    search_fields = ['patient__full_name', 'doctor__full_name', 'snils']


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'published_at', 'is_published']
    list_filter = ['is_published', 'published_at']
    search_fields = ['title', 'summary', 'content']
    list_editable = ['is_published']
    ordering = ['-published_at']
    fieldsets = (
        (None, {'fields': ('title', 'summary', 'content')}),
        ('Публикация', {'fields': ('published_at', 'is_published')}),
    )


@admin.register(AppointmentReview)
class AppointmentReviewAdmin(admin.ModelAdmin):
    list_display = ['patient', 'appointment', 'rating', 'is_published', 'created_at']
    list_filter = ['is_published', 'rating', 'created_at']
    list_editable = ['is_published']
    search_fields = ['patient__full_name', 'appointment__doctor__full_name', 'text']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        (None, {'fields': ('appointment', 'patient', 'rating', 'text')}),
        ('Модерация', {'fields': ('is_published', 'created_at', 'updated_at')}),
    )
