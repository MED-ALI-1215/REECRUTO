# RECRUTO - AI-Powered Recruitment Platform

An intelligent recruitment platform that automates CV parsing, candidate matching, and interview simulation using AI.

## 🌟 Features

### 1. CV Parser (`app1_cv_parser.py`)

* Multi-format support: PDF, Word (.docx), Images (PNG, JPG), Text files
* AI-powered extraction using Groq LLMs
* Candidate database powered by ChromaDB
* Extracted information includes:

  * Name, Email, Phone
  * Education & Certifications
  * Work Experience
  * Technical & Soft Skills

---

### 2. Job Matcher (`app2_job_matcher.py`)

* AI-powered candidate-to-job matching
* Candidate ranking using vector similarity and LLM evaluation
* Automated email workflows:

  * ✅ Acceptance emails
  * ❌ Rejection emails
* Match scoring system from 0–100%

---

### 3. Interview Simulation (`app3_interview.py`)

* AI-powered interview simulation
* Supports:

  * Technical interviews
  * Behavioral interviews
  * Mixed interviews
* Adaptive questioning system
* Multiple answering methods:

  * ✍️ Text responses
  * 🎤 Voice-recorded responses with speech-to-text transcription
* Detailed candidate evaluation:

  * Overall score
  * Strengths & weaknesses
  * Skill assessment
  * Hiring recommendation
* Downloadable interview transcript

---

## 📋 Prerequisites

* Python 3.8+
* Groq API key: https://console.groq.com/keys
* Gmail account with App Password enabled
* Tesseract OCR installed

---

## 🚀 Installation

### Step 1: Clone & Setup

```bash
cd /path/to/recruto

pip install -r requirements.txt
```

---

### Step 2: Install Tesseract OCR

#### Ubuntu / Debian

```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

#### macOS

```bash
brew install tesseract
```

#### Windows

Download:
https://github.com/UB-Mannheim/tesseract/wiki

---

### Step 3: Configure Environment Variables

Copy the template:

```bash
cp .env.template .env
```

Edit `.env`:

```env
# API Keys
GROQ_API_KEY=gsk_xxxxxxxxxxxxx

# Email Configuration
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_gmail_app_password_here

# ChromaDB
CHROMA_DB_PATH=./chroma_db
```

---

### Step 4: Configure Gmail App Password

1. Enable 2-Factor Authentication
2. Go to:
   Security → 2-Step Verification → App Passwords
3. Generate a Mail app password
4. Add it to the `.env` file

---

## 🎮 Running the Applications

Run each service on a separate terminal:

### Terminal 1 — CV Parser

```bash
streamlit run app1_cv_parser.py --server.port 8501
```

### Terminal 2 — Job Matcher

```bash
streamlit run app2_job_matcher.py --server.port 8502
```

### Terminal 3 — Interview Simulation

```bash
streamlit run app3_interview.py --server.port 8503
```

### Terminal 4 — Main Interface (Optional)

```bash
python app.py
```

---

## 🌐 Access URLs

* Main Interface: http://localhost:5000
* CV Parser: http://localhost:8501
* Job Matcher: http://localhost:8502
* Interview Simulation: http://localhost:8503

---

## 📖 User Guide

### CV Parsing

1. Upload a CV
2. Click “Parse CV”
3. Review extracted information
4. Candidate is automatically stored in ChromaDB

### Candidate Matching

1. Enter job title & description
2. Select number of candidates
3. Run AI matching
4. Review ranked candidates
5. Send acceptance/rejection emails

### Interview Simulation

1. Configure interview settings
2. Start interview
3. Candidate answers using:

   * Text
   * Voice recording
4. Generate AI evaluation report
5. Download transcript

---

## 🛠️ Tech Stack

* Python
* Streamlit
* Groq API
* ChromaDB
* Tesseract OCR
* Gmail SMTP

---

## 🔧 Troubleshooting

### Tesseract Not Found

Install Tesseract OCR and ensure it exists in your system PATH.

### Email Authentication Failed

* Use Gmail App Passwords
* Enable 2FA before generating the password

### ChromaDB Error

Delete the `chroma_db` folder and restart the applications.

### API Rate Limit

Groq free-tier requests may have limitations.
Check usage:
https://console.groq.com/

---

## 🔐 Security Notes

* Never commit `.env` files
* Keep API keys secure
* Use Gmail App Passwords instead of personal passwords
* ChromaDB stores data locally

---

## 🚀 Future Enhancements

* Video interview analysis
* Facial expression assessment
* Multi-language support
* Calendar integration
* Recruiter analytics dashboard
* PDF report generation

---

## 📝 License

This project is intended for educational and internal use.

---

## 🤝 Support

* Groq Docs:
  https://console.groq.com/docs

* ChromaDB Docs:
  https://docs.trychroma.com/

---

Built using Groq, Streamlit, and ChromaDB.
