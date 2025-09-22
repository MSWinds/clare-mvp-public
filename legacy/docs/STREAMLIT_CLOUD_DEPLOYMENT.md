# Streamlit Cloud Deployment Plan

## Pre-Deployment Checklist

### ✅ Current Status
- [x] Code refactored to modular architecture
- [x] Database migrated to Supabase (cloud-hosted)
- [x] SSL connections working
- [x] Local testing successful
- [x] Environment variables configured
- [x] Dependencies updated (Streamlit 1.49.1+)

### 🎯 Deployment Goals
- Deploy Clare-AI as public URL for professor access
- Maintain all functionality (chat, profiles, vector search)
- Ensure reliable performance within free tier limits

## Step 1: Repository Preparation

### GitHub Repository Setup
```bash
# Ensure all changes are committed and pushed
git add .
git commit -m "Prepare for Streamlit Cloud deployment"
git push origin yuri-branch-test

# Create main branch deployment (recommended)
git checkout main
git merge yuri-branch-test
git push origin main
```

### Repository Structure Verification
```
repo/
├── main.py                 # Entry point for Streamlit Cloud
├── requirements-Win.txt    # Dependencies (will be used by Streamlit Cloud)
├── .gitignore             # Excludes .env and sensitive files
├── src/                   # Modular codebase
│   ├── auth/
│   ├── database/
│   ├── prompts/
│   └── workflows/
└── legacy/                # Legacy files (won't affect deployment)
```

## Step 2: Streamlit Cloud Configuration

### Account Setup
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect GitHub account
3. Authorize Streamlit to access your repository

### App Deployment Settings
```yaml
# Streamlit Cloud will auto-detect these settings:
Repository: demo-repository
Branch: main (recommended) or yuri-branch-test
Main file path: main.py
Python version: 3.11 (latest supported)
```

## Step 3: Environment Variables Configuration

### Required Environment Variables in Streamlit Cloud Dashboard
```bash
# Database Connection (Supabase)
DATABASE_URL=postgresql://postgres:[PASSWORD]@[HOST]/postgres

# API Keys
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
LANGSMITH_API_KEY=ls__...
LLAMA_CLOUD_API_KEY=llx_...

# Optional: LangSmith Project Configuration
LANGCHAIN_PROJECT=Clare-AI-Production
LANGCHAIN_TRACING_V2=true
```

### How to Set Environment Variables:
1. In Streamlit Cloud dashboard → App Settings
2. Navigate to "Secrets" section
3. Add variables in TOML format:
```toml
DATABASE_URL = "postgresql://postgres:..."
OPENAI_API_KEY = "sk-..."
TAVILY_API_KEY = "tvly-..."
LANGSMITH_API_KEY = "ls__..."
LLAMA_CLOUD_API_KEY = "llx_..."
```

## Step 4: Code Compatibility Verification

### Streamlit Cloud Compatibility ✅
Your current architecture is perfectly compatible:

```python
# main.py - Single entry point ✅
import streamlit as st
from src.auth.authentication import *
from src.workflows.agentic_workflow import get_workflow

# Async workflows work ✅
response = asyncio.run(workflow.ainvoke(inputs))

# Database connections work ✅
from src.database.config import get_database_engine
engine = get_database_engine()  # Uses DATABASE_URL
```

### Dependencies Compatibility ✅
```bash
# requirements-Win.txt will be used by Streamlit Cloud
# All dependencies are compatible:
streamlit==1.49.1          # ✅ Latest version
langchain==0.3.27          # ✅ Works on cloud
langgraph==0.6.7           # ✅ Works on cloud
psycopg==3.2.10           # ✅ PostgreSQL driver
sqlalchemy==2.0.38        # ✅ Database ORM
openai==1.108.1           # ✅ OpenAI API
```

## Step 5: Performance Considerations

### Streamlit Cloud Resource Limits
- **Memory**: 1GB RAM (should be sufficient for your use case)
- **CPU**: Shared vCPU (adequate for LangChain workflows)
- **Storage**: Ephemeral (database is external - Supabase)
- **Timeout**: 5 minutes per request (your workflows are fast enough)

### Optimization Strategies
```python
# Already implemented in your code:
1. External database (Supabase) ✅
2. Async workflows for efficiency ✅
3. Session state management ✅
4. Lazy database connections ✅
5. Error handling with fallbacks ✅
```

