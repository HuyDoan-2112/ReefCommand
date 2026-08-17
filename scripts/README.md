# Scripts

| Script | Purpose |
| --- | --- |
| `prefetch_external_data.py` | Cache NOAA and AGRRA data for the demo window. Run before every event. |
| `seed_demo.py` | Load labeled synthetic field reports and the simulated resource scenario. |

Run the prefetch script from the backend environment so the project package is
available:

```powershell
cd backend
uv run python ../scripts/prefetch_external_data.py --start YYYY-MM-DD --end YYYY-MM-DD
```
