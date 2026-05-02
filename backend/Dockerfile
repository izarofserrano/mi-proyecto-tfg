FROM python:3.11-slim

WORKDIR /app

# pandas / numpy / asyncpg all ship manylinux wheels — no gcc needed.
# Only install build tools if a package forces compilation.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Upload directory (overridden by Docker volume at runtime)
RUN mkdir -p /app/uploads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
