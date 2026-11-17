# Neo Parser 2.0

Desktop lead intelligence. **CEO Neki**

Поддерживаемые сборки:

| Платформа | Артефакт |
|-----------|----------|
| Windows 10/11 **x64** | `Neo Parser.exe` |
| macOS **Apple Silicon (M1+)** | `Neo-Parser-macOS-Apple-Silicon-arm64.dmg` |

Intel Mac не поддерживается.

## Запуск из исходников

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
# ключ 2ГИС: Settings в приложении или TWOGIS_API_KEY в .env
python main.py
```

## Сборка

### Windows x64 (CI или локально)

GitHub Actions → workflow **Build Neo Parser** → артефакт Windows.

Локально:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1
```

### macOS M1+ (рекомендуется локально)

GitHub часто **не выделяет** `macos-latest` runner (очередь). Надёжный путь — сборка на Mac M1/M2/M3/M4:

```bash
chmod +x scripts/build_macos.sh
./scripts/build_macos.sh
# → dist/Neo-Parser-macOS-Apple-Silicon-arm64.dmg
```

## API 2ГИС

Поиск компаний нужен ключ Catalog/Places: [platform.2gis.ru](https://platform.2gis.ru).  
Без ключа поиск не имитируется. Импорт CSV, аудит сайтов, score, экспорт работают.

## Тесты

```bash
pytest tests/ -q
```
