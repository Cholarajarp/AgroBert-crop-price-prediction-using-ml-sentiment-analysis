# AgroBert Crop Price Prediction using ML & Sentiment Analysis

A multilingual agricultural web application that provides crop price predictions, weather insights, and farming recommendations using machine learning and sentiment analysis.

## Features

- 🌾 **Crop Price Prediction**: AI-powered price forecasting for various agricultural commodities with detailed breakdown (average, minimum, maximum prices)
- 🌦️ **Weather Integration**: Real-time weather data and its impact on crops
- 💬 **Multilingual Support**: Available in English, Hindi (हिंदी), and Kannada (ಕನ್ನಡ)
- 🤖 **AI Chatbot**: Intelligent assistant for farming queries with voice input support
- 📊 **Sentiment Analysis**: Market sentiment analysis from agricultural news for better decision making
- 🌱 **Crop Recommendations**: Smart crop suggestions based on soil type, rainfall, pH, and temperature
- 📍 **Regional Analysis**: Crop analysis across different Indian regions with interactive heatmap
- 💰 **Price Alerts**: Get notifications when commodity prices reach your target levels
- 📊 **Model Performance Metrics**: View ARIMA baseline vs AgroBERT AI model performance with improvement percentage
- 🔄 **Commodity Comparison**: Compare price trends of multiple commodities side-by-side
- 📄 **PDF Report Generation**: Generate detailed reports with price predictions and analysis
- 🔄 **Data Synchronization**: Sync agricultural data from multiple sources (Agmarknet, OpenWeather, FAOSTAT)

## Technology Stack

- **Backend**: Python Flask
- **Security**: JWT Authentication
- **APIs**: RESTful architecture
- **External Services**: Twilio for OTP
- **Environment**: Python virtual environment

## Getting Started

### Prerequisites

- Python 3.x
- Git

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Cholarajarp/AgroBert-crop-price-prediction-using-ml-sentiment-analysis.git
   cd AgroBert-crop-price-prediction-using-ml-sentiment-analysis
   ```

2. Create and activate virtual environment:
   ```bash
   python -m venv venv
   # On Windows
   .\venv\Scripts\activate
   # On Unix/MacOS
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create `.env` file with required environment variables:
   ```
   JWT_SECRET_KEY=your_jwt_secret
   TWILIO_ACCOUNT_SID=your_twilio_sid
   TWILIO_AUTH_TOKEN=your_twilio_token
   TWILIO_PHONE_NUMBER=your_twilio_phone
   ```

5. Run the application:
   ```bash
   python app.py
   ```

## API Endpoints

### Authentication
- `POST /api/login` - User login
- `POST /api/register` - New user registration
- `POST /api/send-otp` - Send OTP for password reset
- `POST /api/reset-password` - Reset password using OTP

### Core Features
- `POST /api/predict` - Get crop price predictions with detailed breakdown
- `POST /api/analyze-sentiment` - Analyze market sentiment from news
- `GET /api/weather` - Get weather information for selected market
- `POST /api/recommend-crop` - Get crop recommendations based on soil/weather
- `GET /api/news` - Get latest agricultural news
- `POST /api/chat` - Interact with AI chatbot
- `GET /api/model-performance` - Get model performance metrics (ARIMA vs AgroBERT)
- `GET /api/heatmap-data` - Get regional price data for heatmap visualization
- `POST /api/set-price-alert` - Create price alert for commodity

## Features in Detail

### Price Prediction
- Historical data analysis with trend visualization
- Market trend consideration across multiple APMC markets
- XAI (Explainable AI) insights showing key price drivers
- Detailed price breakdown (average, minimum, maximum per quintal and per kg)
- 7-365 day ahead predictions

### Sentiment Analysis
- Real-time news sentiment extraction using BERT
- Positive/Negative/Neutral classification
- Sentiment score calculation
- Impact analysis on commodity prices

### Weather Integration
- Real-time temperature and condition monitoring
- Location-based weather data
- Crop-specific impact analysis
- Historical weather trends

### Crop Recommendations
- Soil type analysis (Alluvial, Black, Red, Laterite)
- Rainfall requirements consideration
- pH level optimization
- Temperature requirements matching
- Regional suitability assessment

### Regional Analysis
- Interactive India state-level price heatmap
- Market comparison across 180+ mandis
- Regional trend analysis
- State-wise commodity performance

### Model Performance
- ARIMA Baseline model comparison
- AgroBERT (AI + Sentiment) advanced model
- RMSE (Root Mean Squared Error) metrics
- Improvement percentage visualization
- Real-time performance tracking

### Multilingual Support
- English (en) - Full support
- Hindi (hi) - हिंदी भाषा समर्थन
- Kannada (kn) - ಕನ್ನಡ ಭಾಷೆ ಬೆಂಬಲ
- Currency formatting in locale-specific format
- Language-specific number and date formatting

### Chatbot Capabilities
- Price inquiries for any commodity and market
- Weather updates and impact analysis
- Crop recommendations
- Market trend analysis
- Voice input support (English, Hindi, Kannada)
- Multi-turn conversation support

## Security Features

- JWT-based authentication
- Password hashing
- OTP verification
- Secure session management

## Recent Updates (v2.0)

### UI/UX Improvements
- Enhanced result box formatting with proper text wrapping
- Price display with Indian number formatting (₹2,370 format)
- Improved crop recommendation box layout
- Better sentiment analysis display

### New Features Added
- **Price Alerts**: Set and receive notifications for target prices
- **Commodity Comparison**: Side-by-side price trend comparison
- **Data Sync**: Manual data synchronization from all sources
- **Model Performance Dashboard**: View baseline vs AI model metrics
- **Regional Heatmap**: Interactive visualization of state-wise prices

### Performance Metrics
- ARIMA (Baseline) model RMSE tracking
- AgroBERT (AI + Sentiment) RMSE display
- Improvement percentage calculation and visualization
- Real-time metric updates after predictions

### Localization Enhancements
- Locale-specific currency formatting
- Language-specific number formatting
- Improved Hindi and Kannada translations
- Better character support across UI

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Thanks to all contributors who have helped with the development
- Special thanks to the agricultural community for their valuable feedback
