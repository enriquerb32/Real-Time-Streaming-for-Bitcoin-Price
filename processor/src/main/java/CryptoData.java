import java.sql.Timestamp;

public class CryptoData {
    public String symbol;
    public Timestamp timestamp;
    public double price;
    public double volume;

    // Constructor
    public CryptoData(String symbol, Timestamp timestamp, double price, double volume) {
        this.symbol = symbol;
        this.timestamp = timestamp;
        this.price = price;
        this.volume = volume;
    }

    // Getters and Setters (if needed)
}
