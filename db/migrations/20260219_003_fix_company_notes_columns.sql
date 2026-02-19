-- Fix silver.fmp_company_notes column mapping errors:
--   The table was incorrectly populated using CompanyDTO (company-profile schema).
--   The actual payload is: {cik, symbol, title, exchange}.
--   Add missing title column, drop all columns that don't exist in the payload.
ALTER TABLE silver.fmp_company_notes ADD COLUMN IF NOT EXISTS title VARCHAR;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS isin;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS cusip;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS exchange_full_name;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS currency;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS price;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS market_cap;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS beta;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS last_dividend;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS "range";
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS change;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS change_percentage;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS volume;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS average_volume;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS company_name;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS industry;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS sector;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS description;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS website;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS ceo;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS country;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS full_time_employees;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS phone;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS address;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS city;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS state;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS zip;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS image;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS ipo_date;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS default_image;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS is_etf;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS is_actively_trading;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS is_adr;
ALTER TABLE silver.fmp_company_notes DROP COLUMN IF EXISTS is_fund;
