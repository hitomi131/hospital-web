import sqlite3
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from clinic.models import Appointment, User


def parse_legacy_date(value):
    if not value:
        return None
    for pattern in ('%Y-%m-%d', '%d.%m.%Y'):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    return None


def parse_legacy_time(value):
    if not value:
        return None
    for pattern in ('%H:%M', '%H:%M:%S'):
        try:
            return datetime.strptime(value, pattern).time()
        except ValueError:
            continue
    return None


class Command(BaseCommand):
    help = 'Import accounts and appointments from the old Tkinter hospital.db file.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            default=str(settings.BASE_DIR / 'hospital.db'),
            help='Path to the legacy SQLite database (default: hospital.db in the project folder).',
        )

    def handle(self, *args, **options):
        source_path = Path(options['path']).expanduser()
        if not source_path.is_file():
            raise CommandError(f'Legacy database not found: {source_path}')

        try:
            source = sqlite3.connect(f'file:{source_path.resolve().as_posix()}?mode=ro', uri=True)
            source.row_factory = sqlite3.Row
            users = source.execute('SELECT * FROM users ORDER BY id').fetchall()
            appointments = source.execute('SELECT * FROM appointments ORDER BY id').fetchall()
        except sqlite3.Error as exc:
            raise CommandError(f'Cannot read legacy database: {exc}') from exc
        finally:
            if 'source' in locals():
                source.close()

        account_map = {}
        imported_users = 0
        imported_appointments = 0
        skipped_appointments = 0

        with transaction.atomic():
            for old_user in users:
                username = (old_user['username'] or '').strip()
                if not username:
                    continue
                role = old_user['role'] if old_user['role'] in {'patient', 'doctor'} else 'patient'
                user = User.objects.filter(username=username).first()
                if user is None:
                    user = User(
                        username=username,
                        role=role,
                        full_name=old_user['full_name'] or username,
                        dob=parse_legacy_date(old_user['dob']),
                        phone=old_user['phone'] or '',
                        city=old_user['city'] or '',
                        address=old_user['address'] or '',
                        specialty=old_user['specialty'] or '',
                    )
                    user.set_password(old_user['password'] or None)
                    user.save()
                    imported_users += 1
                account_map[old_user['id']] = user

            for old_appt in appointments:
                patient = account_map.get(old_appt['patient_id'])
                doctor = account_map.get(old_appt['doctor_id'])
                appt_date = parse_legacy_date(old_appt['appt_date'])
                appt_time = parse_legacy_time(old_appt['appt_time'])
                if not patient or not doctor or doctor.role != 'doctor' or not appt_date or not appt_time:
                    skipped_appointments += 1
                    continue

                try:
                    with transaction.atomic():
                        _, created = Appointment.objects.get_or_create(
                            doctor=doctor,
                            appt_date=appt_date,
                            appt_time=appt_time,
                            defaults={
                                'patient': patient,
                                'snils': old_appt['snils'] or '',
                                'hospital_name': old_appt['hospital_name'] or Appointment._meta.get_field('hospital_name').default,
                                'visited': bool(old_appt['visited']),
                                'report': old_appt['report'] or '',
                            },
                        )
                    imported_appointments += int(created)
                    skipped_appointments += int(not created)
                except IntegrityError:
                    skipped_appointments += 1

        self.stdout.write(self.style.SUCCESS(
            f'Imported {imported_users} user(s) and {imported_appointments} appointment(s).'
        ))
        if skipped_appointments:
            self.stdout.write(self.style.WARNING(
                f'Skipped {skipped_appointments} appointment(s) that were invalid or already present.'
            ))
