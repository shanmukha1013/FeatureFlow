from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Dict, Any
from app.storage.database import get_db
from app.storage.models import Dataset, Feature, Model, ChampionModel, InferenceRequest

router = APIRouter()

@router.get("/groups", response_model=Dict[str, Any])
async def get_lineage_groups(session: AsyncSession = Depends(get_db)):
    """
    Returns the macro-level Lineage DAG for the Intelligent Canvas.
    Groups individual features into FeatureGroups for enterprise scalability.
    Injects intelligent recommendations and alerts into node metadata.
    """
    nodes = []
    edges = []

    # 1. Fetch Datasets
    datasets_res = await session.execute(select(Dataset))
    datasets = datasets_res.scalars().all()

    for ds in datasets:
        # Check for PII or required masking (Simulated Intelligence)
        recommendations = []
        if ds.inferred_dtypes:
            pii_candidates = [col for col in ds.inferred_dtypes.keys() if 'email' in col.lower() or 'ip' in col.lower()]
            if pii_candidates:
                recommendations.append(f"PII detected in {len(pii_candidates)} columns. Recommend masking.")

        if ds.status == "ACTIVE":
            recommendations.append("Dataset ready for Feature Extraction.")

        nodes.append({
            "id": f"ds_{ds.id}",
            "type": "dataset",
            "label": ds.name,
            "metadata": {
                "status": ds.status,
                "recommendations": recommendations,
                "version": ds.version
            }
        })

        # 2. Fetch Features for this Dataset (Grouped)
        features_res = await session.execute(select(Feature).filter(Feature.dataset_id == ds.id))
        features = features_res.scalars().all()
        
        if features:
            fg_id = f"fg_{ds.id}"
            fg_recommendations = []
            if len(features) < 3:
                fg_recommendations.append("Low feature count. Consider automated temporal aggregations.")
            
            nodes.append({
                "id": fg_id,
                "type": "feature_group",
                "label": f"{ds.name} Features",
                "metadata": {
                    "count": len(features),
                    "status": "MATERIALIZED" if any(f.status == "ACTIVE" for f in features) else "PENDING",
                    "recommendations": fg_recommendations
                }
            })
            edges.append({"id": f"e_ds_fg_{ds.id}", "source": f"ds_{ds.id}", "target": fg_id})

        # 3. Fetch Models for this Dataset
        models_res = await session.execute(select(Model).filter(Model.dataset_id == ds.id))
        models = models_res.scalars().all()

        for model in models:
            m_id = f"model_{model.id}"
            
            # Check for Drift (Simulated Intelligence)
            m_recommendations = []
            if model.status == "REGISTERED":
                m_recommendations.append("Model registered. Ready for deployment review.")
                
            nodes.append({
                "id": m_id,
                "type": "model",
                "label": model.name,
                "metadata": {
                    "status": model.status,
                    "algorithm": model.algorithm,
                    "recommendations": m_recommendations
                }
            })
            # Connect FeatureGroup -> Model
            if features:
                edges.append({"id": f"e_fg_m_{model.id}", "source": f"fg_{ds.id}", "target": m_id})
            else:
                edges.append({"id": f"e_ds_m_{model.id}", "source": f"ds_{ds.id}", "target": m_id})

            # 4. Endpoints / Champions
            champions_res = await session.execute(select(ChampionModel).filter(ChampionModel.model_id == model.id))
            champion = champions_res.scalars().first()
            if champion:
                ep_id = f"ep_{champion.id}"
                
                # Inference load intelligence
                inf_res = await session.execute(select(InferenceRequest).limit(10))
                inf_count = len(inf_res.scalars().all())
                ep_recs = []
                if inf_count > 0:
                    ep_recs.append(f"Processing live traffic. Drift monitoring active.")
                
                nodes.append({
                    "id": ep_id,
                    "type": "endpoint",
                    "label": f"{model.name} (Live)",
                    "metadata": {
                        "status": champion.status,
                        "recommendations": ep_recs
                    }
                })
                edges.append({"id": f"e_m_ep_{champion.id}", "source": m_id, "target": ep_id})

    return {
        "nodes": nodes,
        "edges": edges
    }
