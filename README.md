# Sambandha API

A FastAPI backend for Sambandha - a Nepali Matrimonial App.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Setup Instructions](#setup-instructions)
- [Environment Variables](#environment-variables)
- [Database Migrations](#database-migrations)
- [Running with Docker](#running-with-docker)
- [API Documentation](#api-documentation)
- [API Endpoints](#api-endpoints)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

---

## Project Overview

Sambandha is a Nepali matrimonial platform. This repository contains the backend API, built with FastAPI, supporting
user registration, matchmaking, chat, admin management, and more.

## Features

- User registration and authentication (email/phone)
- Profile management and completion suggestions
- Preferences and AI-powered matchmaking
- Likes, matches, and chat messaging
- Notifications
- Admin panel for user/report management
- CORS support
- OpenAPI docs (Swagger & ReDoc)

## Tech Stack

- Python 3.10+
- FastAPI
- SQLAlchemy
- Pydantic
- PostgreSQL (recommended)
- Alembic (migrations)
- JWT authentication
- Docker & Docker Compose

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/sambandha-backend.git
cd sambandha-backend
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env` and update values as needed:

```bash
cp .env.example .env
```

Or edit `.env` directly. See [Environment Variables](#environment-variables) below for details.

### 4. Run the server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

For network access, you can also run:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Environment Variables

The following variables are required in your `.env` file:

| Variable                          | Description                           |
|-----------------------------------|---------------------------------------|
| DATABASE_URL                      | PostgreSQL connection string          |
| SECRET_KEY                        | JWT secret for users                  |
| ALGORITHM                         | JWT algorithm (default: HS256)        |
| ACCESS_TOKEN_EXPIRE_MINUTES       | JWT expiry (user) in minutes          |
| ADMIN_SECRET_KEY                  | JWT secret for admin                  |
| ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES | JWT expiry (admin) in minutes         |
| SMTP_SERVER                       | SMTP server for email                 |
| SMTP_PORT                         | SMTP port                             |
| SMTP_USERNAME                     | SMTP username                         |
| SMTP_PASSWORD                     | SMTP password                         |
| EMAIL_FROM                        | Sender email address                  |
| EMAIL_FROM_NAME                   | Sender name                           |
| DEBUG                             | Debug mode (True/False)               |
| ALLOWED_ORIGINS                   | CORS allowed origins (list)           |
| ADMIN_ALLOWED_ORIGINS             | CORS allowed origins for admin (list) |

See the provided `.env` file for example values.

## Database Migrations

This project uses Alembic for migrations.

- To create a new migration:
  ```bash
  alembic revision --autogenerate -m "Migration message"
  ```
- To apply migrations:
  ```bash
  alembic upgrade head
  ```

## Running with Docker

You can run the backend and database using Docker Compose:

```bash
docker-compose up --build
```

- The backend will be available at `http://localhost:8000`
- The database will be available at `localhost:5432`

## API Documentation

- Swagger UI: [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs)
- ReDoc: [http://127.0.0.1:8000/api/redoc](http://127.0.0.1:8000/api/redoc)

## API Endpoints

- `/api/auth/register` - Register user
- `/api/auth/token` - Login (get JWT)
- `/api/users/me` - Get current user
- `/api/profiles/me` - Manage profile
- `/api/preferences/me` - Manage preferences
- `/api/likes/` - Like users
- `/api/matches/` - View matches
- `/api/chats/` - Chat with matches
- `/api/messages/` - Send/receive messages
- `/api/notifications/` - User notifications
- `/api/admin/` - Admin endpoints
- `/api/shortlist/` - Shortlist users

See `/api/docs` for full details and request/response formats.

## Testing

You can use [Postman](https://www.postman.com/) or Swagger UI to test endpoints.

To run automated tests (if available):

```bash
pytest
```

## Contributing

Contributions are welcome! Please open issues or submit pull requests for improvements or bug fixes.

## License

MIT

---

**Sambandha** – Nepali Matrimonial App Backend
