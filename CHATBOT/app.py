from flask import Flask, request, jsonify
from flask_cors import CORS
import zipfile
import os
import fitz
import requests
import re
import time
import speech_recognition as sr
try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    util = None
    SentenceTransformer = None
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.llms import Ollama
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.prompts import PromptTemplate

app = Flask(__name__)
CORS(app)  

current_class = None
current_subject = None
pdf_chunks = {}  
all_documents = []  
chunk_embeddings = None
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma:2b-instruct"

AVAILABLE_CLASSES = {
    "Class 3": "class3_books",
    "Class 4": "class4_books"
}

AVAILABLE_SUBJECTS = {
    "English": "english",
    "Maths": "maths", 
    "EVS": "evs"
}

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    length_function=len,
)

llm = Ollama(
    base_url="http://localhost:11434",
    model=OLLAMA_MODEL,
    temperature=0.1,
    top_p=0.8,
    repeat_penalty=1.1
)

# Helper functions
def extract_text_from_pdf(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = []
    for page in doc:
        text.append(page.get_text())
    return "\n".join(text)

def clean_text(text):
    text = re.sub(r"[^a-zA-Z0-9\s\.\,\;\:\?\!\-]", " ", text)  
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def load_syllabus_data(class_folder, subject_filter=None):  
    global pdf_chunks, all_documents
    
    pdf_chunks = {}
    all_documents = []
    books_path = os.path.join("datasets", class_folder)
    
    if not os.path.exists(books_path):
        print(f"Path does not exist: {books_path}")
        return False
    
    print(f"Loading data from: {books_path}")
    
    for zip_file in os.listdir(books_path):
        if zip_file.endswith(".zip"):
            if subject_filter:
                subject_key = subject_filter.lower()
                zip_subject = zip_file.lower()
                if subject_key not in zip_subject:
                    continue
            
            zip_path = os.path.join(books_path, zip_file)
            print(f"Processing: {zip_file}")
            
            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    for pdf_name in zf.namelist():
                        if pdf_name.endswith(".pdf"):
                            with zf.open(pdf_name) as pdf_file:
                                pdf_bytes = pdf_file.read()
                                text = extract_text_from_pdf(pdf_bytes)  
                                text = clean_text(text)  
                                
                                documents = text_splitter.split_text(text)
                                for i, doc_text in enumerate(documents):
                                    metadata = {"source": pdf_name, "chunk": i}
                                    all_documents.append(Document(page_content=doc_text, metadata=metadata))
                                
                                pdf_chunks[pdf_name] = documents
                print(f" Processed {zip_file}")
            except Exception as e:
                print(f" Error processing {zip_file}: {e}")
    
    print(f"Total PDFs loaded: {len(pdf_chunks)}")
    print(f"Total chunks collected: {len(all_documents)}")
    
    if all_documents:
        print("Data loaded successfully for LangChain processing!")
        return True
    else:
        print(" No syllabus content found.")
        return False

def retrieve_context(query, k=3):
    if not all_documents:
        return "No context available", None
    
    document_texts = [doc.page_content for doc in all_documents]
    
    query_embedding = embedding_model.embed_query(query)
    document_embeddings = embedding_model.embed_documents(document_texts)
    
    if util:
        similarities = util.pytorch_cos_sim([query_embedding], document_embeddings)[0]
        top_k_indices = similarities.topk(k).indices.tolist()
    else:
        from numpy import dot
        from numpy.linalg import norm
        similarities = []
        for doc_embedding in document_embeddings:
            cos_sim = dot(query_embedding, doc_embedding) / (norm(query_embedding) * norm(doc_embedding))
            similarities.append(cos_sim)
        
        import numpy as np
        top_k_indices = np.argsort(similarities)[-k:][::-1].tolist()
    
    pdf_names = set()
    top_chunks = []
    for idx in top_k_indices:
        chunk_text = all_documents[idx].page_content
        top_chunks.append(chunk_text)
        pdf_names.add(all_documents[idx].metadata["source"])
    
    return "\n".join(top_chunks), list(pdf_names)

def query_ollama(prompt, max_tokens=500):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": max_tokens,
            "top_p": 0.8,
            "repeat_penalty": 1.1
        }
    }
    
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["response"]
    except requests.exceptions.RequestException:
        return "I'm having trouble connecting to the knowledge base right now."

def answer_general_question(query):
    """Answer general questions using the entire syllabus"""
    context, _ = retrieve_context(query, k=5)
    
    prompt_template = PromptTemplate(
        input_variables=["context", "question"],
        template="""You are a helpful teacher for students. Answer the question based on the provided context.
        Use the information from the context. Keep your answer concise and in simple words suitable for students.
        
        Context: {context}
        
        Question: {question}
        
        Answer:"""
    )
    
    prompt = prompt_template.format(context=context, question=query)
    return query_ollama(prompt)

