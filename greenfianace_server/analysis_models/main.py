"""Prediction-focused offline entrypoint.

The legacy empirical-analysis modules have been decoupled from this entrypoint
so prediction generation can still run after those modules are archived.
"""

import os
import traceback
import warnings

from config import core_vars, output_path
from data_loader import load_raw_data, verify_panel_structure
from prediction_model import run_full_prediction
from preprocessing import full_preprocessing_pipeline

warnings.filterwarnings("ignore")


def _env_flag(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


RUN_DATA = _env_flag("GF_RUN_DATA", True)
RUN_PREDICTION = _env_flag("GF_RUN_PREDICTION", True)


def run_data_pipeline():
    """Refresh the cleaned panel CSV used by the prediction model."""
    print("\n[Step 1/2] Loading raw data and validating panel structure")
    df_raw = load_raw_data()
    df_balanced = verify_panel_structure(df_raw)
    print("[OK] Raw data loaded and validated")

    print("\n[Step 2/2] Running preprocessing pipeline")
    df_final, keep_vars = full_preprocessing_pipeline(df_balanced)
    print(
        "[OK] Preprocessing completed: "
        f"samples={len(df_final)}, variables={len(keep_vars)}"
    )
    return df_final, keep_vars


def run_prediction_pipeline():
    """Generate STIRPAT, system-dynamics, combo, and Logit prediction outputs."""
    primary_target = core_vars["dep_vars"].get("primary")
    if not primary_target:
        raise ValueError("Missing primary prediction target in config.core_vars['dep_vars']")

    print("\n[Prediction] Running current STIRPAT + system dynamics + combo pipeline")
    run_full_prediction(primary_target)
    print("[OK] Prediction outputs generated")


def main():
    print("\n" + "=" * 80)
    print("Green finance carbon-intensity prediction pipeline")
    print("=" * 80)

    try:
        if RUN_DATA:
            run_data_pipeline()
        else:
            print("\n[Skip] GF_RUN_DATA is disabled; using existing cleaned panel CSV")

        if RUN_PREDICTION:
            run_prediction_pipeline()
        else:
            print("\n[Skip] GF_RUN_PREDICTION is disabled; prediction outputs were not regenerated")

        print("\n" + "=" * 80)
        print(f"Pipeline completed. Outputs are under: {output_path}")
        print("=" * 80)
    except Exception as exc:
        print("\n" + "=" * 80)
        print(f"Pipeline failed: {exc}")
        print("=" * 80)
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
