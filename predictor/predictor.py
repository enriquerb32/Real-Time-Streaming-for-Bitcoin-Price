import sys
import json
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from xgboost import XGBRegressor
from sqlalchemy import create_engine

def load_data_from_db():
    # Update the connection string with your database credentials
    engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
    query = "SELECT price, volume, timestamp FROM CryptoData ORDER BY timestamp"
    data = pd.read_sql(query, engine)
    return data

def preprocess_data(data, n_lags=3):
    # Create lag features for time series
    for lag in range(1, n_lags + 1):
        data[f'price_lag_{lag}'] = data['price'].shift(lag)
        data[f'volume_lag_{lag}'] = data['volume'].shift(lag)
    
    data.dropna(inplace=True)
    
    features = data[[f'price_lag_{i}' for i in range(1, n_lags + 1)] + 
                    [f'volume_lag_{i}' for i in range(1, n_lags + 1)]]
    target = data['price']
    
    scaler = MinMaxScaler()
    features_scaled = scaler.fit_transform(features)
    return features_scaled, target, scaler

def create_and_train_model(features, target):
    model = XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.1)
    model.fit(features, target)
    return model

def main(input_data, n_lags=3):
    data = load_data_from_db()
    features, target, scaler = preprocess_data(data, n_lags)
    model = create_and_train_model(features, target)
    
    # Prepare the input for prediction
    input_df = pd.DataFrame([input_data])
    for lag in range(1, n_lags + 1):
        input_df[f'price_lag_{lag}'] = input_df['price'].shift(lag)
        input_df[f'volume_lag_{lag}'] = input_df['volume'].shift(lag)
    
    input_df.dropna(inplace=True)
    if input_df.empty:
        raise ValueError("Insufficient data for prediction. Provide enough lags.")
    
    input_scaled = scaler.transform(input_df[[f'price_lag_{i}' for i in range(1, n_lags + 1)] + 
                                              [f'volume_lag_{i}' for i in range(1, n_lags + 1)]])
    
    prediction = model.predict(input_scaled)
    return prediction[0]

if __name__ == "__main__":
    try:
        input_data = json.loads(sys.stdin.read())
        if not input_data:
            raise ValueError("No input data received")
        prediction = main(input_data)
        print(prediction)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
