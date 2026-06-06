1. Initialize python virtual environment and configure `uv` package manager in `Product/` directory. → verify: Run `uv --version` and confirm `.venv` directory is created.

2. Create `Product/pyproject.toml` with dependencies for FastAPI, LangGraph, ChromaDB, SQLAlchemy, and Gemini API. → verify: The file exists and specifies packages: `fastapi`, `langgraph`, `chromadb`, `sqlalchemy`, `langchain-google-genai`, `uvicorn`, `pydantic-settings`, and `pytest`.

3. Create the directory structures for `Product/backend/` and `Product/ai/` directories according to the structure layout specification. → verify: Directory paths like `Product/backend/app/api/v1/` and `Product/ai/tools/` exist.

4. Implement SQLite database models (`User`, `UserPreference`, `Conversation`, `Message`, `OrderHistory`) using SQLAlchemy in `Product/backend/app/models/`. → verify: Run a script to initialize the SQLite tables and confirm database schema matches `database_and_vectordb_spec.md`.

5. Implement semantic chat history indexing and recall query logic in `Product/ai/vector_rag.py` using ChromaDB and Gemini embeddings. → verify: Run a test script to insert a message and perform a similarity search query returning the expected result.

6. Implement BurgerPrints API Client Wrapper in `Product/ai/tools.py` for Catalog products, Factory quotes, Shipping options, and Order creation, supporting a toggle `USE_MOCK_API` fallback mode. → verify: Run tests to verify sandbox API calls (or mock responses if key is not configured) retrieve products and create an order with a catalog SKU.

7. Implement the deterministic Python-based pricing engine in `Product/ai/pricing_engine.py` to calculate landed cost, retail suggestions, margins, and shipping SLA risks. → verify: Run unit tests to check calculations for US, EU, and VN shipping destinations.

8. Define the LangGraph `AgentState` TypedDict structure in `Product/ai/state.py`. → verify: State definition contains all fields specified in the agent design specification.

9. Implement the LangGraph node functions (`extract_intent_node`, `clarify_node`, `retrieve_catalog_node`, `calculate_pricing_node`, `rank_and_recommend_node`, `execute_order_node`) in `Product/ai/nodes.py`. → verify: Each node function runs and outputs correct state modifications.

10. Compile the LangGraph workflow state machine with transitions and SQLiteSaver persistence checkpointing in `Product/ai/agent.py`. → verify: Mock execution of the graph shows correct routing from intent extraction to clarification or catalog retrieval nodes.

11. Implement core configuration, security utilities (JWT generation, password hashing) and CORS middleware in `Product/backend/app/core/`. → verify: Test cases for JWT verification and password encryption pass successfully.

12. Create API endpoint routes (`auth.py`, `chat.py`, `order.py`) and dependency injection hooks (`deps.py`) in `Product/backend/app/api/v1/`. → verify: FastAPI application starts and Swagger page `/docs` exposes all REST endpoints.

13. Build intermediate service classes `chat_service.py` and `order_service.py` to orchestrate database operations and LangGraph state invocation. → verify: An API POST request to `/api/v1/chat/message` successfully returns decision-ready recommendations or a clarification question.

14. Create Dockerfile and Docker Compose settings for local deployment. → verify: Running `docker compose build backend` succeeds.

15. Execute the Pre-Commit Verification Loop on the entire backend and AI codebase. → verify: Run `pytest` on all written code and confirm 100% success rate with no linting errors.
