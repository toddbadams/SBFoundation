-- Gold layer: static dimension tables (bootstrapped from code, never updated by ingestion)
-- These define the controlled vocabulary for instrument classification.

-- dim_date: all calendar dates 1990-01-01 to 2030-12-31
CREATE TABLE IF NOT EXISTS gold.dim_date (
    date_sk          INTEGER PRIMARY KEY,
    full_date        DATE    NOT NULL UNIQUE,
    year             INTEGER NOT NULL,
    quarter          INTEGER NOT NULL,
    month            INTEGER NOT NULL,
    week_of_year     INTEGER NOT NULL,
    day_of_month     INTEGER NOT NULL,
    day_of_week      INTEGER NOT NULL,
    day_name         VARCHAR NOT NULL,
    month_name       VARCHAR NOT NULL,
    is_weekend       BOOLEAN NOT NULL,
    is_us_market_day BOOLEAN NOT NULL DEFAULT FALSE
);

INSERT OR IGNORE INTO gold.dim_date
SELECT
    CAST(strftime(d.dt, '%Y%m%d') AS INTEGER)        AS date_sk,
    d.dt                                              AS full_date,
    EXTRACT('year'    FROM d.dt)::INTEGER             AS year,
    EXTRACT('quarter' FROM d.dt)::INTEGER             AS quarter,
    EXTRACT('month'   FROM d.dt)::INTEGER             AS month,
    EXTRACT('week'    FROM d.dt)::INTEGER             AS week_of_year,
    EXTRACT('day'     FROM d.dt)::INTEGER             AS day_of_month,
    EXTRACT('dow'     FROM d.dt)::INTEGER             AS day_of_week,
    strftime(d.dt, '%A')                              AS day_name,
    strftime(d.dt, '%B')                              AS month_name,
    EXTRACT('dow' FROM d.dt) IN (0, 6)               AS is_weekend,
    FALSE                                             AS is_us_market_day
FROM (
    SELECT CAST(range AS DATE) AS dt
    FROM range(DATE '1990-01-01', DATE '2031-01-01', INTERVAL '1 day')
) d;

-- dim_instrument_type: controlled vocabulary for asset classes
CREATE TABLE IF NOT EXISTS gold.dim_instrument_type (
    instrument_type_sk SMALLINT PRIMARY KEY,
    instrument_type    VARCHAR  NOT NULL UNIQUE
);

INSERT OR IGNORE INTO gold.dim_instrument_type VALUES
    (1, 'commodity'),
    (2, 'crypto'),
    (3, 'etf'),
    (4, 'fx'),
    (5, 'index'),
    (6, 'stock'),
    (7, 'fund'),
    (8, 'trust');

-- dim_country: ISO 3166-1 alpha-2 country codes
CREATE TABLE IF NOT EXISTS gold.dim_country (
    country_sk   SMALLINT PRIMARY KEY,
    country_code VARCHAR(4) NOT NULL UNIQUE
);

