1. [x] Verify and align database and VectorDB roles across all files, establishing SQLite as the primary database and ChromaDB as the VectorDB for semantic chat history retrieval (ensuring zero product/factory catalog caching in VectorDB) → verify: Design constraints are updated in all specification files.

2. [x] Review and update `Solution/docs/ai/database_and_vectordb_spec.md` to shift ChromaDB's role from catalog indexing to semantic chat/conversation history index → verify: ChromaDB configuration and indexing flow match the new constraint.

3. [x] Update `Solution/docs/ai/system_architecture.md` to ensure real-time BurgerPrints API sourcing is used for all product catalog requests and ChromaDB is used for conversation memory retrieval → verify: Sequence diagram and component description reflect the real-time sourcing flow.

4. [x] Update `Solution/docs/ai/solution_overview.md` to align with the real-time catalog sourcing and ChromaDB-based chat memory retrieval → verify: Solution overview text is consistent with the updated system.

5. [x] Update `Solution/docs/ai/user_flow_and_conversation_flow.md` to align the 3 user scenarios (T-shirt, Hoodie, Margin-based recommendation) with the precise example prompts in `tasks/request.md` → verify: Scenarios match the user-provided prompts exactly.

6. [x] Perform the Pre-Commit Verification Loop on all updated document files → verify: Checks in step 6 of `AGENTS.md` are completed and conventional commits are made.
