# MVP Deployment Plan for Clare-AI

## Overview
Convert the current VPN-dependent Clare-AI system into a cloud-hosted MVP that can be shared via URL with the professor for demonstration purposes.

## Current Challenge
- Database requires university VPN access (`134.173.236.12:1433`)
- Need to deploy as a publicly accessible demo
- Goal: Share URL with professor for testing

## Deployment Strategy

### Phase 1: Database Assessment & Migration Planning
- [ ] **Check current database tables and assess data volume**
  - Run SQL queries to identify table sizes and row counts
  - Determine which tables contain substantial data vs empty/schema-only tables

- [ ] **Identify migration strategy per table**
  - **Full Migration**: Tables with important data (likely `chat_history`, `student_profiles`, `final_data`)
  - **Schema Only**: Empty or test tables that just need structure recreation

### Phase 2: Code Refactoring & Organization
- [ ] **Create new branch for MVP refactoring**
  - Clean separation from current development branch

- [ ] **Code organization cleanup**
  - Move prompts out of `main.py` into separate `prompts/` module
  - Move workflows out of `main.py` into separate `workflows/` module
  - Create `legacy/` folder for old/unused code
  - Streamline main application file

### Phase 3: Cloud Infrastructure Setup
- [ ] **Set up cloud database**
  - **Recommended**: Supabase (free tier, pgvector support, PostgreSQL compatible)
  - **Alternatives**: Railway, Neon
  - Enable pgvector extension for embeddings

- [ ] **Data migration**
  - Export essential data from current database
  - Import to cloud database
  - Recreate schemas for empty tables

### Phase 4: Deployment Configuration
- [ ] **Update database connection configuration**
  - Replace VPN-dependent connection string
  - Configure environment variables for cloud deployment
  - Test database connectivity

- [ ] **Deploy to Streamlit Cloud**
  - Connect GitHub repository
  - Configure environment variables
  - Deploy and test functionality

## Cloud Database Options

### Supabase (Recommended)
- **Pros**: Free tier, built-in pgvector, PostgreSQL compatible, good documentation
- **Cons**: Learning curve for new platform
- **Free Tier**: 500MB database, 2 concurrent connections

### Railway
- **Pros**: Simple setup, good PostgreSQL support
- **Cons**: Limited free tier
- **Free Tier**: $5 credit monthly

### Neon
- **Pros**: Serverless PostgreSQL, good performance
- **Cons**: Newer platform
- **Free Tier**: 3GB storage, 1 project

## Streamlit Cloud Deployment
- **Cost**: Free
- **URL Format**: `https://your-app-name.streamlit.app`
- **Requirements**: Public GitHub repository
- **Automatic**: Handles Python dependencies from requirements files

## Success Criteria
1. Professor can access demo via public URL
2. Core chat functionality works without VPN
3. Student profiles and chat history persist
4. Document retrieval system functions
5. No authentication required for demo purposes

## Timeline Estimate
- **Database Setup**: 2-3 hours
- **Code Refactoring**: 3-4 hours
- **Migration & Testing**: 2-3 hours
- **Total**: 1-2 days for complete MVP deployment

## Next Steps
1. Run database assessment queries
2. Choose cloud database provider
3. Create refactoring branch
4. Begin code organization cleanup