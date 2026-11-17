import sys, csv
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,
 QPushButton,QLineEdit,QTableWidget,QTableWidgetItem,QFileDialog,QMessageBox,QComboBox,QFrame,
 QHeaderView,QProgressBar,QStatusBar)
from .db import Database
from .services import import_csv, audit_website, calculate_score

DARK = '''
QWidget { background:#10131a; color:#e8edf5; font-family:Inter,Segoe UI,Arial; font-size:13px; }
QFrame#Sidebar { background:#171c26; border:1px solid #242c3a; border-radius:14px; }
QLabel#Brand { font-size:22px; font-weight:800; color:#ffffff; }
QLabel#Muted { color:#8995a8; }
QPushButton { background:#202938; border:1px solid #303d50; border-radius:8px; padding:9px 14px; color:#e8edf5; }
QPushButton:hover { background:#2a384d; }
QPushButton#Primary { background:#6d5dfc; border:0; font-weight:700; }
QPushButton#Primary:hover { background:#8073ff; }
QLineEdit,QComboBox { background:#171e2a; border:1px solid #30394a; border-radius:8px; padding:9px; selection-background-color:#6d5dfc; }
QTableWidget { background:#151b25; alternate-background-color:#192230; border:1px solid #2a3444; border-radius:10px; gridline-color:#263142; }
QHeaderView::section { background:#202938; color:#aebbd0; padding:9px; border:0; }
QProgressBar { background:#202938; border:0; border-radius:5px; height:8px; text-align:center; }
QProgressBar::chunk { background:#6d5dfc; border-radius:5px; }
'''

