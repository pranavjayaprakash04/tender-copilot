# Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- USERS & TENANCY
CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  supabase_uid  TEXT UNIQUE NOT NULL,
  email         TEXT UNIQUE NOT NULL,
  role          TEXT NOT NULL CHECK (role IN ('msme_owner', 'ca_partner')),
  plan_tier     TEXT NOT NULL DEFAULT 'free' CHECK (plan_tier IN ('free', 'msme', 'ca')),
  lang          TEXT NOT NULL DEFAULT 'en' CHECK (lang IN ('en', 'ta')),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE companies (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  owner_user_id     UUID NOT NULL REFERENCES users(id),
  name              TEXT NOT NULL,
  gstin             TEXT,
  pan               TEXT,
  state             TEXT NOT NULL,
  categories        TEXT[] NOT NULL DEFAULT '{}',
  annual_turnover   NUMERIC,
  employee_count    INTEGER,
  capabilities_text TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE ca_managed_companies (
  ca_user_id  UUID NOT NULL REFERENCES users(id),
  company_id  UUID NOT NULL REFERENCES companies(id),
  added_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (ca_user_id, company_id)
);

-- TENDERS
CREATE TABLE tenders (
  id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  portal           TEXT NOT NULL CHECK (portal IN ('gem', 'cppp', 'state', 'other')),
  portal_ref_no    TEXT NOT NULL,
  title            TEXT NOT NULL,
  department       TEXT NOT NULL,
  state            TEXT,
  category         TEXT,
  estimated_value  NUMERIC,
  bid_deadline     TIMESTAMPTZ,
  published_at     TIMESTAMPTZ,
  status           TEXT NOT NULL DEFAULT 'open',
  raw_content      TEXT,
  embedding        VECTOR(768),
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(portal, portal_ref_no)
);

CREATE INDEX idx_tenders_deadline ON tenders(bid_deadline);
CREATE INDEX idx_tenders_category ON tenders(category);
CREATE INDEX idx_tenders_embedding ON tenders USING hnsw (embedding vector_cosine_ops);

-- BIDS
CREATE TABLE bids (
  id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id     UUID NOT NULL REFERENCES companies(id),
  tender_id      UUID NOT NULL REFERENCES tenders(id),
  status         TEXT NOT NULL DEFAULT 'draft'
                   CHECK (status IN ('draft', 'reviewing', 'submitted', 'won', 'lost', 'withdrawn')),
  draft_content  TEXT,
  version        INTEGER NOT NULL DEFAULT 1,
  submitted_at   TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- BID LIFECYCLE — THE MOAT STARTS HERE
CREATE TABLE bid_outcomes (
  id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  bid_id           UUID NOT NULL REFERENCES bids(id),
  tender_id        UUID NOT NULL REFERENCES tenders(id),
  company_id       UUID NOT NULL REFERENCES companies(id),
  category         TEXT NOT NULL,
  estimated_value  NUMERIC,
  our_price        NUMERIC,
  winning_price    NUMERIC,
  outcome          TEXT NOT NULL CHECK (outcome IN ('win', 'loss', 'not_qualified', 'withdrawn')),
  department       TEXT NOT NULL,
  state            TEXT NOT NULL,
  financial_year   TEXT NOT NULL,
  recorded_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ENFORCEMENT: bid cannot close without outcome record
CREATE UNIQUE INDEX idx_bid_outcomes_bid_id ON bid_outcomes(bid_id);

CREATE TABLE loss_analyses (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  bid_outcome_id        UUID NOT NULL REFERENCES bid_outcomes(id),
  loss_reason_ai        TEXT,
  loss_reason_manual    TEXT,
  recommendations       JSONB,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- COMPLIANCE VAULT
CREATE TABLE vault_documents (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id    UUID NOT NULL REFERENCES companies(id),
  doc_type      TEXT NOT NULL,
  filename      TEXT NOT NULL,
  storage_path  TEXT NOT NULL,
  version       INTEGER NOT NULL DEFAULT 1,
  expires_at    TIMESTAMPTZ,
  is_current    BOOLEAN NOT NULL DEFAULT TRUE,
  uploaded_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE vault_document_mappings (
  vault_doc_id  UUID NOT NULL REFERENCES vault_documents(id),
  tender_id     UUID NOT NULL REFERENCES tenders(id),
  used_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (vault_doc_id, tender_id)
);

-- WHATSAPP SESSIONS
CREATE TABLE whatsapp_sessions (
  phone_number   TEXT PRIMARY KEY,
  company_id     UUID REFERENCES companies(id),
  session_state  JSONB NOT NULL DEFAULT '{}',
  current_flow   TEXT,
  last_active    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ALERTS
CREATE TABLE alert_rules (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id    UUID NOT NULL REFERENCES companies(id),
  categories    TEXT[],
  states        TEXT[],
  min_value     NUMERIC,
  max_value     NUMERIC,
  channels      TEXT[] NOT NULL DEFAULT '{email}',
  is_active     BOOLEAN NOT NULL DEFAULT TRUE
);

-- SUBSCRIPTIONS
CREATE TABLE subscriptions (
  id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id             UUID NOT NULL REFERENCES users(id),
  razorpay_sub_id     TEXT UNIQUE,
  plan_tier           TEXT NOT NULL,
  status              TEXT NOT NULL DEFAULT 'active',
  current_period_end  TIMESTAMPTZ,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ROW LEVEL SECURITY
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE bids ENABLE ROW LEVEL SECURITY;
ALTER TABLE bid_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE vault_documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "company_isolation" ON companies
  USING (
    owner_user_id = auth.uid()
    OR id IN (
      SELECT company_id FROM ca_managed_companies WHERE ca_user_id = auth.uid()
    )
  );

CREATE POLICY "bids_isolation" ON bids
  USING (
    company_id IN (
      SELECT id FROM companies WHERE owner_user_id = auth.uid()
      UNION
      SELECT company_id FROM ca_managed_companies WHERE ca_user_id = auth.uid()
    )
  );
