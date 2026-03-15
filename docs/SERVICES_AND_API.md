# Сервисы и API (план 3.2, 3.3, 4.1–4.4)

## 3.2. Сервисы работы с данными (источники)

| Сервис | Модуль | Описание |
|--------|--------|----------|
| **DataLoaderService** | `kripton.datasources.services.data_loader` | Универсальный загрузчик: CSV → ClickHouse; заготовки под PostgreSQL и Google Sheets. Обновляет `last_load_*` у DataSource. |
| **DataValidatorService** | `kripton.datasources.services.data_validator` | Валидация имён колонок, длины строк, пути к CSV, `connection_data`, данных отчёта (`validate_report_data`). |
| **DataTransformService** | `kripton.datasources.services.data_transform` | Нормализация имён колонок, преобразование строк в словари и обратно, приведение к строкам. |
| **DataPreviewService** | `kripton.datasources.services.data_preview` | Предпросмотр таблицы/запроса в ClickHouse: `preview_table(table_name, limit, offset)`, `preview_query(query)`. |

Импорт: `from kripton.datasources.services import DataLoaderService, DataValidatorService, DataTransformService, DataPreviewService`.

---

## 3.3. API источников данных

Роутер: `GET/POST /api/datasources/`, `GET/PUT/PATCH/DELETE /api/datasources/<id>/`.

| Действие | Метод | URL | Описание |
|----------|--------|-----|----------|
| Список / создание | GET, POST | `/api/datasources/` | Расширенный DataSourceViewSet (поля `last_load_*` в сериализаторе). |
| Проверка подключения | POST | `/api/datasources/<id>/test_connection/` | **DataSourceTestConnectionView** — валидация `connection_data` по типу источника. |
| Запуск загрузки | POST | `/api/datasources/<id>/load/` | **DataSourceLoadView** — вызов DataLoaderService.load(). |
| Статус загрузки | GET | `/api/datasources/<id>/status/` | **DataSourceStatusView** — `last_load_status`, `last_load_at`, `last_load_error`, `last_load_rows`. |
| Предпросмотр | GET | `/api/datasources/<id>/preview/?limit=50&offset=0` | **DataSourcePreviewView** — предпросмотр с пагинацией и полями `columns`, `rows`, `total`. |

Модель **DataSource** дополнена полями: `last_load_status`, `last_load_at`, `last_load_error`, `last_load_rows`. Миграция: `kripton/datasources/migrations/0002_datasource_load_status.py`.

---

## 4.1. Сервис отчётов

| Метод | Описание |
|-------|----------|
| **ReportService.create_report(...)** | Создание отчёта (title, report_type, description, created_by, data, clickhouse_*). |
| **ReportService.submit_report(report)** | Установка `submitted_at`. |
| **ReportService.approve_report(report, approved_by)** | Установка `approved_at`, `approved_by`. |
| **ReportService.generate_pdf(report)** | Экспорт в PDF. |
| **ReportService.generate_excel(report)** | Экспорт в Excel. |
| **ReportService.generate_word(report)** | Экспорт в Word. |
| **ReportService.validate_report(report)** | Валидация `report.data` (возвращает `(ok, errors)`). |

Модуль: `Reports.services.report_service`. В ReportViewSet используются submit, approve, export (через сервис) и добавлен эндпоинт **GET** `/api/reports/reports/<id>/validate/` — ответ `{ "valid": bool, "errors": [...] }`.

---

## 4.2. Сервис уведомлений

| Метод | Описание |
|-------|----------|
| **NotificationService.send_email(to_emails, subject, body)** | Отправка email через Django. |
| **NotificationService.notify_internal(user, message, resource_type, resource_id)** | Внутреннее уведомление — запись в лог аудита. |
| **NotificationService.get_report_request_reminders(days_ahead)** | Список заявок с deadline в ближайшие N дней. |
| **NotificationService.send_deadline_reminders(days_ahead)** | Отправка email-напоминаний по этим заявкам. |

Модуль: `kripton.notifications.services`. Команда для cron: **`python manage.py send_report_reminders --days=3`**.

---

## 4.3. Сервис аудита

| Метод | Описание |
|-------|----------|
| **AuditService.log_action(...)** | Единая точка логирования (обёртка над `log_audit`). |
| **AuditService.log_crud(instance, action, request, user)** | Автоматическое логирование CRUD (create/update/delete) по модели. |
| **AuditService.log_data_access(request, resource_type, resource_id, details)** | Логирование доступа к данным (view). |

Модуль: `kripton.audit_services`. Экспорт логов: уже реализован в **AuditLogViewSet.export** (CSV) — `GET /api/audit/.../export/`.

---

## 4.4. Сервис прав доступа

| Метод | Описание |
|-------|----------|
| **PermissionService.check_report_access(user, report)** | Доступ к отчёту: создатель, stakeholder типа, staff. |
| **PermissionService.check_department_access(user, department)** | Доступ к подразделению: руководитель, сотрудник отдела, staff. |
| **PermissionService.get_user_departments(user)** | Список подразделений пользователя (руководитель + сотрудник). |

Модуль: `kripton.permissions_services`. API:
- **GET** `/api/reports/report-requests/my-departments/` — подразделения текущего пользователя.
- **GET** `/api/reports/reports/<id>/check_access/` — `{ "can_access": true/false }`.
- **GET** `/api/reports/departments/<id>/check_access/` — `{ "can_access": true/false }`.

---

## Дополнительно

- **Импорт Department**: в Reports везде используется `from kripton.guide.models import Department`; модель зарегистрирована в `kripton.guide.admin`.
- **Обратная совместимость**: `preview_table()` в `kripton.datasources.services.preview` вызывает DataPreviewService; старые URL предпросмотра заменены на ViewSet action `preview`.
- Для работы email напоминаний настройте в `settings`: `EMAIL_*`, `DEFAULT_FROM_EMAIL`.
