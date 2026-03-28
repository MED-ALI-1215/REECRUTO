#!/bin/bash

# RECRUTO - Quick Start Script
# This script runs all three Streamlit apps on different ports

echo "🚀 Starting RECRUTO Platform..."
echo "================================"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "Please create .env from .env.template and add your API keys"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

# Check if requirements are installed
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "📦 Installing requirements..."
    pip install -r requirements.txt
fi

echo ""
echo "Starting applications..."
echo "================================"

# Start CV Parser on port 8501
echo "📄 Starting CV Parser on port 8501..."
streamlit run app1_cv_parser.py --server.port 8501 &
CV_PARSER_PID=$!

# Wait a bit before starting next app
sleep 2

# Start Job Matcher on port 8502
echo "🎯 Starting Job Matcher on port 8502..."
streamlit run app2_job_matcher.py --server.port 8502 &
JOB_MATCHER_PID=$!

# Wait a bit before starting next app
sleep 2

# Start Interview Simulation on port 8503
echo "💬 Starting Interview Simulation on port 8503..."
streamlit run app3_interview.py --server.port 8503 &
INTERVIEW_PID=$!

echo ""
echo "================================"
echo "✅ All applications started!"
echo "================================"
echo ""
echo "Access the applications at:"
echo "  📄 CV Parser:            http://localhost:8501"
echo "  🎯 Job Matcher:          http://localhost:8502"
echo "  💬 Interview Simulation: http://localhost:8503"
echo ""
echo "Press Ctrl+C to stop all applications"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping all applications..."
    kill $CV_PARSER_PID 2>/dev/null
    kill $JOB_MATCHER_PID 2>/dev/null
    kill $INTERVIEW_PID 2>/dev/null
    echo "✅ All applications stopped"
    exit 0
}

# Set trap to cleanup on Ctrl+C
trap cleanup SIGINT SIGTERM

# Wait for processes
wait