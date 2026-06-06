- [x] 1. Initialize python virtual environment and configure `uv` package manager in `Product/` directory. → verify: Run `uv --version` and confirm `.venv` directory is created.

- [x] 2. Create `Product/pyproject.toml` with dependencies for FastAPI, LangGraph, ChromaDB, SQLAlchemy, and Gemini API. → verify: The file exists and specifies packages: `fastapi`, `langgraph`, `chromadb`, `sqlalchemy`, `langchain-google-genai`, `uvicorn`, `pydantic-settings`, and `pytest`.

- [x] 3. Create the directory structures for `Product/backend/` and `Product/ai/` directories according to the structure layout specification. → verify: Directory paths like `Product/backend/app/api/v1/` and `Product/ai/tools/` exist.

- [x] 4. Implement SQLite database models (`User`, `UserPreference`, `Conversation`, `Message`, `OrderHistory`) using SQLAlchemy in `Product/backend/app/models/`. → verify: Run a script to initialize the SQLite tables and confirm database schema matches `database_and_vectordb_spec.md`.

- [x] 5. Implement semantic chat history indexing and recall query logic in `Product/ai/vector_rag.py` using ChromaDB and Gemini embeddings. → verify: Run a test script to insert a message and perform a similarity search query returning the expected result.

- [x] 6. Implement BurgerPrints API Client Wrapper in `Product/ai/tools.py` for Catalog products, Factory quotes, Shipping options, and Order creation, supporting a toggle `USE_MOCK_API` fallback mode. → verify: Run tests to verify sandbox API calls (or mock responses if key is not configured) retrieve products and create an order with a catalog SKU.

- [x] 7. Implement the deterministic Python-based pricing engine in `Product/ai/pricing_engine.py` to calculate landed cost, retail suggestions, margins, and shipping SLA risks. → verify: Run unit tests to check calculations for US, EU, and VN shipping destinations.

- [x] 8. Define the LangGraph `AgentState` TypedDict structure in `Product/ai/state.py`. → verify: State definition contains all fields specified in the agent design specification.

- [x] 9. Implement the LangGraph node functions (`extract_intent_node`, `clarify_node`, `retrieve_catalog_node`, `calculate_pricing_node`, `rank_and_recommend_node`, `execute_order_node`) in `Product/ai/nodes.py`. → verify: Each node function runs and outputs correct state modifications.

- [x] 10. Compile the LangGraph workflow state machine with transitions and SQLiteSaver persistence checkpointing in `Product/ai/agent.py`. → verify: Mock execution of the graph shows correct routing from intent extraction to clarification or catalog retrieval nodes.

- [x] 11. Implement core configuration, security utilities (JWT generation, password hashing) and CORS middleware in `Product/backend/app/core/`. → verify: Test cases for JWT verification and password encryption pass successfully.

- [x] 12. Create API endpoint routes (`auth.py`, `chat.py`, `order.py`) and dependency injection hooks (`deps.py`) in `Product/backend/app/api/v1/`. → verify: FastAPI application starts and Swagger page `/docs` exposes all REST endpoints.

- [x] 13. Build intermediate service classes `chat_service.py` and `order_service.py` to orchestrate database operations and LangGraph state invocation. → verify: An API POST request to `/api/v1/chat/message` successfully returns decision-ready recommendations or a clarification question.

- [x] 14. Create Dockerfile and Docker Compose settings for local deployment. → verify: Dockerfile and Docker Compose files are present and match settings.

- [x] 15. Execute the Pre-Commit Verification Loop on the entire backend and AI codebase. → verify: Run `pytest` on all written code and confirm 100% success rate with no linting errors.

- [x] 16. Initialize frontend Vite project with React and TypeScript in `Product/frontend/`. → verify: Confirm files `package.json`, `tsconfig.json` and `vite.config.ts` are generated in the `Product/frontend/` directory.

- [x] 17. Configure `package.json` with scripts for `dev`, `build`, and `preview`, and install npm dependencies (`axios`, `lucide-react`, `canvas-confetti`, `@types/canvas-confetti` as devDependencies). → verify: Run `npm install` and confirm `node_modules/` is created without dependency conflicts.

- [x] 18. Create global stylesheet `src/index.css` with CSS variables for the color system (Navy backdrop, electric blue, neon violet), Outfit & Inter fonts, and glassmorphic utility classes. → verify: Import CSS in entry point and verify no syntax errors during Vite compilation.

- [x] 19. Implement API Client with Axios at `src/services/api.ts` including interceptors to automatically attach stored JWT access tokens to authorization headers. → verify: Inspect request headers on outgoing requests to confirm `Authorization: Bearer <token>` is sent.

