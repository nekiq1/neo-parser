# Neo Parser — CEO Neki

Cross-platform desktop lead qualification workspace for Windows and macOS.

## Current MVP (0.1.0)
- Modern dark desktop UI (PySide6)
- Local SQLite database
- CSV import with common Russian/English column aliases and encoding detection
- Duplicate suppression
- Search and CRM statuses
- Website availability/title/basic form audit
- Transparent heuristic lead score
- CSV export (Excel-compatible UTF-8 BOM)
- Background audit with progress and stop

## Important scope
This is a clean new project scaffold, not a decompilation or source-level port of LeadGen Mac. The supplied LeadGen Mac ZIP is a frozen PyInstaller application; it does not contain the original editable Python source. The previous `nekiq1/parser-2gis` repository was not accessible during preparation, so its code has not yet been merged. No automated 2GIS scraping is included. Add sources only through their permitted APIs/exports and respect source terms, robots policies, rate limits, and privacy requirements.

## Run locally
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Build installers via GitHub Actions
1. Create a new empty GitHub repository, e.g. `nekiq1/neo-parser`.
2. Extract this ZIP and push all files to the repository's `main` branch.
3. Open Actions and run **Build Neo Parser**. Download the generated artifacts.
4. To create a GitHub Release with files attached, create and push a version tag:
```bash
git tag v0.1.0
git push origin v0.1.0
```
The workflow builds Windows x64 and macOS Apple Silicon + Intel DMGs. macOS builds are unsigned/not notarized by default; Gatekeeper may warn. For public distribution, configure Apple Developer ID signing and notarization secrets and extend the workflow. Windows EXE is also unsigned unless code signing is configured.

## CSV columns
Required: `company` or `Название`.
Optional: `category`, `city`, `phone`, `email`, `website`, `vk`, `telegram`, `address`, `notes` (Russian aliases supported).

## Product identity
**Neo Parser**  
**CEO Neki**
