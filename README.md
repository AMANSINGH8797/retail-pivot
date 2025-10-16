# Retail Pivot Dash (Web)

## Deploy to Render (easy)
1. Create a new **Web Service** on Render -> **Build & Deploy from Git**.
2. Push these files to a repo, select it on Render.
3. Render will use `render.yaml` to build & run (Python 3.11).
4. Upload CSVs into the `data/` folder in your repo (or mount a disk).

## Deploy to Railway/Heroku
- Railway: create new service from repo, it uses **Procfile** -> `web: gunicorn app:server`.
- Heroku (if you use it): same Procfile works; set Python 3.11 in system settings if needed.

## Deploy with Docker
```
docker build -t retail-pivot .
docker run -p 8080:8080 -v $(pwd)/data:/app/data retail-pivot
```

## Local run
```
pip install -r requirements.txt
python app.py
```

Put CSV files under `data/` folder. Exports are saved under `exports/`.
