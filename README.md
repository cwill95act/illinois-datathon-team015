# UIUC Statistics Datathon 2026  
## Call Center Forecasting Project

This project was developed for the **UIUC Statistics Datathon 2026**, focused on forecasting call center workload metrics using time-series modeling techniques.

---

# 📌 Problem Overview

The objective of this project is to **predict intraday call center metrics** at **30-minute intervals** across multiple portfolios.

The model forecasts:

- **Call Volume (Calls Offered)**
- **Customer Care Time (CCT)**
- **Abandon Rate**

Predictions must account for:

- Daily patterns
- Weekly seasonality
- Monthly trends
- Portfolio-level differences
- Non-negative output constraints

The final output is formatted to match the official submission template.

---

# 📂 Repository Structure

```
datathon-project/

│── data/
│   ├── raw/          # Original datasets
│   ├── processed/    # Cleaned datasets
│   └── output/       # Submission-ready forecasts

│── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_feature_engineering.ipynb
│   ├── 03_model_training.ipynb
│   ├── 04_model_evaluation.ipynb
│   └── 05_submission_generation.ipynb

│── models/
│   └── saved_models/

│── visuals/
│   └── plots/

│── README.md

```

## 📊 Data Description

The project uses two primary datasets:

### 1️⃣ Daily Aggregate Data

Contains daily-level statistics:

- Date  
- Call Volume  
- Customer Care Time (CCT)  
- Service Level  
- Abandon Rate  

Used for:

- Trend detection  
- Seasonality modeling  
- Feature engineering  

---

### 2️⃣ Intraday Time-Series Template

Contains:

- Month  
- Day  
- 30-minute intervals  
- Portfolio-specific placeholders  

Used for:

- Model predictions  
- Submission formatting  

---

## ⚙️ Project Workflow

The project follows a structured modeling workflow:

1. Data exploration  
2. Data cleaning  
3. Feature engineering  
4. Model training  
5. Model evaluation  
6. Forecast generation  
7. Submission formatting  

---

## 🧠 Modeling Approach (Planned)

Initial modeling strategies include:

- Baseline time-shift models  
- Linear regression models  
- Tree-based models (e.g., XGBoost)  
- Time-series feature engineering  
- Lag and rolling window features  

Final models will be selected based on performance metrics and validation results.

---

## 📈 Evaluation Strategy

Models will be evaluated using:

- Mean Absolute Error (MAE)  
- Root Mean Squared Error (RMSE)  
- Forecast accuracy across portfolios  
- Stability across time intervals  

---

## 🏆 Results

**🥈 2nd Place — UIUC Statistics Datathon 2026 (Synchrony Datathon)**

---

👥 Team

Chris Williams
Trustan Price
Chidera Ibe
Daryl Okeke

---

🛠️ Tools & Technologies

Planned tools include:

Python
Pandas
NumPy
Scikit-learn
XGBoost
Matplotlib / Seaborn
Jupyter Notebook

---

---

## 📦 Output

The final submission will generate:

forecast_v01.csv
This file contains:

Predicted call volume
Predicted CCT
Predicted abandon rate

At 30-minute intervals.
---
# illinois-datathon-team015
# Illinois Datathon - Team 015

## 📊 Competition Slides

- [2026 Synchrony Datathon Kickoff Presentation](./Competition_Slides/2026%20Synchrony%20Datathon%20Kickoff%20Presentation.pdf)
- [2026 Datathon Schedule & Sponsors](./Competition_Slides/2026%20Datathon%20Schedule%2BSponsor.pdf)
