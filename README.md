# Smart Assistant

A modern, full-stack AI-powered assistant application for job searching, news aggregation, and intelligent conversation management.

![Smart Assistant Interface](./screenshot.png)

## 🚀 Features

- **Modern Chat Interface**: Beautiful gradient-based UI with glassmorphism effects
- **Job Search Automation**: Automated job scraping and analysis with AI-powered matching
- **Document RAG**: Upload and analyze documents with AI-powered question answering
- **News Aggregation**: Daily digest of relevant news and industry updates
- **Conversation Memory**: Persistent chat history and conversation management
- **Airtable Integration**: Seamless job database management

## 🛠️ Tech Stack

### Frontend
- **React 18** with modern hooks and functional components
- **Tailwind CSS** for responsive, utility-first styling
- **Lucide React** for beautiful, consistent icons
- **Axios** for API communication
- **Vite** for fast development and building

### Backend
- **FastAPI** for high-performance async API endpoints
- **ChromaDB** for vector storage and document similarity search
- **OpenAI GPT** for intelligent conversation and analysis
- **Beautiful Soup** for web scraping
- **Airtable API** for job database management
- **Python 3.9+** with async/await patterns

## 📦 Installation

### Prerequisites
- Node.js 16+ and npm
- Python 3.9+
- OpenAI API key
- Airtable API credentials (optional)

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy environment template and configure
cp .env.template .env
# Edit .env with your API keys
```

### Frontend Setup
```bash
cd frontend
npm install
```

## 🔧 Configuration

Create a `.env` file in the backend directory:

```env
OPENAI_API_KEY=your_openai_api_key
AIRTABLE_API_KEY=your_airtable_api_key
AIRTABLE_BASE_ID=your_airtable_base_id
AIRTABLE_TABLE_NAME=your_table_name
```

## 🚀 Running the Application

### Start Backend Server
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Start Frontend Development Server
```bash
cd frontend
npm run dev
```

Visit `http://localhost:5173` to access the application.

## 📚 API Endpoints

### Chat
- `POST /api/chat` - Send message to AI assistant
- `POST /api/ingest-conversation` - Save conversation to memory

### Job Management
- `POST /api/scrape-jobs` - Scrape jobs from job boards
- `GET /api/jobs` - Retrieve stored jobs
- `POST /api/analyze-jobs` - AI analysis of job matches

### Document Management
- `POST /api/ingest-document` - Upload and process documents
- `POST /api/query-documents` - Query documents with RAG

## 🎨 UI Components

### Modern Design Features
- **Gradient Backgrounds**: Indigo to purple color schemes
- **Glassmorphism**: Semi-transparent elements with backdrop blur
- **Collapsible Sidebar**: Responsive navigation with expandable sections
- **Modern Action Bar**: Gradient pill buttons with hover animations
- **Smart Chat Input**: Context-aware input with suggestion pills
- **Beautiful Messages**: Styled chat bubbles with proper spacing

### Component Architecture
- `Sidebar.jsx` - Collapsible navigation with daily digest
- `ActionBar.jsx` - Top action buttons for key features
- `ChatInput.jsx` - Modern input with file upload and voice
- `ChatMessage.jsx` - Styled message components for chat

## 🔄 Deployment

### Production Build
```bash
# Frontend
cd frontend
npm run build

# Backend (using gunicorn)
cd backend
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Environment Variables for Production
- Set `NODE_ENV=production`
- Configure CORS settings for your domain
- Use environment-specific API endpoints

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI for GPT API
- The React and FastAPI communities
- Tailwind CSS for the amazing utility framework
- Lucide React for beautiful icons

## 📞 Support

If you have any questions or need help with setup, please open an issue or contact [your-email@example.com](mailto:your-email@example.com).

---

**Built with ❤️ using React, FastAPI, and modern web technologies**
