CREATE TABLE IF NOT EXISTS ops.dataset_watermarks (
    domain        VARCHAR NOT NULL,
    source        VARCHAR NOT NULL,
    dataset       VARCHAR NOT NULL,
    discriminator VARCHAR NOT NULL DEFAULT '',
    ticker        VARCHAR NOT NULL DEFAULT '',
    backfill_floor_date DATE,
    PRIMARY KEY (domain, source, dataset, discriminator, ticker)
);
