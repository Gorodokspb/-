BEGIN;

ALTER TABLE estimates ADD COLUMN IF NOT EXISTS company_id BIGINT NULL REFERENCES companies(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_estimates_company_id ON estimates (company_id);

COMMIT;