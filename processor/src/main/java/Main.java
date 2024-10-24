import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.api.common.functions.MapFunction;
import org.apache.flink.api.common.serialization.SimpleStringSchema;
import org.apache.flink.connector.jdbc.JdbcConnectionOptions;
import org.apache.flink.connector.jdbc.JdbcExecutionOptions;
import org.apache.flink.connector.jdbc.JdbcSink;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.datastream.DataStreamSource;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.connectors.kafka.FlinkKafkaConsumer;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.sql.Timestamp;
import java.util.Properties;

public class Main {

    static final String BROKERS = "kafka:9092";
    static final String POSTGRES_URL = "jdbc:postgresql://postgres:5432/postgres";
    static final String POSTGRES_USER = "postgres";
    static final String POSTGRES_PASSWORD = "postgres";

    public static void main(String[] args) throws Exception {
        final StreamExecutionEnvironment env1 = StreamExecutionEnvironment.getExecutionEnvironment();
        final StreamExecutionEnvironment env2 = StreamExecutionEnvironment.getExecutionEnvironment();

        // Run CryptoPredictionJob
        runCryptoPredictionJob(env1);

        // Run CryptoDataJob
        runCryptoDataJob(env2);

        // Execute the Flink jobs
        env1.execute("Crypto Prediction Job");
        env2.execute("Crypto Data Processing Job");
    }

    private static void runCryptoPredictionJob(StreamExecutionEnvironment env) throws Exception {
        // Set up the Kafka consumer
        Properties properties = new Properties();
        properties.setProperty("bootstrap.servers", "kafka:9092");
        properties.setProperty("group.id", "bitcoin-prediction");

        FlinkKafkaConsumer<String> consumer = new FlinkKafkaConsumer<>(
                "crypto-data",
                new SimpleStringSchema(),
                properties
        );

        DataStream<String> inputStream = env.addSource(consumer);

        DataStream<CryptoPrediction> predictions = inputStream.map(new MapFunction<String, CryptoPrediction>() {
            @Override
            public CryptoPrediction map(String value) throws Exception {
                // Assuming input is JSON formatted with keys: symbol, price, volume, timestamp
                JSONObject json = new JSONObject(value);
                String symbol = json.getString("symbol");
                double price = json.getDouble("price");
                double volume = json.getDouble("volume");
                Timestamp timestamp = Timestamp.valueOf(json.getString("timestamp"));

                // Prepare input for Python script
                JSONObject inputJson = new JSONObject();
                inputJson.put("price", price);
                inputJson.put("volume", volume);

                // Call the Python script
                ProcessBuilder pb = new ProcessBuilder("python3", "./predictor/predictor.py");
                Process process = pb.start();

                // Send input data to the Python script
                process.getOutputStream().write(inputJson.toString().getBytes());
                process.getOutputStream().close();

                // Read the output from the Python script
                BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
                String prediction = reader.readLine();
                reader.close();

                // Create CryptoPrediction object
                double predictedPrice = Double.parseDouble(prediction);
                return new CryptoPrediction(symbol, timestamp, price, predictedPrice);
            }
        });

        // Sink: Insert predictions into PostgreSQL
        predictions.addSink(JdbcSink.sink(
                "INSERT INTO crypto_predictions (symbol, prediction_time, close_price, predicted_price) VALUES (?, ?, ?, ?)",
                (statement, prediction) -> {
                    statement.setString(1, prediction.symbol);
                    statement.setTimestamp(2, prediction.predictionTime);
                    statement.setDouble(3, prediction.closePrice);
                    statement.setDouble(4, prediction.predictedPrice);
                },
                JdbcExecutionOptions.builder()
                        .withBatchSize(1000)
                        .withBatchIntervalMs(200)
                        .withMaxRetries(5)
                        .build(),
                new JdbcConnectionOptions.JdbcConnectionOptionsBuilder()
                        .withUrl(POSTGRES_URL)
                        .withDriverName("org.postgresql.Driver")
                        .withUsername(POSTGRES_USER)
                        .withPassword(POSTGRES_PASSWORD)
                        .build()
        ));
    }

    private static void runCryptoDataJob(StreamExecutionEnvironment env) throws Exception {
        // Kafka source for CryptoData
        KafkaSource<CryptoData> cryptoDataSource = KafkaSource.<CryptoData>builder()
                .setBootstrapServers(BROKERS)
                .setTopics("CryptoData")
                .setGroupId("crypto-data-group")
                .setStartingOffsets(OffsetsInitializer.earliest())
                .setValueOnlyDeserializer(new CryptoDataDeserializationSchema())
                .build();

        DataStreamSource<CryptoData> cryptoDataStream = env.fromSource(cryptoDataSource, WatermarkStrategy.noWatermarks(), "Kafka CryptoData Source");

        cryptoDataStream.addSink(JdbcSink.sink(
                "INSERT INTO CryptoData (symbol, timestamp, price, volume) VALUES (?, ?, ?, ?)",
                (statement, cryptoData) -> {
                    statement.setString(1, cryptoData.symbol);
                    statement.setTimestamp(2, cryptoData.timestamp);
                    statement.setDouble(3, cryptoData.price);
                    statement.setDouble(4, cryptoData.volume);
                },
                JdbcExecutionOptions.builder()
                        .withBatchSize(1000)
                        .withBatchIntervalMs(200)
                        .withMaxRetries(5)
                        .build(),
                new JdbcConnectionOptions.JdbcConnectionOptionsBuilder()
                        .withUrl(POSTGRES_URL)
                        .withDriverName("org.postgresql.Driver")
                        .withUsername(POSTGRES_USER)
                        .withPassword(POSTGRES_PASSWORD)
                        .build()
        ));
    }
}
