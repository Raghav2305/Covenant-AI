# Contract AI Copilot - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git

### 1. Clone and Setup
```bash
# Clone the repository
git clone <your-repo-url>
cd contract-ai-copilot

# Run the setup script
python setup.py
```

### 2. Configure Environment
```bash
# Copy environment template
cp env.example .env

# Edit .env with your settings
# At minimum, set:
# - OPENAI_API_KEY=your_openai_key
# - SECRET_KEY=your_secret_key
```

### 3. Start Development Environment

#### Option A: Docker (Recommended)
```bash
# Start all services with Docker
docker-compose -f docker-compose.dev.yml up -d

# Check services are running
docker-compose ps
```

#### Option B: Manual Start
```bash
# Terminal 1: Start backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Terminal 2: Start frontend
cd frontend
npm install
npm start

# Terminal 3: Start MCP server
cd backend
python -m app.mcp.database_server
```

### 4. Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MCP Server**: http://localhost:3001

## 🎯 Demo Scenarios

### Scenario 1: Contract Upload & Processing
1. Go to http://localhost:3000
2. Upload a sample contract PDF
3. Watch the AI extract obligations automatically
4. View the structured obligation data

### Scenario 2: Obligation Monitoring
1. Navigate to the monitoring dashboard
2. See real-time obligation status
3. Check deadline alerts
4. View compliance metrics

### Scenario 3: AI Copilot Query
1. Open the copilot interface
2. Ask: "Show me all obligations due next month"
3. Get natural language responses with citations
4. Explore contract insights

## 🔧 Development Commands

### Backend Development
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run with hot reload
uvicorn app.main:app --reload

# Start MCP server
python -m app.mcp.database_server
```

### Frontend Development
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start

# Run tests
npm test

# Build for production
npm run build
```

### Database Operations
```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Reset database
alembic downgrade base
alembic upgrade head
```

## 🐛 Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Find process using port
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows
```

#### Docker Issues
```bash
# Clean up Docker
docker-compose down
docker system prune -f
docker-compose -f docker-compose.dev.yml up -d
```

#### Python Environment Issues
```bash
# Recreate virtual environment
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

#### Node.js Issues
```bash
# Clear npm cache
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### Environment Variables
Make sure these are set in your `.env` file:
- `OPENAI_API_KEY` - Required for AI processing
- `DATABASE_URL` - Database connection string
- `SECRET_KEY` - Application secret key
- `MCP_SERVER_URL` - MCP server endpoint

## 📊 Monitoring & Logs

### Application Logs
```bash
# View backend logs
docker-compose logs -f backend

# View frontend logs
docker-compose logs -f frontend

# View all logs
docker-compose logs -f
```

### Health Checks
- Backend: http://localhost:8000/health
- MCP Server: http://localhost:3001/schema
- Frontend: http://localhost:3000

## 🚀 Next Steps

1. **Explore the Code**: Check out the project structure
2. **Read Documentation**: Review `DEVELOPMENT_PLAN.md`
3. **Run Tests**: Ensure everything works
4. **Customize**: Modify for your specific needs
5. **Deploy**: Follow deployment guide in docs/

## 📚 Additional Resources

- [Development Plan](DEVELOPMENT_PLAN.md) - Detailed technical plan
- [API Documentation](http://localhost:8000/docs) - Interactive API docs
- [Architecture Guide](docs/architecture/) - System design details
- [User Guide](docs/user_guide/) - End-user documentation

## 🆘 Getting Help

- Check the logs for error messages
- Review the troubleshooting section above
- Create an issue in the repository
- Check the documentation in `/docs`

---

**Happy coding! 🎉**
