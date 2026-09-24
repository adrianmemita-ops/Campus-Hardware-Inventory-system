# Campus Inventory

Flask web app for managing campus inventory, borrowing, reservations, and accounts.

## Run locally

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python web_app.py
```

Without `DATABASE_URL`, the app uses the local `lab_tracker.db` SQLite database.

## Deploy with GitHub, Supabase, and Render

1. Create a GitHub repository and push this project (do not push `.env`, database files, or secrets).
2. Create a Supabase project and copy its Postgres connection string from **Connect**. Use the transaction pooler connection if the direct connection is unavailable.
3. In Render, choose **New > Blueprint**, connect the GitHub repository, and select `render.yaml`.
4. Set the `DATABASE_URL` environment variable in Render to the Supabase Postgres connection string. Render generates `SECRET_KEY`.
5. Deploy. Render will run the schema setup automatically, and `/health` is the service health check.

To migrate the existing local SQLite data before deploying, run:

```powershell
python postgresql.py --database-url "your-supabase-postgres-connection-string"
```
>>>>>>> 2ac3e35 (Prepare campus inventory for Render deployment)
