"""
HANDWRITTEN DIGIT RECOGNITION SYSTEM USING CONVOLUTIONAL NEURAL NETWORK (CNN)
Module: Model Evaluation Script (evaluate_model.py)
B.Tech Capstone Project

This script performs:
1. Loading the trained `digit_model.keras`.
2. Loading the unseen MNIST test dataset (10,000 images).
3. Calculating test accuracy and test loss.
4. Generating predictions and computing per-class Precision, Recall, and F1-Scores.
5. Plotting and saving the Confusion Matrix heatmap to `results/confusion_matrix.png`.
6. Exporting real evaluation metrics to `model_metrics.json` for live website display.
"""

import os
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import tensorflow as tf
from sklearn.metrics import classification_report, confusion_matrix

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, 'results')
MODEL_PATH = os.path.join(BASE_DIR, 'digit_model.keras')
METRICS_JSON_PATH = os.path.join(BASE_DIR, 'model_metrics.json')


def evaluate_model():
    print("=" * 70)
    print("STEP 1: LOADING TRAINED MODEL AND TEST DATA")
    print("=" * 70)

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model file not found at: {MODEL_PATH}. Run train_model.py first!")

    model = tf.keras.models.load_model(MODEL_PATH)
    print(f"Loaded model successfully from: {MODEL_PATH}")

    # Load MNIST test set
    (_, _), (x_test_raw, y_test) = tf.keras.datasets.mnist.load_data()
    x_test = x_test_raw.astype('float32') / 255.0
    x_test = np.expand_dims(x_test, axis=-1)

    print(f"Evaluating on {x_test.shape[0]} test samples...")

    # 1. Model evaluate
    eval_results = model.evaluate(x_test, y_test, batch_size=128, verbose=1)
    test_loss = float(eval_results[0])
    test_accuracy = float(eval_results[1])
    print(f"\n--> Test Accuracy: {test_accuracy * 100:.2f}%")
    print(f"--> Test Loss:     {test_loss:.4f}")

    # 2. Predictions
    print("\n" + "=" * 70)
    print("STEP 2: GENERATING PREDICTIONS AND CLASSIFICATION METRICS")
    print("=" * 70)
    y_pred_probs = model.predict(x_test, batch_size=128, verbose=1)
    y_pred = np.argmax(y_pred_probs, axis=1)

    # 3. Classification Report
    target_names = [f"Digit {i}" for i in range(10)]
    report_dict = classification_report(y_test, y_pred, target_names=target_names, output_dict=True)
    report_text = classification_report(y_test, y_pred, target_names=target_names)
    print("\nClassification Report:\n")
    print(report_text)

    # Convert keys to string "0".."9" for convenient frontend lookup
    clean_report = {}
    for i in range(10):
        key = f"Digit {i}"
        if key in report_dict:
            clean_report[str(i)] = report_dict[key]
    if 'macro avg' in report_dict:
        clean_report['macro avg'] = report_dict['macro avg']
    if 'weighted avg' in report_dict:
        clean_report['weighted avg'] = report_dict['weighted avg']
    if 'accuracy' in report_dict:
        clean_report['accuracy'] = report_dict['accuracy']

    # 4. Confusion Matrix Heatmap
    print("\n" + "=" * 70)
    print("STEP 3: GENERATING CONFUSION MATRIX HEATMAP")
    print("=" * 70)
    cm = confusion_matrix(y_test, y_pred)

    plt.figure(figsize=(9, 7.5), facecolor='#0b0f19')
    ax = plt.axes()
    ax.set_facecolor('#111827')

    sns.heatmap(
        cm,
        annot=True,
        fmt='d',
        cmap='Blues',
        cbar=True,
        xticklabels=[str(i) for i in range(10)],
        yticklabels=[str(i) for i in range(10)],
        annot_kws={'size': 10, 'weight': 'bold', 'color': '#ffffff'},
        linewidths=0.5,
        linecolor='#1e293b'
    )

    plt.title('MNIST CNN Test Set Confusion Matrix (10,000 Samples)', color='#f3f4f6', fontsize=13, pad=16, fontweight='bold')
    plt.xlabel('Predicted Digit Label', color='#94a3b8', fontsize=11, labelpad=10)
    plt.ylabel('Actual Digit Label', color='#94a3b8', fontsize=11, labelpad=10)
    plt.tick_params(colors='#94a3b8', labelsize=10)

    cm_path = os.path.join(RESULTS_DIR, 'confusion_matrix.png')
    plt.savefig(cm_path, dpi=200, bbox_inches='tight', facecolor='#0b0f19')
    plt.close()
    print(f"Confusion matrix saved to: {cm_path}")

    # 5. Calculate Per-Digit Accuracy
    per_digit_accuracy = {}
    for i in range(10):
        total_for_digit = np.sum(cm[i, :])
        correct_for_digit = cm[i, i]
        per_digit_accuracy[str(i)] = float(correct_for_digit / total_for_digit) if total_for_digit > 0 else 0.0

    # 6. Save model_metrics.json
    metrics_data = {
        "test_accuracy": round(test_accuracy, 4),
        "test_loss": round(test_loss, 4),
        "total_parameters": int(model.count_params()),
        "epochs_trained": 10,
        "classification_report": clean_report,
        "confusion_matrix": cm.tolist(),
        "per_digit_accuracy": per_digit_accuracy
    }

    with open(METRICS_JSON_PATH, 'w') as f:
        json.dump(metrics_data, f, indent=2)
    print(f"\nModel metrics successfully exported to: {METRICS_JSON_PATH}")

    print("\n" + "=" * 70)
    print("EVALUATION COMPLETE - ALL ARTIFACTS GENERATED SUCCESSFULLY")
    print("=" * 70)
    return metrics_data


if __name__ == '__main__':
    evaluate_model()

