# ATLAS — AI Trust & Observability Platform

ATLAS is a full-stack AI reliability monitoring system designed for LLM-based applications.

It introduces observability into AI systems by measuring trust scores, risk signals, and reliability trends over time.

---

## 🧠 Problem

Most LLM applications generate responses but do not measure:

- Hallucination risk
- Response reliability
- Trust score drift over time
- Enterprise risk signals

ATLAS solves this by acting as an AI observability layer.

---

## 🏗 Architecture Overview

User → Chat API → LLM  
                      ↘  
               Evaluation Engine → ATLAS → Dashboard  

ATLAS evaluates responses and tracks reliability metrics in real time.

---

## 📊 Key Features

- Trust Score (0–100)
- Block / Warn Rate Tracking
- 7-Day Trust Trend Visualization
- Evaluation Logging API
- Weekly Performance Analysis
- PostgreSQL Storage
- Dockerized Setup

---

## 🛠 Tech Stack

Backend:
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL

Frontend:
- Next.js 16
- Prisma 7
- TypeScript
- TailwindCSS

Infrastructure:
- Docker
- REST API Architecture

---

## 📂 Repository Structure
