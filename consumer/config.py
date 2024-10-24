"""
Central place to setup needed config

All config via environment variables for now.
"""
import os

_config_cache = None

class ProducerConfig():
    def __init__(self):
        # Kafka settings
        self.KAFKA_BOOTSTRAP_SERVER = os.environ.get('KAFKA_BOOTSTRAP_SERVER', 'kafka:9092')
        self.KAFKA_TOPIC_DATA = os.environ.get('KAFKA_TOPIC_DATA', 'CryptoData')
        self.KAFKA_TOPIC_PREDICTIONS = os.environ.get('KAFKA_TOPIC_PREDICTIONS', 'CryptoPrediction')
        self.KAFKA_CERT_PATH = os.environ.get('KAFKA_CERT_PATH', None)  # Optional

        # Producer settings
        self.PRODUCER_INTERVAL_SECONDS = int(os.environ.get('PRODUCER_INTERVAL_SECONDS', '60'))
        self.crypto_SYMBOLS = [os.environ.get('crypto_SYMBOLS', 'BTCUSDT')]

        # Alpha Vantage API Key
        self.FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY', 'cqa231pr01qkfes2e360cqa231pr01qkfes2e36g')

        self._check_missing_configs()

    def _check_missing_configs(self):
        required_vars = [
            'KAFKA_BOOTSTRAP_SERVER', 'KAFKA_TOPIC_DATA', 'KAFKA_TOPIC_PREDICTIONS',
            'PRODUCER_INTERVAL_SECONDS', 'crypto_SYMBOLS', 'FINNHUB_API_KEY'
        ]
        missing_vars = [var for var in required_vars if not getattr(self, var)]
        if missing_vars:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

def load_config() -> ProducerConfig:
    global _config_cache
    if not _config_cache:
        _config_cache = ProducerConfig()
    return _config_cache
