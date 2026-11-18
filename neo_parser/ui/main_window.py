"""Main application window with multi-page navigation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
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

from ..config import CITIES, DEFAULT_NICHES, STATUSES, get_api_key, save_api_key
from ..db import Database
from ..services.export import export_csv, export_xlsx
from ..sources.twogis import TwoGisProvider
from ..workers import AuditWorker, SearchWorker
from .styles import DARK_STYLE


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.search_worker: SearchWorker | None = None
        self.audit_worker: AuditWorker | None = None
        self.nav_buttons: dict[str, QPushButton] = {}

        self.setWindowTitle("Neo Parser 2.0 — Lead Intelligence")
        self.resize(1400, 860)
        self.setMinimumSize(1100, 700)
        self._apply_window_icon()

        root = QWidget()
        outer = QHBoxLayout(root)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(14)

        # Sidebar
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(220)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(14, 18, 14, 18)
        sl.setSpacing(4)

        brand = QLabel("NEO PARSER")
        brand.setObjectName("Brand")
        sl.addWidget(brand)
        sub = QLabel("v2.0  ·  CEO Neki")
        sub.setObjectName("Muted")
        sl.addWidget(sub)
        sl.addSpacing(20)

        for key, title in [
            ("dashboard", "Dashboard"),
            ("search", "Search"),
            ("leads", "Leads"),
            ("audit", "Website Audit"),
            ("categories", "Categories"),
            ("history", "History"),
            ("settings", "Settings"),
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

    # ── navigation ─────────────────────────────────────────
    def switch_page(self, key: str) -> None:
        for k, btn in self.nav_buttons.items():
            btn.setObjectName("NavActive" if k == key else "Nav")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.stack.setCurrentWidget(self.pages[key])
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
        title = QLabel("Dashboard")
        title.setObjectName("SectionTitle")
        desc = QLabel("Сводка по базе потенциальных клиентов")
        desc.setObjectName("Muted")
        lay.addWidget(title)
        lay.addWidget(desc)

        cards = QHBoxLayout()
        self.dash_total_f, self.dash_total = self._card("Всего лидов")
        self.dash_hot_f, self.dash_hot = self._card("Высокий приоритет (≥60)")
        self.dash_site_f, self.dash_site = self._card("С сайтом")
        self.dash_nosite_f, self.dash_nosite = self._card("Без сайта")
        for f in (self.dash_total_f, self.dash_hot_f, self.dash_site_f, self.dash_nosite_f):
            cards.addWidget(f)
        lay.addLayout(cards)

        info = QLabel(
            "Поиск компаний выполняется через официальный API 2ГИС. "
            "Без API-ключа данные не подставляются — настройте ключ в Settings."
        )
        info.setObjectName("Muted")
        info.setWordWrap(True)
        lay.addWidget(info)
        lay.addStretch()
        return w

    def refresh_dashboard(self) -> None:
        s = self.db.stats()
        self.dash_total.setText(str(s["total"]))
        self.dash_hot.setText(str(s["hot"]))
        self.dash_site.setText(str(s["with_site"]))
        self.dash_nosite.setText(str(s["no_site"]))

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
        title = QLabel("Leads")
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
                r["status"],
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

        status, ok = QInputDialog.getItem(self, "Статус", "Новый статус:", STATUSES, 0, False)
        if ok and status:
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
        title = QLabel("Website Audit")
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
        title = QLabel("Categories")
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
        title = QLabel("History")
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
        title = QLabel("Settings")
        title.setObjectName("SectionTitle")
        desc = QLabel("API-ключи и параметры")
        desc.setObjectName("Muted")
        lay.addWidget(title)
        lay.addWidget(desc)

        card = QFrame()
        card.setObjectName("Card")
        cl = QVBoxLayout(card)
        cl.addWidget(QLabel("API-ключ 2ГИС (Catalog / Places)"))
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
    app.setApplicationDisplayName("Neo Parser 2.0")
    app.setOrganizationName("CEO Neki")
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLE)
    icon_file = _icon_path()
    if icon_file:
        app.setWindowIcon(QIcon(str(icon_file)))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