### Cold Start Mitigation
```python
# Add to main.py if needed:
@st.cache_resource
def initialize_workflow():
    """Cache workflow initialization to reduce cold starts"""
    return get_workflow()

# Use cached workflow
workflow = initialize_workflow()
```

## Step 6: Testing Strategy

### Pre-Deployment Testing
```bash
# Test locally with production environment variables
export DATABASE_URL="your_supabase_url"
streamlit run main.py

# Verify all functionality:
# 1. Sign-in flow works
# 2. Profile questionnaire submission
# 3. Chat responses with RAG
# 4. Database storage (chat_history, student_profiles)
# 5. Vector search functionality
```

### Post-Deployment Verification
1. **Authentication Flow**: Test sign-in → questionnaire → chat
2. **AI Responses**: Verify LangGraph workflow execution
3. **Database Operations**: Check profile storage and retrieval
4. **Vector Search**: Test RAG functionality
5. **Error Handling**: Verify graceful fallbacks

## Step 7: Deployment Execution

### Deploy to Streamlit Cloud
1. **Connect Repository**:
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Select your GitHub repository
   - Choose branch: `main`
   - Main file: `main.py`

2. **Configure Environment Variables**:
   - Add all required secrets in TOML format
   - Save configuration

3. **Deploy**:
   - Click "Deploy!"
   - Monitor deployment logs
   - Wait for app to be available

### Expected Deployment Time
- **Initial deployment**: 5-10 minutes
- **Subsequent updates**: 2-3 minutes
- **Cold starts**: 10-30 seconds

## Step 8: Post-Deployment Configuration

### Custom Domain (Optional)
- Streamlit provides: `https://your-app-name.streamlit.app`
- Custom domain available for teams plan

### Monitoring and Maintenance
```python
# Add usage analytics to main.py if desired:
def log_app_usage():
    """Optional: Log app usage for monitoring"""
    student_id = get_current_student_id()
    if student_id:
        print(f"App accessed by: {student_id} at {datetime.now()}")

# Add error reporting
def handle_deployment_errors(e):
    """Enhanced error handling for production"""
    st.error("⚠️ Something went wrong. Please try again.")
    print(f"Production error: {e}")  # Logs to Streamlit Cloud console
```

## Step 9: Sharing with Professor

### Access Information
```
Production URL: https://your-app-name.streamlit.app
Description: Clare-AI Teaching Assistant
Features:
- Student profile questionnaire
- Personalized AI tutoring
- RAG-powered document search
- Chat history persistence
```

### Demo Instructions for Professor
```markdown
# Clare-AI Demo Instructions

## Quick Start:
1. Visit the URL
2. Click "🔑 Sign In"
3. Fill out the student questionnaire
4. Start asking course-related questions

## Key Features to Test:
- Profile-based personalization
- Socratic questioning approach
- Document retrieval from course materials
- Chat history persistence
- Student learning analytics
```

## Troubleshooting Guide

### Common Issues and Solutions

**App Won't Start:**
```bash
# Check Streamlit Cloud logs for:
1. Missing environment variables
2. Import errors
3. Database connection issues
```

**Database Connection Errors:**
```python
# Verify in secrets:
DATABASE_URL = "postgresql://postgres:password@host:5432/postgres"

# Test connection in app:
try:
    engine = get_database_engine()
    st.success("✅ Database connected")
except Exception as e:
    st.error(f"❌ Database error: {e}")
```

**Workflow Execution Failures:**
```python
# Add error handling:
try:
    response = asyncio.run(workflow.ainvoke(inputs))
except Exception as e:
    st.error("⚠️ AI workflow temporarily unavailable")
    print(f"Workflow error: {e}")
```

## Success Metrics

### Deployment Success Indicators
- [ ] App accessible via public URL
- [ ] Sign-in flow completes successfully
- [ ] Chat responses generated correctly
- [ ] Database operations working
- [ ] No critical errors in logs
- [ ] Professor can access and test all features

### Performance Benchmarks
- **Page load time**: < 5 seconds
- **Chat response time**: < 30 seconds
- **Profile creation**: < 60 seconds
- **Uptime**: > 99% (Streamlit Cloud SLA)

## Next Steps After Deployment

1. **Share URL with professor**
2. **Monitor usage and performance**
3. **Collect feedback for improvements**
4. **Document any issues for future iterations**
5. **Consider scaling options if needed**

---

**Estimated Total Deployment Time**: 30-60 minutes
**Complexity Level**: Low (thanks to current architecture)
**Success Probability**: High (all components tested locally)