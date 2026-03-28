# RECRUTO - Complete Setup Guide

## 📋 Table of Contents
1. [System Requirements](#system-requirements)
2. [Installation Steps](#installation-steps)
3. [Configuration](#configuration)
4. [Running the Platform](#running-the-platform)
5. [Testing](#testing)
6. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Requirements:
- **OS**: Windows 10/11, macOS 10.15+, or Ubuntu 20.04+
- **Python**: 3.8 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Disk Space**: 2GB for dependencies and database
- **Internet**: Required for API calls

### Required Accounts:
1. **Anthropic Account** - For Claude AI API
2. **Gmail Account** - For sending emails (with App Password enabled)

---

## Installation Steps

### Step 1: Install Python

#### Windows:
1. Download from https://www.python.org/downloads/
2. Run installer
3. ✅ Check "Add Python to PATH"
4. Click "Install Now"

#### macOS:
```bash
# Using Homebrew
brew install python@3.11
```

#### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install python3 python3-pip
```

Verify installation:
```bash
python3 --version
# Should show Python 3.8 or higher
```

### Step 2: Install Tesseract OCR (Required for Image CV Parsing)

#### Windows:
1. Download installer: https://github.com/UB-Mannheim/tesseract/wiki
2. Run installer (remember installation path, e.g., `C:\Program Files\Tesseract-OCR`)
3. Add to PATH:
   - Right-click "This PC" → Properties → Advanced System Settings
   - Environment Variables → System Variables → Path → Edit
   - Add Tesseract installation path

#### macOS:
```bash
brew install tesseract
```

#### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install tesseract-ocr
```

Verify installation:
```bash
tesseract --version
# Should display Tesseract version
```

### Step 3: Install Python Dependencies

Navigate to project folder and install requirements:

```bash
cd /path/to/recruto
pip install -r requirements.txt
```

This installs:
- Streamlit (web interface)
- Flask (routing)
- python-docx (Word documents)
- PyPDF2, pdfplumber (PDF parsing)
- pytesseract (OCR)
- ChromaDB (vector database)
- Anthropic (Claude AI)
- And more...

---

## Configuration

### Step 1: Get Anthropic API Key

1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to "API Keys"
4. Click "Create Key"
5. Copy the key (starts with `sk-ant-`)
6. **Important**: Store it securely - you won't see it again!

**Free Tier**: $5 in free credits (sufficient for testing)

### Step 2: Setup Gmail App Password

1. Go to https://myaccount.google.com/
2. Click "Security" in left sidebar
3. Enable "2-Step Verification" (if not already enabled)
4. Go back to Security → "2-Step Verification"
5. Scroll down to "App passwords"
6. Select app: "Mail"
7. Select device: "Other" → Enter "RECRUTO"
8. Click "Generate"
9. Copy the 16-character password (no spaces)

**Note**: This is NOT your regular Gmail password!

### Step 3: Create .env File

1. Copy the template:
```bash
cp .env.template .env
```

2. Edit `.env` file with your credentials:
```env
# API Keys
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Email Configuration  
EMAIL_ADDRESS=medalialouani7@gmail.com
EMAIL_PASSWORD=abcd efgh ijkl mnop

# ChromaDB Configuration
CHROMA_DB_PATH=./chroma_db
```

**Security**: Never commit `.env` file to Git!

### Step 4: Verify Setup

Run the setup verification script:
```bash
python setup_check.py
```

This checks:
- ✅ Python version
- ✅ All dependencies installed
- ✅ Tesseract OCR available
- ✅ .env file properly configured
- ✅ All required files present

---

## Running the Platform

### Option 1: Quick Start (Recommended)

#### Linux/macOS:
```bash
chmod +x start.sh
./start.sh
```

#### Windows:
```bash
start.bat
```

This automatically starts all three applications:
- CV Parser on port 8501
- Job Matcher on port 8502
- Interview Simulation on port 8503

### Option 2: Manual Start

Open **3 separate terminals**:

#### Terminal 1 - CV Parser:
```bash
streamlit run app1_cv_parser.py --server.port 8501
```

#### Terminal 2 - Job Matcher:
```bash
streamlit run app2_job_matcher.py --server.port 8502
```

#### Terminal 3 - Interview Simulation:
```bash
streamlit run app3_interview.py --server.port 8503
```
#### terminal 4 - AI interview :
streamlit run app4_dashboard.py --server.port 8504

### Accessing the Applications

Once running, open in browser:
- **CV Parser**: http://localhost:8501
- **Job Matcher**: http://localhost:8502
- **Interview Simulation**: http://localhost:8503

---

## Testing

### Test 1: CV Parser

1. Open CV Parser (http://localhost:8501)
2. Upload `test_data/sample_cv.txt`
3. Enter API key in sidebar
4. Click "Parse CV"
5. Verify structured information is extracted
6. Check that candidate is saved to database

### Test 2: Job Matcher

1. Open Job Matcher (http://localhost:8502)
2. Copy job description from `test_data/sample_job_description.txt`
3. Enter job title: "Senior Python Developer"
4. Paste job description
5. Click "Find Matching Candidates"
6. Verify sample CV appears with match score

### Test 3: Interview Simulation

1. Open Interview Simulation (http://localhost:8503)
2. Enter candidate name: "Test User"
3. Job position: "Python Developer"
4. Select interview type and difficulty
5. Click "Start Interview"
6. Answer a few questions
7. Click "Generate Evaluation"

### Test 4: Email Functionality

**Important**: Test with your own email first!

1. In Job Matcher, find matched candidate
2. Enter YOUR email address
3. Click "Accept" or "Reject"
4. Check your email inbox
5. Verify email received and formatted correctly

---

## Troubleshooting

### Issue: "Module not found" error

**Solution**:
```bash
pip install -r requirements.txt --upgrade
```

### Issue: "Tesseract not found"

**Solution**:
- **Windows**: Add Tesseract to PATH (see Installation Step 2)
- **Mac/Linux**: Reinstall with `brew install tesseract` or `apt install tesseract-ocr`
- Verify: `tesseract --version`

### Issue: "ChromaDB error: Cannot connect"

**Solution**:
```bash
# Delete existing database and restart
rm -rf chroma_db/
# Restart applications
```

### Issue: "Email authentication failed"

**Solutions**:
1. Verify you're using App Password, not regular password
2. Ensure 2-Factor Authentication is enabled
3. Generate new App Password
4. Check for typos in `.env` file (remove any spaces)
5. Try this test:
```python
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your_email@gmail.com', 'your_app_password')
print("Success!")
```

### Issue: "API rate limit exceeded"

**Solutions**:
1. Wait a few minutes
2. Check usage at https://console.anthropic.com/
3. Free tier: $5 credit limit
4. Upgrade to paid tier if needed

### Issue: Port already in use

**Solution**:
```bash
# Find and kill process using port 8501
# Linux/Mac:
lsof -ti:8501 | xargs kill -9

# Windows:
netstat -ano | findstr :8501
taskkill /PID <PID> /F
```

### Issue: "Streamlit command not found"

**Solution**:
```bash
# Reinstall Streamlit
pip uninstall streamlit
pip install streamlit

# Or use python -m
python -m streamlit run app1_cv_parser.py --server.port 8501
```

### Issue: ChromaDB storage grows too large

**Solution**:
```bash
# Clear database (WARNING: Deletes all candidates)
rm -rf chroma_db/
# Restart applications - new empty DB will be created
```

---

## Performance Tips

1. **CV Parsing**: 
   - PDFs parse faster than images
   - Well-formatted CVs extract better

2. **Job Matching**:
   - Specific job descriptions = better matches
   - Start with 5 candidates, increase if needed

3. **Interviews**:
   - 5-7 questions is optimal
   - Longer interviews consume more API credits

4. **Database**:
   - ChromaDB is fast for dozens of candidates
   - For 100+ candidates, response times may increase slightly

---

## Security Best Practices

1. ✅ Never commit `.env` to version control
2. ✅ Use App Passwords, not regular passwords
3. ✅ Keep API keys secure
4. ✅ Regularly rotate credentials
5. ✅ Don't share `.env` files

---

## Need Help?

1. Check this troubleshooting guide
2. Review README.md
3. Check Anthropic docs: https://docs.anthropic.com/
4. Check ChromaDB docs: https://docs.trychroma.com/
5. Check Streamlit docs: https://docs.streamlit.io/

---

## Quick Reference

### Common Commands

```bash
# Check setup
python setup_check.py

# Start all apps
./start.sh  # Linux/Mac
start.bat   # Windows

# Install dependencies
pip install -r requirements.txt

# Run individual apps
streamlit run app1_cv_parser.py --server.port 8501
streamlit run app2_job_matcher.py --server.port 8502
streamlit run app3_interview.py --server.port 8503

# Clear database
rm -rf chroma_db/
```

### File Structure

```
recruto/
├── app1_cv_parser.py          # CV Parser app
├── app2_job_matcher.py        # Job Matcher app  
├── app3_interview.py          # Interview app
├── start.sh / start.bat       # Quick start scripts
├── setup_check.py             # Setup verification
├── requirements.txt           # Dependencies
├── .env                       # Your config (CREATE THIS)
├── .env.template             # Config template
├── README.md                  # Main documentation
├── SETUP_GUIDE.md            # This file
├── utils/                    # Utilities
│   ├── cv_parser.py
│   ├── database.py
│   └── email_sender.py
└── test_data/                # Sample test files
    ├── sample_cv.txt
    └── sample_job_description.txt
```

---

**You're all set! 🎉**

Start with the test files in `test_data/` to familiarize yourself with the platform.