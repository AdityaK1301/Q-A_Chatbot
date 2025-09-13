#  Smart Q/A Tool - Educational Assistant

A **Flask + Streamlit** web application that serves as an intelligent educational assistant for students. This tool allows students to ask questions about their syllabus and get AI-powered answers based on their curriculum materials.

---

##  Features

- **Class & Subject Selection:** Choose from available classes and subjects
- **PDF Syllabus Processing:** Automatically extracts and processes syllabus content from ZIP files
- **AI-Powered Q&A:** Uses Ollama with LangChain for intelligent question answering
- **Voice Input Support:** Speak your questions instead of typing
- **Context-Aware Answers:** Retrieves relevant context from syllabus materials before answering

---

##  Architecture

This application uses a two-part architecture:

- **Backend (Flask):** Handles PDF processing, text extraction, and AI model interactions
- **Frontend (Streamlit):** Provides a clean, interactive user interface

---

##  Installation

### Prerequisites

- Python 3.8+
- [Ollama](https://ollama.com) installed and running locally
- Microphone (for voice input feature)

### Setup

**Clone the repository:**
```bash
git clone <your-repo-url>
cd smart-qa-tool
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Set up your syllabus data:**

- Create a `datasets` folder in the project root
- Add ZIP files containing PDFs organised by class and subject

**Example structure:**
```
datasets/
├── class3_books/
│   ├── english_books.zip
│   ├── maths_books.zip
│   └── evs_books.zip
└── class4_books/
    ├── english_books.zip
    ├── maths_books.zip
    └── evs_books.zip
```

**Start Ollama service:**
```bash
ollama serve
```

**Make sure you have the required model:**
```bash
ollama pull gemma:2b-instruct
```

---

##  Usage

**Start the Flask backend:**
```bash
python app.py
```
The backend will run on [http://localhost:5000](http://localhost:5000)

**Start the Streamlit frontend (in a new terminal):**
```bash
streamlit run streamlit_app.py
```
The frontend will open in your browser at [http://localhost:8501](http://localhost:8501)

**Using the application:**
- Select your class and subject from the dropdown menus
- Click "Load Syllabus" to process the curriculum materials
- Type your question in the chat input or use the voice input button
- View the AI-generated answers based on your syllabus content

---

## 🛠️ Technology Stack

- **Backend Framework:** Flask
- **Frontend Framework:** Streamlit
- **AI Model:** Ollama with Gemma 2B Instruct
- **NLP Processing:** LangChain, Sentence Transformers
- **PDF Processing:** PyMuPDF
- **Voice Recognition:** SpeechRecognition
- **Embeddings:** HuggingFace Transformers

---

##  Project Structure

```
smart-qa-tool/
├── app.py                 # Flask backend API
├── streamlit_app.py       # Streamlit frontend
├── requirements.txt       # Python dependencies
├── datasets/              # Syllabus data (ZIP files with PDFs)
├── README.md              # This file
└── .gitignore             # Git ignore rules
```

---

##  Configuration

### Available Classes and Subjects

The application is currently valdated on:
- **Classes:** Class 3, Class 4
- **Subjects:** English, Maths, EVS

You can modify these in `app.py` by updating the `AVAILABLE_CLASSES` and `AVAILABLE_SUBJECTS` dictionaries.

### Model Configuration

The default AI model is `gemma:2b-instruct`. To use a different model:
- Update the `OLLAMA_MODEL` variable in `app.py`
- Make sure the model is available in your Ollama installation

---

##  How It Works

### Syllabus Loading
- User selects class and subject
- System loads corresponding ZIP file
- Extracts and processes all PDFs into text chunks

### Question Processing
- User asks a question (text or voice)
- System finds relevant context from syllabus materials
- Constructs a prompt with context and question

### Answer Generation
- Sends prompt to Ollama model
- Returns AI-generated answer to user
- Maintains conversation history

---

##  Troubleshooting

**Common Issues**

- **Ollama Connection Error:**
  - Ensure Ollama is running: `ollama serve`
  - Check if the model is downloaded: `ollama list`
- **Voice Input Not Working:**
  - Check microphone permissions in your browser
  - Ensure microphone is properly connected
  - Try using text input instead
- **PDF Processing Errors:**
  - Verify ZIP files contain valid PDFs
  - Check file paths in the datasets folder
- **Module Import Errors:**
  - Install missing dependencies: `pip install -r requirements.txt`

**Debug Mode**

For detailed debugging, run the Flask app with debug enabled:
```bash
python app.py
```
Check the terminal output for processing details and error messages.

---

##  API Endpoints

The Flask backend provides these API endpoints:

- `GET /api/classes` &mdash; List available classes
- `GET /api/subjects` &mdash; List available subjects
- `POST /api/select` &mdash; Load syllabus for selected class/subject
- `POST /api/ask` &mdash; Ask a question and get an answer

---

##  Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

##  Acknowledgments

- Ollama team for the easy-to-use local LLM framework
- LangChain team for the NLP orchestration framework
- Streamlit team for the intuitive web app framework
- HuggingFace for the sentence transformer models

> **Note:**  
> This application requires Ollama to be installed and running locally with the appropriate model. For best performance, ensure you have sufficient system resources (RAM and CPU) for the AI model operations.
```
