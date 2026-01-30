-- Migration: 002_immutable_audit.sql
-- Purpose: Create tamper-evident audit log with hash chaining
-- Author: HAAIS AIOS Enterprise Hardening
-- Date: 2026-01-29

-- ============================================================================
-- IMMUTABLE AUDIT LOG TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS immutable_audit_log (
    -- Identity
    record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence_number BIGINT NOT NULL,
    tenant_id TEXT NOT NULL,

    -- Timing
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Event details
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info',

    -- Actor information
    actor_id TEXT NOT NULL,
    actor_type TEXT NOT NULL DEFAULT 'user',
    actor_ip INET,

    -- Action details
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,

    -- Outcome
    outcome TEXT NOT NULL DEFAULT 'success',
    outcome_details TEXT,

    -- Payload (structured event data)
    payload JSONB NOT NULL DEFAULT '{}',

    -- Chain integrity
    previous_hash TEXT NOT NULL DEFAULT '',
    record_hash TEXT NOT NULL,

    -- Metadata
    environment TEXT NOT NULL DEFAULT 'production',
    api_version TEXT NOT NULL DEFAULT '1.0',
    correlation_id TEXT,

    -- Constraints
    CONSTRAINT unique_tenant_sequence UNIQUE (tenant_id, sequence_number),
    CONSTRAINT valid_severity CHECK (severity IN ('debug', 'info', 'warning', 'error', 'critical')),
    CONSTRAINT valid_actor_type CHECK (actor_type IN ('user', 'agent', 'system', 'service', 'external')),
    CONSTRAINT valid_outcome CHECK (outcome IN ('success', 'failure', 'partial'))
);

-- ============================================================================
-- INDEXES FOR EFFICIENT QUERYING
-- ============================================================================

-- Primary query pattern: tenant + time range
CREATE INDEX IF NOT EXISTS idx_audit_tenant_time
ON immutable_audit_log(tenant_id, timestamp DESC);

-- Chain verification: tenant + sequence
CREATE INDEX IF NOT EXISTS idx_audit_tenant_sequence
ON immutable_audit_log(tenant_id, sequence_number);

-- Event type filtering
CREATE INDEX IF NOT EXISTS idx_audit_event_type
ON immutable_audit_log(tenant_id, event_type, timestamp DESC);

-- Actor lookup
CREATE INDEX IF NOT EXISTS idx_audit_actor
ON immutable_audit_log(tenant_id, actor_id, timestamp DESC);

-- Resource lookup
CREATE INDEX IF NOT EXISTS idx_audit_resource
ON immutable_audit_log(tenant_id, resource_type, resource_id, timestamp DESC)
WHERE resource_type IS NOT NULL;

-- Correlation ID for request tracing
CREATE INDEX IF NOT EXISTS idx_audit_correlation
ON immutable_audit_log(correlation_id)
WHERE correlation_id IS NOT NULL;

-- ============================================================================
-- IMMUTABILITY ENFORCEMENT
-- ============================================================================

-- Trigger function to prevent updates and deletes
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'SECURITY VIOLATION: Audit records cannot be modified or deleted. Record ID: %', OLD.record_id;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to prevent UPDATE
DROP TRIGGER IF EXISTS audit_prevent_update ON immutable_audit_log;
CREATE TRIGGER audit_prevent_update
BEFORE UPDATE ON immutable_audit_log
FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();

-- Apply trigger to prevent DELETE
DROP TRIGGER IF EXISTS audit_prevent_delete ON immutable_audit_log;
CREATE TRIGGER audit_prevent_delete
BEFORE DELETE ON immutable_audit_log
FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();

-- ============================================================================
-- SEQUENCE ENFORCEMENT
-- ============================================================================

-- Trigger to validate sequence number on insert
CREATE OR REPLACE FUNCTION validate_audit_sequence()
RETURNS TRIGGER AS $$
DECLARE
    expected_sequence BIGINT;
    last_hash TEXT;
