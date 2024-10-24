CREATE TABLE CryptoData (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    volume DECIMAL(10, 6) NOT NULL
);

CREATE TABLE CryptoPrediction (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    prediction_time TIMESTAMP NOT NULL,
    close_price DECIMAL(10, 2) NOT NULL,
    predicted_price DECIMAL(10, 2) NOT NULL
);
