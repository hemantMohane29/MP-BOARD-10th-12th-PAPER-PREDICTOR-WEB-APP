# MP Board Exam Pattern Intelligence System (Hindi Medium Edition)

A premium, AI-powered system to analyze MP Board question papers, predict important topics, and generate study strategies.

## ✨ Features
- **Premium Design**: Dark-themed, animated glassmorphism UI.
- **Bilingual Support**: Fully functional in both English and Hindi.
- **Deep Learning Analysis**: Uses Gemini AI to predict 20-50 questions based on the number of PDFs uploaded.
- **Hindi OCR**: Advanced extraction for Hindi medium papers.
- **Auth System**: Secure Login and Signup for students.

## 🚀 Quick Start

### 1. Setup Environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. API Keys
Ensure your `.env` file has the following:
- `GEMINI_API_KEY`: Your Google AI Studio key.
- `SARVAM_API_KEY`: Your Sarvam AI key (for advanced OCR).

### 4. Run the Project
```bash
python manage.py migrate
python manage.py runserver
```

## 📂 Project Structure
- `analyzer/`: Backend logic and AI pipeline.
- `templates/`: Premium HTML designs by Friend & AI.
- `static/`: Custom CSS/JS for animations.
- `media/`: Storage for uploaded PDFs.