class AuditWorker(QThread):
    progress = Signal(int, int)
    result_ready = Signal(int, str, str, bool, int)
    finished_all = Signal()

    def __init__(self, rows):
        super().__init__()
        self.rows = rows
        self.stop_requested = False

    def run(self):
        total = len(self.rows)
        for index, row in enumerate(self.rows, 1):
            if self.stop_requested:
                break
            status, title, has_form = audit_website(row['website'])
            score = calculate_score(dict(row), status, has_form)
            # Send results to the UI thread. SQLite connections must not be
            # used from this worker thread.
            self.result_ready.emit(row['id'], status, title, has_form, score)
            self.progress.emit(index, total)
        self.finished_all.emit()

    def stop(self):
        self.stop_requested = True

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.db=Database(); self.worker=None
        self.setWindowTitle('Neo Parser — CEO Neki'); self.resize(1320,820); self.setMinimumSize(980,650)
        root=QWidget(); outer=QHBoxLayout(root); outer.setContentsMargins(18,18,18,18); outer.setSpacing(16)
        side=QFrame(); side.setObjectName('Sidebar'); side.setFixedWidth(220); sl=QVBoxLayout(side); sl.setContentsMargins(16,18,16,18)
        brand=QLabel('NEO PARSER'); brand.setObjectName('Brand'); sl.addWidget(brand)
        sub=QLabel('LEAD INTELLIGENCE'); sub.setObjectName('Muted'); sl.addWidget(sub); sl.addSpacing(28)
        for name in ['Обзор','База лидов','Аудит сайтов']:
            b=QPushButton(name); b.setCursor(Qt.PointingHandCursor); b.clicked.connect(self.refresh); sl.addWidget(b)
        sl.addStretch(); foot=QLabel('CEO Neki\nNeo Parser 0.1.1'); foot.setObjectName('Muted'); sl.addWidget(foot)
        outer.addWidget(side)
        content=QVBoxLayout(); outer.addLayout(content,1)
        top=QHBoxLayout(); heading=QVBoxLayout(); title=QLabel('Рабочее пространство'); title.setStyleSheet('font-size:25px;font-weight:800'); desc=QLabel('Собирай, проверяй и квалифицируй потенциальных клиентов'); desc.setObjectName('Muted'); heading.addWidget(title); heading.addWidget(desc); top.addLayout(heading); top.addStretch()
        imp=QPushButton('Импорт CSV'); imp.clicked.connect(self.import_file); top.addWidget(imp)
        exp=QPushButton('Экспорт XLSX/CSV'); exp.clicked.connect(self.export_file); top.addWidget(exp)
        content.addLayout(top)
        cards=QHBoxLayout(); self.card_total=self.make_card('Всего лидов','0'); self.card_hot=self.make_card('Высокий приоритет','0'); self.card_sites=self.make_card('С сайтами','0')
        cards.addWidget(self.card_total); cards.addWidget(self.card_hot); cards.addWidget(self.card_sites); content.addLayout(cards)
        controls=QHBoxLayout(); self.search=QLineEdit(); self.search.setPlaceholderText('Поиск по компании, нише, городу, телефону или сайту…'); self.search.textChanged.connect(self.populate); controls.addWidget(self.search,1)
        self.status_filter=QComboBox(); self.status_filter.addItems(['Все статусы','Новый','Проверен','Готов к обращению','Написал','Ответил','Переговоры','Клиент','Отказ']); self.status_filter.currentTextChanged.connect(self.populate); controls.addWidget(self.status_filter)
        content.addLayout(controls)
        self.table=QTableWidget(0,8); self.table.setHorizontalHeaderLabels(['Компания','Ниша','Город','Телефон','Сайт','Аудит','Оценка','Статус']); self.table.setAlternatingRowColors(True); self.table.setSelectionBehavior(QTableWidget.SelectRows); self.table.setEditTriggers(QTableWidget.NoEditTriggers); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.table.setSortingEnabled(True); content.addWidget(self.table,1)
        actions=QHBoxLayout(); self.audit_btn=QPushButton('Проверить сайты'); self.audit_btn.setObjectName('Primary'); self.audit_btn.clicked.connect(self.start_audit); actions.addWidget(self.audit_btn)
        self.stop_btn=QPushButton('Остановить'); self.stop_btn.clicked.connect(self.stop_audit); self.stop_btn.setEnabled(False); actions.addWidget(self.stop_btn)
        self.delete_btn=QPushButton('Удалить выбранного'); self.delete_btn.clicked.connect(self.delete_selected); actions.addWidget(self.delete_btn); actions.addStretch()
        self.progress=QProgressBar(); self.progress.setFixedWidth(180); self.progress.setValue(0); actions.addWidget(self.progress); content.addLayout(actions)
        self.setCentralWidget(root); self.setStatusBar(QStatusBar()); self.statusBar().showMessage('Локальная база готова. Импортируй CSV для начала работы.')
        self.setStyleSheet(DARK); self.refresh()
    def make_card(self,label,value):
        f=QFrame(); f.setObjectName('Sidebar'); l=QVBoxLayout(f); a=QLabel(label); a.setObjectName('Muted'); v=QLabel(value); v.setStyleSheet('font-size:26px;font-weight:800'); l.addWidget(a); l.addWidget(v); f.value_label=v; return f
    def refresh(self): self.populate()
    def populate(self):
        rows=self.db.all(self.search.text()); status=self.status_filter.currentText()
        if status!='Все статусы': rows=[r for r in rows if r['status']==status]
        self.table.setSortingEnabled(False); self.table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            vals=[r['company'],r['category'],r['city'],r['phone'],r['website'],r['website_status'],str(r['score']),r['status']]
            for j,v in enumerate(vals):
                it=QTableWidgetItem(str(v or '—')); it.setData(Qt.UserRole,r['id']); self.table.setItem(i,j,it)
        self.table.setSortingEnabled(True)
        allrows=self.db.all(); self.card_total.value_label.setText(str(len(allrows))); self.card_hot.value_label.setText(str(sum(1 for r in allrows if r['score']>=60))); self.card_sites.value_label.setText(str(sum(1 for r in allrows if r['website'])))
    def import_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Импортировать базу','','CSV (*.csv)')
        if not path:return
        added=0; skipped=0
        try:
            for item in import_csv(path):
                item['score']=calculate_score(item); item['source']='CSV import'
                if self.db.add_lead(item): added+=1
                else: skipped+=1
            self.populate(); self.statusBar().showMessage(f'Импорт завершён: добавлено {added}, дубликатов пропущено {skipped}')
        except Exception as e: QMessageBox.critical(self,'Ошибка импорта',str(e))
    def export_file(self):
        path,_=QFileDialog.getSaveFileName(self,'Экспорт базы','neo_parser_leads.xlsx','Excel (*.xlsx);;CSV (*.csv)')
        if not path:return
        rows=self.db.all(); fields=['company','category','city','phone','email','website','vk','telegram','address','notes','website_status','website_title','website_has_form','score','status','source']
        try:
            if path.lower().endswith('.xlsx'):
                from openpyxl import Workbook
                from openpyxl.styles import Font, PatternFill
                wb=Workbook(); ws=wb.active; ws.title='Leads'; ws.append(fields)
                for cell in ws[1]: cell.font=Font(bold=True,color='FFFFFF'); cell.fill=PatternFill('solid',fgColor='252F40')
                for r in rows: ws.append([r[k] for k in fields])
                ws.freeze_panes='A2'; ws.auto_filter.ref=ws.dimensions
                for col in ws.columns:
                    letter=col[0].column_letter
                    ws.column_dimensions[letter].width=min(max(max(len(str(c.value or '')) for c in col)+2,12),42)
                wb.save(path)
            else:
                if not path.lower().endswith('.csv'): path += '.csv'
                with open(path,'w',newline='',encoding='utf-8-sig') as f:
                    w=csv.DictWriter(f,fieldnames=fields,delimiter=';'); w.writeheader()
                    for r in rows:w.writerow({k:r[k] for k in fields})
            self.statusBar().showMessage(f'Экспортировано записей: {len(rows)}')
        except Exception as e: QMessageBox.critical(self,'Ошибка экспорта',str(e))
    def selected_id(self):
        row=self.table.currentRow()
        if row<0:return None
        it=self.table.item(row,0); return it.data(Qt.UserRole) if it else None
    def delete_selected(self):
        lid=self.selected_id()
        if lid is None:return
        if QMessageBox.question(self,'Удаление','Удалить выбранную компанию?')==QMessageBox.Yes:self.db.delete(lid); self.populate()
    def start_audit(self):
        rows=[r for r in self.db.all() if r['website']]
        if not rows: QMessageBox.information(self,'Аудит','В базе нет сайтов для проверки.'); return
        self.worker=AuditWorker(rows); self.worker.result_ready.connect(self.on_audit_result); self.worker.progress.connect(self.on_progress); self.worker.finished_all.connect(self.audit_done); self.worker.start(); self.audit_btn.setEnabled(False); self.stop_btn.setEnabled(True); self.progress.setMaximum(len(rows)); self.progress.setValue(0)
    def on_audit_result(self, lead_id, status, title, has_form, score):
        self.db.update_audit(lead_id, status, title, has_form, score)
    def on_progress(self,i,total): self.progress.setValue(i); self.statusBar().showMessage(f'Проверка сайтов: {i}/{total}')
    def audit_done(self): self.audit_btn.setEnabled(True); self.stop_btn.setEnabled(False); self.populate(); self.statusBar().showMessage('Проверка завершена')
    def stop_audit(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.stop_btn.setEnabled(False)
            self.statusBar().showMessage('Остановка проверки…')

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(9000)
        self.db.conn.close()
        event.accept()

def main():
    app=QApplication(sys.argv); app.setApplicationName('Neo Parser'); w=MainWindow(); w.show(); sys.exit(app.exec())
if __name__=='__main__': main()
