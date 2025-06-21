# TeamPrompt 🧠

**AI-Powered Document Chat for Teams**

TeamPrompt lets you upload documents and chat with them using AI. Built for startups and SMBs who need intelligent document search and Q&A.

## Features

- **Multi-format support**: PDF, DOCX, TXT, CSV, HTML, Markdown
- **Vector search**: Fast semantic search with embeddings
- **AI chat**: Get contextual answers from your documents
- **Source attribution**: See which documents inform each answer
- **Real-time processing**: Instant upload and chat responses

## Tech Stack

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS
- **Backend**: FastAPI, Sentence Transformers, Pinecone, OpenRouter
- **Processing**: PyMuPDF, python-docx

## Quick Start

### Prerequisites

- Node.js 18+, Python 3.8+
- Pinecone account + API key
- OpenRouter account + API key

### Setup

```bash
# Clone repo
git clone <your-repo-url>
cd teamprompt

# Backend setup
cd backend
pip install -r requirements.txt
cp .env.example .env
# Add your API keys to .env
python main.py

# Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000`

### Environment Variables

Create `backend/.env`:
```env
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=teamprompt-index
OPENROUTER_API_KEY=your_openrouter_api_key
```

## Usage

1. **Upload** documents via drag & drop
2. **Chat** with your documents in natural language
3. **Get answers** with source citations

## API Endpoints

- `POST /upload-document` - Upload and process files
- `POST /query` - Search documents
- `POST /chat` - AI-powered Q&A
- `GET /health` - System status

## Contributing

1. Fork the repo
2. Create feature branch: `git checkout -b feature/name`
3. Commit changes: `git commit -m 'Add feature'`
4. Push and open PR

## License

MIT License - see [LICENSE](LICENSE) for details.

---

Built for growing teams who need smart document management.
