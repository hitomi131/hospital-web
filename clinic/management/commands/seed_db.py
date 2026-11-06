from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from clinic.models import User


class Command(BaseCommand):
    help = 'Seed the database with initial data (doctors, etc.)'

    def add_arguments(self, parser):
        parser.add_argument('--password', required=True, help='Password to assign to demo accounts.')

    def handle(self, *args, **options):
        password = options['password']
        try:
            validate_password(password)
        except ValidationError as exc:
            raise CommandError('; '.join(exc.messages)) from exc

        # Create test doctors if none exist
        if not User.objects.filter(role='doctor').exists():
            doctors = [
                {'username': 'doc_ivanov', 'full_name': 'Иванов Иван Иванович', 'specialty': 'Терапевт'},
                {'username': 'doc_petrov', 'full_name': 'Петров Пётр Петрович', 'specialty': 'Хирург'},
                {'username': 'doc_sidorova', 'full_name': 'Сидорова Анна Николаевна', 'specialty': 'Кардиолог'},
                {'username': 'doc_kozlov', 'full_name': 'Козлов Дмитрий Александрович', 'specialty': 'Невролог'},
                {'username': 'doc_morozova', 'full_name': 'Морозова Елена Сергеевна', 'specialty': 'Педиатр'},
            ]
            for d in doctors:
                user = User(
                    username=d['username'],
                    full_name=d['full_name'],
                    specialty=d['specialty'],
                    role='doctor',
                )
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.SUCCESS(f'  Created doctor: {d["full_name"]} ({d["specialty"]})'))

            self.stdout.write(self.style.SUCCESS('Doctors seeded successfully!'))
        else:
            self.stdout.write(self.style.WARNING('Doctors already exist, skipping.'))

        # Create test patient if none exist
        if not User.objects.filter(role='patient').exists():
            patient = User(
                username='patient1',
                full_name='Смирнов Алексей Игоревич',
                role='patient',
                phone='+7 (999) 123-45-67',
                city='Москва',
                address='ул. Ленина, д. 10, кв. 5',
            )
            patient.set_password(password)
            patient.save()
            self.stdout.write(self.style.SUCCESS(f'  Created patient: {patient.full_name}'))