- [x] 20. Implement Authentication Context and a simple Login/Register UI with validation, blurred backdrop overlay, and local storage token management. → verify: Log in with mock credentials and confirm the token is successfully saved to `localStorage` and modal hides.

- [x] 21. Implement Left Sidebar component displaying "New Chat" button, dynamic historical session list grouped by date, and User Preference modal. → verify: Confirm clicking "New Chat" calls API to create a new session and preference updates write back to SQLite via FastAPI `/api/v1/auth/preference`.

- [x] 22. Implement Center Panel Chat component with auto-scroll and markdown parsing. Integrate a dynamic HTML/React candidate comparison table, highlighting Option 1 as "RECOMMENDED". → verify: Send a product query and check that the comparison table renders with correct highlight, color coding, and selectable rows.

- [x] 23. Implement Right Panel displaying mockup images, product information specifications, and the checkout Order HUD. → verify: Confirm details dynamically update when selecting a quote option, and calculations show correct landed cost breakdown.

- [x] 24. Implement Order Confirmation and success animations (Confetti) upon clicking "Confirm Fulfillment Order" via `POST /api/v1/order/confirm`. → verify: Confirm clicking CTA submits the order draft, locks the button, triggers confetti, and prints the generated Order ID and tracking details.

- [x] 25. Perform full end-to-end integration and run tests verifying user registration, profile preference updates, multi-turn AI consultation, option selection, and successful order execution. → verify: Complete a standard user journey from login to final order receipt, checking for zero console errors and correct database persistence.

- [x] 26. Update Gemini chat/reasoning model to "gemini-3.1-flash-lite" in `Product/ai/nodes.py`. → verify: Run content generation test with client and see it doesn't fail.

- [x] 27. Configure ChromaDB embedding model to "gemini-embedding-2" (3072 dimensions) and update fallback embedding logic in `Product/ai/vector_rag.py`. → verify: Embedding calls return 3072-dimensional vectors.

- [x] 28. Fix test isolation in `Product/tests/test_api.py` using dynamic emails and update mock queries in `Product/tests/test_agent.py` to stabilize tests under real LLM execution. → verify: Run `py.test.exe` and confirm all tests pass successfully.

- [x] 29. Define global `flex-col` utilities in `Product/frontend/src/index.css`. → verify: Confirm `.flex-col` class is added with `display: flex; flex-direction: column;`.

- [x] 30. Optimize `.col-chat` column styling in `Product/frontend/src/App.css` to prevent layout expansion. → verify: Confirm `.col-chat` has `min-width: 0;` and `overflow: hidden;`.

- [x] 31. Correct `.chat-area` and `.chat-messages` flex dimensions in `Product/frontend/src/components/ChatArea.css`. → verify: Confirm `.chat-messages` scroll vertically and input box remains visible at the bottom of the screen.

- [x] 32. Adjust width limits on chat bubbles containing large tables in `Product/frontend/src/components/ChatArea.css`. → verify: Boulders containing tables expand to full width if needed, table wrapper handles overflow scroll horizontally, and no panels are pushed offscreen.

- [x] 33. Import `Be Vietnam Pro` font and redefine variables for BurgerPrints brand identity (Orange primary, Blue secondary) in `Product/frontend/src/index.css`. → verify: Confirm custom theme styles apply and use brand orange `#FF5B00` and blue `#0052CC`.

- [x] 34. Implement Light Mode CSS variables using `:root[data-theme="light"]` in `Product/frontend/src/index.css`. → verify: Verify color properties like text, backgrounds, and borders adapt correctly when attribute is toggled.

- [x] 35. Implement theme state management and add a Sun/Moon theme toggle button to the Sidebar header in `Product/frontend/src/components/Sidebar.tsx`. → verify: Toggle button functions, switches layout theme dynamically, and preserves preferences in `localStorage`.

- [x] 36. Refine UI elements across components for optimal contrast and readability in Light Mode. → verify: Check that login modal, tables, inspector, and chat area maintain professional contrast and glassmorphism.

- [x] 37. Refine dynamic color gradients and buttons in CSS files for high-contrast Light Mode. → verify: Gradients (welcome text h2, primary CTA buttons) remain clear and readable on light backgrounds.

- [x] 38. Resolve style conflicts on tables, inputs, chips, and overlays for Light Mode. → verify: Table recommended highlights, active state indicators, overlay backdrops, and select options display with clear, accessible contrast (meeting WCAG standards).

- [x] 39. Align brand primary color token to official BurgerPrints orange (#f26522). → verify: Verify variables `--primary` and `--primary-hsl` use the exact brand HSL value `18, 92%, 54%`.

- [x] 40. Correct scrollbar and Landed Cost text invisibility in Light Mode. → verify: Bảng so sánh Landed Cost has legible dark text color (var(--text-primary)), and scrollbars adapt to light backgrounds without blending in.
