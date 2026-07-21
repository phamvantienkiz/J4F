import argparse
import logging
from typing import Dict, Iterable, List, Optional

from openai import AzureOpenAI
from sqlalchemy import text
from sqlmodel import Session, create_engine, select

from app.config import settings
from app.models.catalog import Product

logger = logging.getLogger(__name__)


def build_product_text(product: Product) -> str:
    parts = [
        product.name,
        product.display_name,
        product.category,
        product.description,
        product.short_code,
        product.id,
    ]
    if product.metadata_json:
        parts.append(str(product.metadata_json))
    return "\n".join(str(part).strip() for part in parts if part and str(part).strip())


def _client() -> AzureOpenAI:
    if not settings.azure_openai_embed_endpoint:
        raise RuntimeError("AZURE_OPENAI_EMBED_ENDPOINT is required")
    if not settings.azure_openai_embed_api_key:
        raise RuntimeError("AZURE_OPENAI_EMBED_API_KEY is required")
    if not settings.azure_openai_embed_deployment:
        raise RuntimeError("AZURE_OPENAI_EMBED_DEPLOYMENT is required")
    return AzureOpenAI(
        api_key=settings.azure_openai_embed_api_key,
        azure_endpoint=settings.azure_openai_embed_endpoint,
        api_version=settings.azure_openai_embed_api_version,
    )


def _chunks(items: List[Product], size: int) -> Iterable[List[Product]]:
    for index in range(0, len(items), size):
        yield items[index:index + size]


def _vector_literal(values: List[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in values) + "]"


def _update_embedding(session: Session, product: Product, embedding: List[float]) -> None:
    if session.get_bind().dialect.name == "postgresql":
        session.execute(
            text("UPDATE products SET embedding = CAST(:embedding AS vector) WHERE id = :product_id"),
            {"embedding": _vector_literal(embedding), "product_id": product.id},
        )
    else:
        product.embedding = embedding
        session.add(product)


def hydrate_product_vectors(limit: Optional[int] = None, batch_size: int = 32) -> Dict[str, int]:
    engine = create_engine(settings.supabase_db_url, echo=False)
    stats = {"scanned": 0, "encoded": 0, "skipped": 0, "failed": 0}
    client = _client()

    with Session(engine) as session:
        statement = select(Product).order_by(Product.id)
        if limit:
            statement = statement.limit(limit)
        products = list(session.exec(statement).all())
        stats["scanned"] = len(products)

        for batch in _chunks(products, batch_size):
            text_by_product = [(product, build_product_text(product)) for product in batch]
            text_by_product = [(product, value) for product, value in text_by_product if value]
            stats["skipped"] += len(batch) - len(text_by_product)
            if not text_by_product:
                continue

            try:
                response = client.embeddings.create(
                    model=settings.azure_openai_embed_deployment,
                    input=[value for _, value in text_by_product],
                    dimensions=384,
                )
                for product, embedding_data in zip([item[0] for item in text_by_product], response.data):
                    embedding = [float(value) for value in embedding_data.embedding]
                    if len(embedding) != 384:
                        raise RuntimeError(f"Embedding dimension mismatch for product {product.id}: {len(embedding)}")
                    _update_embedding(session, product, embedding)
                    stats["encoded"] += 1
                session.commit()
            except Exception as exc:
                session.rollback()
                stats["failed"] += len(text_by_product)
                logger.exception("Không hydrate được batch embeddings: %s", exc)

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Hydrate product embeddings into Supabase pgvector")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    stats = hydrate_product_vectors(limit=args.limit, batch_size=args.batch_size)
    logger.info("Hoàn tất hydrate vectors: %s", stats)


if __name__ == "__main__":
    main()
