import logging
import re
from typing import Any, Dict, List, Optional

from sqlalchemy import or_, text
from sqlmodel import Session, select

from app.config import settings
from app.models.catalog import Product

logger = logging.getLogger(__name__)

RankedProductMatch = Dict[str, Any]


def _contains_word(text_value: str, word: str) -> bool:
    if not text_value or not word:
        return False
    # Thay thế ký tự | và - thành khoảng trắng và chuẩn hóa khoảng trắng để tránh lỗi so khớp word-boundary
    text_clean = re.sub(r'\s+', ' ', text_value.replace("|", " ").replace("-", " ")).strip()
    word_clean = re.sub(r'\s+', ' ', word.replace("|", " ").replace("-", " ")).strip()
    pattern = rf"(?<!\w){re.escape(word_clean)}(?!\w)"
    return bool(re.search(pattern, text_clean, re.UNICODE | re.IGNORECASE))


def _apply_noun_filtering_to_matches(session: Session, query: str, matches: List[RankedProductMatch]) -> List[RankedProductMatch]:
    if not matches:
        return matches

    q_clean = (query or "").strip().lower()
    pants_query_words = ["quần", "quan", "pants", "shorts", "leggings", "pajamas", "pajama", "boxer briefs", "sweatpant", "bottoms"]
    shirt_query_words = ["áo", "ao", "shirt", "t-shirt", "tshirt", "tee", "hoodie", "sweatshirt", "sweater", "tank", "jersey", "onesie", "ba lỗ", "ba lo", "apparel"]
    mug_query_words = ["cốc", "coc", "mug", "mugs", "ly", "tách", "tach"]

    has_pants_query = any(_contains_word(q_clean, w) for w in pants_query_words)
    has_shirt_query = any(_contains_word(q_clean, w) for w in shirt_query_words)
    has_mug_query = any(_contains_word(q_clean, w) for w in mug_query_words)

    # Nếu không có từ khóa phân biệt rõ ràng hoặc có cả áo và quần trong câu query thì không lọc loại trừ
    if not (has_pants_query or has_shirt_query or has_mug_query):
        return matches
    if (has_pants_query + has_shirt_query + has_mug_query) > 1:
        return matches

    product_ids = [ranked_product_id(m) for m in matches]
    products = session.exec(select(Product).where(Product.id.in_(product_ids))).all()
    product_map = {p.id: p for p in products}

    filtered_matches = []
    for m in matches:
        pid = ranked_product_id(m)
        p = product_map.get(pid)
        if not p:
            continue

        name_lower = (p.name or "").lower()
        cat_lower = (p.category or "").lower()

        if has_pants_query:
            is_pants = cat_lower == "bottoms" or any(w in name_lower for w in ["pants", "shorts", "leggings", "pajamas", "pajama", "boxer briefs", "sweatpant", "bottoms", "quần", "quan"])
            is_upper = cat_lower in ["t-shirts", "hoodies", "sweatshirts", "tank tops"] or any(w in name_lower for w in ["tank top", "t-shirt", "tshirt", "hoodie", "sweatshirt", "sweater", "onesie"])
            if is_pants and not is_upper:
                # Xác định các tiểu loại quần trong câu query
                is_long_pants_query = any(_contains_word(q_clean, w) for w in ["dài", "dai", "pajama", "pajamas", "sweatpant", "sweatpants", "leggings", "legging", "long"])
                is_shorts_query = any(_contains_word(q_clean, w) for w in ["short", "shorts", "đùi", "dui"])
                is_boxer_query = any(_contains_word(q_clean, w) for w in ["lót", "lot", "sịp", "sip", "boxer", "boxers"])

                name_has_shorts = any(w in name_lower for w in ["shorts", "short"])
                name_has_boxer = any(w in name_lower for w in ["boxer", "briefs", "underpants"])
                name_has_long = any(w in name_lower for w in ["long pants", "pajamas", "pajama", "sweatpant", "leggings", "legging", "long-sleeve"])

                if is_long_pants_query:
                    if name_has_shorts or name_has_boxer:
                        continue
                    # Lọc chi tiết hơn cho quần dài cụ thể
                    has_pajama_word = any(_contains_word(q_clean, w) for w in ["pajama", "pajamas"])
                    has_leggings_word = any(_contains_word(q_clean, w) for w in ["leggings", "legging"])
                    has_sweatpant_word = any(_contains_word(q_clean, w) for w in ["sweatpant", "sweatpants"])

                    name_has_pajama = any(w in name_lower for w in ["pajama", "pajamas"])
                    name_has_leggings = any(w in name_lower for w in ["leggings", "legging"])
                    name_has_sweatpant = any(w in name_lower for w in ["sweatpant", "sweatpants"])

                    if has_pajama_word and not name_has_pajama:
                        continue
                    if has_leggings_word and not name_has_leggings:
                        continue
                    if has_sweatpant_word and not name_has_sweatpant:
                        continue
                elif is_shorts_query:
                    if name_has_long or name_has_boxer:
                        continue
                elif is_boxer_query:
                    if name_has_long or name_has_shorts:
                        continue
                else:
                    if name_has_boxer:
                        continue

                filtered_matches.append(m)
        elif has_shirt_query:
            is_shirt = cat_lower in ["t-shirts", "hoodies", "sweatshirts", "tank tops"] or any(w in name_lower for w in ["tank top", "jersey", "t-shirt", "tshirt", "tee", "hoodie", "sweatshirt", "sweater", "shirt", "onesie", "áo", "ao", "ba lỗ", "ba lo", "apparel"])
            is_bottom = cat_lower == "bottoms" or any(w in name_lower for w in ["pants", "shorts", "leggings", "pajamas", "pajama", "boxer briefs", "sweatpant", "bottoms"])
            if is_shirt and not is_bottom:
                filtered_matches.append(m)
        elif has_mug_query:
            is_mug = cat_lower == "mugs" or any(w in name_lower for w in ["mug", "mugs", "cốc", "coc", "ly", "tách", "tach"])
            if is_mug:
                filtered_matches.append(m)

    return filtered_matches


