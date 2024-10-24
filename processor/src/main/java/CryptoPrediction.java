import java.sql.Timestamp;

public class CryptoPrediction {
    public String symbol;
    public Timestamp predictionTime;
    public double closePrice;
    public double predictedPrice;

    // Constructor
    public CryptoPrediction(String symbol, Timestamp predictionTime, double closePrice, double predictedPrice) {
        this.symbol = symbol;
        this.predictionTime = predictionTime;
        this.closePrice = closePrice;
        this.predictedPrice = predictedPrice;
    }

    // Getters and Setters (if needed)
}
