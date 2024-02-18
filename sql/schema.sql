DROP TABLE IF EXISTS posts;

CREATE TABLE finvars (
    perpetual_growth_rate FLOAT NOT NULL,
    market_return FLOAT NOT NULL,
    PRIMARY KEY (perpetual_growth_rate)
);