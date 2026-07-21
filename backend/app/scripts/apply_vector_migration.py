from sqlalchemy import create_engine, text

from app.config import settings

DDL = [
    "CREATE EXTENSION IF NOT EXISTS vector",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS embedding vector(384)",
    "CREATE INDEX IF NOT EXISTS products_embedding_hnsw_idx ON products USING hnsw (embedding vector_cosine_ops)",
    """
    CREATE INDEX IF NOT EXISTS products_search_tsv_idx
    ON products
    USING gin (
        to_tsvector(
            'simple',
            coalesce(name, '') || ' ' ||
            coalesce(display_name, '') || ' ' ||
            coalesce(category, '') || ' ' ||
            coalesce(description, '')
        )
    )
    """,
]


def apply_vector_migration() -> None:
    engine = create_engine(settings.supabase_db_url, echo=False)
    with engine.begin() as connection:
        for statement in DDL:
            connection.execute(text(statement))


if __name__ == "__main__":
    apply_vector_migration()
    print("migration_applied")
