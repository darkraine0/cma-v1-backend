del homes.db
call venv\Scripts\Activate
uvicorn app.main:app --host 0.0.0.0 --port 8080