INSERT OR IGNORE INTO gold.dim_country VALUES
    (1, 'US'), (2, 'GB'), (3, 'CA'), (4, 'AU'), (5, 'DE'),
    (6, 'FR'), (7, 'JP'), (8, 'CN'), (9, 'HK'), (10, 'SG'),
    (11, 'IN'), (12, 'KR'), (13, 'TW'), (14, 'BR'), (15, 'MX'),
    (16, 'IT'), (17, 'ES'), (18, 'NL'), (19, 'SE'), (20, 'CH'),
    (21, 'NO'), (22, 'DK'), (23, 'FI'), (24, 'BE'), (25, 'AT'),
    (26, 'PT'), (27, 'IE'), (28, 'NZ'), (29, 'ZA'), (30, 'RU'),
    (31, 'PL'), (32, 'CZ'), (33, 'HU'), (34, 'GR'), (35, 'TR'),
    (36, 'IL'), (37, 'AE'), (38, 'SA'), (39, 'EG'), (40, 'NG'),
    (41, 'AR'), (42, 'CL'), (43, 'CO'), (44, 'PE'), (45, 'VE'),
    (46, 'ID'), (47, 'MY'), (48, 'TH'), (49, 'PH'), (50, 'VN'),
    (51, 'PK'), (52, 'BD'), (53, 'LK'), (54, 'MM'), (55, 'KH'),
    (56, 'KE'), (57, 'GH'), (58, 'TZ'), (59, 'UG'), (60, 'ET'),
    (61, 'MA'), (62, 'DZ'), (63, 'TN'), (64, 'LY'), (65, 'SD'),
    (66, 'UA'), (67, 'RO'), (68, 'BG'), (69, 'RS'), (70, 'HR'),
    (71, 'SK'), (72, 'SI'), (73, 'EE'), (74, 'LV'), (75, 'LT'),
    (76, 'BY'), (77, 'KZ'), (78, 'UZ'), (79, 'AZ'), (80, 'GE'),
    (81, 'AM'), (82, 'CY'), (83, 'MT'), (84, 'LU'), (85, 'LI'),
    (86, 'IS'), (87, 'MK'), (88, 'AL'), (89, 'BA'), (90, 'ME'),
    (91, 'XK'), (92, 'MD'), (93, 'MN'), (94, 'KG'), (95, 'TJ'),
    (96, 'TM'), (97, 'AF'), (98, 'IQ'), (99, 'IR'), (100, 'SY'),
    (101, 'LB'), (102, 'JO'), (103, 'KW'), (104, 'BH'), (105, 'QA'),
    (106, 'OM'), (107, 'YE'), (108, 'PA'), (109, 'CR'), (110, 'GT'),
    (111, 'HN'), (112, 'SV'), (113, 'NI'), (114, 'DO'), (115, 'CU'),
    (116, 'JM'), (117, 'TT'), (118, 'HT'), (119, 'PR'), (120, 'EC'),
    (121, 'BO'), (122, 'PY'), (123, 'UY'), (124, 'GY'), (125, 'SR'),
    (126, 'ZW'), (127, 'ZM'), (128, 'BW'), (129, 'NA'), (130, 'MZ'),
    (131, 'AO'), (132, 'CM'), (133, 'SN'), (134, 'CI'), (135, 'MU'),
    (136, 'RE'), (137, 'MW'), (138, 'RW'), (139, 'UNK');

-- dim_exchange: major stock exchange identifiers
CREATE TABLE IF NOT EXISTS gold.dim_exchange (
    exchange_sk   SMALLINT PRIMARY KEY,
    exchange_code VARCHAR(24) NOT NULL UNIQUE
);

INSERT OR IGNORE INTO gold.dim_exchange VALUES
    (1, 'NASDAQ'), (2, 'NYSE'), (3, 'AMEX'), (4, 'NYSE ARCA'), (5, 'NYSE MKT'),
    (6, 'LSE'), (7, 'TSX'), (8, 'TSXV'), (9, 'ASX'), (10, 'XETRA'),
    (11, 'EURONEXT'), (12, 'SIX'), (13, 'JSE'), (14, 'NSE'), (15, 'BSE'),
    (16, 'HKEX'), (17, 'SSE'), (18, 'SZSE'), (19, 'TSE'), (20, 'KRX'),
    (21, 'TWSE'), (22, 'SGX'), (23, 'BURSA'), (24, 'SET'), (25, 'IDX'),
    (26, 'PSE'), (27, 'HOSE'), (28, 'NZX'), (29, 'BME'), (30, 'BORSA'),
    (31, 'WARSAW'), (32, 'PRAGUE'), (33, 'BUDAPEST'), (34, 'ATHENS'), (35, 'OSLO'),
    (36, 'STOCKHOLM'), (37, 'HELSINKI'), (38, 'COPENHAGEN'), (39, 'BRUSSELS'), (40, 'AMSTERDAM'),
    (41, 'LISBON'), (42, 'DUBLIN'), (43, 'VIENNA'), (44, 'MILAN'), (45, 'PARIS'),
    (46, 'FRANKFURT'), (47, 'ZURICH'), (48, 'TADAWUL'), (49, 'DFM'), (50, 'ADX'),
    (51, 'BVB'), (52, 'BOVESPA'), (53, 'BMV'), (54, 'BCS'), (55, 'OTC'),
    (56, 'PINK'), (57, 'OTCBB'), (58, 'UNKNOWN');

