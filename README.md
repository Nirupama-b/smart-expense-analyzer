# AI-Powered Smart Expense & Receipt Analyzer

**Course:** CS 520: Theory and Practice of Software Engineering (Spring 2026)  
**University:** University of Massachusetts Amherst  

### Team Members
* Dhevdharsan Bhavani Satish Kumar 
* Harshit Katragadda 
* Nirupama Balasubramanian 
* Daniel Kennedy

---

## 📖 Project Overview

**The Problem:** Traditional expense trackers rely heavily on tedious manual data entry or synchronous optical character recognition (OCR). Synchronous OCR blocks server threads, leading to poor performance and a frustrating user experience. Additionally, most standard financial applications only offer historical data without providing proactive insights. 

**The Solution:** We are architecting a full-stack web application that completely automates the extraction, categorization, and predictive forecasting of financial data from unstructured receipt images. By implementing an event-driven, asynchronous data ingestion pipeline and utilizing local machine learning for classification, the system provides a seamless, non-blocking user experience. 

**Community Impact:** This financial tool is specifically designed to serve the Five College community. It provides students, student organizations, and faculty with an efficient, automated way to track limited budgets, manage project funds, or monitor personal daily expenses (such as dining and groceries) without the friction of manual entry.

## ✨ Core Features (MVP)

* **Responsive Client Interface:** Upload unstructured receipt images (JPG/PNG) and view real-time processing status.
* **Asynchronous Data Ingestion:** An API gateway that accepts payloads and offloads computation to background queues, ensuring the main web thread is never blocked.
* **Decentralized Worker Nodes:** Background processing using EasyOCR/Tesseract to extract raw text from image tensors.
* **Semantic Data Categorization:** A local NLP pipeline (e.g., Hugging Face BERT) that automatically classifies noisy OCR output into structured financial buckets (e.g., "Food", "Transport").
* **Analytics Dashboard:** Data visualization layer displaying aggregated historical spending metrics.

*Note: Future phases will introduce predictive financial forecasting and an Agentic AI (ReAct) for natural language database querying.*

## 🛠️ Technology Stack

* **Frontend:** 
* **Backend:** 
* **Infrastructure:** 
* **AI / ML:** EasyOCR, Hugging Face (BERT), Scikit-learn / XGBoost

---
*Detailed setup, installation, and deployment instructions will be added in subsequent sprints.*
