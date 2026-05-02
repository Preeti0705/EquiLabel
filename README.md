# EquiLabel

An AI Fairness Audit Platform that provides an "Algorithmic Nutrition Label" for your machine learning models.

## Features
- **Frontend**: Built with Flutter Web. Features a stunning Nutrition Label, monitoring dashboard, and mock Gemini chat for explanations.
- **Backend**: Built with FastAPI. Provides endpoints for CSV upload, fairness computations (demographic parity, equalized odds, proxies), and streaming LLM explanations.

## Running Locally via Docker Compose

1. Make sure you have Docker and Docker Compose installed.
2. In the root directory, run:
   ```bash
   docker-compose up --build
   ```
3. Wait for the containers to build and start. The frontend (Flutter Web) compilation can take some time.
4. Once running:
   - Access the **Frontend Web App** at: [http://localhost](http://localhost)
   - Access the **Backend API Docs** at: [http://localhost:8000/docs](http://localhost:8000/docs)


