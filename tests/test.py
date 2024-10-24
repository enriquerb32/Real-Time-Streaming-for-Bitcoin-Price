import pytest
from unittest.mock import MagicMock, patch
import json
from datetime import datetime
from producer.producer import create_topics, create_producer, on_message, generate_prediction, delivery_report

@pytest.fixture
def mock_admin_client(mocker):
    return mocker.patch('producer.producer.KafkaAdminClient')

@pytest.fixture
def mock_logger(mocker):
    return mocker.patch('producer.producer.logger')

@pytest.fixture
def mock_producer(mocker):
    return mocker.patch('producer.producer.KafkaProducer')

@pytest.fixture
def mock_sleep(mocker):
    return mocker.patch('producer.producer.time.sleep', return_value=None)

@pytest.fixture
def mock_producer(mocker):
    return mocker.patch('producer.producer.producer')

def test_create_topics(mock_admin_client, mock_logger):
    mock_client = MagicMock()
    mock_admin_client.return_value = mock_client
    mock_client.list_topics.return_value = []

    create_topics()

    mock_client.create_topics.assert_called_once()
    mock_logger.info.assert_called_with('Kafka client closed.')

def test_create_producer_success(mock_sleep, mock_producer):
    mock_producer = MagicMock()
    mock_producer.return_value = mock_producer

    producer = create_producer('localhost:9092')

    assert producer == mock_producer
    mock_sleep.assert_not_called()

def test_create_producer_failure(mock_logger, mock_sleep, mock_producer):
    mock_producer.side_effect = Exception('Kafka producer creation failed')

    with pytest.raises(Exception, match='Failed to create Kafka producer after several attempts'):
        create_producer('localhost:9092')

    assert mock_sleep.call_count == 5
    assert mock_logger.error.call_count == 5

def test_on_message(mock_logger, mock_producer):
    mock_ws = MagicMock()
    message = json.dumps({
        'type': 'trade',
        'data': [{
            's': 'BTCUSD',
            't': 1625234873000,
            'p': 34000.0,
            'v': 0.5
        }]
    })

    on_message(mock_ws, message)

    mock_producer.send.assert_called_once()
    mock_logger.info.assert_called()

def test_generate_prediction(mock_logger, mock_producer):
    mock_producer.send.return_value = MagicMock(add_callback=MagicMock(), add_errback=MagicMock())
    latest_trade_data = {
        'BTCUSD': {
            'symbol': 'BTCUSD',
            'timestamp': datetime.now().strftime('%Y_%m_%d %H:%M:%S'),
            'price': 34000.0,
            'volume': 0.5
        }
    }

    with patch.dict('producer.producer.latest_trade_data', latest_trade_data, clear=True):
        generate_prediction()

        assert mock_producer.send.called
        mock_logger.info.assert_called()
