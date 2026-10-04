# Aura 2026

Aura 2026 is an AI-powered personalized goal architect, study companion, and progress tracker built using Streamlit, Groq LLMs, and PostgreSQL (Supabase).

---

### **Live Demo:** [Live Demo link](https://aura-2026-a5brye7uysowjzmfrehbkm.streamlit.app/)

## Features

- **Architect:** Set ambitious career/learning goals and break them down into actionable steps with an AI coach.
- **Study & Notes:** Organize study material and keep track of key insights.
- **Coach & History:** Store and review past coaching conversations and feedback.
- **Progress & Energy Check-in:** Track daily energy levels, earn Aura Points, and keep momentum high.
- **Leaderboard & Profile:** Gamify your learning progress and manage your user profile.
- **Cloud Database Integration:** Persistent storage for user data, logs, and preferences using SQLAlchemy and PostgreSQL.

---

## Tech Stack

- **Frontend / Framework:** [Streamlit](https://streamlit.io/)
- **AI / LLM:** [Groq API](https://groq.com/)
- **Database:** PostgreSQL (via [Supabase](https://supabase.com/))
- **ORM:** SQLAlchemy
- **Language:** Python 3.10+

---

## Getting Started

### Prerequisites

Ensure you have Python 3.10+ and `pip` installed on your machine.

### 1. Clone the Repository

```bash
git clone [https://github.com/Teju-2007/Aura-2026.git](https://github.com/Teju-2007/Aura-2026.git)
cd Aura-2026
```

### 2. Create and Activate a Virtual Environment

* **Using Conda:**
  ```bash
  conda create -n scaling_mle python=3.10 -y
  conda activate scaling_mle
  ```
* **Using `venv`:**
  ```bash
  python -m venv venv
  # On Windows:
  venv\Scripts\activate
  # On macOS/Linux:
  source venv/bin/activate
  ```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Configuration

Create a `.env` file in the root directory of the project and add the following environment variables:

```env
# Groq API Configuration
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b

# PostgreSQL Database Connection String
DATABASE_URL=postgresql://postgres.gvkblkcqdvthjfwfwaio:your_password@db.gvkblkcqdvthjfwfwaio.supabase.co:5432/postgres?sslmode=require

# Optional Email Reminders
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
```

---

## Running the Application Locally

Start the Streamlit development server:

```bash
streamlit run app.py
```

The app will automatically initialize database tables on startup if they do not already exist and open in your default browser at `http://localhost:8501`.

---

## Deployment

To deploy on **Streamlit Community Cloud**:

1. Push your repository to GitHub (ensure `.env` is listed in your `.gitignore`).
2. Go to [share.streamlit.io](https://share.streamlit.io) and create a new app linked to your repository.
3. In the Streamlit deployment settings, open **Advanced Settings** -> **Secrets**.
4. Add your secrets in TOML format:

   ```toml
   GROQ_API_KEY = "your_groq_api_key_here"
   GROQ_MODEL = "openai/gpt-oss-120b"
   DATABASE_URL = "postgresql://postgres.gvkblkcqdvthjfwfwaio:your_password@db.gvkblkcqdvthjfwfwaio.supabase.co:5432/postgres?sslmode=require"
   ```
5. Click **Deploy**.

---

## Author

Built by **Tejaveni Chillapalli** | Aspiring Machine Learning Engineer
