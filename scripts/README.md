# Scripts

| Script | Purpose |
| --- | --- |
| `prefetch_external_data.py` | Cache NOAA and AGRRA data for the demo window. Run before every event. |
| `seed_demo.py` | Load labeled synthetic field reports and the simulated resource scenario. |

Run them through the task runner from the repository root so they pick up the
backend environment:

```powershell
.\tasks.ps1 prefetch
```

On macOS or Linux, run the same commands listed in that script by hand, or use
`Makefile` if your team keeps one.
