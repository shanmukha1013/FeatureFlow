"""
Implements the Online Feature Store endpoints for serving real-time feature vectors.
"""
from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional, Dict, Any

from app.serving.schemas.features import (
    StoreFeatureRequestSchema,
    StoreFeatureBatchRequestSchema,
    RefreshFeatureRequestSchema,
    FeatureVectorResponseSchema
)
from app.cache.online_store import get_online_store

router = APIRouter()


@router.post("/features/store", status_code=status.HTTP_200_OK)
async def store_online_feature(payload: StoreFeatureRequestSchema):
    """
    Writes an entity feature vector into Redis Online Store.
    """
    store = get_online_store()
    success = await store.store_online_features(
        dataset=payload.dataset,
        entity_id=payload.entity_id,
        feature_values=payload.feature_values,
        feature_version=payload.feature_version,
        dataset_version=payload.dataset_version,
        ttl=payload.ttl
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Failed to write feature vector to Redis.")
    return {"status": "success", "stored": True, "entity_id": payload.entity_id}


@router.post("/features/store/batch", status_code=status.HTTP_200_OK)
async def store_online_features_batch(payload: StoreFeatureBatchRequestSchema):
    """
    Batch writes multiple entity feature vectors into Redis Online Store concurrently.
    """
    store = get_online_store()
    results = await store.store_online_features_batch(
        dataset=payload.dataset,
        entity_features_map=payload.entity_features_map,
        feature_version=payload.feature_version,
        dataset_version=payload.dataset_version,
        ttl=payload.ttl
    )
    return {"status": "success", "results": results}


@router.post("/features/refresh", response_model=FeatureVectorResponseSchema)
async def refresh_online_feature(payload: RefreshFeatureRequestSchema):
    """
    Loads feature values from authoritative PostgreSQL offline store, reconstructs vector,
    stores back into Redis (`repopulation`), and returns the payload.
    """
    store = get_online_store()
    repopulated = await store.refresh_online_features(
        dataset=payload.dataset,
        entity_id=payload.entity_id,
        ttl=payload.ttl
    )
    if not repopulated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No offline features found in PostgreSQL for entity '{payload.entity_id}' in dataset '{payload.dataset}'."
        )
    return FeatureVectorResponseSchema(**repopulated)


@router.get("/features/{dataset}/{entity}", response_model=FeatureVectorResponseSchema)
async def get_feature_by_dataset_and_entity(dataset: str, entity: str):
    """
    Retrieves an online feature vector by dataset and entity ID.
    If missing in Redis, checks fallback to PostgreSQL.
    """
    store = get_online_store()
    payload, source = await store.get_online_features_with_fallback(dataset=dataset, entity_id=entity)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature vector for entity '{entity}' in dataset '{dataset}' not found in online or offline store."
        )
    return FeatureVectorResponseSchema(**payload)


@router.get("/features/{entity}", response_model=FeatureVectorResponseSchema)
async def get_feature_by_entity(entity: str, dataset: str = Query("default")):
    """
    Retrieves an online feature vector by entity ID (using optional dataset parameter).
    """
    return await get_feature_by_dataset_and_entity(dataset=dataset, entity=entity)


@router.delete("/features/{dataset}/{entity}", status_code=status.HTTP_200_OK)
async def delete_feature_by_dataset_and_entity(dataset: str, entity: str):
    """Deletes an entity feature vector from the online store."""
    store = get_online_store()
    deleted = await store.delete_online_features(dataset=dataset, entity_id=entity)
    return {"status": "success", "deleted": deleted, "entity_id": entity}


@router.delete("/features/{entity}", status_code=status.HTTP_200_OK)
async def delete_feature_by_entity(entity: str, dataset: str = Query("default")):
    """Deletes an entity feature vector from the online store by entity ID and optional dataset query parameter."""
    return await delete_feature_by_dataset_and_entity(dataset=dataset, entity=entity)
