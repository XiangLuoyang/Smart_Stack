# Smart_Stack
Test of using AI to predict the stack price.
## Project Structure
smart_stack/
│
├── src/
│   ├── __init__.py
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   └── processor.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── technical.py
│   │   ├── risk.py
│   │   └── prediction.py
│   │
│   ├── visualization/
│   │   ├── __init__.py
│   │   ├── charts.py
│   │   └── reports.py
│   │
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
│
├── data/
│   └── sz100_stocks.csv
│
├── tests/
│   ├── __init__.py
│   ├── test_data.py
│   ├── test_models.py
│   └── test_visualization.py
│
├── main.py
├── requirements.txt
└── README.md
