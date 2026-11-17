from datetime import datetime, timezone
import math
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    recall_score,
    r2_score,
)
from sklearn.model_selection import train_test_split
from analytics.preprocessing import (
    DEFAULT_RANDOM_STATE,
    FEATURE_COLUMNS,
    build_anomaly_pipeline,
    build_dropout_pipeline,
    build_gpa_pipeline,
    parse_binary_label,
    parse_gpa_label,
    prepare_feature_frame,
    validate_eval_params,
)

MIN_EVALUATION_SAMPLES = 10
DEFAULT_TEST_SIZE = 0.2


def _base_dataset_info(df, target_col, valid_count):
    missing_cells = int(df[list(FEATURE_COLUMNS)].isna().sum().sum()) if not df.empty else 0
    total_rows = int(len(df))
    return {
        "total_rows": total_rows,
        "valid_labelled_rows": int(valid_count),
        "unlabelled_or_invalid_rows": max(0, total_rows - int(valid_count)),
        "feature_columns": list(FEATURE_COLUMNS),
        "target_column": target_col,
        "missing_feature_cells": missing_cells,
    }


def _build_eval_result(
    model_name, task_type, status, uses_genuine_labels, label_source,
    dataset_info, random_state, test_size, train_samples=0, test_samples=0,
    metrics=None, warnings=None, limitations=None,
):
    return {
        "model_name": model_name,
        "task_type": task_type,
        "status": status,
        "uses_genuine_labels": uses_genuine_labels,
        "label_source": label_source,
        "dataset_info": dataset_info,
        "train_samples": int(train_samples),
        "test_samples": int(test_samples),
        "random_state": random_state,
        "test_size": test_size,
        "metrics": metrics,
        "warnings": list(warnings or []),
        "limitations": list(limitations or []),
    }


def _collect_data_warnings(info, label_col):
    warnings = []
    if info["unlabelled_or_invalid_rows"] > 0:
        warnings.append(
            f"Excluded {info['unlabelled_or_invalid_rows']} rows with missing or invalid '{label_col}' values."
        )
    if info["missing_feature_cells"] > 0:
        warnings.append(
            f"Imputed {info['missing_feature_cells']} missing feature cell(s) using training-split medians only."
        )
    return warnings


def _evaluate_binary_classifier(
    df, label_col, model_name, fallback_label_source, missing_label_limitation,
    pipeline_builder, predict_transform, test_size, random_state,
):
    total_rows = int(len(df))
    if label_col not in df.columns or total_rows == 0:
        return _build_eval_result(
            model_name, "classification", "EMPTY" if total_rows == 0 else "UNAVAILABLE",
            False, fallback_label_source, _base_dataset_info(df, label_col, 0),
            random_state, test_size, limitations=[missing_label_limitation],
        )

    parsed_labels = df[label_col].apply(parse_binary_label)
    valid_mask = parsed_labels.notna()
    valid_count = int(valid_mask.sum())
    info = _base_dataset_info(df, label_col, valid_count)
    if valid_count == 0:
        return _build_eval_result(
            model_name, "classification", "UNAVAILABLE", False, fallback_label_source,
            info, random_state, test_size, limitations=[missing_label_limitation],
        )

    y_all = parsed_labels[valid_mask].astype(int).to_numpy()
    x_all = df.loc[valid_mask, list(FEATURE_COLUMNS)].to_numpy(dtype=float)
    unique_vals, counts = np.unique(y_all, return_counts=True)
    info["class_distribution"] = {str(int(k)): int(v) for k, v in zip(unique_vals, counts)}
    warnings = _collect_data_warnings(info, label_col)

    if valid_count < MIN_EVALUATION_SAMPLES:
        return _build_eval_result(
            model_name, "classification", "INSUFFICIENT_DATA", True, label_col,
            info, random_state, test_size, warnings=warnings,
            limitations=[f"At least {MIN_EVALUATION_SAMPLES} genuine labelled samples are required for evaluation (found {valid_count})."],
        )

    if len(unique_vals) < 2 or int(counts.min()) < 2:
        return _build_eval_result(
            model_name, "classification", "INSUFFICIENT_DATA", True, label_col,
            info, random_state, test_size, warnings=warnings,
            limitations=[f"Stratified train/test evaluation requires both classes (0 and 1) with at least 2 samples each in '{label_col}'."],
        )

    try:
        x_train, x_test, y_train, y_test = train_test_split(
            x_all, y_all, test_size=test_size, random_state=random_state, stratify=y_all
        )
    except ValueError as exc:
        return _build_eval_result(
            model_name, "classification", "INSUFFICIENT_DATA", True, label_col,
            info, random_state, test_size, warnings=warnings,
            limitations=[f"Could not create stratified split: {exc}"],
        )

    pipeline = pipeline_builder()
    pipeline.fit(x_train, y_train)
    y_pred = predict_transform(pipeline.predict(x_test))

    cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
    metrics = {
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred, pos_label=1, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, y_pred, pos_label=1, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_test, y_pred, pos_label=1, zero_division=0)), 4),
        "confusion_matrix": {
            "labels": [0, 1],
            "matrix": [[int(cm[0, 0]), int(cm[0, 1])], [int(cm[1, 0]), int(cm[1, 1])]],
            "tn": int(cm[0, 0]), "fp": int(cm[0, 1]), "fn": int(cm[1, 0]), "tp": int(cm[1, 1]),
        },
    }
    limitations = []
    if len(y_test) < 10:
        limitations.append(f"Small held-out test set ({len(y_test)} samples); metric estimates may have high variance.")

    return _build_eval_result(
        model_name, "classification", "EVALUATED", True, label_col,
        info, random_state, test_size, train_samples=len(y_train),
        test_samples=len(y_test), metrics=metrics, warnings=warnings, limitations=limitations,
    )


