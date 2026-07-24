import shap
from typing import Any, Tuple


def get_explainer_for_model(model: Any) -> Tuple[Any, str]:
    """
    Dynamically inspects a loaded ML model object and returns the appropriate SHAP Explainer class.
    Also returns a string identifier of the explainer type.
    """
    model_type = type(model).__name__

    # Tree Models
    if model_type in [
        "RandomForestClassifier", "RandomForestRegressor",
        "DecisionTreeClassifier", "DecisionTreeRegressor",
        "GradientBoostingClassifier", "GradientBoostingRegressor",
        "XGBClassifier", "XGBRegressor", "Booster",
        "LGBMClassifier", "LGBMRegressor", "Booster",
        "CatBoostClassifier", "CatBoostRegressor", "CatBoost",
        "IsolationForest"
    ]:
        return shap.TreeExplainer, "TreeExplainer"

    # Linear Models
    elif model_type in [
        "LogisticRegression", "LinearRegression",
        "Ridge", "Lasso", "ElasticNet", "SGDClassifier"
    ]:
        return shap.LinearExplainer, "LinearExplainer"

    # Fallback to Kernel for anything else
    else:
        return shap.KernelExplainer, "KernelExplainer"
