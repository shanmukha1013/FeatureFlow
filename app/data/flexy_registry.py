"""
Official Schema Registration for the Flexy Marketplace Dataset.

Defines the explicit domain models and storage configurations for the 13 official
marketplace tables. Ensures the Data Layer strictly validates all ingested files
against these deterministic contracts.
"""
from app.data.schema import DatasetSchema, ColumnSchema, SchemaRegistry


def register_flexy_schemas(registry: SchemaRegistry) -> None:
    schemas = [
        DatasetSchema(
            name="users",
            entity_id_column="user_id",
            columns=[
                ColumnSchema("user_id", "int64"),
                ColumnSchema("username", "object"),
                ColumnSchema("email", "object"),
                ColumnSchema("password_hash", "object", required=False),
                ColumnSchema("created_at", "object"),
                ColumnSchema("updated_at", "object", required=False)
            ]
        ),
        DatasetSchema(
            name="addresses",
            entity_id_column="address_id",
            columns=[
                ColumnSchema("address_id", "int64"),
                ColumnSchema("user_id", "int64"),
                ColumnSchema("street", "object"),
                ColumnSchema("city", "object"),
                ColumnSchema("state", "object"),
                ColumnSchema("zip_code", "object"),
                ColumnSchema("country", "object")
            ]
        ),
        DatasetSchema(
            name="categories",
            entity_id_column="category_id",
            columns=[
                ColumnSchema("category_id", "int64"),
                ColumnSchema("name", "object"),
                ColumnSchema("parent_id", "float64", required=False)
            ]
        ),
        DatasetSchema(
            name="brands",
            entity_id_column="brand_id",
            columns=[
                ColumnSchema("brand_id", "int64"),
                ColumnSchema("name", "object"),
                ColumnSchema("description", "object", required=False)
            ]
        ),
        DatasetSchema(
            name="collections",
            entity_id_column="collection_id",
            columns=[
                ColumnSchema("collection_id", "int64"),
                ColumnSchema("name", "object"),
                ColumnSchema("description", "object", required=False),
                ColumnSchema("created_at", "object")
            ]
        ),
        DatasetSchema(
            name="items",
            entity_id_column="item_id",
            columns=[
                ColumnSchema("item_id", "int64"),
                ColumnSchema("seller_id", "int64"),
                ColumnSchema("category_id", "int64"),
                ColumnSchema("brand_id", "float64", required=False),
                ColumnSchema("title", "object"),
                ColumnSchema("description", "object"),
                ColumnSchema("condition", "object"),
                ColumnSchema("created_at", "object")
            ]
        ),
        DatasetSchema(
            name="auctions",
            entity_id_column="auction_id",
            columns=[
                ColumnSchema("auction_id", "int64"),
                ColumnSchema("item_id", "int64"),
                ColumnSchema("starting_price", "float64"),
                ColumnSchema("reserve_price", "float64", required=False),
                ColumnSchema("start_time", "object"),
                ColumnSchema("end_time", "object"),
                ColumnSchema("status", "object")
            ]
        ),
        DatasetSchema(
            name="bids",
            entity_id_column="bid_id",
            columns=[
                ColumnSchema("bid_id", "int64"),
                ColumnSchema("auction_id", "int64"),
                ColumnSchema("bidder_id", "int64"),
                ColumnSchema("amount", "float64"),
                ColumnSchema("bid_time", "object")
            ]
        ),
        DatasetSchema(
            name="orders",
            entity_id_column="order_id",
            columns=[
                ColumnSchema("order_id", "int64"),
                ColumnSchema("buyer_id", "int64"),
                ColumnSchema("item_id", "int64"),
                ColumnSchema("total_amount", "float64"),
                ColumnSchema("status", "object"),
                ColumnSchema("created_at", "object")
            ]
        ),
        DatasetSchema(
            name="payments",
            entity_id_column="payment_id",
            columns=[
                ColumnSchema("payment_id", "int64"),
                ColumnSchema("order_id", "int64"),
                ColumnSchema("amount", "float64"),
                ColumnSchema("payment_method", "object"),
                ColumnSchema("status", "object"),
                ColumnSchema("processed_at", "object")
            ]
        ),
        DatasetSchema(
            name="reviews",
            entity_id_column="review_id",
            columns=[
                ColumnSchema("review_id", "int64"),
                ColumnSchema("reviewer_id", "int64"),
                ColumnSchema("reviewee_id", "int64"),
                ColumnSchema("item_id", "int64"),
                ColumnSchema("rating", "int64"),
                ColumnSchema("comment", "object", required=False),
                ColumnSchema("created_at", "object")
            ]
        ),
        DatasetSchema(
            name="watchlists",
            entity_id_column="watchlist_id",
            columns=[
                ColumnSchema("watchlist_id", "int64"),
                ColumnSchema("user_id", "int64"),
                ColumnSchema("auction_id", "int64"),
                ColumnSchema("added_at", "object")
            ]
        ),
        DatasetSchema(
            name="notifications",
            entity_id_column="notification_id",
            columns=[
                ColumnSchema("notification_id", "int64"),
                ColumnSchema("user_id", "int64"),
                ColumnSchema("type", "object"),
                ColumnSchema("message", "object"),
                ColumnSchema("is_read", "bool"),
                ColumnSchema("created_at", "object")
            ]
        )
    ]

    for s in schemas:
        registry.register(s)


# Global Schema Registry for Dataset Discovery
registry = SchemaRegistry()
register_flexy_schemas(registry)
