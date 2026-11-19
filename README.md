# AI-Based Resume Matching & Ranking System

An AI-powered recruitment platform that automates resume parsing, skill extraction, job description analysis, candidate matching, and candidate ranking.

## 🚀 Features

- **Job Description Analysis:** Extract job titles, required skills, experience, and qualifications from job descriptions.
- **AI-Powered Extraction:** Uses Google Gemini API for intelligent job description processing.
- **Resume Parsing:** Extract candidate information from PDF and DOCX resumes.
- **Information Extraction:** Extract names, email addresses, phone numbers, technical skills, education, experience, projects, certifications, and professional links.
- **Candidate Matching:** Match resumes against job requirements.
- **Candidate Ranking:** Rank candidates based on matching scores and relevant skills.
- **Batch Resume Processing:** Upload and process multiple resumes.

## 🛠️ Tech Stack

### Frontend
- React.js
- Vite
- JavaScript
- CSS

### Backend
- Python
- FastAPI
- SQLAlchemy
- Pydantic
- spaCy
- Google Gemini API

### Database
- PostgreSQL

### Tools
- Git & GitHub
- VS Code
- Swagger UI

## 📁 Project Structure

```text
AI-Resume-Parser/
│
├── backend/
│   ├── app/
│   │   ├── core/
│   │   ├── database/
│   │   ├── models/
│   │   ├── routes/
│   │   ├── schemas/
│   │   └── services/
│   │
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── services/
│   │   └── App.jsx
│   └── package.json
│
└── README.md
```

## ⚙️ Local Installation

### 1. Clone the repository

```bash
git clone https://github.com/manikanta2008/AI-Based-Resume-Matching-Ranking-System.git
```

### 2. Backend Setup

```bash
cd AI-Based-Resume-Matching-Ranking-System/backend
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure your `.env` file:

```env
DATABASE_URL=your_postgresql_connection_string
GEMINI_API_KEY=your_gemini_api_key
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

### 3. Frontend Setup

Open another terminal:

```bash
cd AI-Based-Resume-Matching-Ranking-System/frontend
```

Install dependencies:

```bash
npm install
```

Start the frontend:

```bash
npm run dev
```

## 🔐 Environment Variables

Store sensitive credentials in environment variables.

Never commit `.env` files, API keys, or database passwords to GitHub.

## 🎯 Project Objective

To simplify recruitment by automating resume screening and identifying the most relevant candidates based on job requirements using AI, NLP, and semantic matching techniques.

## 👨‍💻 Developer

**Manikanta Repaka**

- GitHub: https://github.com/manikanta2008
- LinkedIn: https://www.linkedin.com/in/mani-kanta-repaka/
- Portfolio: https://manikanta-portfolio-ten.vercel.app/