def evaluate_dropout_classifier(df, test_size=DEFAULT_TEST_SIZE, random_state=DEFAULT_RANDOM_STATE):
    ts, rs = validate_eval_params(test_size, random_state)
    return _evaluate_binary_classifier(
        df=df,
        label_col="dropout_label",
        model_name="Dropout Risk Classifier (RandomForestClassifier)",
        fallback_label_source="synthetic_anchor_and_heuristic_weak_labels",
        missing_label_limitation=(
            "No genuine 'dropout_label' ground truth is available. Current predictions rely on synthetic "
            "anchor samples and heuristic weak targets, so real-world classification accuracy cannot be established."
        ),
        pipeline_builder=lambda: build_dropout_pipeline(random_state=rs),
        predict_transform=lambda preds: np.asarray(preds, dtype=int),
        test_size=ts,
        random_state=rs,
    )


def evaluate_gpa_regressor(df, test_size=DEFAULT_TEST_SIZE, random_state=DEFAULT_RANDOM_STATE):
    ts, rs = validate_eval_params(test_size, random_state)
    model_name = "GPA Forecaster (Ridge)"
    fallback_source = "synthetic_anchor_and_heuristic_weak_labels"
    missing_limitation = (
        "No genuine 'actual_gpa' ground truth is available. Current predictions rely on synthetic "
        "anchor targets and heuristic GPA formulas, so real-world regression error cannot be established."
    )
    total_rows = int(len(df))
    if "actual_gpa" not in df.columns or total_rows == 0:
        return _build_eval_result(
            model_name, "regression", "EMPTY" if total_rows == 0 else "UNAVAILABLE",
            False, fallback_source, _base_dataset_info(df, "actual_gpa", 0),
            rs, ts, limitations=[missing_limitation],
        )

    parsed_targets = df["actual_gpa"].apply(parse_gpa_label)
    valid_mask = parsed_targets.notna()
    valid_count = int(valid_mask.sum())
    info = _base_dataset_info(df, "actual_gpa", valid_count)
    if valid_count == 0:
        return _build_eval_result(
            model_name, "regression", "UNAVAILABLE", False, fallback_source, info, rs, ts,
            limitations=["No valid 'actual_gpa' values (0.0-4.0) found; real-world GPA regression performance cannot be established."],
        )

    warnings = _collect_data_warnings(info, "actual_gpa")
    if valid_count < MIN_EVALUATION_SAMPLES:
        return _build_eval_result(
            model_name, "regression", "INSUFFICIENT_DATA", True, "actual_gpa",
            info, rs, ts, warnings=warnings,
            limitations=[f"At least {MIN_EVALUATION_SAMPLES} genuine labelled samples are required for evaluation (found {valid_count})."],
        )

    y_all = parsed_targets[valid_mask].astype(float).to_numpy()
    x_all = df.loc[valid_mask, list(FEATURE_COLUMNS)].to_numpy(dtype=float)
    x_train, x_test, y_train, y_test = train_test_split(x_all, y_all, test_size=ts, random_state=rs)
    if len(y_test) < 2 or len(y_train) < 2:
        return _build_eval_result(
            model_name, "regression", "INSUFFICIENT_DATA", True, "actual_gpa",
            info, rs, ts, warnings=warnings,
            limitations=["Train and test splits must each contain at least 2 samples to compute regression metrics."],
        )

    pipeline = build_gpa_pipeline()
    pipeline.fit(x_train, y_train)
    y_pred = np.clip(pipeline.predict(x_test), 0.0, 4.0)

    mse = round(float(mean_squared_error(y_test, y_pred)), 4)
    limitations = []
    if float(np.var(y_test)) == 0.0:
        r2 = None
        limitations.append("Test target 'actual_gpa' has zero variance, so R2 score is undefined.")
    else:
        r2 = round(float(r2_score(y_test, y_pred)), 4)
    if len(y_test) < 10:
        limitations.append(f"Small held-out test set ({len(y_test)} samples); error metrics may have high variance.")

    return _build_eval_result(
        model_name, "regression", "EVALUATED", True, "actual_gpa", info, rs, ts,
        train_samples=len(y_train), test_samples=len(y_test),
        metrics={
            "mae": round(float(mean_absolute_error(y_test, y_pred)), 4),
            "mse": mse,
            "rmse": round(float(math.sqrt(mean_squared_error(y_test, y_pred))), 4),
            "r2_score": r2,
        },
        warnings=warnings, limitations=limitations,
    )


