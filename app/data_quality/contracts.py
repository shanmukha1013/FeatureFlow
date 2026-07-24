from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd

from app.data_quality.models import DataContractModel
from app.data_quality.repositories import DataContractRepository


class DataContractEngine:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = DataContractRepository(session)

    async def get_or_create_contract(self, dataset_name: str, df: Optional[pd.DataFrame] = None) -> DataContractModel:
        """
        Retrieves the active data contract for the given dataset.
        If it doesn't exist, and a dataframe is provided, it infers a baseline contract.
        """
        contract = await self.repo.get_by_dataset(dataset_name)

        if contract is None and df is not None:
            # Infer schema definition from Pandas dataframe
            schema_def = {str(col): str(dtype) for col, dtype in df.dtypes.items()}

            # Auto-infer primary key (first column typically)
            primary_keys = [df.columns[0]] if len(df.columns) > 0 else []

            # Default Business rules
            business_rules = {
                "max_null_percentage_default": 0.05,  # Max 5% nulls by default
                "reject_extra_columns": False,
                "require_all_columns": True
            }

            contract = await self.repo.create(
                dataset_name=dataset_name,
                schema_def=schema_def,
                business_rules=business_rules,
                primary_keys=primary_keys,
                owner="auto-discovered"
            )
            # flush so ID is populated
            await self.session.flush()

        return contract
