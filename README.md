# 🚀 Chirp — Real-Time Distributed Chat System

Chirp is a real-time chat application built with Django Channels and WebSockets, designed with a scalable backend architecture integrating Redis, PostgreSQL, Docker-based workflows, and OTP-based authentication via an external FastAPI service.

This project goes beyond a basic chat app by incorporating asynchronous communication, external service integration, and production-oriented design patterns.

---

## ✨ Features

* ⚡ Real-time messaging using WebSockets (Django Channels)
* 💬 Private and group chat support
* 📇 Contact-based chat initiation
* 🔐 OTP-based authentication via external FastAPI service
* 🔑 API-key secured authentication flow
* 🧠 Persistent message storage using PostgreSQL
* 🚀 Redis-backed channel layer for real-time scalability
* 🐳 Docker-inspired architecture for environment consistency
* 🔍 Live contact search and dynamic chat creation
* 👥 Group creation with multi-user support
* 📡 Fully asynchronous message handling (ASGI)

---

## 🧠 Tech Stack

### Backend

* Django
* Django Channels
* ASGI

### Real-Time Infrastructure

* Redis (channel layer)

### Database

* PostgreSQL

### Authentication

* FastAPI (OTP service)
* API Key-based access control

### DevOps / Environment

* Docker (inspired setup)

### Frontend

* HTML, CSS, JavaScript (Vanilla)

---

## 🏗 Architecture Overview

The system follows a **modular domain-based architecture**:

```
accounts  → authentication & identity
contacts  → user relationships
chat      → real-time messaging (WebSockets + async logic)
home      → UI & routing
config    → ASGI, settings, global routing
```

### Extended System Components

* **Django App** → Core backend & WebSocket handling
* **Redis** → Real-time message broadcasting layer
* **PostgreSQL** → Persistent storage
* **FastAPI Service** → OTP authentication provider
* **API Key Layer** → Secure service-to-service communication

---

## ⚡ System Flow

### 🔐 Authentication Flow

1. User enters phone number
2. Django calls FastAPI OTP service (secured via API key)
3. OTP is generated and verified
4. User session is authenticated

---

### 💬 Chat Flow

1. User selects contact
2. System:

   * finds existing chat room OR
   * creates a new one
3. Client connects via WebSocket:

```
ws://<host>/ws/chat/<room_id>/
```

4. Messages:

   * sent via WebSocket
   * handled asynchronously
   * broadcast using Redis channel layer
   * stored in PostgreSQL

---

## 🔄 Real-Time Architecture

* ASGI enables async request handling
* Django Channels manages WebSocket connections
* Redis acts as the message broker between clients
* Consumers process and broadcast messages
* Database ensures persistence of chat history

---

## 🔐 Security & Configuration

* 🔑 SECRET_KEY stored in environment variables
* 🚫 DEBUG disabled in production mode
* 🔐 OTP authentication handled externally (FastAPI)
* 🔒 API key protection for service communication
* 🧾 Controlled logging (no sensitive data exposure)
* 📦 Sensitive files excluded via `.gitignore`

> ⚠️ Note: WebSocket-level authorization can be further enhanced with room-based access validation.

---

## 📂 Project Structure

```
chirp/
│
├── accounts/
├── contacts/
├── chat/
│   ├── consumers.py
│   ├── routing.py
│   └── models.py
│
├── home/
├── config/
│   ├── settings.py
│   ├── asgi.py
│   └── routing.py
│
├── templates/
├── static/
├── manage.py
└── docker/ (optional setup)
```

---

## 🛠 Setup Instructions

### 1. Clone repository

```bash
git clone https://github.com/<your-username>/chirp-chat-app.git
cd chirp-chat-app
```

---

### 2. Setup virtual environment

```bash
python -m venv venv
venv\Scripts\activate
```

---

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Setup environment variables

Create `.env`:

```
SECRET_KEY=your_secret_key
DEBUG=False
POSTGRES_DB=your_db
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
REDIS_URL=redis://localhost:6379
FAST2API=your_api_key
```

---

### 5. Run services

Ensure:

* PostgreSQL is running
* Redis is running

---

### 6. Apply migrations

```bash
python manage.py migrate
```

---

### 7. Run server

```bash
daphne config.asgi:application
```

---

## 📸 Screenshots

(Add dashboard, chat UI, OTP flow)

---

## 🚧 Future Improvements

* 🔐 WebSocket room-level authorization
* 📦 Full Docker containerization
* ☁️ Deployment (AWS / GCP)
* 🔔 Push notifications
* 📱 Mobile-first UI improvements
* 📊 Message delivery & read receipts

---

## 💡 Key Learnings

* Designing real-time systems with Redis and WebSockets
* Managing async communication using Django Channels
* Integrating external authentication services (FastAPI OTP)
* Structuring scalable backend architectures
* Handling state across distributed components

---

## 👤 Author

Built by Sourya Ghosh

---

## ⭐ Final Note

Chirp demonstrates a transition from simple CRUD applications to **real-time, distributed system design**, integrating multiple services and infrastructure components to simulate production-grade backend architecture.
