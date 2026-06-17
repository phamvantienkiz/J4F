import asyncio
from sqlmodel import Session, select
from app.services.burgerprints import BurgerPrintsClient
from app.models.catalog import Product, ProductVariant, ShippingZone, ShippingFee
import logging

logger = logging.getLogger(__name__)

async def sync_catalog(session: Session) -> bool:
    """
    Đồng bộ danh mục sản phẩm và phí ship từ BurgerPrints API V2 vào Database Cache.
    Sử dụng cơ chế chạy song song giới hạn (Semaphore) và lưu hàng loạt để tối ưu hóa hiệu năng.
    """
    client = BurgerPrintsClient()
    try:
        logger.info("Bắt đầu đồng bộ danh mục sản phẩm từ BurgerPrints API V2...")

        # 1. Lấy danh sách toàn bộ sản phẩm
        products_data = await client.get_products()
        if not products_data:
            logger.warning("Không lấy được dữ liệu sản phẩm từ API.")
            return False

        logger.info(f"Đã lấy thông tin của {len(products_data)} sản phẩm. Bắt đầu tải chi tiết biến thể...")

        # Giới hạn số lượng request gọi chi tiết sản phẩm đồng thời (tối đa 15 request)
        semaphore = asyncio.Semaphore(15)

        async def fetch_and_save_product(prod_data):
            async with semaphore:
                prod_id = prod_data["id"]
                # 1.1 Đồng bộ sản phẩm
                # Tạo session độc lập cho từng thread để tránh xung đột luồng khi commit song song
                # Tuy nhiên do session truyền vào là chung, để an toàn ta sẽ thực hiện việc query/tải trước,
                # sau đó lưu tuần tự vào DB.
                try:
                    variants_data = await client.get_product_variants(prod_id, prod_data.get("alias", ""))
                    return prod_data, variants_data
                except Exception as ex:
                    logger.error(f"Lỗi khi fetch variants cho {prod_id}: {str(ex)}")
                    return prod_data, []

        # Chạy tải dữ liệu bất đồng bộ song song
        tasks = [fetch_and_save_product(p) for p in products_data]
        results = await asyncio.gather(*tasks)

        logger.info("Đã tải xong toàn bộ dữ liệu từ API. Bắt đầu ghi vào Database...")

        # Lưu dữ liệu vào DB tuần tự (SQLite không hỗ trợ ghi song song tốt)
        count_products = 0
        count_variants = 0

        for prod_data, variants_data in results:
            prod_id = prod_data["id"]
            if not prod_id:
                continue

            # Kiểm tra sản phẩm đã tồn tại chưa
            db_product = session.exec(select(Product).where(Product.id == prod_id)).first()
            if not db_product:
                db_product = Product(
                    id=prod_id,
                    name=prod_data["name"],
                    description=prod_data.get("description"),
                    category=prod_data.get("category"),
                    image_url=prod_data.get("image_url")
                )
                session.add(db_product)
            else:
                db_product.name = prod_data["name"]
                db_product.description = prod_data.get("description")
                db_product.category = prod_data.get("category")
                db_product.image_url = prod_data.get("image_url")
                session.add(db_product)

            count_products += 1

            # Lưu các biến thể
            for var_data in variants_data:
                var_id = var_data["id"]
                db_variant = session.exec(select(ProductVariant).where(ProductVariant.id == var_id)).first()

                partner_name = var_data.get("partner_name", "BurgerPrints")
                location_name = var_data.get("location_name", "US")

                if not db_variant:
                    db_variant = ProductVariant(
                        id=var_id,
                        product_id=prod_id,
                        sku=var_data["sku"],
                        color=var_data.get("color"),
                        size=var_data.get("size"),
                        base_cost=var_data.get("base_cost", 0.0),
                        second_item_price=var_data.get("second_item_price", 0.0),
                        addition_price=var_data.get("addition_price", 0.0),
                        clone_price=var_data.get("clone_price", 0.0),
                        weight=var_data.get("weight", 0.0),
                        mockup_url=var_data.get("mockup_url"),
                        catalog_variant_id=partner_name,
                        partner_name=partner_name,
                        location_name=location_name,
                        shipping_cost_us=var_data.get("shipping_cost_us", 4.5),
                        shipping_adding_us=var_data.get("shipping_adding_us", 1.5),
                        shipping_cost_ww=var_data.get("shipping_cost_ww", 5.99),
                        shipping_adding_ww=var_data.get("shipping_adding_ww", 2.0)
                    )
                    session.add(db_variant)
                else:
                    db_variant.sku = var_data["sku"]
                    db_variant.color = var_data.get("color")
                    db_variant.size = var_data.get("size")
                    db_variant.base_cost = var_data.get("base_cost", 0.0)
                    db_variant.second_item_price = var_data.get("second_item_price", 0.0)
                    db_variant.addition_price = var_data.get("addition_price", 0.0)
                    db_variant.clone_price = var_data.get("clone_price", 0.0)
                    db_variant.weight = var_data.get("weight", 0.0)
                    db_variant.mockup_url = var_data.get("mockup_url")
                    db_variant.partner_name = partner_name
                    db_variant.location_name = location_name
                    db_variant.shipping_cost_us = var_data.get("shipping_cost_us", 4.5)
                    db_variant.shipping_adding_us = var_data.get("shipping_adding_us", 1.5)
                    db_variant.shipping_cost_ww = var_data.get("shipping_cost_ww", 5.99)
                    db_variant.shipping_adding_ww = var_data.get("shipping_adding_ww", 2.0)
                    session.add(db_variant)

                count_variants += 1

            # Commit định kỳ sau mỗi 20 sản phẩm để tối ưu hiệu năng ghi DB và không bị nghẽn
            if count_products % 20 == 0:
                session.commit()
                logger.info(f"Đang ghi DB... Đã đồng bộ {count_products}/{len(products_data)} sản phẩm.")

        session.commit()
        logger.info(f"Đã đồng bộ {count_products} sản phẩm và {count_variants} biến thể vào Database Cache.")

        # 3. Đồng bộ phí vận chuyển (Shipping Fees) từ V2 Fallback
        logger.info("Bắt đầu đồng bộ phí vận chuyển mặc định...")
        shipping_data = await client.get_shipping_fees()
        for zone_data in shipping_data:
            country_code = zone_data["country_code"]
            db_zone = session.exec(select(ShippingZone).where(ShippingZone.country_code == country_code)).first()

            if not db_zone:
                db_zone = ShippingZone(
                    country_code=country_code,
                    country_name=zone_data["country_name"]
                )
                session.add(db_zone)
                session.commit()
                session.refresh(db_zone)

            # Xóa các phí ship cũ của zone này và nạp lại để tránh trùng lặp
            old_fees = session.exec(select(ShippingFee).where(ShippingFee.zone_id == db_zone.id)).all()
            for fee in old_fees:
                session.delete(fee)
            session.commit()

            for fee_data in zone_data["fees"]:
                db_fee = ShippingFee(
                    zone_id=db_zone.id,
                    carrier=fee_data["carrier"],
                    first_item_fee=fee_data["first_item"],
                    additional_item_fee=fee_data["additional_item"],
                    delivery_time=fee_data.get("delivery_time")
                )
                session.add(db_fee)

            session.commit()

        logger.info("Đã đồng bộ phí vận chuyển thành công.")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi đồng bộ catalog: {str(e)}")
        session.rollback()
        return False
    except Exception as e:
        logger.error(f"Lỗi khi đồng bộ catalog: {str(e)}")
        session.rollback()
        return False
