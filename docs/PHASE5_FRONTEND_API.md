# Фаза 5: Frontend-интеграция

## 5.1. API для фронтенда

### Эндпоинты для всех действий из шаблонов

**GET /api/frontend/actions/** — единая точка входа для фронта. Возвращает:
- `user` — id, username, email, is_staff, is_superuser
- `endpoints` — объект с URL всех действий (отчёты, заявки, дашборд, отделы, аудит, источники данных, realtime)
- `filters_docs` — подсказки по query-параметрам фильтрации и поиска

Фронт может один раз вызвать этот эндпоинт и строить меню/запросы по `endpoints`.

### API для дашбордов (статистика, графики)

| Метод | URL | Описание |
|-------|-----|----------|
| GET | **/api/reports/dashboard/summary/** | Сводка: счётчики заявок по статусам, отчётов (всего/отправлено/утверждено), список своих подразделений, типы отчётов |
| GET | **/api/reports/dashboard/charts/** | Данные для графиков: заявки по дням (`?days=30`), по отделам, по типам отчётов, по статусам |

Ответ `summary`: `request_stats`, `reports_total`, `reports_submitted`, `reports_approved`, `my_departments`, `report_types`.

Ответ `charts`: `requests_by_day`, `requests_by_department`, `requests_by_type`, `requests_by_status`.

### API для фильтрации и поиска

Уже реализованы в ViewSet’ах через DRF:

- **report-requests**: `?status=...&department=...&report_type=...&search=...&ordering=-created_at`
- **reports**: `?report_type=...&created_by=...&search=...&ordering=...`
- **audit logs**: `?user=...&action_type=...&resource_type=...&date_from=...&date_to=...`
- **departments**: `?is_active=...&parent=...&search=...`
- **personal-data**: `?search=...&ordering=...`

Документация по параметрам возвращается в **/api/frontend/actions/** в поле `filters_docs`.

### API для экспорта данных

| Метод | URL | Описание |
|-------|-----|----------|
| GET | **/api/reports/reports/export/?format=csv\|xlsx** | Экспорт списка отчётов (с учётом фильтров), до 5000 записей |
| GET | **/api/reports/report-requests/export/?format=csv\|xlsx** | Экспорт списка заявок (с учётом фильтров), до 5000 записей |
| GET | **/api/reports/reports/<id>/export/?format=pdf\|xlsx\|docx** | Экспорт одного отчёта в файл |
| GET | **/api/audit/logs/export/** | Экспорт логов аудита (CSV по текущим фильтрам) |

---

## 5.2. WebSocket / SSE (реал-тайм)

### SSE — реал-тайм уведомления

**GET /api/stream/events/** — поток в формате Server-Sent Events (SSE). Требуется аутентификация.

- Клиент открывает соединение и получает события по мере появления.
- События создаются при: отправке/утверждении отчёта, утверждении/отклонении заявки.
- Типы событий: `report_submitted`, `report_approved`, `request_approved`, `request_rejected`.
- В теле события: `id`, `payload` (report_id, title, by, request_id и т.д.), `created_at`.
- Сервер опрашивает новые события каждые 2 с; таймаут потока ~5 мин (клиент может переподключаться).

Пример на фронте (EventSource):

```js
const es = new EventSource('/api/stream/events/', { withCredentials: true });
es.addEventListener('report_approved', (e) => {
  const data = JSON.parse(e.data);
  // обновить UI, показать уведомление
});
```

### Обновление статусов отчётов

При вызове submit/approve (отчёт) и approve/reject (заявка) в БД создаётся запись **RealtimeEvent**. Все, кому нужно уведомление (создатель отчёта, заинтересованные лица, заявитель, руководитель отдела), получают событие в своём SSE-потоке. Фронт может обновлять список заявок/отчётов при получении события.

### Онлайн-статус пользователей

**GET /api/stream/online/** — список пользователей, активных за последние 5 минут.

- Ответ: `{ "online": [ { "id", "username", "email", "last_seen" }, ... ] }`.
- **Last seen** обновляется middleware’ом **UserActivityMiddleware** при каждом запросе аутентифицированного пользователя.

В `settings.MIDDLEWARE` добавлено: `kripton.realtime_middleware.UserActivityMiddleware`.

---

## Модели и миграции

- **RealtimeEvent** (user, event_type, payload, created_at, read) — события для SSE.
- **UserActivity** (user OneToOne, last_seen) — активность для «кто онлайн».

Миграция: `kripton/migrations/0002_realtime_event_user_activity.py`. Выполнить: `python manage.py migrate`.

---

## Краткий чеклист

1. **Эндпоинты под шаблоны** — GET /api/frontend/actions/
2. **Дашборд** — GET /api/reports/dashboard/summary/, GET /api/reports/dashboard/charts/
3. **Фильтрация и поиск** — через query-параметры существующих list-эндпоинтов (см. filters_docs)
4. **Экспорт** — reports/export/, report-requests/export/, reports/<id>/export/, audit/logs/export/
5. **SSE** — GET /api/stream/events/
6. **Онлайн** — GET /api/stream/online/, middleware UserActivityMiddleware
