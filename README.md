# SnapAI — AI-Powered Event Photo Delivery Platform

> Deliver thousands of event photos professionally. Guests find their pictures instantly using AI face recognition.

---

## Project Structure

```
snapai/
├── backend/
│   ├── app.py                  # Flask entry point (sync route loading + face_recognition preload)
│   ├── config.py               # Configuration & settings
│   ├── requirements.txt        # Python dependencies
│   ├── requirements_fixed.txt   # Alternate dependency snapshot
│   ├── models/
│   │   └── database.py         # SQLAlchemy ORM models
│   ├── routes/
│   │   ├── auth.py             # Photographer auth (register/login/JWT)
│   │   ├── events.py           # Event CRUD & stats
│   │   ├── photos.py           # Upload, indexing, serving photos
│   │   └── guest.py            # Public gallery + AI face search
│   └── services/
│       ├── cloudinary_service.py # Cloud storage integration
│       ├── face_service.py     # Face detection & matching (face_recognition)
│       └── upload_service.py   # File saving, thumbnail generation, watermark
└── frontend/
    ├── index.html              # Landing page
    ├── login.html              # Photographer login/register
    ├── dashboard.html          # Photographer admin dashboard
    ├── gallery_final.html      # Guest-facing event gallery served by /gallery/<slug>
    ├── css/
    │   ├── main.css            # Global styles (luxury dark editorial theme)
    │   ├── dashboard.css       # Dashboard-specific styles
    │   └── gallery.css         # Gallery-specific styles
    └── js/
        ├── api.js              # API client + toast system
        └── dashboard.js        # Dashboard logic
```

## Current Runtime

- The recommended launcher from the repository root is `python start.py`.
- That launcher changes into `snapai/backend` and imports `app` from `app.py`.
- `snapai/backend/app.py` registers all API routes synchronously and preloads `face_recognition` at startup.
- The guest gallery route serves `gallery_final.html`, not `gallery.html`.

---

## Prerequisites

| Tool    | Version  |
|---------|----------|
| Python  | 3.10+    |
| pip     | Latest   |
| CMake   | Required by dlib (face_recognition) |
| dlib    | Installed via pip |

---

## Setup Instructions

### 1. Clone / Extract the project

```bash
cd snapai
```

### 2. Install system dependencies (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y cmake build-essential libopenblas-dev liblapack-dev \
    libx11-dev libgtk-3-dev python3-dev python3-pip
```

**macOS (Homebrew):**
```bash
brew install cmake
```

**Windows:** Install Visual Studio Build Tools + CMake from cmake.org

### 3. Create a virtual environment

```bash
cd backend
python3 -m venv venv
source venv/bin/activate      # Linux/macOS
# or: venv\Scripts\activate   # Windows
```

### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

> `face-recognition` installs `dlib` which takes 5–15 minutes to compile. Be patient!

### 5. Set environment variables (optional)

Create `backend/.env`:

```env
SECRET_KEY=your-super-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
DEBUG=True
FACE_RECOGNITION_MODEL=hog        # 'hog' (CPU, fast) or 'cnn' (GPU, accurate)
FACE_RECOGNITION_TOLERANCE=0.5    # 0.4 = strict, 0.6 = lenient
```

### 6. Run the server

```bash
cd backend
python app.py
```

Server starts at: **http://localhost:5000**

If you are running from the repository root, use:

```bash
python start.py
```

---

## Usage Guide

### For Photographers

1. Open **http://localhost:5000** → Click **Get Started**
2. Register with your name, email, brand color, and watermark
3. In the **Dashboard**, create a new event
4. Go to **Upload Photos** — select your event and drag-drop images
5. Click **Start AI Indexing** — AI scans all faces in the background
6. Share the gallery link with your clients: `http://localhost:5000/gallery/<event-slug>`

### For Guests / Clients

1. Open the gallery link shared by the photographer
2. Click **"Find My Photos"** → take a selfie or upload a photo
3. Give consent for face recognition
4. AI instantly shows all photos with you in them
5. Download or share your photos

---

## API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Photographer registration |
| POST | `/api/auth/login` | Login → JWT token |
| GET  | `/api/auth/me` | Get own profile |
| PUT  | `/api/auth/update-profile` | Update name/brand/watermark |

### Events (JWT required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/events/` | List all events |
| POST | `/api/events/` | Create event |
| GET  | `/api/events/<id>` | Get event |
| PUT  | `/api/events/<id>` | Update event |
| DELETE | `/api/events/<id>` | Delete event |
| GET  | `/api/events/<id>/stats` | Event statistics |
| GET  | `/api/events/dashboard/summary` | Dashboard overview |

### Photos (JWT required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/photos/upload/<event_id>` | Upload photos (multipart) |
| POST | `/api/photos/index/<event_id>` | Start background AI indexing |
| GET  | `/api/photos/indexing-status/<event_id>` | Indexing progress |
| GET  | `/api/photos/list/<event_id>` | Paginated photo list |
| DELETE | `/api/photos/delete/<photo_id>` | Delete a photo |
| GET  | `/api/photos/serve/<event_id>/<filename>` | Serve original |
| GET  | `/api/photos/thumbnail/<event_id>/<filename>` | Serve thumbnail |

### Guest (Public)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/guest/event/<slug>` | Get event info (+ PIN check) |
| GET  | `/api/guest/event/<slug>/photos` | Paginated gallery |
| POST | `/api/guest/event/<slug>/find-me` | AI face match (selfie upload) |
| POST | `/api/guest/verify-pin` | Verify gallery PIN |

---

## Configuration Reference (`config.py`)

| Setting | Default | Description |
|---------|---------|-------------|
| `FACE_RECOGNITION_TOLERANCE` | `0.5` | 0.4 = strict, 0.6 = lenient |
| `FACE_RECOGNITION_MODEL` | `hog` | `hog` for CPU, `cnn` for GPU |
| `THUMBNAIL_SIZE` | `(500, 500)` | Generated thumbnail dimensions |
| `MAX_CONTENT_LENGTH` | `500 MB` | Max upload size per request |

---

## Production Deployment

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn (4 workers)
cd backend
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Or with HTTPS proxy (nginx recommended)
```

**Recommended production stack:**
- **Gunicorn** (WSGI server)
- **Nginx** (reverse proxy + static files)
- **PostgreSQL** (replace SQLite)
- **AWS S3 / Cloudflare R2** (photo storage)
- **Redis** (background job queue — replace threading)

---

## Mobile Support

The guest gallery (`gallery_final.html`) is fully mobile-optimized:
- Responsive grid layout
- Camera access via `getUserMedia` for selfie capture
- Touch-friendly interface
- Fast thumbnail loading with lazy images

---

## Privacy & Consent

- Guests must explicitly check a consent checkbox before face scanning
- Selfies are processed in-memory and **not stored** on disk
- Face encodings (numerical vectors) are stored — not actual photos of faces
- Event owners can make galleries PIN-protected

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `dlib` won't install | Install cmake first, then retry |
| No faces detected | Use well-lit, front-facing selfies |
| Slow indexing | Switch to `FACE_RECOGNITION_MODEL=cnn` with GPU |
| Camera not working | Use HTTPS in production (required by browsers) |
| 500 on upload | Check `UPLOAD_FOLDER` permissions |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, Flask, SQLAlchemy, Flask-JWT-Extended |
| AI/ML | face_recognition (dlib), numpy, Pillow |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Frontend | Vanilla HTML/CSS/JS (zero frameworks) |
| Fonts | Playfair Display, DM Sans, Space Mono |

---

*Built with — SnapAI © 2026*
