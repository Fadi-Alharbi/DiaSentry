# ═══════════════════════════════════════════════════════════════
# Stage 1: Build React Vite Frontend
# ═══════════════════════════════════════════════════════════════
FROM node:20-alpine AS build-stage
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ═══════════════════════════════════════════════════════════════
# Stage 2: Python Backend & Static Serving for Hugging Face Spaces
# ═══════════════════════════════════════════════════════════════
FROM python:3.11-slim
WORKDIR /app

# Install build dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code and environment/config files
COPY backend/ ./backend/
COPY README.md ./.env* ./

# Copy built static frontend from Stage 1
COPY --from=build-stage /app/frontend/dist ./frontend/dist

# Hugging Face Spaces default port
EXPOSE 7860

# Environment variables for Hugging Face
ENV PORT=7860
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1

# Start the FastAPI server
CMD ["python", "-m", "backend.main"]
