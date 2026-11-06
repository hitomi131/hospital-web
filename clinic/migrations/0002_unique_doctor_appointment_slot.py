from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clinic', '0001_initial'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='appointment',
            constraint=models.UniqueConstraint(
                fields=('doctor', 'appt_date', 'appt_time'),
                name='unique_doctor_appointment_slot',
            ),
        ),
    ]