-- dim_sector: 11 GICS sectors
CREATE TABLE IF NOT EXISTS gold.dim_sector (
    sector_sk SMALLINT PRIMARY KEY,
    sector    VARCHAR  NOT NULL UNIQUE
);

INSERT OR IGNORE INTO gold.dim_sector VALUES
    (1,  'Basic Materials'),
    (2,  'Communication Services'),
    (3,  'Consumer Cyclical'),
    (4,  'Consumer Defensive'),
    (5,  'Energy'),
    (6,  'Financial Services'),
    (7,  'Healthcare'),
    (8,  'Industrials'),
    (9,  'Real Estate'),
    (10, 'Technology'),
    (11, 'Utilities'),
    (12, 'Unknown');

-- dim_industry: common FMP industry strings (not exhaustive; new values resolved at Gold build time)
CREATE TABLE IF NOT EXISTS gold.dim_industry (
    industry_sk SMALLINT PRIMARY KEY,
    industry    VARCHAR  NOT NULL UNIQUE
);

INSERT OR IGNORE INTO gold.dim_industry VALUES
    (1,  'Aerospace & Defense'),
    (2,  'Agricultural Inputs'),
    (3,  'Airlines'),
    (4,  'Airports & Air Services'),
    (5,  'Aluminum'),
    (6,  'Asset Management'),
    (7,  'Auto Manufacturers'),
    (8,  'Auto Parts'),
    (9,  'Auto & Truck Dealerships'),
    (10, 'Banks—Diversified'),
    (11, 'Banks—Regional'),
    (12, 'Beverages—Alcoholic'),
    (13, 'Beverages—Brewers'),
    (14, 'Beverages—Non-Alcoholic'),
    (15, 'Beverages—Wineries & Distilleries'),
    (16, 'Biotechnology'),
    (17, 'Broadcasting'),
    (18, 'Building Materials'),
    (19, 'Building Products & Equipment'),
    (20, 'Business Equipment & Supplies'),
    (21, 'Capital Markets'),
    (22, 'Chemicals'),
    (23, 'Coal'),
    (24, 'Communication Equipment'),
    (25, 'Computer Hardware'),
    (26, 'Conglomerates'),
    (27, 'Consulting Services'),
    (28, 'Consumer Electronics'),
    (29, 'Copper'),
    (30, 'Credit Services'),
    (31, 'Department Stores'),
    (32, 'Diagnostics & Research'),
    (33, 'Discount Stores'),
    (34, 'Drug Manufacturers—General'),
    (35, 'Drug Manufacturers—Specialty & Generic'),
    (36, 'Education & Training Services'),
    (37, 'Electrical Equipment & Parts'),
    (38, 'Electronic Components'),
    (39, 'Electronic Gaming & Multimedia'),
    (40, 'Electronics & Computer Distribution'),
    (41, 'Engineering & Construction'),
    (42, 'Entertainment'),
    (43, 'Farm & Heavy Construction Machinery'),
    (44, 'Farm Products'),
    (45, 'Financial Data & Stock Exchanges'),
    (46, 'Food Distribution'),
    (47, 'Footwear & Accessories'),
    (48, 'Furnishings, Fixtures & Appliances'),
    (49, 'Gambling'),
    (50, 'Gold'),
    (51, 'Grocery Stores'),
    (52, 'Health Information Services'),
    (53, 'Healthcare Plans'),
    (54, 'Home Improvement Retail'),
    (55, 'Household & Personal Products'),
    (56, 'Industrial Distribution'),
    (57, 'Industrial Metals & Minerals'),
    (58, 'Information Technology Services'),
    (59, 'Insurance—Diversified'),
    (60, 'Insurance—Life'),
    (61, 'Insurance—Property & Casualty'),
    (62, 'Insurance—Reinsurance'),
    (63, 'Insurance—Specialty'),
    (64, 'Integrated Freight & Logistics'),
    (65, 'Internet Content & Information'),
    (66, 'Internet Retail'),
    (67, 'Leisure'),
    (68, 'Lodging'),
    (69, 'Lumber & Wood Production'),
    (70, 'Luxury Goods'),
    (71, 'Marine Shipping'),
    (72, 'Medical Care Facilities'),
    (73, 'Medical Devices'),
    (74, 'Medical Distribution'),
    (75, 'Medical Instruments & Supplies'),
    (76, 'Metal Fabrication'),
    (77, 'Mortgage Finance'),
    (78, 'Oil & Gas Drilling'),
    (79, 'Oil & Gas E&P'),
    (80, 'Oil & Gas Equipment & Services'),
    (81, 'Oil & Gas Integrated'),
    (82, 'Oil & Gas Midstream'),
    (83, 'Oil & Gas Refining & Marketing'),
    (84, 'Other Industrial Metals & Mining'),
    (85, 'Other Precious Metals & Mining'),
    (86, 'Packaged Foods'),
    (87, 'Packaging & Containers'),
    (88, 'Paper & Paper Products'),
    (89, 'Personal Services'),
    (90, 'Pharmaceutical Retailers'),
    (91, 'Pollution & Treatment Controls'),
    (92, 'Publishing'),
    (93, 'REIT—Diversified'),
    (94, 'REIT—Healthcare Facilities'),
    (95, 'REIT—Hotel & Motel'),
    (96, 'REIT—Industrial'),
    (97, 'REIT—Mortgage'),
    (98, 'REIT—Office'),
    (99, 'REIT—Residential'),
    (100, 'REIT—Retail'),
    (101, 'REIT—Specialty'),
    (102, 'Railroads'),
    (103, 'Real Estate—Development'),
    (104, 'Real Estate—Diversified'),
    (105, 'Real Estate Services'),
    (106, 'Recreational Vehicles'),
    (107, 'Rental & Leasing Services'),
    (108, 'Residential Construction'),
    (109, 'Resorts & Casinos'),
    (110, 'Restaurants'),
    (111, 'Scientific & Technical Instruments'),
    (112, 'Security & Protection Services'),
    (113, 'Semiconductor Equipment & Materials'),
    (114, 'Semiconductors'),
    (115, 'Shell Companies'),
    (116, 'Silver'),
    (117, 'Software—Application'),
    (118, 'Software—Infrastructure'),
    (119, 'Solar'),
    (120, 'Specialty Business Services'),
    (121, 'Specialty Chemicals'),
    (122, 'Specialty Industrial Machinery'),
    (123, 'Specialty Retail'),
    (124, 'Staffing & Employment Services'),
    (125, 'Steel'),
    (126, 'Telecom Services'),
    (127, 'Textile Manufacturing'),
    (128, 'Thermal Coal'),
    (129, 'Tobacco'),
    (130, 'Tools & Accessories'),
    (131, 'Travel Services'),
    (132, 'Trucking'),
    (133, 'Uranium'),
    (134, 'Utilities—Diversified'),
    (135, 'Utilities—Independent Power Producers'),
    (136, 'Utilities—Regulated Electric'),
    (137, 'Utilities—Regulated Gas'),
    (138, 'Utilities—Regulated Water'),
    (139, 'Utilities—Renewable'),
    (140, 'Waste Management'),
    (141, 'Unknown');
