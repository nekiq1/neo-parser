"""Main application window with multi-page navigation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon, QPainter, QPen, QBrush, QColor, QFont
from PySide6.QtWidgets import QGraphicsOpacityEffect
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QGroupBox,
    QGridLayout,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..config import CITIES, DEFAULT_NICHES, STATUSES, get_api_key, save_api_key, get_language, save_language, get_animations_enabled, save_animations_enabled
from ..db import Database
from ..services.export import export_csv, export_xlsx
from ..sources.twogis import TwoGisProvider
from ..workers import AuditWorker, SearchWorker
from .styles import DARK_STYLE


TRANSLATIONS = {
    "NEO PARSER": "NEO PARSER", "v2.0  ·  CEO Neki": "v2.1  ·  Lead Intelligence",
    "Dashboard": "Обзор", "Search": "Поиск", "Leads": "Компании", "Website Audit": "Аудит сайтов",
    "Categories": "Ниши", "History": "История", "Settings": "Настройки",
    "Тёмная тема · 2ГИС API": "Локальная база · 2ГИС",
    "Сводка по базе потенциальных клиентов": "Ключевые показатели и состояние вашей базы",
    "Всего лидов": "Всего компаний", "Высокий приоритет (≥60)": "Высокий потенциал (≥60)",
    "С сайтом": "Есть сайт", "Без сайта": "Без сайта", "Проверено сайтов": "Проверено сайтов",
    "Поиск компаний": "Поиск компаний", "Поиск через сайт 2ГИС (Chromium) — без API-ключа разработчика": "Поиск через веб-каталог 2ГИС. API-ключ не обязателен.",
    "Город:": "Город:", "Ниша / запрос:": "Ниша / запрос:", "Стр.:": "Страниц:",
    "Только с телефоном": "Есть телефон", "Только с сайтом": "Только с сайтом", "С email": "Есть email",
    "Запустить поиск": "Запустить поиск", "Остановить": "Остановить", "Лог поиска появится здесь…": "Здесь появится ход поиска…",
    "Leads": "Компании", "Импорт CSV": "Импорт CSV", "Экспорт": "Экспорт",
    "Поиск по названию, городу, телефону, сайту…": "Поиск по компании, городу, контакту или сайту…",
    "Все статусы": "Все статусы", "Все города": "Все города", "Удалить": "Удалить",
    "Сменить статус": "Изменить статус", "Проверка доступности, HTTPS, форм, портфолио и мобильности": "Проверка доступности, HTTPS, форм, портфолио и мобильной версии",
    "Проверить все сайты": "Проверить все сайты", "Ниши для быстрого выбора в поиске": "Управляйте списком поисковых ниш",
    "Новая ниша…": "Добавить новую нишу…", "Добавить": "Добавить", "Удалить выбранную (только пользовательские)": "Удалить выбранную нишу",
    "История поисковых задач": "Последние поисковые задачи", "Дата": "Дата", "Город": "Город", "Запрос": "Запрос",
    "Найдено": "Найдено", "Добавлено": "Добавлено", "API-ключи и параметры": "Язык, внешний вид и подключение источников",
    "API-ключ 2ГИС (Catalog / Places)": "API-ключ 2ГИС (необязательно)", "Вставьте ключ…": "Вставьте API-ключ…",
    "Сохранить ключ": "Сохранить ключ", "Настройки": "Настройки", "Готово": "Готово",
    "Язык интерфейса": "Язык интерфейса", "Русский": "Русский", "Английский": "Английский",
    "Внешний вид": "Внешний вид", "Тёмная тема": "Тёмная тема", "Анимации интерфейса": "Плавные анимации интерфейса",
    "Сохранить настройки": "Сохранить настройки", "Настройки сохранены.": "Настройки сохранены.",
    "Обзор базы": "Обзор базы", "Активность базы": "Активность базы", "Рабочее пространство Neo Parser": "Рабочее пространство Neo Parser",
    "Находите компании, оценивайте их цифровое присутствие и ведите работу с лидами в одной системе.": "Находите компании, оценивайте их цифровое присутствие и ведите работу с лидами в одной системе.",
    "Перейти к поиску  →": "Перейти к поиску  →", "●  Поиск готов к запуску": "●  Поиск готов к запуску", "Компании с сайтом и без сайта": "Компании с сайтом и без сайта",
    "Потенциал базы": "Потенциал базы", "Сильные кандидаты": "Высокий приоритет", "Аудит": "Аудит",
    "2ГИС Web · Chromium": "2ГИС Web · Chromium", "Поиск готов к запуску": "Поиск готов к запуску",
    "База хранится локально на этом компьютере": "База данных хранится локально на этом компьютере",
}

EN_TRANSLATIONS = {
    "Обзор": "Overview", "Обзор базы": "Database overview", "Поиск компаний": "Company search", "Поиск": "Search", "Компании": "Companies", "Аудит сайтов": "Website audit",
    "Ниши": "Niches", "История": "History", "Настройки": "Settings", "Готово": "Ready",
    "Всего компаний": "Total companies", "Высокий потенциал (≥60)": "High potential (≥60)",
    "Есть сайт": "Has website", "Без сайта": "No website", "Проверено сайтов": "Websites audited",
    "Ключевые показатели и состояние вашей базы": "Key metrics and database health",
    "Компании с сайтом и без сайта": "Companies with and without a website", "Активность базы": "Database activity", "Рабочее пространство Neo Parser": "Neo Parser workspace",
    "Находите компании, оценивайте их цифровое присутствие и ведите работу с лидами в одной системе.": "Find companies, assess their digital presence and manage leads in one workspace.",
    "Перейти к поиску  →": "Go to search  →", "●  Поиск готов к запуску": "●  Search is ready", "Поиск готов к запуску": "Search is ready",
    "Высокий приоритет": "High priority", "Язык интерфейса": "Interface language", "Русский": "Russian", "Английский": "English",
    "Внешний вид": "Appearance", "Тёмная тема": "Dark theme", "Плавные анимации интерфейса": "Smooth interface animations",
    "Сохранить настройки": "Save settings", "Настройки сохранены.": "Settings saved.",
    "Компания": "Company", "Ниша": "Niche", "Город": "City", "Телефон": "Phone", "Сайт": "Website",
    "Аудит": "Audit", "Оценка": "Score", "Увер.": "Confidence", "Статус": "Status",
    "Новый": "New", "Связался": "Contacted", "Заинтересован": "Interested", "Переговоры": "Negotiation", "Клиент": "Customer", "Отказ": "Declined",
    "Дата": "Date", "Запрос": "Query", "Найдено": "Found", "Добавлено": "Added",
    "Только с телефоном": "Has phone", "С email": "Has email", "Без сайта": "No website", "Только с сайтом": "Website only",
    "Поиск через сайт 2ГИС (Chromium) — без API-ключа разработчика": "Search via 2GIS public website using Chromium. No developer API key required.",
    "Проверка доступности, HTTPS, форм, портфолио и мобильности": "Checks availability, HTTPS, forms, portfolio and mobile layout",
    "Ниши для быстрого выбора в поиске": "Manage saved search niches",
    "История поисковых задач": "Search task history", "API-ключи и параметры": "Language, appearance and source settings",
    "База данных: ": "Database: ", "Ключ сохранён.": "API key saved.",
    "Ключ можно получить на https://platform.2gis.ru\nТакже поддерживается переменная окружения TWOGIS_API_KEY.\nКлюч хранится локально в ~/.neo_parser/settings.json и не попадает в Git.": "Get a key at https://platform.2gis.ru\nThe TWOGIS_API_KEY environment variable is also supported.\nThe key is stored locally in ~/.neo_parser/settings.json and is never committed to Git.",
    "Добавить новую нишу…": "Add a niche…", "Добавить": "Add", "Удалить выбранную нишу": "Remove selected niche",
    "Запустить поиск": "Start search", "Остановить": "Stop", "Импорт CSV": "Import CSV", "Экспорт": "Export",
    "Все статусы": "All statuses", "Все города": "All cities", "Удалить": "Delete", "Изменить статус": "Change status",
    "Проверить все сайты": "Audit all websites", "Город:": "City:", "Ниша / запрос:": "Niche / query:", "Страниц:": "Pages:",
    "Есть телефон": "Has phone", "Только с сайтом": "Website only", "Есть email": "Has email",
    "Здесь появится ход поиска…": "Search activity will appear here…", "Поиск по компании, городу, контакту или сайту…": "Search company, city, contact or website…",
    "Последние поисковые задачи": "Recent search tasks", "Дата": "Date", "Город": "City", "Запрос": "Query", "Найдено": "Found", "Добавлено": "Added",
    "API-ключ 2ГИС (необязательно)": "2GIS API key (optional)", "Вставьте API-ключ…": "Paste API key…", "Сохранить ключ": "Save key",
}

class MetricChart(QWidget):
    """Small native Qt chart; no external plotting dependency."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = [0, 0, 0]
        self.labels = ["Есть сайт", "Без сайта", "Проверено"]
        self.setMinimumHeight(170)

    def set_values(self, values):
        self.values = [max(0, int(v)) for v in values]
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(12, 12, -12, -12)
        maxv = max(self.values + [1])
        colors = [QColor("#42d8cf"), QColor("#4288e8"), QColor("#a58bff")]
        row_h = max(38, rect.height() // 3)
        for i, (label, value) in enumerate(zip(self.labels, self.values)):
            y = rect.top() + i * row_h
            p.setPen(QColor("#9aabc0")); p.setFont(QFont("Segoe UI", 9, QFont.DemiBold))
            p.drawText(rect.left(), y + 13, label)
            p.setPen(QColor("#eaf2ff")); p.setFont(QFont("Segoe UI", 10, QFont.Bold))
            p.drawText(rect.right() - 34, y + 13, str(value))
            track = rect.adjusted(0, 20, 0, 0)
            track.setTop(y + 21); track.setHeight(9); track.setWidth(rect.width())
            p.setPen(Qt.NoPen); p.setBrush(QColor("#1c2b3d")); p.drawRoundedRect(track, 4, 4)
            fill = track; fill.setWidth(int(track.width() * value / maxv))
            p.setBrush(colors[i]); p.drawRoundedRect(fill, 4, 4)
        p.end()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.search_worker: SearchWorker | None = None
        self.audit_worker: AuditWorker | None = None
        self.nav_buttons: dict[str, QPushButton] = {}
        self.language = get_language()
        self.page_animation = None
        self.animations_enabled = get_animations_enabled()

        self.setWindowTitle("Neo Parser 2.1 — Lead Intelligence")
        self.resize(1500, 920)
        self.setMinimumSize(1120, 740)
        self._apply_window_icon()

        root = QWidget()
        outer = QHBoxLayout(root)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(16)

        # Sidebar
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(236)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(14, 18, 14, 18)
        sl.setSpacing(4)

        brand = QLabel("NEO PARSER")
        brand.setObjectName("Brand")
        sl.addWidget(brand)
        brand_tag = QLabel("LEAD INTELLIGENCE PLATFORM")
        brand_tag.setObjectName("BrandAccent")
        sl.addWidget(brand_tag)
        sl.addSpacing(5)
        sub = QLabel("v2.1  ·  CEO Neki")
        sub.setObjectName("Muted")
        sl.addWidget(sub)
        sl.addSpacing(20)

        for key, title in [
            ("dashboard", "Обзор"),
            ("search", "Поиск"),
            ("leads", "Компании"),
            ("audit", "Аудит сайтов"),
            ("categories", "Ниши"),
            ("history", "История"),
            ("settings", "Настройки"),
        ]:
            btn = QPushButton(title)
            btn.setObjectName("Nav")
            btn.clicked.connect(lambda checked=False, k=key: self.switch_page(k))
            sl.addWidget(btn)
            self.nav_buttons[key] = btn

        sl.addStretch()
        hint = QLabel("Тёмная тема · 2ГИС API")
        hint.setObjectName("Muted")
        sl.addWidget(hint)
        outer.addWidget(side)

        # Content stack
        self.stack = QStackedWidget()
        self.pages = {}
        self.pages["dashboard"] = self._build_dashboard()
        self.pages["search"] = self._build_search()
        self.pages["leads"] = self._build_leads()
        self.pages["audit"] = self._build_audit()
        self.pages["categories"] = self._build_categories()
        self.pages["history"] = self._build_history()
        self.pages["settings"] = self._build_settings()
        for p in self.pages.values():
            self.stack.addWidget(p)
        outer.addWidget(self.stack, 1)

        self.setCentralWidget(root)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Готово")
        self.switch_page("dashboard")
        self.refresh_all()
        self.apply_language(self.language)

    # ── navigation ─────────────────────────────────────────
    def switch_page(self, key: str) -> None:
        for k, btn in self.nav_buttons.items():
            btn.setObjectName("NavActive" if k == key else "Nav")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.stack.setCurrentWidget(self.pages[key])
        if self.animations_enabled:
            effect = QGraphicsOpacityEffect(self.pages[key])
            self.pages[key].setGraphicsEffect(effect)
            self.page_animation = QPropertyAnimation(effect, b"opacity", self)
            self.page_animation.setDuration(190)
            self.page_animation.setStartValue(0.55)
            self.page_animation.setEndValue(1.0)
            self.page_animation.setEasingCurve(QEasingCurve.OutCubic)
            self.page_animation.start()
        if key == "leads":
            self.populate_leads()
        elif key == "dashboard":
            self.refresh_dashboard()
        elif key == "history":
            self.populate_history()
        elif key == "categories":
            self.populate_categories()
        elif key == "settings":
            self.key_input.setText(get_api_key())

    def refresh_all(self) -> None:
        self.refresh_dashboard()
        self.populate_leads()
        self.populate_history()
        self.populate_categories()

    # ── cards helper ───────────────────────────────────────
    def _card(self, label: str, value: str = "0") -> tuple[QFrame, QLabel]:
        frame = QFrame()
        frame.setObjectName("Card")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(16, 14, 16, 14)
        val = QLabel(value)
        val.setObjectName("CardValue")
        lab = QLabel(label)
        lab.setObjectName("CardLabel")
        lay.addWidget(val)
        lay.addWidget(lab)
        return frame, val

    # ── Dashboard ──────────────────────────────────────────
    def _build_dashboard(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(16)
        title = QLabel("Обзор базы")
        title.setObjectName("SectionTitle")
        desc = QLabel("Ключевые показатели и состояние вашей базы")
        desc.setObjectName("Muted")
        lay.addWidget(title)
        lay.addWidget(desc)

        hero = QFrame(); hero.setObjectName("Hero")
        hl = QHBoxLayout(hero); hl.setContentsMargins(24, 22, 24, 22)
        left = QVBoxLayout()
        htitle = QLabel("Рабочее пространство Neo Parser")
        htitle.setObjectName("HeroTitle")
        hdesc = QLabel("Находите компании, оценивайте их цифровое присутствие и ведите работу с лидами в одной системе.")
        hdesc.setObjectName("HeroText"); hdesc.setWordWrap(True)
        left.addWidget(htitle); left.addWidget(hdesc)
        self.hero_status = QLabel("●  Поиск готов к запуску")
        self.hero_status.setObjectName("MetricAccent")
        left.addSpacing(8); left.addWidget(self.hero_status)
        hl.addLayout(left, 1)
        self.hero_action = QPushButton("Перейти к поиску  →")
        self.hero_action.setObjectName("Primary")
        self.hero_action.clicked.connect(lambda: self.switch_page("search"))
        hl.addWidget(self.hero_action, 0, Qt.AlignVCenter)
        lay.addWidget(hero)

        cards = QGridLayout(); cards.setSpacing(12)
        self.dash_total_f, self.dash_total = self._card("Всего компаний")
        self.dash_hot_f, self.dash_hot = self._card("Высокий потенциал (≥60)")
        self.dash_site_f, self.dash_site = self._card("Есть сайт")
        self.dash_nosite_f, self.dash_nosite = self._card("Без сайта")
        self.dash_audited_f, self.dash_audited = self._card("Проверено сайтов")
        for i, frame in enumerate((self.dash_total_f, self.dash_hot_f, self.dash_site_f, self.dash_nosite_f, self.dash_audited_f)):
            frame.setObjectName("MetricCard")
            cards.addWidget(frame, 0, i)
        lay.addLayout(cards)

        lower = QHBoxLayout(); lower.setSpacing(14)
        chart_card = QFrame(); chart_card.setObjectName("Card")
        c_lay = QVBoxLayout(chart_card); c_lay.setContentsMargins(18, 16, 18, 16)
        c_title = QLabel("Компании с сайтом и без сайта"); c_title.setObjectName("CardLabel")
        self.metric_chart = MetricChart()
        c_lay.addWidget(c_title); c_lay.addWidget(self.metric_chart)
        lower.addWidget(chart_card, 3)
        info_card = QFrame(); info_card.setObjectName("Card")
        i_lay = QVBoxLayout(info_card); i_lay.setContentsMargins(18, 16, 18, 16)
        it = QLabel("Активность базы"); it.setObjectName("CardLabel")
        self.dash_activity = QLabel("База данных хранится локально на этом компьютере")
        self.dash_activity.setWordWrap(True); self.dash_activity.setObjectName("Muted")
        self.dash_audit_progress = QProgressBar(); self.dash_audit_progress.setRange(0, 100)
        self.dash_audit_progress.setValue(0)
        self.dash_audit_label = QLabel("Аудит: 0% проверено"); self.dash_audit_label.setObjectName("MetricAccent")
        i_lay.addWidget(it); i_lay.addSpacing(8); i_lay.addWidget(self.dash_activity)
        i_lay.addStretch(); i_lay.addWidget(self.dash_audit_label); i_lay.addWidget(self.dash_audit_progress)
        lower.addWidget(info_card, 2)
        lay.addLayout(lower)
        lay.addStretch()
        return w

    def refresh_dashboard(self) -> None:
        s = self.db.stats()
        self.dash_total.setText(str(s["total"]))
        self.dash_hot.setText(str(s["hot"]))
        self.dash_site.setText(str(s["with_site"]))
        self.dash_nosite.setText(str(s["no_site"]))
        self.dash_audited.setText(str(s.get("audited", 0)))
        self.metric_chart.set_values([s["with_site"], s["no_site"], s.get("audited", 0)])
        pct = int((s.get("audited", 0) / max(s["with_site"], 1)) * 100)
        self.dash_audit_progress.setValue(min(100, pct))
        self.dash_audit_label.setText(f"Аудит: {min(100, pct)}% проверено")

    # ── Search ─────────────────────────────────────────────
    def _build_search(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(14)
        title = QLabel("Поиск компаний")
        title.setObjectName("SectionTitle")
        desc = QLabel("Поиск через сайт 2ГИС (Chromium) — без API-ключа разработчика")
        desc.setObjectName("Muted")
        lay.addWidget(title)
        lay.addWidget(desc)

        form = QHBoxLayout()
        self.city_combo = QComboBox()
        self.city_combo.addItems(list(CITIES.keys()))
        form.addWidget(QLabel("Город:"))
        form.addWidget(self.city_combo, 1)

        self.niche_combo = QComboBox()
        self.niche_combo.setEditable(True)
        self.niche_combo.addItems(DEFAULT_NICHES)
        form.addWidget(QLabel("Ниша / запрос:"))
        form.addWidget(self.niche_combo, 2)

        self.pages_spin = QSpinBox()
        self.pages_spin.setRange(1, 20)
        self.pages_spin.setValue(3)
        form.addWidget(QLabel("Стр.:"))
        form.addWidget(self.pages_spin)
        lay.addLayout(form)

        fl = QHBoxLayout()
        self.flt_phone = QCheckBox("Только с телефоном")
        self.flt_no_site = QCheckBox("Без сайта")
        self.flt_no_site.setChecked(False)
        self.flt_with_site = QCheckBox("Только с сайтом")
        self.flt_email = QCheckBox("С email")
        fl.addWidget(self.flt_phone)
        fl.addWidget(self.flt_no_site)
        fl.addWidget(self.flt_with_site)
        fl.addWidget(self.flt_email)
        fl.addStretch()
        lay.addLayout(fl)

        actions = QHBoxLayout()
        self.search_btn = QPushButton("Запустить поиск")
        self.search_btn.setObjectName("Primary")
        self.search_btn.clicked.connect(self.start_search)
        actions.addWidget(self.search_btn)
        self.search_stop_btn = QPushButton("Остановить")
        self.search_stop_btn.setEnabled(False)
        self.search_stop_btn.clicked.connect(self.stop_search)
        actions.addWidget(self.search_stop_btn)
        actions.addStretch()
        lay.addLayout(actions)

        self.search_progress = QProgressBar()
        self.search_progress.setRange(0, 0)
        self.search_progress.setVisible(False)
        lay.addWidget(self.search_progress)

        self.search_log = QTextEdit()
        self.search_log.setReadOnly(True)
        self.search_log.setPlaceholderText("Лог поиска появится здесь…")
        lay.addWidget(self.search_log, 1)

        key_status = QLabel(
            "Режим: 2ГИС Web (сайт 2gis.ru + Chromium). Ключ API не обязателен."
        )
        key_status.setObjectName("Muted")
        self.search_key_status = key_status
        lay.addWidget(key_status)
        return w

    def start_search(self) -> None:
        query = self.niche_combo.currentText().strip()
        city = self.city_combo.currentText()
        if not query:
            QMessageBox.information(self, "Запрос", "Введите нишу или поисковый запрос.")
            return

        filters = {
            "require_public_contact": True,
            "only_with_phone": self.flt_phone.isChecked(),
            "only_without_website": self.flt_no_site.isChecked(),
            "only_with_website": self.flt_with_site.isChecked(),
            "only_with_email": self.flt_email.isChecked(),
        }

        self.search_log.clear()
        self.search_log.append(f"▶ Поиск «{query}» в {city} (2ГИС Web)…")
        self.search_btn.setEnabled(False)
        self.search_stop_btn.setEnabled(True)
        self.search_progress.setVisible(True)

        self.search_worker = SearchWorker(
            query, city, max_pages=self.pages_spin.value(), filters=filters
        )
        self.search_worker.progress.connect(self.on_search_progress)
        self.search_worker.finished_ok.connect(self.on_search_done)
        self.search_worker.failed.connect(self.on_search_failed)
        self.search_worker.start()

    def on_search_progress(self, name: str, found: int, added: int) -> None:
        self.search_log.append(f"  [{found}] {name}  (новых: {added})")
        self.statusBar().showMessage(f"Найдено: {found}, добавлено: {added}")

    def on_search_done(self, result: dict) -> None:
        self.search_progress.setVisible(False)
        self.search_btn.setEnabled(True)
        self.search_stop_btn.setEnabled(False)
        self.search_log.append(
            f"\n✓ Готово. Найдено: {result['found']}, добавлено в базу: {result['added']}"
        )
        self.statusBar().showMessage(
            f"Поиск завершён: +{result['added']} из {result['found']}"
        )
        self.refresh_all()

    def on_search_failed(self, message: str) -> None:
        self.search_progress.setVisible(False)
        self.search_btn.setEnabled(True)
        self.search_stop_btn.setEnabled(False)
        self.search_log.append(f"\n✗ Ошибка:\n{message}")
        QMessageBox.critical(self, "Ошибка поиска", message[:800])

    def stop_search(self) -> None:
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.stop()
            self.search_stop_btn.setEnabled(False)
            self.search_log.append("… остановка запрошена")

    # ── Leads ──────────────────────────────────────────────
    def _build_leads(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)
        header = QHBoxLayout()
        title = QLabel("Компании")
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch()
        imp = QPushButton("Импорт CSV")
        imp.clicked.connect(self.import_csv)
        header.addWidget(imp)
        exp = QPushButton("Экспорт")
        exp.clicked.connect(self.export_leads)
        header.addWidget(exp)
        lay.addLayout(header)

        filters = QHBoxLayout()
        self.leads_search = QLineEdit()
        self.leads_search.setPlaceholderText("Поиск по названию, городу, телефону, сайту…")
        self.leads_search.textChanged.connect(self.populate_leads)
        filters.addWidget(self.leads_search, 2)
        self.leads_status = QComboBox()
        self.leads_status.addItems(["Все статусы"] + STATUSES)
        self.leads_status.currentTextChanged.connect(self.populate_leads)
        filters.addWidget(self.leads_status)
        self.leads_city = QComboBox()
        self.leads_city.addItems(["Все города"] + list(CITIES.keys()))
        self.leads_city.currentTextChanged.connect(self.populate_leads)
        filters.addWidget(self.leads_city)
        lay.addLayout(filters)

        self.leads_table = QTableWidget(0, 9)
        self.leads_table.setHorizontalHeaderLabels(
            ["Компания", "Ниша", "Город", "Телефон", "Сайт", "Аудит", "Score", "Увер.", "Статус"]
        )
        self.leads_table.setAlternatingRowColors(True)
        self.leads_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.leads_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.leads_table.setSortingEnabled(True)
        self.leads_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.leads_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.leads_table.doubleClicked.connect(self.show_lead_details)
        lay.addWidget(self.leads_table, 1)

        actions = QHBoxLayout()
        del_btn = QPushButton("Удалить")
        del_btn.setObjectName("Danger")
        del_btn.clicked.connect(self.delete_selected_lead)
        actions.addWidget(del_btn)
        status_btn = QPushButton("Сменить статус")
        status_btn.clicked.connect(self.change_lead_status)
        actions.addWidget(status_btn)
        actions.addStretch()
        lay.addLayout(actions)
        return w

    def populate_leads(self) -> None:
        query = self.leads_search.text().strip()
        status = self.leads_status.currentText()
        if self.language == "en":
            status = next((ru for ru, en in EN_TRANSLATIONS.items() if en == status), status)
        city = self.leads_city.currentText()
        rows = self.db.all(query=query, status=status, city=city)
        self.leads_table.setSortingEnabled(False)
        self.leads_table.setRowCount(0)
        for r in rows:
            row = self.leads_table.rowCount()
            self.leads_table.insertRow(row)
            values = [
                r["company"],
                r["category"],
                r["city"],
                r["phone"],
                r["website"],
                r["website_status"],
                str(r["score"]),
                str(r["confidence"] or ""),
                self._display_status(r["status"]),
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val or ""))
                if col == 0:
                    item.setData(Qt.UserRole, r["id"])
                if col == 6:
                    item.setData(Qt.DisplayRole, int(r["score"] or 0))
                self.leads_table.setItem(row, col, item)
        self.leads_table.setSortingEnabled(True)
        self.statusBar().showMessage(f"Лидов: {len(rows)}")

    def _display_status(self, status: str) -> str:
        return EN_TRANSLATIONS.get(status, status) if self.language == "en" else status

    def selected_lead_id(self) -> int | None:
        row = self.leads_table.currentRow()
        if row < 0:
            return None
        item = self.leads_table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def delete_selected_lead(self) -> None:
        lid = self.selected_lead_id()
        if lid is None:
            return
        if QMessageBox.question(self, "Удаление", "Удалить выбранную компанию?") == QMessageBox.Yes:
            self.db.delete(lid)
            self.refresh_all()

    def change_lead_status(self) -> None:
        lid = self.selected_lead_id()
        if lid is None:
            return
        from PySide6.QtWidgets import QInputDialog

        labels = [self._display_status(item) for item in STATUSES]
        status, ok = QInputDialog.getItem(self, "Status" if self.language == "en" else "Статус", "New status:" if self.language == "en" else "Новый статус:", labels, 0, False)
        if ok and status:
            if self.language == "en":
                status = next((ru for ru, en in EN_TRANSLATIONS.items() if en == status), status)
            self.db.update_status(lid, status)
            self.populate_leads()

    def show_lead_details(self) -> None:
        lid = self.selected_lead_id()
        if lid is None:
            return
        lead = self.db.get(lid)
        if not lead:
            return
        reasons = lead["score_reasons"] or "[]"
        try:
            reasons_list = json.loads(reasons) if isinstance(reasons, str) else reasons
            reasons_txt = "\n".join(f"• {x}" for x in reasons_list)
        except Exception:
            reasons_txt = str(reasons)
        text = (
            f"<b>{lead['company']}</b><br>"
            f"Город: {lead['city']}<br>"
            f"Категория: {lead['category']}<br>"
            f"Телефон: {lead['phone']}<br>"
            f"Email: {lead['email']}<br>"
            f"Сайт: {lead['website']}<br>"
            f"ВКонтакте: {lead['vk']}<br>"
            f"Telegram: {lead['telegram']}<br>"
            f"WhatsApp: {lead['whatsapp']}<br>"
            f"Адрес: {lead['address']}<br>"
            f"Источник: {lead['source']} · {lead['card_url']}<br>"
            f"Score: {lead['score']} (уверенность {lead['confidence']}%)<br><br>"
            f"<b>Причины оценки:</b><br>{reasons_txt}<br><br>"
            f"Аудит: {lead['website_status']} · {lead['website_title']}"
        )
        QMessageBox.information(self, "Карточка лида", text)

    def import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Импорт CSV", "", "CSV (*.csv)")
        if not path:
            return
        try:
            from ..services.audit import normalize_url
            import csv as csvmod

            added = 0
            with open(path, encoding="utf-8-sig", newline="") as f:
                sample = f.read(4096)
                f.seek(0)
                try:
                    dialect = csvmod.Sniffer().sniff(sample, delimiters=";,\t")
                except csvmod.Error:
                    dialect = csvmod.excel
                    dialect.delimiter = ";"
                reader = csvmod.DictReader(f, dialect=dialect)
                aliases = {
                    "company": {"company", "название", "name", "фирма", "организация"},
                    "city": {"city", "город"},
                    "phone": {"phone", "телефон", "тел"},
                    "email": {"email", "почта", "e-mail"},
                    "website": {"website", "сайт", "url", "site"},
                    "category": {"category", "категория", "ниша"},
                    "address": {"address", "адрес"},
                    "vk": {"vk", "вк", "vkontakte"},
                    "telegram": {"telegram", "tg"},
                    "notes": {"notes", "заметки", "комментарий"},
                }
                mapping = {}
                for col in reader.fieldnames or []:
                    key = col.strip().lstrip("\ufeff").casefold()
                    for target, names in aliases.items():
                        if key in names:
                            mapping[col] = target
                            break
                if "company" not in mapping.values():
                    raise ValueError("Нужен столбец company / Название")
                for row in reader:
                    item = {t: (row.get(s) or "").strip() for s, t in mapping.items()}
                    item["website"] = normalize_url(item.get("website", ""))
                    item["source"] = item.get("source") or "CSV"
                    if item.get("company") and self.db.add_lead(item):
                        added += 1
            self.refresh_all()
            QMessageBox.information(self, "Импорт", f"Добавлено записей: {added}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", str(e))

    def export_leads(self) -> None:
        path, filt = QFileDialog.getSaveFileName(
            self, "Экспорт", "leads.xlsx", "Excel (*.xlsx);;CSV (*.csv)"
        )
        if not path:
            return
        rows = self.db.all()
        try:
            if path.lower().endswith(".csv") or "CSV" in filt:
                n = export_csv(rows, path)
            else:
                n = export_xlsx(rows, path)
            self.statusBar().showMessage(f"Экспортировано: {n}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", str(e))

    # ── Website Audit ──────────────────────────────────────
    def _build_audit(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        title = QLabel("Аудит сайтов")
        title.setObjectName("SectionTitle")
        desc = QLabel("Проверка доступности, HTTPS, форм, портфолио и мобильности")
        desc.setObjectName("Muted")
        lay.addWidget(title)
        lay.addWidget(desc)

        actions = QHBoxLayout()
        self.audit_btn = QPushButton("Проверить все сайты")
        self.audit_btn.setObjectName("Primary")
        self.audit_btn.clicked.connect(self.start_audit)
        actions.addWidget(self.audit_btn)
        self.audit_stop_btn = QPushButton("Остановить")
        self.audit_stop_btn.setEnabled(False)
        self.audit_stop_btn.clicked.connect(self.stop_audit)
        actions.addWidget(self.audit_stop_btn)
        actions.addStretch()
        self.audit_progress = QProgressBar()
        self.audit_progress.setFixedWidth(220)
        actions.addWidget(self.audit_progress)
        lay.addLayout(actions)

        self.audit_log = QTextEdit()
        self.audit_log.setReadOnly(True)
        lay.addWidget(self.audit_log, 1)
        return w

    def start_audit(self) -> None:
        rows = [r for r in self.db.all() if r["website"]]
        if not rows:
            QMessageBox.information(self, "Аудит", "В базе нет сайтов для проверки.")
            return
        self.audit_log.clear()
        self.audit_log.append(f"Проверка {len(rows)} сайтов…")
        self.audit_btn.setEnabled(False)
        self.audit_stop_btn.setEnabled(True)
        self.audit_progress.setMaximum(len(rows))
        self.audit_progress.setValue(0)
        self.audit_worker = AuditWorker(rows)
        self.audit_worker.result_ready.connect(self.on_audit_result)
        self.audit_worker.progress.connect(self.on_audit_progress)
        self.audit_worker.finished_all.connect(self.on_audit_done)
        self.audit_worker.start()

    def on_audit_result(self, lead_id: int, audit: dict) -> None:
        self.db.update_audit(lead_id, audit)
        self.audit_log.append(
            f"  #{lead_id}: {audit.get('status')} · score={audit.get('score')}"
        )

    def on_audit_progress(self, i: int, total: int) -> None:
        self.audit_progress.setValue(i)
        self.statusBar().showMessage(f"Аудит сайтов: {i}/{total}")

    def on_audit_done(self) -> None:
        self.audit_btn.setEnabled(True)
        self.audit_stop_btn.setEnabled(False)
        self.audit_log.append("\n✓ Аудит завершён")
        self.refresh_all()
        self.statusBar().showMessage("Аудит завершён")

    def stop_audit(self) -> None:
        if self.audit_worker and self.audit_worker.isRunning():
            self.audit_worker.stop()
            self.audit_stop_btn.setEnabled(False)
            self.audit_log.append("… остановка")

    # ── Categories ─────────────────────────────────────────
    def _build_categories(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        title = QLabel("Ниши")
        title.setObjectName("SectionTitle")
        desc = QLabel("Ниши для быстрого выбора в поиске")
        desc.setObjectName("Muted")
        lay.addWidget(title)
        lay.addWidget(desc)

        row = QHBoxLayout()
        self.cat_input = QLineEdit()
        self.cat_input.setPlaceholderText("Новая ниша…")
        row.addWidget(self.cat_input, 1)
        add_btn = QPushButton("Добавить")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self.add_category)
        row.addWidget(add_btn)
        lay.addLayout(row)

        self.cat_list = QListWidget()
        lay.addWidget(self.cat_list, 1)

        del_btn = QPushButton("Удалить выбранную (только пользовательские)")
        del_btn.clicked.connect(self.remove_category)
        lay.addWidget(del_btn)
        return w

    def populate_categories(self) -> None:
        self.cat_list.clear()
        for name in self.db.categories():
            self.cat_list.addItem(name)
        # keep niche combo in sync
        current = self.niche_combo.currentText()
        self.niche_combo.clear()
        self.niche_combo.addItems(self.db.categories())
        if current:
            self.niche_combo.setEditText(current)

    def add_category(self) -> None:
        name = self.cat_input.text().strip()
        if not name:
            return
        if self.db.add_category(name):
            self.cat_input.clear()
            self.populate_categories()
        else:
            QMessageBox.information(self, "Категории", "Такая ниша уже есть.")

    def remove_category(self) -> None:
        item = self.cat_list.currentItem()
        if not item:
            return
        self.db.remove_category(item.text())
        self.populate_categories()

    # ── History ────────────────────────────────────────────
    def _build_history(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        title = QLabel("История")
        title.setObjectName("SectionTitle")
        desc = QLabel("История поисковых задач")
        desc.setObjectName("Muted")
        lay.addWidget(title)
        lay.addWidget(desc)

        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(
            ["Дата", "Город", "Запрос", "Найдено", "Добавлено"]
        )
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        lay.addWidget(self.history_table, 1)
        return w

    def populate_history(self) -> None:
        rows = self.db.history()
        self.history_table.setRowCount(0)
        for r in rows:
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)
            for col, val in enumerate(
                [r["created_at"], r["city"], r["query"], str(r["found"]), str(r["added"])]
            ):
                self.history_table.setItem(row, col, QTableWidgetItem(val or ""))

    # ── Settings ───────────────────────────────────────────
    def _build_settings(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        title = QLabel("Настройки")
        title.setObjectName("SectionTitle")
        desc = QLabel("API-ключи и параметры")
        desc.setObjectName("Muted")
        lay.addWidget(title)
        lay.addWidget(desc)

        prefs = QFrame(); prefs.setObjectName("Card")
        pl = QVBoxLayout(prefs); pl.setContentsMargins(18, 16, 18, 16)
        pl.addWidget(QLabel("Внешний вид"))
        pl.addWidget(QLabel("Язык интерфейса"))
        self.language_combo = QComboBox(); self.language_combo.addItem("Русский", "ru"); self.language_combo.addItem("Английский", "en")
        self.language_combo.setCurrentIndex(0 if self.language == "ru" else 1)
        pl.addWidget(self.language_combo)
        self.animations_check = QCheckBox("Плавные анимации интерфейса")
        self.animations_check.setChecked(self.animations_enabled); pl.addWidget(self.animations_check)
        pref_save = QPushButton("Сохранить настройки"); pref_save.setObjectName("Primary")
        pref_save.clicked.connect(self.save_preferences); pl.addWidget(pref_save)
        lay.addWidget(prefs)

        card = QFrame()
        card.setObjectName("Card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(18, 16, 18, 16)
        cl.addWidget(QLabel("API-ключ 2ГИС (необязательно)"))
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.Password)
        self.key_input.setPlaceholderText("Вставьте ключ…")
        self.key_input.setText(get_api_key())
        cl.addWidget(self.key_input)
        save_btn = QPushButton("Сохранить ключ")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self.save_settings)
        cl.addWidget(save_btn)
        help_lbl = QLabel(
            "Ключ можно получить на https://platform.2gis.ru\n"
            "Также поддерживается переменная окружения TWOGIS_API_KEY.\n"
            "Ключ хранится локально в ~/.neo_parser/settings.json и не попадает в Git."
        )
        help_lbl.setObjectName("Muted")
        help_lbl.setWordWrap(True)
        cl.addWidget(help_lbl)
        lay.addWidget(card)

        db_info = QLabel(f"База данных: {self.db.path}")
        db_info.setObjectName("Muted")
        lay.addWidget(db_info)
        lay.addStretch()
        return w

    def save_preferences(self) -> None:
        self.language = self.language_combo.currentData()
        save_language(self.language)
        self.animations_enabled = self.animations_check.isChecked()
        save_animations_enabled(self.animations_enabled)
        self.apply_language(self.language)
        QMessageBox.information(self, "Настройки", "Настройки сохранены." if self.language == "ru" else "Settings saved.")

    def apply_language(self, language: str) -> None:
        """Apply UI language without restarting the app; data values remain untouched."""
        mapping = ({**TRANSLATIONS, **{v: k for k, v in EN_TRANSLATIONS.items()}} if language == "ru" else {**TRANSLATIONS, **EN_TRANSLATIONS})
        for widget in self.findChildren(QLabel):
            value = widget.text()
            if value in mapping:
                widget.setText(mapping[value])
        for widget in self.findChildren(QPushButton):
            value = widget.text()
            if value in mapping:
                widget.setText(mapping[value])
        for widget in self.findChildren(QCheckBox):
            value = widget.text()
            if value in mapping:
                widget.setText(mapping[value])
        for widget in self.findChildren(QLineEdit):
            value = widget.placeholderText()
            if value in mapping:
                widget.setPlaceholderText(mapping[value])
        for widget in self.findChildren(QTextEdit):
            value = widget.placeholderText()
            if value in mapping:
                widget.setPlaceholderText(mapping[value])
        for widget in self.findChildren(QComboBox):
            for index in range(widget.count()):
                value = widget.itemText(index)
                if value in mapping:
                    widget.setItemText(index, mapping[value])
        for table in self.findChildren(QTableWidget):
            for column in range(table.columnCount()):
                item = table.horizontalHeaderItem(column)
                if item and item.text() in mapping:
                    item.setText(mapping[item.text()])
        # Navigation is rebuilt from stable keys to avoid translating dynamic data.
        nav = {
            "dashboard": ("Обзор", "Overview"), "search": ("Поиск", "Search"),
            "leads": ("Компании", "Companies"), "audit": ("Аудит сайтов", "Website audit"),
            "categories": ("Ниши", "Niches"), "history": ("История", "History"),
            "settings": ("Настройки", "Settings"),
        }
        for key, button in self.nav_buttons.items():
            button.setText(nav[key][0 if language == "ru" else 1])
        self.setWindowTitle("Neo Parser 2.1 — Lead Intelligence")

    def save_settings(self) -> None:
        key = self.key_input.text().strip()
        save_api_key(key)
        self.search_key_status.setText(
            "API-ключ 2ГИС: настроен" if key else "API-ключ 2ГИС: не задан — поиск недоступен"
        )
        QMessageBox.information(self, "Настройки", "Ключ сохранён.")

    # ── lifecycle ──────────────────────────────────────────
    def _apply_window_icon(self) -> None:
        path = _icon_path()
        if path:
            self.setWindowIcon(QIcon(str(path)))

    def closeEvent(self, event) -> None:
        for worker in (self.search_worker, self.audit_worker):
            if worker and worker.isRunning():
                worker.stop()
                worker.wait(8000)
        self.db.close()
        event.accept()


def _icon_path() -> Path | None:
    """Resolve app icon for dev, frozen (PyInstaller) and relative installs."""
    candidates = []
    if getattr(sys, "frozen", False):
        # PyInstaller one-file / one-dir
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "assets" / "icon.png")
            candidates.append(Path(meipass) / "assets" / "icon.ico")
        candidates.append(Path(sys.executable).resolve().parent / "assets" / "icon.png")
        candidates.append(Path(sys.executable).resolve().parent / "icon.ico")
    # Source tree: neo_parser/ui/main_window.py -> ../../assets
    here = Path(__file__).resolve()
    candidates.append(here.parents[2] / "assets" / "icon.png")
    candidates.append(here.parents[2] / "assets" / "icon.ico")
    candidates.append(Path.cwd() / "assets" / "icon.png")
    for p in candidates:
        if p.is_file():
            return p
    return None


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Neo Parser")
    app.setApplicationDisplayName("Neo Parser 2.1")
    app.setOrganizationName("CEO Neki")
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLE)
    icon_file = _icon_path()
    if icon_file:
        app.setWindowIcon(QIcon(str(icon_file)))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
