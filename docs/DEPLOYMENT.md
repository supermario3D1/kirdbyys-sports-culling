# Deployment Instructions

Kirdbyys is designed to run as a **local desktop application** or a **single-user local server**. There is no cloud deployment or remote access required.

## Deployment Modes

### 1. Desktop Application (Recommended)

Run Kirdbyys on your local machine and open it in your browser.

```bash
cd kirdbyys-sports-culling
source .venv/bin/activate
python -m kirdbyys
```

Open: http://127.0.0.1:7840

### 2. Systemd Service (Linux)

Create a user service to start Kirdbyys automatically on login.

Create `~/.config/systemd/user/kirdbyys.service`:

```ini
[Unit]
Description=Kirdbyys Sports Culling Tool
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/YOURUSER/kirdbyys-sports-culling
ExecStart=/home/YOURUSER/kirdbyys-sports-culling/.venv/bin/python -m kirdbyys
Restart=on-failure

[Install]
WantedBy=default.target
```

Enable and start:

```bash
systemctl --user daemon-reload
systemctl --user enable kirdbyys
systemctl --user start kirdbyys
```

### 3. Windows Shortcut

Create a shortcut with target:

```cmd
C:\Users\YOURUSER\kirdbyys-sports-culling\.venv\Scripts\python.exe -m kirdbyys
```

Set start in to `C:\Users\YOURUSER\kirdbyys-sports-culling`.

### 4. macOS Automator

Use Automator to create an application that runs:

```bash
cd /Users/YOURUSER/kirdbyys-sports-culling && source .venv/bin/activate && python -m kirdbyys
```

## Security Notes

- By default, Kirdbyys binds to `127.0.0.1` only. It is not accessible from other devices.
- To allow LAN access, set `HOST=0.0.0.0` in `.env`. This is not recommended on untrusted networks.
- No authentication is implemented; this is a single-user local tool.

## Data Locations

All application data lives in the project directory:

| Directory | Contents |
|-----------|----------|
| `kirdbyys/data/` | SQLite database and imported project files |
| `kirdbyys/cache/` | Thumbnails and previews |
| `kirdbyys/models/` | Downloaded ONNX models |
| `kirdbyys/exports/` | Exported selections |
| `kirdbyys/temp/` | Temporary uploads |

## Backup

To back up your work:

```bash
# Back up the entire data directory
tar -czvf kirdbyys-backup-$(date +%Y%m%d).tar.gz kirdbyys/data kirdbyys/cache
```

## Updates

1. Pull or download the latest release
2. Activate virtual environment
3. Run `pip install -r requirements.txt` to update dependencies
4. Run `python scripts/setup_models.py` to update models
5. Restart Kirdbyys

The database schema is automatically created on startup. Schema migrations for future versions will be handled via Alembic (planned).

## Troubleshooting

- If the port is already in use, set `PORT=7841` in `.env`
- If the UI fails to load, check that the virtual environment is activated and all dependencies are installed
- If analysis fails, check `kirdbyys/data/*.log` or the job error log in the API response
