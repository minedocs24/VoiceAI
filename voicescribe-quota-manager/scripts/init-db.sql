-- Minimal schema for standalone Quota Manager
CREATE TYPE tier_at_creation AS ENUM ('FREE', 'PRO', 'ENTERPRISE');

CREATE TABLE IF NOT EXISTS tenants (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    tier tier_at_creation NOT NULL DEFAULT 'FREE',
    api_key_hash VARCHAR(128),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS free_tier_usage (
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id) ON UPDATE CASCADE ON DELETE CASCADE,
    usage_date DATE NOT NULL,
    used_count INTEGER NOT NULL DEFAULT 0 CHECK (used_count >= 0),
    quota_exceeded_attempts INTEGER NOT NULL DEFAULT 0 CHECK (quota_exceeded_attempts >= 0),
    reset_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, usage_date)
);

CREATE INDEX IF NOT EXISTS idx_free_tier_usage_date ON free_tier_usage(usage_date DESC);
CREATE INDEX IF NOT EXISTS idx_free_tier_usage_exceeded ON free_tier_usage(quota_exceeded_attempts DESC);

INSERT INTO tenants (id, name, tier) VALUES ('dev-tenant-001', 'Dev Tenant', 'FREE') ON CONFLICT (id) DO NOTHING;
