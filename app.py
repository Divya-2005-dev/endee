from flask import Flask, request, jsonify, render_template, send_file, Response
from werkzeug.utils import secure_filename
import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import modules
from modules.data_processing import load_pdf, split_text_into_chunks, extract_metadata
from modules.embedding import get_embeddings, EmbeddingModel
from modules.endee_integration import EndeeClient
from modules.query_handling import process_query, QueryProcessor
from modules.rag_pipeline import generate_answer, RAGPipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize components
endee_client = EndeeClient(mock=os.getenv('ENDEE_MOCK', 'true').lower() == 'true')
embedding_model = EmbeddingModel()
query_processor = QueryProcessor(embedding_model)
rag_pipeline = RAGPipeline()

collection_name = "documents"
vector_dim = 384  # For all-MiniLM-L6-v2

# Global registries
uploaded_documents = []
chat_sessions = {}
user_preferences = {}

# Create collection if not exists
try:
    endee_client.create_collection(collection_name, vector_dim)
    logger.info("Vector collection created successfully")
except Exception as e:
    logger.warning(f"Collection creation failed: {e}")

# Create collection if not exists
try:
    endee_client.create_collection(collection_name, vector_dim)
except:
    pass

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/health')
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/api/stats')
def get_stats():
    total_docs = len(uploaded_documents)
    total_chunks = sum(doc.get('chunks', 0) for doc in uploaded_documents)
    return jsonify({
        "total_documents": total_docs,
        "total_chunks": total_chunks,
        "collection_name": collection_name,
        "vector_dimension": vector_dim
    })

