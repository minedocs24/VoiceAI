-- Seed Free Tier and PRO test users for e2e tests.
-- Run: docker compose exec -T postgres psql -U voicescribe_app -d voicescribe < scripts/seed-e2e-users.sql

-- Free Tier: free@test.local / password, tenant_id free-tier-tenant
INSERT INTO tenants (id, name, tier, email, password_hash, is_active)
VALUES (
  'free-tier-tenant',
  'Free Tier Test',
  'FREE',
  'free@test.local',
  '$2b$12$EixZaYVK1psbw1ZvbXvvOOuIcqbRE.StuF1F4.eG3nN9xR3VqK2yS',
  TRUE
)
ON CONFLICT (id) DO UPDATE SET
  email = EXCLUDED.email,
  password_hash = EXCLUDED.password_hash;

-- PRO tenant (API key only)
INSERT INTO tenants (id, name, tier, api_key_hash, is_active)
VALUES (
  'pro-tenant-01',
  'PRO Test',
  'PRO',
  'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  TRUE
)
ON CONFLICT (id) DO NOTHING;
