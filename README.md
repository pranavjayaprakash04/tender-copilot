# Tender Copilot v1.5

AI-powered government tender intelligence for Indian MSMEs.

## Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL with pgvector extension
- Redis

### Local Development

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd tendercopilot
   cp .env.example .env
   # Edit .env with your credentials
   ```

2. **Start services**
   ```bash
   docker-compose up -d
   ```

3. **Run database migration**
   ```bash
   docker-compose exec backend python -m alembic upgrade head
   ```

4. **Access the API**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Health: http://localhost:8000/health

## Architecture

### Backend (FastAPI)
- **Framework**: FastAPI 0.111 with async/await
- **Database**: PostgreSQL + SQLAlchemy 2.0 (async)
- **Task Queue**: Celery + Redis
- **AI**: Groq SDK (Llama 3.3, DeepSeek-R1)
- **Auth**: Supabase Auth + JWT

### Frontend (Next.js 14)
- **Framework**: Next.js 14 App Router
- **Language**: TypeScript (strict)
- **Styling**: Tailwind CSS
- **State**: Zustand + TanStack Query
- **Auth**: Supabase Auth (SSR)

## Development Phases

1. **Phase 0** - Foundation ✅
   - Repo structure, config, database, middleware
   - Error handling, logging, Celery setup

2. **Phase 1** - Compliance Vault
   - Document upload, classification, expiry tracking
   - Document-to-tender mapping

3. **Phase 2** - Bid Lifecycle Tracker
   - Status tracking, outcome recording
   - Payment follow-ups, loss analysis

4. **Phase 3** - Core Tender Flow
   - Tender discovery, intelligence, bid generation
   - Matching, alerts

5. **Phase 4** - WhatsApp Gateway
   - Webhook, intent classification, session management

6. **Phase 5** - CA Partner Portal
   - Multi-client management, bulk operations

7. **Phase 6** - Bid Intelligence
   - Market prices, competitor analysis, win probability

## API Design

All endpoints follow the pattern:
```
GET    /api/v1/tenders          - List tenders
POST   /api/v1/bids             - Create bid
GET    /api/v1/bids/{id}        - Get bid details
PUT    /api/v1/bids/{id}        - Update bid
DELETE /api/v1/bids/{id}        - Delete bid
```

### Response Format
```json
{
  "data": { ... },
  "success": true,
  "message": "Operation completed",
  "trace_id": "uuid",
  "timestamp": "2024-03-10T20:30:00Z"
}
```

## Database Schema

Key tables:
- `users` - User accounts (MSME owners, CA partners)
- `companies` - Company profiles with capabilities
- `tenders` - Government tender listings
- `bids` - Bid submissions with versioning
- `bid_outcomes` - MANDATORY outcome tracking
- `vault_documents` - Compliance document storage
- `whatsapp_sessions` - WhatsApp conversation state

## AI Integration

### Groq Models
- **Primary** (`llama-3.3-70b-versatile`): Bid generation, document intelligence
- **Fast** (`llama-3.1-8b-instant`): Matching, WhatsApp intent
- **Reasoning** (`deepseek-r1-distill-llama-70b`): Analysis, intelligence

### Prompt System
All prompts are versioned and follow the pattern:
```python
# backend/app/prompts/[context]/[prompt_name]_v1.py
```

## Testing

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Coverage
pytest --cov=app tests/
```

## Deployment

### Production Stack
- **Database**: Supabase PostgreSQL (pgvector)
- **Storage**: Supabase Storage
- **Auth**: Supabase Auth
- **Cache**: Upstash Redis
- **Backend**: Render
- **Frontend**: Vercel
- **Email**: Resend
- **Payments**: Razorpay

## Contributing

1. Follow the exact repository structure
2. No files over 300 lines - split immediately
3. All business logic in service layer
4. Every database access must include company_id scope
5. No synchronous LLM calls in web requests - use Celery
6. Run linter and fix all errors before committing

## License

© 2024 NivedhaAI. All rights reserved.