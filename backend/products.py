"""
Products CRUD Module for EPI Recognition System

Provides product catalog management functions.
Products are trainable items for custom YOLO models.
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List, Dict, Any
import uuid
import datetime
import logging

logger = logging.getLogger(__name__)


class ProductService:
    """Service for product CRUD operations"""

    @staticmethod
    def create_product(
        db: Session,
        user_id: str,
        name: str,
        sku: Optional[str] = None,
        category: Optional[str] = None,
        description: Optional[str] = None,
        image_url: Optional[str] = None,
        detection_threshold: float = 0.85,
        volume_cm3: Optional[float] = None,
        weight_g: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create new product.

        Args:
            db: Database session
            user_id: User UUID (owner)
            name: Product name
            sku: Product SKU code
            category: Product category
            description: Product description
            image_url: Reference image URL
            detection_threshold: Confidence threshold (0.0-1.0)
            volume_cm3: Volume in cubic centimeters
            weight_g: Weight in grams

        Returns:
            Dictionary with product data or None if failed
        """
        try:
            product_id = str(uuid.uuid4())
            now = datetime.datetime.now(datetime.timezone.utc)

            query = text("""
                INSERT INTO products (
                    id, user_id, name, sku, category, description, image_url,
                    detection_threshold, is_active, volume_cm3, weight_g, created_at, updated_at
                )
                VALUES (
                    :id, :user_id, :name, :sku, :category, :description, :image_url,
                    :detection_threshold, TRUE, :volume_cm3, :weight_g, :created_at, :updated_at
                )
                RETURNING *
            """)

            result = db.execute(query, {
                'id': product_id,
                'user_id': user_id,
                'name': name,
                'sku': sku,
                'category': category,
                'description': description,
                'image_url': image_url,
                'detection_threshold': detection_threshold,
                'volume_cm3': volume_cm3,
                'weight_g': weight_g,
                'created_at': now,
                'updated_at': now
            })

            db.commit()
            row = result.fetchone()

            logger.info(f"✅ Product created: {name} for user {user_id}")

            return {
                'id': str(row[0]),
                'user_id': str(row[1]),
                'name': row[2],
                'sku': row[3],
                'category': row[4],
                'description': row[5],
                'image_url': row[6],
                'detection_threshold': float(row[7]),
                'is_active': bool(row[8]),
                'volume_cm3': float(row[9]) if row[9] else None,
                'weight_g': float(row[10]) if row[10] else None,
                'created_at': row[11].isoformat() if row[11] else None,
                'updated_at': row[12].isoformat() if row[12] else None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error creating product: {e}")
            # Check for duplicate SKU
            if 'duplicate key' in str(e).lower() and 'sku' in str(e).lower():
                raise ValueError("Product with this SKU already exists")
            raise

    @staticmethod
    def get_products(
        db: Session,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        category: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        List products with pagination and filters.

        Args:
            db: Database session
            user_id: User UUID
            skip: Number of records to skip
            limit: Max records to return
            category: Filter by category
            is_active: Filter by active status

        Returns:
            List of product dictionaries
        """
        try:
            # Build query with filters
            conditions = ["user_id = :user_id"]
            params = {'user_id': user_id, 'limit': limit, 'skip': skip}

            if category:
                conditions.append("category = :category")
                params['category'] = category

            if is_active is not None:
                conditions.append("is_active = :is_active")
                params['is_active'] = is_active

            where_clause = " AND ".join(conditions)

            query = text(f"""
                SELECT id, user_id, name, sku, category, description, image_url,
                       detection_threshold, is_active, volume_cm3, weight_g,
                       created_at, updated_at,
                       (SELECT COUNT(*) FROM training_images WHERE product_id = products.id) as training_images_count
                FROM products
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :skip
            """)

            result = db.execute(query, params)
            rows = result.fetchall()

            products = []
            for row in rows:
                products.append({
                    'id': str(row[0]),
                    'user_id': str(row[1]),
                    'name': row[2],
                    'sku': row[3],
                    'category': row[4],
                    'description': row[5],
                    'image_url': row[6],
                    'detection_threshold': float(row[7]),
                    'is_active': bool(row[8]),
                    'volume_cm3': float(row[9]) if row[9] else None,
                    'weight_g': float(row[10]) if row[10] else None,
                    'created_at': row[11].isoformat() if row[11] else None,
                    'updated_at': row[12].isoformat() if row[12] else None,
                    'training_images_count': row[13]
                })

            return products

        except Exception as e:
            logger.error(f"❌ Error fetching products: {e}")
            return []

    @staticmethod
    def get_product(db: Session, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Get single product by ID.

        Args:
            db: Database session
            product_id: Product UUID

        Returns:
            Product dictionary or None if not found
        """
        try:
            query = text("""
                SELECT id, user_id, name, sku, category, description, image_url,
                       detection_threshold, is_active, volume_cm3, weight_g,
                       created_at, updated_at,
                       (SELECT COUNT(*) FROM training_images WHERE product_id = products.id) as training_images_count,
                       (SELECT COUNT(*) FROM training_images WHERE product_id = products.id AND is_annotated = TRUE) as annotated_images_count
                FROM products
                WHERE id = :product_id
            """)

            result = db.execute(query, {'product_id': product_id})
            row = result.fetchone()

            if row:
                return {
                    'id': str(row[0]),
                    'user_id': str(row[1]),
                    'name': row[2],
                    'sku': row[3],
                    'category': row[4],
                    'description': row[5],
                    'image_url': row[6],
                    'detection_threshold': float(row[7]),
                    'is_active': bool(row[8]),
                    'volume_cm3': float(row[9]) if row[9] else None,
                    'weight_g': float(row[10]) if row[10] else None,
                    'created_at': row[11].isoformat() if row[11] else None,
                    'updated_at': row[12].isoformat() if row[12] else None,
                    'training_images_count': row[13],
                    'annotated_images_count': row[14]
                }

            return None

        except Exception as e:
            logger.error(f"❌ Error fetching product: {e}")
            return None

    @staticmethod
    def get_active_products(db: Session, user_id: str) -> List[Dict[str, Any]]:
        """
        Get active products ready for detection.

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            List of active product dictionaries
        """
        try:
            query = text("""
                SELECT p.id, p.name, p.sku, p.category, p.image_url,
                       p.detection_threshold, p.volume_cm3, p.weight_g,
                       COUNT(DISTINCT ti.id) as training_images_count,
                       COUNT(DISTINCT CASE WHEN ti.is_annotated = TRUE THEN ti.id END) as annotated_images_count
                FROM active_products p
                WHERE p.user_id = :user_id AND p.is_active = TRUE
                GROUP BY p.id
                ORDER BY p.name
            """)

            result = db.execute(query, {'user_id': user_id})
            rows = result.fetchall()

            products = []
            for row in rows:
                products.append({
                    'id': str(row[0]),
                    'name': row[1],
                    'sku': row[2],
                    'category': row[3],
                    'image_url': row[4],
                    'detection_threshold': float(row[5]),
                    'volume_cm3': float(row[6]) if row[6] else None,
                    'weight_g': float(row[7]) if row[7] else None,
                    'training_images_count': row[8],
                    'annotated_images_count': row[9]
                })

            return products

        except Exception as e:
            logger.error(f"❌ Error fetching active products: {e}")
            return []

    @staticmethod
    def update_product(
        db: Session,
        product_id: str,
        user_id: str,
        **updates
    ) -> Optional[Dict[str, Any]]:
        """
        Update product fields.

        Args:
            db: Database session
            product_id: Product UUID
            user_id: User UUID (for ownership verification)
            **updates: Fields to update (name, sku, category, description, etc.)

        Returns:
            Updated product dictionary or None if failed
        """
        try:
            # Build SET clause dynamically
            allowed_fields = {
                'name', 'sku', 'category', 'description', 'image_url',
                'detection_threshold', 'is_active', 'volume_cm3', 'weight_g'
            }

            update_fields = {k: v for k, v in updates.items() if k in allowed_fields and v is not None}

            if not update_fields:
                raise ValueError("No valid fields to update")

            # Add updated_at timestamp
            update_fields['updated_at'] = datetime.datetime.now(datetime.timezone.utc)

            set_clause = ", ".join([f"{field} = :{field}" for field in update_fields.keys()])
            update_fields['product_id'] = product_id
            update_fields['user_id'] = user_id

            query = text(f"""
                UPDATE products
                SET {set_clause}
                WHERE id = :product_id AND user_id = :user_id
                RETURNING *
            """)

            result = db.execute(query, update_fields)
            db.commit()
            row = result.fetchone()

            if row:
                logger.info(f"✅ Product updated: {product_id}")
                return {
                    'id': str(row[0]),
                    'user_id': str(row[1]),
                    'name': row[2],
                    'sku': row[3],
                    'category': row[4],
                    'description': row[5],
                    'image_url': row[6],
                    'detection_threshold': float(row[7]),
                    'is_active': bool(row[8]),
                    'volume_cm3': float(row[9]) if row[9] else None,
                    'weight_g': float(row[10]) if row[10] else None,
                    'created_at': row[11].isoformat() if row[11] else None,
                    'updated_at': row[12].isoformat() if row[12] else None
                }

            return None

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error updating product: {e}")
            raise

    @staticmethod
    def delete_product(db: Session, product_id: str, user_id: str) -> bool:
        """
        Soft delete product (set is_active = False).

        Args:
            db: Database session
            product_id: Product UUID
            user_id: User UUID (for ownership verification)

        Returns:
            True if successful, False otherwise
        """
        try:
            query = text("""
                UPDATE products
                SET is_active = FALSE, updated_at = :updated_at
                WHERE id = :product_id AND user_id = :user_id
            """)

            result = db.execute(query, {
                'product_id': product_id,
                'user_id': user_id,
                'updated_at': datetime.datetime.now(datetime.timezone.utc)
            })
            db.commit()

            if result.rowcount > 0:
                logger.info(f"✅ Product deactivated: {product_id}")
                return True

            return False

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error deleting product: {e}")
            return False

    @staticmethod
    def count_products(db: Session, user_id: str, is_active: Optional[bool] = None) -> int:
        """
        Count products for a user.

        Args:
            db: Database session
            user_id: User UUID
            is_active: Filter by active status

        Returns:
            Number of products
        """
        try:
            conditions = ["user_id = :user_id"]
            params = {'user_id': user_id}

            if is_active is not None:
                conditions.append("is_active = :is_active")
                params['is_active'] = is_active

            where_clause = " AND ".join(conditions)

            query = text(f"""
                SELECT COUNT(*) FROM products
                WHERE {where_clause}
            """)

            result = db.execute(query, params)
            row = result.fetchone()

            return row[0] if row else 0

        except Exception as e:
            logger.error(f"❌ Error counting products: {e}")
            return 0


# Export service class
__all__ = ['ProductService']