def filter_products_by_gender_and_age(query: str, products: List[Product]) -> List[Product]:
    if not products:
        return products

    q_clean = (query or "").strip().lower()

    # Từ khóa xác định nhóm đối tượng trong query
    kids_query_words = ["trẻ em", "tre em", "em bé", "em be", "con nít", "con nit", "kids", "kid", "baby", "youth", "toddler", "child", "children"]
    women_query_words = ["nữ", "nu", "women", "women's", "lady", "lady's", "ladies", "female", "woman", "gái", "gai"]
    men_query_words = ["nam", "men", "men's", "male", "man", "trai"]

    has_kids_query = any(_contains_word(q_clean, w) for w in kids_query_words)
    has_women_query = any(_contains_word(q_clean, w) for w in women_query_words)
    has_men_query = any(_contains_word(q_clean, w) for w in men_query_words)

    # Nếu không có từ khóa giới tính/độ tuổi cụ thể nào, hoặc nếu có nhiều hơn 1 nhóm đối tượng được nhắc đến, không lọc loại trừ
    if not (has_kids_query or has_women_query or has_men_query):
        return products
    if (has_kids_query + has_women_query + has_men_query) > 1:
        return products

    filtered = []
    for p in products:
        name_lower = (p.name or "").lower()
        display_lower = (p.display_name or "").lower()
        desc_lower = (p.description or "").lower()
        cat_lower = (p.category or "").lower()

        # Hàm kiểm tra sự xuất hiện của từ khóa trong thông tin sản phẩm bằng regex để tránh so khớp nhầm (ví dụ "men" trong "women")
        def product_has_word(words: list[str]) -> bool:
            for w in words:
                if (p.name and _contains_word(name_lower, w)) or \
                   (p.display_name and _contains_word(display_lower, w)) or \
                   (p.description and _contains_word(desc_lower, w)) or \
                   (p.category and _contains_word(cat_lower, w)):
                    return True
            return False

        # Định nghĩa các nhãn giới tính/độ tuổi của sản phẩm dựa trên tên/mô tả
        # Sản phẩm có tính chất trẻ em
        is_product_kids = product_has_word(["kids", "kid", "baby", "youth", "toddler", "child", "children", "trẻ em", "em bé"])

        # Sản phẩm có tính chất nữ
        is_product_women = product_has_word(["women", "lady", "lady's", "ladies", "female", "woman", "nữ", "leggings", "skirt", "dress"])

        # Sản phẩm có tính chất nam
        is_product_men = product_has_word(["men", "men's", "male", "nam", "briefs", "boxer", "boxers"])

        # Sản phẩm ghi rõ Unisex
        is_product_unisex = product_has_word(["unisex"])

        if has_kids_query:
            # Nếu tìm đồ trẻ em, chỉ giữ sản phẩm trẻ em
            if is_product_kids:
                filtered.append(p)
        elif has_women_query:
            # Nếu tìm đồ nữ: loại bỏ trẻ em và loại bỏ nam rõ rệt (nam và không phải unisex hay nữ)
            if is_product_kids:
                continue
            if is_product_men and not is_product_unisex and not is_product_women:
                continue
            filtered.append(p)
        elif has_men_query:
            # Nếu tìm đồ nam: loại bỏ trẻ em và loại bỏ nữ rõ rệt (nữ và không phải unisex hay nam)
            if is_product_kids:
                continue
            if is_product_women and not is_product_unisex and not is_product_men:
                continue
            filtered.append(p)

    return filtered