def answer_summarize_question(query, pdf_name=None):
    """Answer summarize/generate questions with more comprehensive approach"""
    if pdf_name:
        if pdf_name not in pdf_chunks:
            return f"PDF '{pdf_name}' not found in the loaded syllabus."
        
        content = " ".join(pdf_chunks[pdf_name])
    else:
        context, pdf_names = retrieve_context(query, k=10)
        content = context
    
    prompt_template = PromptTemplate(
        input_variables=["content", "question"],
        template="""You are an expert teacher. Analyze the provided content and create a comprehensive response.
        For summary requests, provide a well-structured summary.
        For generation requests, create the requested content based on the material.
        
        Content: {content}
        
        Request: {question}
        
        Comprehensive response:"""
    )
    
    prompt = prompt_template.format(content=content[:6000], question=query)
    return query_ollama(prompt, max_tokens=1000)

def hybrid_answer_question(query):
    """Determine the type of question and use appropriate method"""
    query_lower = query.lower()
    
    summary_keywords = ['summarize', 'summary', 'overview', 'brief', 'recap']
    generate_keywords = ['generate', 'create', 'make', 'write', 'compose', 'develop']
    specific_keywords = ['chapter', 'lesson', 'unit', 'section']
    
    is_summary = any(kw in query_lower for kw in summary_keywords)
    is_generate = any(kw in query_lower for kw in generate_keywords)
    is_specific = any(kw in query_lower for kw in specific_keywords)
    has_pdf = re.search(r'\.pdf', query_lower)
    
    if is_summary or is_generate or is_specific:
        pdf_match = re.search(r'(\w+\.pdf)', query, re.IGNORECASE)
        pdf_name = pdf_match.group(1) if pdf_match else None
        return answer_summarize_question(query, pdf_name)
    
    return answer_general_question(query)

def get_voice_input():
    recognizer = sr.Recognizer()
    
    print("Available microphones:")
    for index, name in enumerate(sr.Microphone.list_microphone_names()):
        print(f"Microphone {index}: {name}")
    
    try:
        with sr.Microphone() as source:
            print("Adjusting for ambient noise...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            print("Listening... Please speak your question now")
            
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=5)
            print("Processing your speech...")
            
            try:
                query = recognizer.recognize_google(audio)
                print(f"Google recognition: {query}")
                return query
            except sr.UnknownValueError:
                try:
                    query = recognizer.recognize_sphinx(audio)
                    print(f"Sphinx recognition: {query}")
                    return query
                except sr.UnknownValueError:
                    return "Sorry, I couldn't understand what you said. Please try again."
            except sr.RequestError as e:
                return f"Speech recognition service error: {e}"
                
    except sr.WaitTimeoutError:
        return "No speech detected. Please try again and speak clearly into your microphone."
    except OSError as e:
        return f"Microphone error: {e}. Please check your microphone connection."
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/api/classes', methods=['GET'])
def get_classes():
    return jsonify(list(AVAILABLE_CLASSES.keys()))

@app.route('/api/subjects', methods=['GET'])
def get_subjects():
    return jsonify(list(AVAILABLE_SUBJECTS.keys()))

@app.route('/api/select', methods=['POST'])
def select_class_subject():
    global current_class, current_subject
    
    data = request.get_json()
    selected_class = data.get('class')
    selected_subject = data.get('subject')
    
    if not selected_class or not selected_subject:
        return jsonify({"status": "error", "message": "Please select both class and subject."})
    
    current_class = selected_class
    current_subject = selected_subject
    
    class_folder = AVAILABLE_CLASSES[selected_class]
    success = load_syllabus_data(class_folder, selected_subject)
    
    if success:
        return jsonify({"status": "success", "message": f"Ready! Selected: {selected_class} - {selected_subject}"})
    else:
        return jsonify({"status": "error", "message": f"No data found for {selected_class} - {selected_subject}"})

@app.route('/api/ask', methods=['POST'])
def ask_question():
    data = request.get_json()
    question = data.get('question')
    use_voice = data.get('use_voice', False)
    
    if use_voice:
        question = get_voice_input()
        if not question or any(x in question.lower() for x in ["error", "sorry", "detected", "couldn't understand"]):
            return jsonify({"answer": question, "is_voice_error": True})
    
    if not all_documents:
        return jsonify({"answer": "Please select a class and subject first."})
    
    answer = hybrid_answer_question(question)
    return jsonify({"answer": answer})

if __name__ == '__main__':
    app.run(debug=True, port=5000)