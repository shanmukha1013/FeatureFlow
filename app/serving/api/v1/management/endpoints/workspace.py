"""
Workspace initialization API.
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
from app.storage.database import get_db

router = APIRouter(tags=["workspace"])

async def _generate_sample_workspace(session: AsyncSession):
    # This will contain the logic to generate real DB entities.
    from app.storage.models import Dataset, DatasetVersion, Feature, Model, ChampionModel, Experiment, AuditLog, PipelineRun
    import uuid
    from datetime import datetime, timezone, timedelta
    import pandas as pd
    import os
    import joblib
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.datasets import make_classification
    
    # 1. Create datasets
    datasets = []
    for base_name in ["Customer_Churn", "Fraud_Detection", "Credit_Scoring"]:
        name = f"{base_name}_{uuid.uuid4().hex[:4]}"
        ds_id = str(uuid.uuid4())
        ds = Dataset(id=ds_id, name=name, description=f"Sample {name} Dataset", status="ACTIVE", version=1)
        session.add(ds)
        
        # Create CSV file
        df_X, df_y = make_classification(n_samples=1000, n_features=10, n_informative=5, random_state=42)
        df = pd.DataFrame(df_X, columns=[f"feature_{i}" for i in range(10)])
        df["target"] = df_y
        
        import io
        csv_buffer = io.BytesIO()
        df.to_csv(csv_buffer, index=False)
        csv_bytes = csv_buffer.getvalue()
        
        dv = DatasetVersion(
            id=str(uuid.uuid4()), 
            dataset_id=ds_id, 
            version_tag="v1", 
            file_path=f"db://datasets/{name}.csv", 
            raw_data=csv_bytes,
            row_count=1000, 
            status="ACTIVE", 
            version=1
        )
        session.add(dv)
        
        for col in df.columns:
            feat = Feature(id=str(uuid.uuid4()), dataset_id=ds_id, name=col, dtype=str(df[col].dtype), transformation="passthrough", status="ACTIVE", version=1)
            session.add(feat)
            
        datasets.append(ds_id)
    
    await session.commit()
    
    # 2. Train and create models
    models = []
    ds_id = datasets[0]
    for alg in ["RandomForest", "LogisticRegression", "DecisionTree"]:
        model_id = str(uuid.uuid4())
        
        # Train a dummy model
        clf = RandomForestClassifier(n_estimators=10)
        df_X, df_y = make_classification(n_samples=100, n_features=5, random_state=42)
        clf.fit(df_X, df_y)
        
        os.makedirs("datasets/artifacts", exist_ok=True)
        artifact_path = f"datasets/artifacts/{model_id}.pkl"
        joblib.dump(clf, artifact_path)
        
        m = Model(
            id=model_id,
            dataset_id=ds_id,
            name=f"{alg}_Model",
            version=1,
            algorithm=alg,
            metrics={"accuracy": 0.85 + (len(models)*0.02), "f1": 0.84},
            hyperparameters={"max_depth": 5},
            status="CANDIDATE",
            artifact_uri=artifact_path
        )
        session.add(m)
        models.append(model_id)
        
        exp = Experiment(
            id=str(uuid.uuid4()),
            name=f"Exp_{alg}",
            dataset_id=ds_id,
            model_id=model_id,
            status="COMPLETED",
            metrics=m.metrics,
            parameters=m.hyperparameters,
            duration=1200.0
        )
        session.add(exp)
        
    await session.commit()
    
    # 3. Set champion and challenger
    champ = ChampionModel(id=str(uuid.uuid4()), dataset_id=ds_id, model_id=models[0], status="ACTIVE")
    session.add(champ)
    
    # Set others as candidates (challengers)
    
    # 4. Pipeline history
    pr = PipelineRun(
        id=str(uuid.uuid4()),
        dataset_id=ds_id,
        status="COMPLETED",
        stages_json={"upload": "done", "train": "done"},
        version=1
    )
    session.add(pr)
    
    await session.commit()
    

@router.post("/sample")
async def generate_sample_workspace(
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db)
):
    await _generate_sample_workspace(session)
    return {"status": "success", "message": "Sample workspace generated successfully"}
