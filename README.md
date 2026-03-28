# RECRUTO - AI-Powered Recruitment Platform

An intelligent recruitment platform that automates CV parsing, candidate matching, and interview simulation using AI.

## 🌟 Features

### 1. CV Parser (`app1_cv_parser.py`)
- **Multi-format support**: PDF, Word (.docx), Images (PNG, JPG), Text files
- **AI-powered extraction**: Uses Claude AI to extract structured information
- **Candidate database**: Stores candidates in ChromaDB for efficient searching
- **Supported data extraction**:
  - Name, Email, Phone
  - Education & Certifications
  - Work Experience
  - Skills (Technical & Soft)

### 2. Job Matcher (`app2_job_matcher.py`)
- **Smart matching**: AI-powered candidate-to-job matching using vector similarity
- **Auto-ranking**: Claude AI ranks candidates based on experience, skills, and fit
- **Email automation**:
  - ✅ Acceptance emails with interview scheduling
  - ❌ Professional rejection emails
- **Match scoring**: 0-100% match score for each candidate

### 3. Interview Simulation (`app3_interview.py`)
- **AI interviewer**: Claude AI conducts realistic text-based interviews
- **Multiple types**: Technical, Behavioral, or Mixed interviews
- **Adaptive questioning**: AI asks follow-up questions based on previous answers
- **Detailed evaluation**:
  - Overall score (0-100)
  - Strengths & weaknesses
  - Skills assessment
  - Hiring recommendation
- **Transcript download**: Save complete interview for records

## 📋 Prerequisites

- Python 3.8 or higher
- Anthropic API key (get it from https://console.anthropic.com/)
- Gmail account with App Password enabled (for email features)
- Tesseract OCR (for image-based CV parsing)

## 🚀 Installation

### Step 1: Clone and Setup

```bash
# Navigate to project directory
cd /path/to/recruto

# Install Python dependencies
pip install -r requirements.txt
```

### Step 2: Install Tesseract OCR

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download installer from: https://github.com/UB-Mannheim/tesseract/wiki

### Step 3: Configure Environment Variables

1. Copy the template:
```bash
cp .env.template .env
```

2. Edit `.env` file with your credentials:
```env
# API Keys
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx

# Email Configuration
EMAIL_ADDRESS=medalialouani7@gmail.com
EMAIL_PASSWORD=your_gmail_app_password_here

# ChromaDB Configuration
CHROMA_DB_PATH=./chroma_db
```

### Step 4: Setup Gmail App Password

1. Go to Google Account settings: https://myaccount.google.com/
2. Enable 2-Factor Authentication
3. Go to Security → 2-Step Verification → App passwords
4. Generate a new app password for "Mail"
5. Copy the 16-character password to `.env` file

## 🎮 Usage

### Running the Applications

You need to run **3 separate Streamlit apps** on different ports:

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

#### Terminal 4 - Main HTML Interface (Optional):
```bash
python app.py
```

### Accessing the Applications

- **Main Landing Page**: http://localhost:5000
- **CV Parser**: http://localhost:8501
- **Job Matcher**: http://localhost:8502
- **Interview Simulation**: http://localhost:8503

## 📖 User Guide

### 1. Parsing CVs

1. Open CV Parser app
2. Upload CV file (PDF, Word, Image, or Text)
3. Enter candidate name (optional - AI will extract it)
4. Click "Parse CV"
5. Review extracted information
6. CV is automatically saved to database

### 2. Matching Candidates to Jobs

1. Open Job Matcher app
2. Enter job title and description
3. Select number of candidates to match
4. Click "Find Matching Candidates"
5. Review matched candidates with scores
6. (Optional) Click "Rank Candidates with AI" for detailed ranking
7. Enter candidate emails and click Accept/Reject to send emails

### 3. Conducting Interviews

1. Open Interview Simulation app
2. Enter candidate details and select interview type
3. Choose difficulty level and number of questions
4. Click "Start Interview"
5. Answer each question thoughtfully
6. After final question, click "Generate Evaluation"
7. Download transcript for records

## 🛠️ Project Structure

```
recruto/
├── app.py                      # Flask router for HTML interface
├── app1_cv_parser.py          # CV Parser Streamlit app
├── app2_job_matcher.py        # Job Matcher Streamlit app
├── app3_interview.py          # Interview Simulation Streamlit app
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (create from .env.template)
├── .env.template             # Environment variables template
├── chroma_db/                # ChromaDB storage (auto-created)
├── utils/
│   ├── cv_parser.py          # CV parsing utilities
│   ├── database.py           # ChromaDB interface
│   └── email_sender.py       # Email sending utilities
├── templates/
│   └── index.html            # Main landing page
└── static/                   # CSS, JS, Images for HTML interface
```

## 🔧 Troubleshooting

### Issue: "Tesseract not found"
**Solution**: Install Tesseract OCR and ensure it's in your system PATH

### Issue: "Email authentication failed"
**Solution**: 
- Make sure you're using Gmail App Password, not regular password
- Enable 2-Factor Authentication first
- Generate new app password if needed

### Issue: "ChromaDB error"
**Solution**: Delete `chroma_db` folder and restart applications

### Issue: "API rate limit exceeded"
**Solution**: 
- Anthropic free tier has limits
- Wait a few minutes or upgrade to paid tier
- Check your API usage at https://console.anthropic.com/

## 📊 API Usage & Costs

- **Anthropic Claude API**: Free tier includes $5 credit
- **ChromaDB**: Completely free, runs locally
- **Gmail SMTP**: Free for reasonable usage

## 🔐 Security Notes

- Never commit `.env` file to version control
- Keep API keys secure
- Gmail app passwords are safer than regular passwords
- ChromaDB stores data locally by default

## 🚀 Future Enhancements

- [ ] Video interview with AI assessment (currently text-only)
- [ ] Resume templates and formatting
- [ ] Multi-language support
- [ ] Calendar integration for interview scheduling
- [ ] Advanced analytics dashboard
- [ ] Export reports to PDF

## 💡 Tips for Best Results

1. **CV Parsing**: Provide clear, well-formatted CVs for better extraction
2. **Job Matching**: Be specific in job descriptions for accurate matching
3. **Interviews**: Answer thoughtfully with specific examples
4. **Email**: Test with your own email first before sending to candidates

## 📝 License

This project is for educational and internal use.

## 🤝 Support

For issues or questions:
1. Check the Troubleshooting section
2. Review Anthropic API documentation: https://docs.anthropic.com/
3. Check ChromaDB docs: https://docs.trychroma.com/

---

**Built with ❤️ using Claude AI, Streamlit, and ChromaDB**