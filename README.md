# Kaushal-Marg-Prototype

Welcome to the Kaushal Marg prototype repository. This application is an AI-powered pathway and recommendation engine.

## 🚀 Getting Started for Developers

A fresh developer can clone this repository and start the application without manually guessing missing packages. Please follow these steps carefully.

### 1. Prerequisites
- **Python Version**: Python 3.9 or higher is required.
- **Git**: To clone the repository.

### 2. Installation & Environment Setup
It is highly recommended to use a clean virtual environment to prevent dependency conflicts.

```bash
# Clone the repository
git clone <repository_url>
cd Kaushal-Marg-Prototype

# Create a clean virtual environment
python -m venv .venv

# Activate the virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install exact dependencies
pip install -r requirements.txt
```

### 3. Environment Variable Setup
This application utilizes the Gemini API and requires a secure API key.

1. Copy the provided `.env.example` file to create a `.env` file:
   ```bash
   # On Windows:
   copy .env.example .env
   # On macOS/Linux:
   cp .env.example .env
   ```
2. Open the `.env` file and insert your active API key:
   ```env
   GEMINI_API_KEY="your_actual_api_key_here"
   ```
   *Note: The `.env` file is safely ignored by `.gitignore` and will never be committed to the repository.*

### 4. Running the Automated Test Suite
Before running the application, it is good practice to run the master test suite to verify your environment is healthy.

```bash
# Run the master test suite
python tests/run_all_tests.py
```
You should see `SUMMARY: 100% OF ALL MASTER TESTS PASSED!`

### 5. Running the Application Locally
Once dependencies are installed and the API key is configured, start the Streamlit server:

```bash
streamlit run app.py
```
The application will launch automatically in your default web browser (typically at `http://localhost:8501`).

## ☁️ Deployment Instructions (Streamlit Community Cloud)

When deploying this application to Streamlit Community Cloud (or any other hosting provider), **NEVER** commit your `.env` file or hardcode your API key into the source code. 

1. Push this repository to your GitHub account.
2. Log into [Streamlit Community Cloud](https://share.streamlit.io/) and create a new app pointing to your repository.
3. Before clicking "Deploy", click on **Advanced settings**.
4. In the **Secrets** section, configure your environment variables like so:
   ```toml
   GEMINI_API_KEY="your_actual_api_key_here"
   ```
5. Click **Deploy**.

For local development, copy `.env.example` to `.env` and put your key there. The `.env` file is safely ignored by `.gitignore`.