def _apply_gender_age_filtering_to_matches(session: Session, query: str, matches: List[RankedProductMatch]) -> List[RankedProductMatch]:
    if not matches:
        return matches
    product_ids = [ranked_product_id(m) for m in matches]
    products = session.exec(select(Product).where(Product.id.in_(product_ids))).all()

    # Lọc các Product object
    filtered_products = filter_products_by_gender_and_age(query, products)
    filtered_product_ids = {p.id for p in filtered_products}

    # Giữ lại các matches có product_id nằm trong danh sách đã lọc
    return [m for m in matches if ranked_product_id(m) in filtered_product_ids]


def _ranked_match(product_id: str, rrf_score: Optional[float] = None) -> RankedProductMatch:
    match: RankedProductMatch = {"product_id": product_id}
    if rrf_score is not None:
        match["rrf_score"] = round(float(rrf_score), 6)
    return match


def ranked_product_id(match: RankedProductMatch | str) -> str:
    if isinstance(match, dict):
        return str(match["product_id"])
    return str(match)


def ranked_product_score(match: RankedProductMatch | str) -> Optional[float]:
    if isinstance(match, dict) and match.get("rrf_score") is not None:
        return float(match["rrf_score"])
    return None


def _ordered_unique(values: List[str]) -> List[str]:
    seen = set()
    result = []
    for value in values:
        normalized = value.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _keyword_product_ids(session: Session, tokens: Optional[List[str]], limit: int) -> List[RankedProductMatch]:
    stmt = select(Product.id)
    if tokens:
        conditions = []
        for token in tokens:
            pattern = f"%{token}%"
            conditions.extend([
                Product.id.ilike(pattern),
                Product.name.ilike(pattern),
                Product.display_name.ilike(pattern),
                Product.category.ilike(pattern),
                Product.description.ilike(pattern),
            ])
        stmt = stmt.where(or_(*conditions))
    stmt = stmt.limit(limit)
    return [_ranked_match(product_id) for product_id in session.exec(stmt).all()]


def fallback_product_ids(session: Session, limit: int = 50) -> List[RankedProductMatch]:
    return [_ranked_match(product_id) for product_id in session.exec(select(Product.id).limit(limit)).all()]


def _embedding_query_text(query: str, tokens: Optional[List[str]]) -> str:
    parts = [query.strip()]
    if tokens:
        parts.extend(tokens)
    return " ".join(_ordered_unique(parts))


def _query_embedding(text_value: str) -> Optional[List[float]]:
    if not text_value:
        return None
    if not settings.azure_openai_embed_endpoint or not settings.azure_openai_embed_api_key or not settings.azure_openai_embed_deployment:
        return None
    try:
        from openai import AzureOpenAI

        client = AzureOpenAI(
            api_key=settings.azure_openai_embed_api_key,
            azure_endpoint=settings.azure_openai_embed_endpoint,
            api_version=settings.azure_openai_embed_api_version,
        )
        response = client.embeddings.create(
            model=settings.azure_openai_embed_deployment,
            input=text_value,
            dimensions=384,
        )
        embedding = response.data[0].embedding
        return [float(value) for value in embedding]
    except Exception as exc:
        logger.warning("Không thể tạo query embedding, dùng fallback keyword: %s", exc)
        return None


