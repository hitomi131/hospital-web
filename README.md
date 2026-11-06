# Веб-система поликлиники

Веб-приложение на Django сохраняет сценарии старой Tkinter-программы: регистрация пациента, запись к врачу, перенос и отмена записи, расписание врача, отметка посещения и протокол осмотра. Пациенты, врачи и администраторы используют разные права доступа; администраторы управляют записями через Django Admin.

## Первый запуск

Из корня проекта выполните команды в PowerShell:

```powershell
py -m venv .venv --clear
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:DJANGO_DEBUG = "true"
$env:DB_ENGINE = "django.db.backends.sqlite3"
python manage.py migrate
python manage.py import_legacy_db
python manage.py createsuperuser
python manage.py runserver
```

Откройте `http://127.0.0.1:8000/`. Команда импорта читает `hospital.db` и добавляет пользователей и записи в Django-базу `db.sqlite3`. Она повторно запускается безопасно: существующие логины и занятые слоты не перезаписываются. Пароли из старой базы сохраняются для входа, но в новой базе хранятся в хешированном виде. По умолчанию настройки теперь выбирают PostgreSQL; для локального SQLite явно задайте `DB_ENGINE` как в примере выше.

`python app.py` запускает тот же Django-сайт. Прежний настольный интерфейс сохранён как `legacy_tkinter_app.py`; для работы с сайтом запускайте `app.py` или `manage.py`.

После входа администратора откройте `/admin/`, создайте учётные записи врачей и назначьте им роль «Врач». Регистрация на сайте создаёт только пациентские учётные записи.

## Публичная часть сайта

Главная страница показывает последние новости, информацию о поликлинике и список активных врачей. Страницы `/about/` и `/news/` доступны без входа. Администратор публикует новости в `/admin/` → «Новости»: заполните заголовок и текст, включите «Опубликовано» и сохраните запись. Черновики и новости с будущей датой публикации посетителям не показываются. Для новых моделей выполните `python manage.py migrate`.

## Настройки для публикации

Перед запуском на сервере задайте `DJANGO_SECRET_KEY` уникальным секретом, `DJANGO_ALLOWED_HOSTS` списком доменов через запятую и `DJANGO_DEBUG=false`. Для PostgreSQL задайте `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` и `DB_PORT`. Для HTTPS приложение включает secure cookies, перенаправление на HTTPS и HSTS. Не публикуйте `hospital.db`, `db.sqlite3`, резервные копии или секретный ключ в открытом доступе.

### Перенос текущих данных из SQLite в PostgreSQL

Перед переносом сделайте отдельную резервную копию `db.sqlite3` и остановите сайт, чтобы данные не менялись во время экспорта. В PowerShell используйте временный файл вне репозитория:

```powershell
$env:DJANGO_DEBUG = "true"
$env:DB_ENGINE = "django.db.backends.sqlite3"
$env:DB_NAME = (Join-Path (Get-Location) "db.sqlite3")
$fixture = Join-Path $env:TEMP "clinic-sqlite-export.json"
python manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.permission --exclude sessions --exclude admin.logentry --indent 2 -o $fixture

$env:DB_ENGINE = "django.db.backends.postgresql"
$env:DB_NAME = "clinic_db"
python manage.py migrate
python manage.py loaddata $fixture
python manage.py shell -c "from django.apps import apps; print({m.__name__: m.objects.count() for m in apps.get_models() if m._meta.managed})"
Remove-Item -LiteralPath $fixture
```

Экспорт включает пользователей и связанные записи приложения; пароли пользователей переносятся в виде уже сохранённых хешей. Сам файл экспорта содержит персональные данные — храните его только временно и удалите после успешной сверки. Не переключайте production на PostgreSQL до проверки количества записей и входа тестового пользователя.

Настройки из локального `.env` загружаются автоматически библиотекой `python-dotenv`. Скопируйте `.env.example` в `.env`, задайте собственные секреты и не добавляйте `.env` в Git.
