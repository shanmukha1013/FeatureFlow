from typing import Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from great_expectations.core.expectation_suite import ExpectationSuite
from great_expectations.core.expectation_configuration import ExpectationConfiguration

from app.data_quality.models import ExpectationSuiteModel, DataContractModel
from app.data_quality.repositories import ExpectationSuiteRepository
from app.data_quality.expectations import generate_base_expectations


class ExpectationSuiteEngine:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ExpectationSuiteRepository(session)

    async def get_or_create_suite(self, contract: DataContractModel) -> Tuple[ExpectationSuiteModel, ExpectationSuite]:
        """
        Retrieves the latest expectation suite model and builds the GX ExpectationSuite object.
        If it doesn't exist, it infers one from the DataContract and persists it.
        """
        suite_model = await self.repo.get_latest_for_contract(contract.id)

        if suite_model is None:
            # Generate baseline configs
            configs = generate_base_expectations(contract)
            suite_model = await self.repo.create(
                contract_id=contract.id,
                name=f"{contract.dataset_name}_baseline_suite",
                expectation_configs=configs,
                created_by="auto-generated"
            )
            await self.session.flush()

        # Build GX Object
        # In modern GX Core (>= 0.18), we can create an ephemeral ExpectationSuite without a persistent context
        gx_suite = ExpectationSuite(expectation_suite_name=suite_model.name)

        for config_dict in suite_model.expectation_configs:
            # Reconstruct the kwargs and meta properly for GX
            expectation_config = ExpectationConfiguration(
                expectation_type=config_dict["expectation_type"],
                kwargs=config_dict["kwargs"],
                meta=config_dict.get("meta", {})
            )
            gx_suite.add_expectation(expectation_config)

        return suite_model, gx_suite
