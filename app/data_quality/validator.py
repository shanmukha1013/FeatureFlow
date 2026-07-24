import great_expectations as gx
import pandas as pd

from great_expectations.core.expectation_suite import ExpectationSuite
from great_expectations.core.expectation_validation_result import ExpectationSuiteValidationResult


class GXEphemeralValidator:
    """
    Executes an ExpectationSuite against a Pandas DataFrame entirely in memory,
    without requiring persistent GX directories or yml configurations.
    """
    def __init__(self):
        self.context = gx.get_context(mode="ephemeral")
        self.data_source = self.context.sources.add_pandas("ephemeral_pandas")

    def validate(self, df: pd.DataFrame, suite: ExpectationSuite, dataset_name: str) -> ExpectationSuiteValidationResult:
        # Avoid asset naming collisions in memory
        asset_name = f"{dataset_name}_asset"
        try:
            ds = self.context.get_datasource("ephemeral_pandas")
            ds.delete_asset(asset_name)
        except Exception:
            pass

        data_asset = self.data_source.add_dataframe_asset(asset_name)
        batch_request = data_asset.build_batch_request(dataframe=df)

        validator = self.context.get_validator(
            batch_request=batch_request,
            expectation_suite=suite
        )

        # Execute validation
        results = validator.validate()
        return results