BEGIN
    -- Get the last sequence number for this tenant
    SELECT sequence_number, record_hash
    INTO expected_sequence, last_hash
    FROM immutable_audit_log
    WHERE tenant_id = NEW.tenant_id
    ORDER BY sequence_number DESC
    LIMIT 1
    FOR UPDATE;  -- Lock to prevent race conditions

    IF expected_sequence IS NULL THEN
        -- First record for tenant
        IF NEW.sequence_number != 1 THEN
            RAISE EXCEPTION 'First audit record must have sequence_number = 1, got %', NEW.sequence_number;
        END IF;
        IF NEW.previous_hash != '' THEN
            RAISE EXCEPTION 'First audit record must have empty previous_hash';
        END IF;
    ELSE
        -- Subsequent record
        IF NEW.sequence_number != expected_sequence + 1 THEN
            RAISE EXCEPTION 'Invalid sequence_number: expected %, got %', expected_sequence + 1, NEW.sequence_number;
        END IF;
        IF NEW.previous_hash != last_hash THEN
            RAISE EXCEPTION 'Invalid previous_hash: chain integrity violation';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS audit_validate_sequence ON immutable_audit_log;
CREATE TRIGGER audit_validate_sequence
BEFORE INSERT ON immutable_audit_log
FOR EACH ROW EXECUTE FUNCTION validate_audit_sequence();

-- ============================================================================
-- CHAIN VERIFICATION FUNCTION
-- ============================================================================

-- Function to verify chain integrity for a tenant
CREATE OR REPLACE FUNCTION verify_audit_chain(p_tenant_id TEXT)
RETURNS TABLE (
    is_valid BOOLEAN,
    records_checked BIGINT,
    error_at_sequence BIGINT,
    error_message TEXT
) AS $$
DECLARE
    rec RECORD;
    prev_hash TEXT := '';
    prev_seq BIGINT := 0;
    rec_count BIGINT := 0;
BEGIN
    FOR rec IN
        SELECT sequence_number, previous_hash, record_hash
        FROM immutable_audit_log
        WHERE tenant_id = p_tenant_id
        ORDER BY sequence_number
    LOOP
        rec_count := rec_count + 1;

        -- Check sequence continuity
        IF prev_seq > 0 AND rec.sequence_number != prev_seq + 1 THEN
            RETURN QUERY SELECT
                FALSE,
                rec_count,
                rec.sequence_number,
                format('Sequence gap: expected %s, got %s', prev_seq + 1, rec.sequence_number);
            RETURN;
        END IF;

        -- Check hash chain
        IF rec.previous_hash != prev_hash THEN
            RETURN QUERY SELECT
                FALSE,
                rec_count,
                rec.sequence_number,
                format('Chain break: previous_hash mismatch at sequence %s', rec.sequence_number);
            RETURN;
        END IF;

        prev_hash := rec.record_hash;
        prev_seq := rec.sequence_number;
    END LOOP;

    -- Chain is valid
    RETURN QUERY SELECT TRUE, rec_count, NULL::BIGINT, NULL::TEXT;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION verify_audit_chain(TEXT) IS
    'Verifies the integrity of the audit hash chain for a tenant';

-- ============================================================================
-- AUDIT STATISTICS VIEW
-- ============================================================================

CREATE OR REPLACE VIEW audit_statistics AS
SELECT
    tenant_id,
    COUNT(*) as total_records,
    MIN(timestamp) as first_record,
    MAX(timestamp) as last_record,
    MAX(sequence_number) as last_sequence,
    COUNT(DISTINCT event_type) as unique_event_types,
    COUNT(DISTINCT actor_id) as unique_actors
FROM immutable_audit_log
GROUP BY tenant_id;

COMMENT ON VIEW audit_statistics IS
    'Summary statistics for audit logs by tenant';

-- ============================================================================
-- RLS FOR AUDIT LOG (tenant can only see their own)
-- ============================================================================

ALTER TABLE immutable_audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE immutable_audit_log FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_audit ON immutable_audit_log;
CREATE POLICY tenant_isolation_audit ON immutable_audit_log
    FOR SELECT  -- Only SELECT, no INSERT through RLS (app handles insert)
    USING (tenant_id = current_tenant_id());

-- Allow INSERT without RLS check (app validates tenant)
DROP POLICY IF EXISTS allow_audit_insert ON immutable_audit_log;
CREATE POLICY allow_audit_insert ON immutable_audit_log
    FOR INSERT
    WITH CHECK (true);  -- App layer validates tenant_id

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE immutable_audit_log IS
    'Tamper-evident audit log with cryptographic hash chaining. Records cannot be modified or deleted.';

COMMENT ON COLUMN immutable_audit_log.sequence_number IS
    'Monotonically increasing sequence within tenant, used for chain verification';

COMMENT ON COLUMN immutable_audit_log.previous_hash IS
    'SHA-256 hash of the previous record, empty string for genesis record';

COMMENT ON COLUMN immutable_audit_log.record_hash IS
    'SHA-256 hash of this record computed from all content fields + previous_hash';

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
