# Senior Care Backend (Django REST)

This folder contains the Django REST API for the Senior Care app.

## Prerequisites
- **Python**: 3.10 or higher recommended.
- **Git** (optional, but recommended).

## Setup & Running the Project

Follow the instructions for your operating system to set up and run the backend.

### 🍎 macOS / 🐧 Linux

1. **Open your terminal**.
2. **Navigate to the project folder:**
   ```bash
   cd path/to/senior_care_project
   ```
3. **Create a virtual environment:**
   ```bash
   python3 -m venv .venv
   ```
4. **Activate the virtual environment:**
   ```bash
   source .venv/bin/activate
   ```
5. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
6. **Set up environment variables:**
   ```bash
   cp .env.example .env
   ```
   *(Note: Edit `.env` to set the `DJANGO_SECRET_KEY` or database configurations if necessary).*
7. **Apply database migrations:**
   ```bash
   python3 manage.py migrate
   ```
8. **Run the server:**
   ```bash
   python3 manage.py runserver 0.0.0.0:8000
   ```

### 🪟 Windows

1. **Open Command Prompt or PowerShell**.
2. **Navigate to the project folder:**
   ```cmd
   cd path\to\senior_care_project
   ```
3. **Create a virtual environment:**
   ```cmd
   python -m venv .venv
   ```
4. **Activate the virtual environment:**
   - **Command Prompt:** `.venv\Scripts\activate.bat`
   - **PowerShell:** `.venv\Scripts\Activate.ps1`
5. **Install dependencies:**
   ```cmd
   pip install -r requirements.txt
   ```
6. **Set up environment variables:**
   ```cmd
   copy .env.example .env
   ```
   *(Note: Edit `.env` to set the `DJANGO_SECRET_KEY` or database configurations if necessary).*
7. **Apply database migrations:**
   ```cmd
   python manage.py migrate
   ```
8. **Run the server:**
   ```cmd
   python manage.py runserver 0.0.0.0:8000
   ```

---

## Access the API

Once the server is running, the API base URL will be:
`http://127.0.0.1:8000/api/` (or your machine's local network IP address).

## Run Tests
To run automated tests, make sure your virtual environment is activated and run:
```bash
pytest -q
```
