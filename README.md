# GCLET Smart Canteen Management System

A full-stack, database-driven canteen platform built with Django REST Framework and React/Vite.

## Demo accounts

Run `python manage.py seed_demo`.

- Administrator: `admin` / `Admin@123`
- Student: `student` / `Demo@1234`
- Faculty: `faculty` / `Demo@1234`
- Staff: `staff` / `Demo@1234`

The admin sidebar's **Manage food** page lets administrators add, edit and remove catalogue items, upload a JPG/PNG/WebP photo (up to 5 MB), adjust stock and manage categories. Each demo menu item has its own bundled photo under `backend/media/food/items/`, so the catalogue does not rely on an external image host. Photo creators, source pages and licenses are listed in `backend/media/food/items/ATTRIBUTION.txt`.

The demo seeder creates all 41 items in the GCLET menu across Rice & Meals, Noodles & Chinese, Fast Food, Rolls & Momos, Breakfast & Snacks, Hot Beverages, Cold Beverages and Desserts. It is safe to rerun: existing stock, prices and discounts are preserved, and items excluded from the final menu are made unavailable instead of being deleted.

## Backend setup

```powershell
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Local development uses SQLite by default. To store orders and simulated payment attempts in PostgreSQL, set `DATABASE_URL` to a PostgreSQL connection URL before running migrations and starting Django. The app does not connect to a real payment gateway; simulated payments are excluded from revenue totals.

## Frontend setup

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. API documentation is at `http://127.0.0.1:8000/api/docs/`.

## Tests

```powershell
cd backend
.venv\Scripts\python.exe manage.py test
```

## Payment mode

Cash at counter is recorded when staff completes pickup. UPI, card, net banking and wallet are simulated payment methods; checkout clearly displays **SIMULATED PAYMENT - TEST MODE** and never contacts a payment gateway. The test-only card and UPI fields stay in the browser and are not submitted or stored.

Online checkout creates one order and derives the payable amount from the saved order. Payment attempts have unique transaction IDs and idempotency keys. A simulated failure keeps the original order available for retry; only successful server-side demo verification marks it paid and exposes it to staff. Students can review transactions and download receipts from **Payments**; administrators can review all transactions from the **Transactions** tab.

The payment API is available at `POST /api/payments/create-demo-payment/`, `POST /api/payments/verify-demo-payment/`, `GET /api/payments/history/` and `GET /api/payments/{id}/receipt/`. Test payments are excluded from sales revenue; completed cash payments remain included. No real money is charged.