@app.route('/upload', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")

        try:
            file.save(file_path)
            logger.info(f"File saved: {file_path}")

            # Process file with enhanced processing
            text = load_pdf(file_path)
            if not text.strip():
                os.remove(file_path)
                return jsonify({"error": "No readable text found in file"}), 400

            chunks = split_text_into_chunks(text)
            metadata = extract_metadata(file_path, filename)

            # Get embeddings
            embeddings = get_embeddings(chunks)

            # Prepare payloads with enhanced metadata
            payloads = [{
                "text": chunk,
                "source": filename,
                "file_id": file_id,
                "page": i // 10 + 1,
                "chunk_id": f"{file_id}_{i}",
                "metadata": metadata,
                "timestamp": datetime.now().isoformat()
            } for i, chunk in enumerate(chunks)]

            # Store in Endee
            endee_client.insert_vectors(collection_name, embeddings, payloads)

            # Add to document registry
            doc_info = {
                'id': file_id,
                'filename': filename,
                'path': file_path,
                'uploaded_at': datetime.now().isoformat(),
                'chunks': len(chunks),
                'size': os.path.getsize(file_path),
                'metadata': metadata
            }
            uploaded_documents.append(doc_info)

            logger.info(f"Document processed: {filename} ({len(chunks)} chunks)")
            return jsonify({
                "message": "File uploaded and processed successfully",
                "document_id": file_id,
                "chunks": len(chunks),
                "metadata": metadata
            }), 200

        except Exception as e:
            logger.error(f"Upload error: {e}")
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({"error": f"Processing failed: {str(e)}"}), 500
    else:
        return jsonify({"error": "Invalid file type. Supported: PDF, TXT, DOCX, MD"}), 400

def allowed_file(filename):
    allowed_extensions = {'pdf', 'txt', 'docx', 'md', 'html'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.json
    question = data.get('question', '').strip()
    session_id = data.get('session_id', str(uuid.uuid4()))
    stream = data.get('stream', False)

    if not question:
        return jsonify({"error": "No question provided"}), 400

    try:
        # Initialize or get session
        if session_id not in chat_sessions:
            chat_sessions[session_id] = {
                'messages': [],
                'created_at': datetime.now().isoformat()
            }

        # Add user message to session
        chat_sessions[session_id]['messages'].append({
            'role': 'user',
            'content': question,
            'timestamp': datetime.now().isoformat()
        })

        # Process query with enhanced processing
        query_embedding = query_processor.process(question)

        # Search with filters
        filters = data.get('filters', {})
        results = endee_client.search(
            collection_name,
            query_embedding,
            limit=5,
            filters=filters
        )

        if not results:
            response = {
                "answer": "No relevant information found in the uploaded documents.",
                "sources": [],
                "confidence": 0,
                "session_id": session_id
            }
        else:
            # Combine context
            context = " ".join([res['payload']['text'] for res in results])

            # Calculate confidence metrics
            confidence = sum(res.get('score', 0) for res in results) / len(results) if results else 0

            # Generate answer with RAG
            answer = rag_pipeline.generate(context, question, chat_sessions[session_id]['messages'])

            # Sources with enhanced info
            sources = [{
                "source": res['payload']['source'],
                "file_id": res['payload'].get('file_id'),
                "page": res['payload']['page'],
                "confidence": res.get('score', 0),
                "chunk_id": res['payload'].get('chunk_id'),
                "text_preview": res['payload']['text'][:100] + "..."
            } for res in results]

            response = {
                "answer": answer,
                "sources": sources,
                "confidence": confidence,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }

        # Add assistant response to session
        chat_sessions[session_id]['messages'].append({
            'role': 'assistant',
            'content': response['answer'],
            'sources': response['sources'],
            'timestamp': response['timestamp']
        })

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Query error: {e}")
        return jsonify({"error": f"Query processing failed: {str(e)}"}), 500

@app.route('/ask/stream', methods=['POST'])
def ask_question_stream():
    data = request.json
    question = data.get('question', '').strip()
    session_id = data.get('session_id', str(uuid.uuid4()))

    if not question:
        return jsonify({"error": "No question provided"}), 400

    def generate():
        try:
            # Similar processing as above
            query_embedding = query_processor.process(question)
            results = endee_client.search(collection_name, query_embedding, limit=5)

            if results:
                context = " ".join([res['payload']['text'] for res in results])
                # Stream the answer generation
                for chunk in rag_pipeline.generate_stream(context, question):
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                yield f"data: {json.dumps({'done': True})}\n\n"
            else:
                yield f"data: {json.dumps({'chunk': 'No relevant information found.'})}\n\n"
                yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype='text/event-stream')

@app.route('/documents', methods=['GET'])
def get_documents():
    return jsonify({"documents": uploaded_documents}), 200

@app.route('/documents/<doc_id>', methods=['GET'])
def get_document(doc_id):
    doc = next((d for d in uploaded_documents if d['id'] == doc_id), None)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    return jsonify(doc), 200

@app.route('/documents/<doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    global uploaded_documents
    doc = next((d for d in uploaded_documents if d['id'] == doc_id), None)

    if not doc:
        return jsonify({"error": "Document not found"}), 404

    try:
        # Remove file
        if os.path.exists(doc['path']):
            os.remove(doc['path'])

        # Remove from registry
        uploaded_documents = [d for d in uploaded_documents if d['id'] != doc_id]

        # Note: In production, would need to delete vectors from Endee
        logger.info(f"Document deleted: {doc['filename']}")
        return jsonify({"message": "Document deleted successfully"}), 200

    except Exception as e:
        logger.error(f"Delete error: {e}")
        return jsonify({"error": f"Delete failed: {str(e)}"}), 500

@app.route('/sessions', methods=['GET'])
def get_sessions():
    return jsonify({
        "sessions": [
            {
                "id": sid,
                "message_count": len(session['messages']),
                "created_at": session['created_at'],
                "last_message": session['messages'][-1]['timestamp'] if session['messages'] else None
            }
            for sid, session in chat_sessions.items()
        ]
    }), 200

@app.route('/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    if session_id not in chat_sessions:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(chat_sessions[session_id]), 200

@app.route('/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    if session_id not in chat_sessions:
        return jsonify({"error": "Session not found"}), 404
    del chat_sessions[session_id]
    return jsonify({"message": "Session deleted"}), 200

@app.route('/export/chat/<session_id>', methods=['GET'])
def export_chat(session_id):
    if session_id not in chat_sessions:
        return jsonify({"error": "Session not found"}), 404

    session = chat_sessions[session_id]
    export_data = {
        "session_id": session_id,
        "exported_at": datetime.now().isoformat(),
        "messages": session['messages']
    }

    # Create export file
    filename = f"chat_export_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    export_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    with open(export_path, 'w') as f:
        json.dump(export_data, f, indent=2)

    return send_file(export_path, as_attachment=True, download_name=filename)

@app.route('/analytics', methods=['GET'])
def get_analytics():
    total_queries = sum(len(session['messages']) // 2 for session in chat_sessions.values())
    total_sessions = len(chat_sessions)
    avg_session_length = total_queries / total_sessions if total_sessions > 0 else 0

    return jsonify({
        "total_documents": len(uploaded_documents),
        "total_sessions": total_sessions,
        "total_queries": total_queries,
        "average_session_length": avg_session_length,
        "documents_by_type": {},
        "queries_over_time": []
    }), 200

if __name__ == '__main__':
    app.run(debug=True)

if __name__ == '__main__':
    app.run(debug=True)