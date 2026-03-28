"""
RECRUTO Setup Verification Script
This script checks if all dependencies and configurations are properly set up.
"""

import sys
import os

def check_python_version():
    """Check if Python version is 3.8 or higher"""
    print("Checking Python version...", end=" ")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} (Need 3.8+)")
        return False

def check_dependencies():
    """Check if all required Python packages are installed"""
    print("\nChecking Python dependencies:")
    
    required_packages = [
        'streamlit',
        'flask',
        'docx',
        'PyPDF2',
        'pdfplumber',
        'pytesseract',
        'PIL',
        'chromadb',
        'anthropic',
        'dotenv',
        'pandas'
    ]
    
    all_installed = True
    
    for package in required_packages:
        try:
            if package == 'docx':
                __import__('docx')
            elif package == 'PIL':
                __import__('PIL')
            elif package == 'dotenv':
                __import__('dotenv')
            else:
                __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} - Not installed")
            all_installed = False
    
    return all_installed

def check_tesseract():
    """Check if Tesseract OCR is installed"""
    print("\nChecking Tesseract OCR...", end=" ")
    try:
        import pytesseract
        
        # SET PATH HERE
        pytesseract.pytesseract.tesseract_cmd = r"C:\Tesseract OCR\tesseract.exe"
        
        pytesseract.get_tesseract_version()
        print("✅ Tesseract installed")
        return True
        
    except Exception as e:
        print("❌ Tesseract not found or not in PATH")
        print(f"   Error: {str(e)}")
        return False


def check_env_file():
    """Check if .env file exists and has required variables"""
    print("\nChecking .env configuration...", end=" ")
    
    if not os.path.exists('.env'):
        print("❌ .env file not found")
        print("   Please copy .env.template to .env and fill in your credentials")
        return False
    
    # Load and check variables
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ['ANTHROPIC_API_KEY', 'EMAIL_ADDRESS']
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value or value == f"your_{var.lower()}_here" or "xxxxx" in value:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  Missing or incomplete: {', '.join(missing_vars)}")
        return False
    else:
        print("✅ Configuration looks good")
        return True

def check_directories():
    """Check if required directories exist"""
    print("\nChecking directories...")
    
    dirs = ['utils', 'templates', 'static']
    all_exist = True
    
    for directory in dirs:
        if os.path.exists(directory):
            print(f"  ✅ {directory}/")
        else:
            print(f"  ❌ {directory}/ - Not found")
            all_exist = False
    
    return all_exist

def check_files():
    """Check if all required Python files exist"""
    print("\nChecking application files...")
    
    files = [
        'app1_cv_parser.py',
        'app2_job_matcher.py',
        'app3_interview.py',
        'utils/cv_parser.py',
        'utils/database.py',
        'utils/email_sender.py'
    ]
    
    all_exist = True
    
    for file in files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - Not found")
            all_exist = False
    
    return all_exist

def main():
    print("=" * 60)
    print("  RECRUTO Setup Verification")
    print("=" * 60)
    
    results = {
        'Python Version': check_python_version(),
        'Dependencies': check_dependencies(),
        'Tesseract OCR': check_tesseract(),
        'Environment Config': check_env_file(),
        'Directories': check_directories(),
        'Application Files': check_files()
    }
    
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{check:.<40} {status}")
    
    all_passed = all(results.values())
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 All checks passed! You're ready to run RECRUTO!")
        print("\nTo start the platform, run:")
        print("  Linux/Mac:  ./start.sh")
        print("  Windows:    start.bat")
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  - Install missing packages: pip install -r requirements.txt")
        print("  - Install Tesseract: See README.md for instructions")
        print("  - Create .env file: cp .env.template .env")
        print("  - Add your API keys to .env file")
    
    print()

if __name__ == "__main__":
    main()