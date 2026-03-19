-- ============================================================
-- HOSPITAL SYNC SCHEMA V3
-- Multi-client incremental sync
-- ISO 15189 audit ready
-- PostgreSQL 13+
-- Safe to run multiple times
-- ============================================================

BEGIN;

-- ============================================================
-- I. STANDARD COLUMNS FOR ALL SYNC TABLES
-- ============================================================

DO $$
DECLARE
    tbl TEXT;
    tables TEXT[] := ARRAY[
        'department_v2',
        'users_v2',
        'catalog_lot_v2',
        'catalog_analyte_v2',
        'iqc_run_v2',
        'iqc_result_v2',
        'audit_log_v2'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables
    LOOP
        EXECUTE format('
            ALTER TABLE IF EXISTS %I
            ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1,
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            ADD COLUMN IF NOT EXISTS is_deleted INTEGER DEFAULT 0
        ', tbl);
    END LOOP;
END $$;

-- ============================================================
-- II. VERSION + TIMESTAMP TRIGGER FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION trg_set_version_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        NEW.version := 1;
        NEW.created_at := NOW();
        NEW.updated_at := NOW();
        RETURN NEW;

    ELSIF TG_OP = 'UPDATE' THEN
        NEW.version := OLD.version + 1;
        NEW.updated_at := NOW();
        RETURN NEW;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- III. ATTACH TRIGGERS TO ALL SYNC TABLES
-- ============================================================

DO $$
DECLARE
    tbl TEXT;
    trg TEXT;
    tables TEXT[] := ARRAY[
        'department_v2',
        'users_v2',
        'catalog_lot_v2',
        'catalog_analyte_v2',
        'iqc_run_v2',
        'iqc_result_v2',
        'audit_log_v2'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables
    LOOP
        trg := 'trg_' || tbl || '_version';

        EXECUTE format('DROP TRIGGER IF EXISTS %I ON %I', trg, tbl);

        EXECUTE format('
            CREATE TRIGGER %I
            BEFORE INSERT OR UPDATE
            ON %I
            FOR EACH ROW
            EXECUTE FUNCTION trg_set_version_timestamp()
        ', trg, tbl);
    END LOOP;
END $$;

-- ============================================================
-- IV. SYNC STATE (PER DEVICE PER TABLE)
-- ============================================================

CREATE TABLE IF NOT EXISTS sync_state (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    last_pull_time TIMESTAMP,
    last_push_time TIMESTAMP,
    UNIQUE(device_id, table_name)
);

CREATE INDEX IF NOT EXISTS idx_sync_state_device
ON sync_state(device_id);

-- ============================================================
-- V. SYNC HISTORY (ISO 15189 AUDIT)
-- ============================================================

CREATE TABLE IF NOT EXISTS sync_history (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    direction VARCHAR(20),         -- PUSH / PULL / FULL
    status VARCHAR(20),            -- SUCCESS / FAILED
    push_count INTEGER DEFAULT 0,
    pull_count INTEGER DEFAULT 0,
    error_log TEXT
);

CREATE INDEX IF NOT EXISTS idx_sync_history_device
ON sync_history(device_id);

CREATE INDEX IF NOT EXISTS idx_sync_history_time
ON sync_history(start_time);

-- ============================================================
-- VI. UPDATED_AT INDEX FOR INCREMENTAL PULL
-- ============================================================

DO $$
DECLARE
    tbl TEXT;
    tables TEXT[] := ARRAY[
        'department_v2',
        'users_v2',
        'catalog_lot_v2',
        'catalog_analyte_v2',
        'iqc_run_v2',
        'iqc_result_v2',
        'audit_log_v2'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables
    LOOP
        EXECUTE format('
            CREATE INDEX IF NOT EXISTS idx_%I_updated
            ON %I(updated_at)
        ', tbl, tbl);
    END LOOP;
END $$;

-- ============================================================
-- VII. UNIQUE CONSTRAINTS (ANTI-DUPLICATE)
-- ============================================================

ALTER TABLE IF EXISTS users_v2
    ADD CONSTRAINT IF NOT EXISTS uq_users_username UNIQUE (username);

-- ============================================================
-- VIII. SECURITY: PREVENT CLIENT FROM TOUCHING VERSION
-- (Optional - enable if using separate DB user for client)
-- ============================================================

-- REVOKE UPDATE(version, created_at, updated_at)
-- ON department_v2, users_v2, catalog_lot_v2,
--    catalog_analyte_v2, iqc_run_v2,
--    iqc_result_v2, audit_log_v2
-- FROM public;

-- ============================================================
-- DONE
-- ============================================================

COMMIT;