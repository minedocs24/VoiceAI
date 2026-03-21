"""initial voicescribe shared schema

Revision ID: 20260314_0001
Revises:
Create Date: 2026-03-14 13:00:00
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260314_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TYPE tier_at_creation AS ENUM ('FREE', 'PRO', 'ENTERPRISE');
        CREATE TYPE job_status AS ENUM ('QUEUED', 'PREPROCESSING', 'TRANSCRIBING', 'DIARIZING', 'EXPORTING', 'DONE', 'FAILED');

        CREATE TABLE IF NOT EXISTS tenants (
            id VARCHAR(64) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            tier tier_at_creation NOT NULL DEFAULT 'FREE',
            api_key_hash VARCHAR(128),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        COMMENT ON TABLE tenants IS 'Anagrafica tenant e configurazione piano di accesso';
        COMMENT ON COLUMN tenants.id IS 'Identificativo tenant esterno, stabile e univoco';
        COMMENT ON COLUMN tenants.name IS 'Nome descrittivo tenant';
        COMMENT ON COLUMN tenants.tier IS 'Piano corrente tenant: FREE, PRO o ENTERPRISE';
        COMMENT ON COLUMN tenants.api_key_hash IS 'Hash SHA-256 API key (solo piani con API key)';
        COMMENT ON COLUMN tenants.is_active IS 'Flag tenant abilitato/disabilitato';
        COMMENT ON COLUMN tenants.created_at IS 'Timestamp creazione tenant (UTC)';
        COMMENT ON COLUMN tenants.updated_at IS 'Timestamp ultimo aggiornamento tenant (UTC)';

        CREATE TABLE IF NOT EXISTS jobs (
            id UUID PRIMARY KEY,
            tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id) ON UPDATE CASCADE ON DELETE RESTRICT,
            tier_at_creation tier_at_creation NOT NULL,
            status job_status NOT NULL,
            priority SMALLINT NOT NULL CHECK (priority IN (1, 5, 10)),
            duration_seconds DOUBLE PRECISION,
            ramdisk_path VARCHAR(512),
            transcription_raw JSONB,
            diarization_raw JSONB,
            gpu_inference_ms INTEGER CHECK (gpu_inference_ms IS NULL OR gpu_inference_ms >= 0),
            celery_task_id VARCHAR(64),
            error_code VARCHAR(64),
            error_message TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            completed_at TIMESTAMPTZ
        );

        COMMENT ON TABLE jobs IS 'Stato pipeline trascrizione e metadati esecuzione per singolo job';
        COMMENT ON COLUMN jobs.id IS 'Job ID UUID generato dal gateway';
        COMMENT ON COLUMN jobs.tenant_id IS 'Tenant proprietario del job';
        COMMENT ON COLUMN jobs.tier_at_creation IS 'Tier immutabile al momento creazione job';
        COMMENT ON COLUMN jobs.status IS 'Stato corrente lifecycle job';
        COMMENT ON COLUMN jobs.priority IS 'Priorita Celery per tier: FREE=1, PRO=5, ENTERPRISE=10';
        COMMENT ON COLUMN jobs.duration_seconds IS 'Durata file originale in secondi da SVC-02 /probe';
        COMMENT ON COLUMN jobs.ramdisk_path IS 'Path WAV temporaneo su ramdisk /mnt/ramdisk';
        COMMENT ON COLUMN jobs.transcription_raw IS 'Output JSON SVC-06 TranscriptResult';
        COMMENT ON COLUMN jobs.diarization_raw IS 'Output JSON SVC-07 DiarizationResult, NULL per Free Tier';
        COMMENT ON COLUMN jobs.gpu_inference_ms IS 'Latenza inference GPU in millisecondi';
        COMMENT ON COLUMN jobs.celery_task_id IS 'Task id Celery per tracking e revoke';
        COMMENT ON COLUMN jobs.error_code IS 'Codice errore applicativo standardizzato';
        COMMENT ON COLUMN jobs.error_message IS 'Dettaglio errore non strutturato';
        COMMENT ON COLUMN jobs.created_at IS 'Timestamp creazione job (UTC)';
        COMMENT ON COLUMN jobs.updated_at IS 'Timestamp ultimo aggiornamento job (UTC)';
        COMMENT ON COLUMN jobs.completed_at IS 'Timestamp completamento job (UTC)';

        CREATE INDEX IF NOT EXISTS idx_jobs_tenant_id ON jobs(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_jobs_tenant_status ON jobs(tenant_id, status);

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

        COMMENT ON TABLE free_tier_usage IS 'Analytics giornaliera consumo Free Tier e tentativi oltre quota';
        COMMENT ON COLUMN free_tier_usage.tenant_id IS 'Tenant owner della metrica giornaliera';
        COMMENT ON COLUMN free_tier_usage.usage_date IS 'Data UTC di contabilizzazione quota';
        COMMENT ON COLUMN free_tier_usage.used_count IS 'Numero trascrizioni consumate nel giorno';
        COMMENT ON COLUMN free_tier_usage.quota_exceeded_attempts IS 'Tentativi oltre limite giornaliero';
        COMMENT ON COLUMN free_tier_usage.reset_at IS 'Timestamp previsto reset quota (mezzanotte UTC)';
        COMMENT ON COLUMN free_tier_usage.created_at IS 'Timestamp creazione record';
        COMMENT ON COLUMN free_tier_usage.updated_at IS 'Timestamp ultimo aggiornamento record';

        CREATE INDEX IF NOT EXISTS idx_free_tier_usage_date ON free_tier_usage(usage_date DESC);
        CREATE INDEX IF NOT EXISTS idx_free_tier_usage_exceeded ON free_tier_usage(quota_exceeded_attempts DESC);

        CREATE OR REPLACE FUNCTION set_updated_at_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS trg_tenants_updated_at ON tenants;
        CREATE TRIGGER trg_tenants_updated_at
            BEFORE UPDATE ON tenants
            FOR EACH ROW EXECUTE FUNCTION set_updated_at_timestamp();

        DROP TRIGGER IF EXISTS trg_jobs_updated_at ON jobs;
        CREATE TRIGGER trg_jobs_updated_at
            BEFORE UPDATE ON jobs
            FOR EACH ROW EXECUTE FUNCTION set_updated_at_timestamp();

        DROP TRIGGER IF EXISTS trg_free_tier_usage_updated_at ON free_tier_usage;
        CREATE TRIGGER trg_free_tier_usage_updated_at
            BEFORE UPDATE ON free_tier_usage
            FOR EACH ROW EXECUTE FUNCTION set_updated_at_timestamp();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_free_tier_usage_updated_at ON free_tier_usage;
        DROP TRIGGER IF EXISTS trg_jobs_updated_at ON jobs;
        DROP TRIGGER IF EXISTS trg_tenants_updated_at ON tenants;
        DROP FUNCTION IF EXISTS set_updated_at_timestamp();
        DROP TABLE IF EXISTS free_tier_usage;
        DROP TABLE IF EXISTS jobs;
        DROP TABLE IF EXISTS tenants;
        DROP TYPE IF EXISTS job_status;
        DROP TYPE IF EXISTS tier_at_creation;
        """
    )