def _vector_literal(values: List[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in values) + "]"


def _postgres_hybrid_product_ids(session: Session, query: str, query_embedding: List[float], limit: int) -> List[RankedProductMatch]:
    statement = text("""
        WITH query_input AS (
            SELECT
                :q AS q,
                websearch_to_tsquery('simple', :q) AS tsq,
                CAST(:query_embedding AS vector) AS qvec
        ),
        keyword AS (
            SELECT
                p.id,
                row_number() OVER (
                    ORDER BY
                        ts_rank_cd(
                            to_tsvector(
                                'simple',
                                concat_ws(' ', p.name, p.display_name, p.category, p.description, CAST(p.metadata_json AS text))
                            ),
                            query_input.tsq
                        ) DESC,
                        CASE
                            WHEN p.name ILIKE '%' || query_input.q || '%' THEN 1
                            WHEN p.display_name ILIKE '%' || query_input.q || '%' THEN 1
                            WHEN p.category ILIKE '%' || query_input.q || '%' THEN 1
                            ELSE 0
                        END DESC
                ) AS rank_keyword
            FROM products p, query_input
            WHERE
                to_tsvector(
                    'simple',
                    concat_ws(' ', p.name, p.display_name, p.category, p.description, CAST(p.metadata_json AS text))
                ) @@ query_input.tsq
                OR p.name ILIKE '%' || query_input.q || '%'
                OR p.display_name ILIKE '%' || query_input.q || '%'
                OR p.category ILIKE '%' || query_input.q || '%'
                OR p.description ILIKE '%' || query_input.q || '%'
            LIMIT :candidate_limit
        ),
        semantic AS (
            SELECT
                p.id,
                row_number() OVER (ORDER BY p.embedding <=> query_input.qvec) AS rank_semantic
            FROM products p, query_input
            WHERE p.embedding IS NOT NULL
            ORDER BY p.embedding <=> query_input.qvec
            LIMIT :candidate_limit
        ),
        rrf AS (
            SELECT
                COALESCE(keyword.id, semantic.id) AS product_id,
                COALESCE(1.0 / (:rrf_k + keyword.rank_keyword), 0) +
                COALESCE(1.0 / (:rrf_k + semantic.rank_semantic), 0) AS rrf_score
            FROM keyword
            FULL OUTER JOIN semantic ON semantic.id = keyword.id
        )
        SELECT product_id, rrf_score
        FROM rrf
        ORDER BY rrf_score DESC
        LIMIT :limit
    """)
    rows = session.execute(statement, {
        "q": query,
        "query_embedding": _vector_literal(query_embedding),
        "candidate_limit": 100,
        "rrf_k": 60,
        "limit": limit,
    }).all()
    return [_ranked_match(row.product_id, row.rrf_score) for row in rows]


def hybrid_search_products(session: Session, query: str, tokens: Optional[List[str]], limit: int = 50) -> List[RankedProductMatch]:
    clean_query = query.replace("|", " ") if query else ""
    keyword_matches = _keyword_product_ids(session, tokens, limit)
    dialect_name = session.get_bind().dialect.name
    query_text = _embedding_query_text(clean_query, tokens)
    embedding = _query_embedding(query_text)

    product_matches = []
    if dialect_name == "postgresql" and embedding:
        try:
            product_matches = _postgres_hybrid_product_ids(session, query_text, embedding, limit)
        except Exception as exc:
            logger.warning("Hybrid search PostgreSQL lỗi, dùng fallback keyword: %s", exc)

    if not product_matches:
        product_matches = keyword_matches if keyword_matches else []

    # Lọc danh từ để loại bỏ các cấu trúc không khớp hoặc ưu tiên
    filtered_matches = _apply_noun_filtering_to_matches(session, clean_query, product_matches)

    # Lọc giới tính và độ tuổi để tránh rò rỉ sản phẩm không liên quan
    filtered_matches = _apply_gender_age_filtering_to_matches(session, clean_query, filtered_matches)

    return filtered_matches
