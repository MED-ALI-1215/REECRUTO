from flask import Flask, render_template, redirect
import os

app = Flask(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Port map
#   5000  → Flask  (this file — serves index.html landing page)
#   8501  → app1_cv_parser.py
#   8502  → app2_job_matcher.py
#   8503  → app3_interview.py   (candidate-facing, token-gated)
#   8504  → app4_dashboard.py   (recruiter dashboard — embedded as iframe)
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/app1_cv_parser')
def cv_parser():
    """Redirect to CV Parser Streamlit app"""
    return redirect('http://localhost:8501')


@app.route('/app2_job_matcher')
def job_matcher():
    """Redirect to Job Matcher Streamlit app"""
    return redirect('http://localhost:8502')


@app.route('/app3_interview')
def interview():
    """
    Candidate interview — NOT linked from index.html anymore.
    Candidates reach this directly via the token link in their email:
        http://localhost:8503/?token=<token>
    """
    return redirect('http://localhost:8503')


@app.route('/app4_dashboard')
def dashboard():
    """Recruiter Dashboard — also embedded as iframe in index.html"""
    return redirect('http://localhost:8504')


if __name__ == '__main__':
    app.run(debug=True, port=5000)