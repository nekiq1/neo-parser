# Neo Parser 2.0

Desktop-приложение для поиска и квалификации компаний, которым потенциально нужен сайт.

**CEO Neki · Lead Intelligence**

## Возможности

- Автоматический поиск организаций через **официальный API 2ГИС** (Catalog / Places)
- Выбор города (Москва, МО, Санкт-Петербург, ЛО) и ниши / произвольного запроса
- Сохранение лидов в локальную SQLite-базу с дедупликацией
- Аудит сайтов: доступность, HTTPS, формы, портфолио, каталог, мобильность
- Объяснимый **Lead Score** 0–100 с причинами и уверенностью
- Экспорт CSV / XLSX
- Тёмный SaaS-интерфейс на PySide6 (Dashboard, Search, Leads, Audit, Categories, History, Settings)
- Фоновые workers — UI не зависает; поиск и аудит можно остановить

## Требования

- Python 3.12+
- API-ключ 2ГИС с доступом к Catalog / Places API  
  Получение: [platform.2gis.ru](https://platform.2gis.ru) / [dev.2gis.ru](https://dev.2gis.ru)

Без ключа поиск **не выполняется** и **не имитируется**. Остальной функционал (импорт CSV, аудит, экспорт, CRM) работает.

## Установка и запуск

```bash
cd NeoParser
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # опционально: пропишите TWOGIS_API_KEY=

python main.py
```

Скрипты:

- Windows: `scripts/run_windows.bat`
- macOS: `scripts/run_macos.sh` (chmod +x)

Ключ также можно вставить в разделе **Settings** — он сохраняется в `~/.neo_parser/settings.json`.

## Структура

```
NeoParser/
├── main.py
├── requirements.txt
├── .env.example
├── neo_parser/
│   ├── config.py          # города, ниши, пути
│   ├── db.py              # SQLite
│   ├── workers.py         # QThread search/audit
│   ├── sources/
│   │   ├── base.py        # SourceProvider ABC
│   │   └── twogis.py      # 2GIS API
│   ├── services/
│   │   ├── audit.py
│   │   ├── scoring.py
│   │   ├── export.py
│   │   └── search.py
│   └── ui/
│       ├── styles.py
│       └── main_window.py
├── tests/
├── scripts/
├── pyinstaller_windows.spec
└── pyinstaller_macos.spec
```

## Сборка

```bash
pip install pyinstaller
# Windows
pyinstaller pyinstaller_windows.spec
# macOS (Apple Silicon)
pyinstaller pyinstaller_macos.spec
```

Артефакты появятся в `dist/`. Подписи/нотаризации нет — при первом запуске ОС может показать предупреждение.

## Тесты

```bash
pytest tests/ -q
```

Тесты не требуют API-ключа и сети.

## Важно

- Соблюдайте условия использования 2ГИС API, лимиты и политику данных.
- Приложение не обходит CAPTCHA и не парсит закрытые интерфейсы.
- Секреты не коммитьте: `.env` и `settings.json` в `.gitignore`.

## Что требует API-ключа

- Автопоиск на вкладке **Search** (2ГИС `/3.0/items`).

## Что работает без ключа

- Импорт CSV, таблица лидов, статусы CRM, аудит сайтов, Lead Score, экспорт, история, категории.
