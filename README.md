# Neo Parser — CEO Neki

Desktop workspace for managing and qualifying business leads.

## Supported builds

- **Windows 10/11 x64** — `Neo Parser.exe`
- **macOS Apple Silicon (M1 and newer, arm64)** — `Neo-Parser-macOS-Apple-Silicon-arm64.dmg`
- Intel Macs are intentionally not included.

The project uses one Python/PySide6 codebase and creates separate native builds on GitHub-hosted Windows and Apple Silicon macOS runners.

## Current MVP

- Dark desktop UI (PySide6)
- Local SQLite database
- CSV import with Russian/English column aliases and common encoding detection
- Duplicate suppression
- Search and CRM statuses
- Basic website availability/title/form audit
- Heuristic lead score
- CSV and XLSX export
- Background website audit with progress and stop

## Important scope

This is a clean project, not a decompilation or source-level port of LeadGen Mac. The supplied LeadGen Mac ZIP was a frozen PyInstaller application and did not contain the original editable Python source. The previous `nekiq1/parser-2gis` repository was not accessible during preparation, so its code has not been merged. Automated 2GIS data collection is not included yet. Add data sources only through permitted APIs/exports and respect their terms, rate limits, and privacy requirements.

## Run locally

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS:
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

## Build with GitHub Actions

1. Open the repository's **Actions** tab.
2. Select **Build Neo Parser** and click **Run workflow** to create downloadable artifacts.
3. To create a GitHub Release with both installers attached, push a version tag:

```bash
git tag v0.1.1
git push origin v0.1.1
```

The workflow uses Node 24-compatible action versions: checkout v6, setup-python v6, upload-artifact v6, download-artifact v7, and softprops/action-gh-release v3.

### macOS first launch

The DMG is currently unsigned and not notarized because Apple Developer signing credentials have not been configured. macOS may show a Gatekeeper warning on first launch. Public distribution should add Developer ID signing and notarization.

The Windows executable is also unsigned, so Windows SmartScreen may show a warning.

## CSV columns

Required: `company` or `Название`.

Optional: `category`, `city`, `phone`, `email`, `website`, `vk`, `telegram`, `address`, `notes`.

## Product identity

**Neo Parser**  
**CEO Neki**