def evaluate_anomaly_detector(df, test_size=DEFAULT_TEST_SIZE, random_state=DEFAULT_RANDOM_STATE):
    ts, rs = validate_eval_params(test_size, random_state)
    result = _evaluate_binary_classifier(
        df=df,
        label_col="anomaly_label",
        model_name="Anomaly Detector (IsolationForest)",
        fallback_label_source="unsupervised_outlier_and_threshold_rules",
        missing_label_limitation=(
            "IsolationForest runs in unsupervised mode without genuine 'anomaly_label' ground truth; "
            "supervised precision and recall cannot be established."
        ),
        pipeline_builder=lambda: build_anomaly_pipeline(contamination=0.12, random_state=rs),
        predict_transform=lambda preds: np.where(np.asarray(preds, dtype=int) == -1, 1, 0),
        test_size=ts,
        random_state=rs,
    )
    if not result["uses_genuine_labels"] and result["status"] == "UNAVAILABLE":
        result["status"] = "UNSUPERVISED"
        result["task_type"] = "unsupervised"
    return result


def evaluate_model_suite(records, test_size=DEFAULT_TEST_SIZE, random_state=DEFAULT_RANDOM_STATE):
    ts, rs = validate_eval_params(test_size, random_state)
    df = prepare_feature_frame(records)
    dropout_res = evaluate_dropout_classifier(df, test_size=ts, random_state=rs)
    gpa_res = evaluate_gpa_regressor(df, test_size=ts, random_state=rs)
    anomaly_res = evaluate_anomaly_detector(df, test_size=ts, random_state=rs)

    models = {
        "dropout_classifier": dropout_res,
        "gpa_regressor": gpa_res,
        "anomaly_detector": anomaly_res,
    }
    evaluated_count = sum(1 for item in models.values() if item["status"] == "EVALUATED")
    if df.empty:
        overall_status = "EMPTY"
    elif evaluated_count == len(models):
        overall_status = "COMPLETED"
    elif evaluated_count > 0:
        overall_status = "PARTIAL"
    else:
        overall_status = "NO_GENUINE_LABELS"

    suite_warnings = []
    if overall_status == "NO_GENUINE_LABELS":
        suite_warnings.append(
            "No genuine ground-truth labels were found in the dataset. Evaluation did not manufacture "
            "accuracy scores from synthetic anchor samples or heuristic weak targets."
        )

    return {
        "status": overall_status,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "random_state": rs,
        "test_size": ts,
        "dataset_summary": {
            "total_records": int(len(df)),
            "missing_feature_cells": int(df[list(FEATURE_COLUMNS)].isna().sum().sum()) if not df.empty else 0,
            "genuine_dropout_labels": dropout_res["dataset_info"]["valid_labelled_rows"],
            "genuine_gpa_labels": gpa_res["dataset_info"]["valid_labelled_rows"],
            "genuine_anomaly_labels": anomaly_res["dataset_info"]["valid_labelled_rows"],
        },
        "models": models,
        "warnings": suite_warnings,
    }
