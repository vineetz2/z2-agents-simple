# Agents Simple

A simplified, clean implementation of an AI agent system with just the essentials.

## Features

- **4 Core Agents**:
  - **Router**: LLM-based intelligent routing
  - **Data**: Handles all data operations (search, API calls, file processing)
  - **Code**: Safe Python execution with sandbox
  - **Chat**: General conversation handling

- **Comprehensive Z2Data API Integration**:
  - All Z2Data endpoints implemented
  - Full part details with lifecycle, compliance, risk data
  - Market availability and cross-references
  - Company information and supply chain data

- **Minimal Stack**:
  - Backend: FastAPI with comprehensive Z2Data API client
  - Frontend: React with Vite, TypeScript, and TanStack Table
  - Database: PostgreSQL (3 tables: conversations, messages, system_config)
  - Docker: 2 services (PostgreSQL + Backend)
  - Dependencies: 16 Python packages, focused functionality

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Copy .env.example to .env and add your API keys
cp .env.example .env

# Start with Docker
docker-compose up

# Backend: http://localhost:8003
# Frontend: http://localhost:3001
```

### Option 2: Local Development

```bash
# Backend (with auto-reload for development)
cd backend
pip install -r requirements.txt
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8003

# The --reload flag enables auto-restart when code changes
# This eliminates the need to manually restart the server during development

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

**Note:** The `--reload` flag watches for changes in Python files and automatically restarts the server. This is perfect for development but should not be used in production.

## Environment Variables

Create a `.env` file:

```env
# Required: At least one LLM key
OPENAI_API_KEY=your_key_here
# OR
ANTHROPIC_API_KEY=your_key_here

# Optional: Z2Data API for parts search
Z2_API_KEY=your_z2data_key
Z2_API_URL=https://api.z2data.com

# Database (if not using Docker)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/agentsimple
```

## Z2Data API Endpoints Implementation

All Z2Data API methods are implemented in: **`backend/z2data_client.py`**

| **Endpoint** | **Method Name** | **Test Query** | **Status** |
|-------------|----------------|----------------|------------|
| **GetValidationPart** | `validate_part()` | Internal use for part validation | ✅ Implemented |
| **GetPartDetailsBypartID** | `get_part_details()` | "LM317-W Texas Instruments Incorporated" | ✅ Tested |
| **GetPartDetailsBySearch** | `search_parts()` | "search BAV99" | ✅ Implemented |
| **MarketAvailability** | `get_market_availability()` | "market availability for LM317T" | ✅ Implemented |
| **GetCrossDataByPartId** | `get_cross_references()` | "cross references for LM317" | ✅ Implemented |
| **CompanyValidation** | `validate_company()` | Internal use for company validation | ✅ Implemented |
| **GetCompanyDataDetailsByCompanyID** | `get_company_details()` | "company details Texas Instruments" | ✅ Implemented |
| **GetCompanyLitigationsByCompanyID** | `get_company_litigations()` | "Intel litigation history" | ✅ Implemented |
| **GetCompanySupplyChainByCompanyID** | `get_company_supply_chain()` | "NXP supply chain" | ✅ Implemented |
| **GetAllEventsGrouped** | `get_supply_chain_events()` | "recent supply chain events" | ✅ Implemented |
| **Compliance Data** | `get_compliance_data()` | "RoHS compliance TPS62840" | ✅ Implemented |
| **RoHS Check** | `check_rohs_compliance()` | "RoHS status for BAV99" | ✅ Implemented |

## Project Structure

```
agents-hosted-simple/
├── backend/
│   ├── app.py           # Main application
│   ├── agents_simple.py # Agent orchestration
│   ├── z2data_client.py # ✨ ALL Z2Data API methods (560+ lines)
│   ├── models.py        # Database models
│   └── code_sandbox.py  # Code execution
├── frontend/
│   └── src/
│       ├── App.tsx              # Main React component
│       ├── PartDetailsDisplay.tsx # Comprehensive part details
│       └── TanStackDataTable.tsx # Data table component
├── tests/
│   ├── test_agents.py    # Agent tests
│   └── test_api.py       # API tests
└── docker-compose.yml    # Docker setup
```

## Architecture

```
User → WebSocket/REST → Router Agent → Data/Code/Chat Agent → Response
                            ↓
                     Pattern Matching
                     (No LLM overhead)
```


## API Endpoints

### WebSocket Chat Interface
```javascript
const ws = new WebSocket('ws://localhost:8003/ws/{conversation_id}');
ws.send(JSON.stringify({content: "search for resistors"}));
```

### File Upload & Enrichment
```bash
# Upload CSV/Excel file
curl -X POST http://localhost:8003/api/upload \
  -F "file=@parts.csv"

# Enrich uploaded data
curl -X POST http://localhost:8003/api/enrich \
  -H "Content-Type: application/json" \
  -d '{"uploaded_data": [...], "enrichment_type": "z2data"}'
```


## Admin Panel

Access the admin panel at `http://localhost:8003/admin` to:
- View system statistics
- Configure agent settings
- Monitor active connections
- Clear cache and reset database

## Deployment

```bash
# Production build
docker-compose up -d

# Check health
curl http://localhost:8003/
```

## License

MIT