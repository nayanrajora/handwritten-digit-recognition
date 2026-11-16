"""
HANDWRITTEN DIGIT RECOGNITION SYSTEM USING CONVOLUTIONAL NEURAL NETWORK (CNN)
Module: Flask Web Application Backend (app.py)
B.Tech Capstone Project

Features:
- Web interface serving (Home, Interactive Drawing Canvas, Model Evaluation, Architecture).
- Base64 canvas image decoding and MNIST-standard image preprocessing:
    1. Grayscale conversion.
    2. Polarity inversion (dark strokes on white canvas -> bright strokes on black background).
    3. Blank canvas detection and validation.
    4. Bounding box cropping and aspect-ratio preserved scaling to 20x20 inside 28x28.
    5. Center-of-mass alignment and [0, 1] normalization.
- Live CNN inference using `digit_model.keras`.
- Serving real empirical performance metrics from `model_metrics.json`.
"""

import os
import io
import time
import json
import base64
import numpy as np
from PIL import Image
from flask import Flask, render_template, request, jsonify, send_from_directory
import tensorflow as tf

# Initialize Flask application
app = Flask(__name__, static_folder='static', template_folder='templates')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, 'results')
MODEL_PATH = os.path.join(BASE_DIR, 'digit_model.keras')
METRICS_PATH = os.path.join(BASE_DIR, 'model_metrics.json')

# Global model cache
model = None


def get_model():
    """
    Lazy-loads and caches the trained CNN model.
    """
    global model
    if model is None:
        if os.path.exists(MODEL_PATH):
            print(f"Loading trained CNN model from {MODEL_PATH}...")
            model = tf.keras.models.load_model(MODEL_PATH)
            # Warm up model with a dummy inference
            dummy = np.zeros((1, 28, 28, 1), dtype=np.float32)
            model.predict(dummy, verbose=0)
            print("Model loaded and warmed up successfully.")
        else:
            print(f"Warning: Model file not found at {MODEL_PATH}. Inference will fail until model is trained.")
    return model


def preprocess_canvas_image(base64_str):
    """
    Preprocesses raw user-drawn canvas image to replicate MNIST conditions:
    1. Base64 decode into PIL image.
    2. Convert to Grayscale ('L').
    3. Invert colors (Black pen on white canvas -> White digit on black background).
    4. Check for blank/empty canvas.
    5. Crop bounding box of stroke.
    6. Resize bounding box to fit inside 20x20 keeping aspect ratio.
    7. Center the 20x20 digit inside a 28x28 frame using center-of-mass or bounding center.
    8. Normalize to [0.0, 1.0].
    """
    if not base64_str:
        return None, None, "Empty image data received."

    # Strip header if present
    if ',' in base64_str:
        base64_str = base64_str.split(',')[1]

    try:
        image_bytes = base64.b64decode(base64_str)
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        return None, None, f"Failed to decode image data: {str(e)}"

    # Convert to grayscale
    img_gray = img.convert('L')
    arr = np.array(img_gray, dtype=np.float32)

    # Invert polarity if image background is bright (white)
    # Canvas default is white (255) with black strokes (0)
    if np.mean(arr) > 127:
        inverted = 255.0 - arr
    else:
        inverted = arr

    # Validate non-empty drawing: check if any stroke exists
    stroke_threshold = 30.0
    stroke_pixels = np.where(inverted > stroke_threshold)
    if len(stroke_pixels[0]) < 20 or np.max(inverted) < 50:
        return None, None, "Canvas is empty or drawing is too faint. Please draw a clear digit."

    # Locate bounding box of the drawn digit
    min_y, max_y = np.min(stroke_pixels[0]), np.max(stroke_pixels[0])
    min_x, max_x = np.min(stroke_pixels[1]), np.max(stroke_pixels[1])

    # Crop bounding box
    cropped = inverted[min_y:max_y + 1, min_x:max_x + 1]
    crop_h, crop_w = cropped.shape

    # Scale cropped patch to fit within a 20x20 box preserving aspect ratio
    max_dim = max(crop_h, crop_w)
    scale_factor = 20.0 / max_dim
    new_w = max(1, int(round(crop_w * scale_factor)))
    new_h = max(1, int(round(crop_h * scale_factor)))

    crop_img = Image.fromarray(cropped.astype(np.uint8))
    resized_patch = crop_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    resized_arr = np.array(resized_patch, dtype=np.float32)

    # Place resized digit into a blank 28x28 canvas
    canvas_28 = np.zeros((28, 28), dtype=np.float32)
    start_y = (28 - new_h) // 2
    start_x = (28 - new_w) // 2
    canvas_28[start_y:start_y + new_h, start_x:start_x + new_w] = resized_arr

    # Center of mass alignment (Yann LeCun's MNIST standard)
    total_mass = np.sum(canvas_28)
    if total_mass > 0:
        y_indices, x_indices = np.indices(canvas_28.shape)
        cy = np.sum(y_indices * canvas_28) / total_mass
        cx = np.sum(x_indices * canvas_28) / total_mass
        shift_y = int(round(14.0 - cy))
        shift_x = int(round(14.0 - cx))

        # Restrict shifts to avoid clipping
        shift_y = max(-3, min(3, shift_y))
        shift_x = max(-3, min(3, shift_x))

        if shift_y != 0 or shift_x != 0:
            canvas_28 = np.roll(canvas_28, shift_y, axis=0)
            canvas_28 = np.roll(canvas_28, shift_x, axis=1)

    # Normalize to [0.0, 1.0]
    canvas_normalized = canvas_28 / 255.0
    input_tensor = np.expand_dims(canvas_normalized, axis=(0, -1))  # (1, 28, 28, 1)

    # Generate base64 thumbnail of preprocessed 28x28 image for frontend preview
    preview_img = Image.fromarray(np.clip(canvas_28, 0, 255).astype(np.uint8))
    preview_buffer = io.BytesIO()
    preview_img.save(preview_buffer, format='PNG')
    preview_b64 = "data:image/png;base64," + base64.b64encode(preview_buffer.getvalue()).decode('utf-8')

    return input_tensor, preview_b64, None


# ==============================================================================
# Routes
# ==============================================================================

@app.route('/')
def home():
    """Serves the main single-page application."""
    return render_template('index.html')


@app.route('/results/<path:filename>')
def static_results(filename):
    """Serves generated charts (accuracy, loss, confusion matrix)."""
    return send_from_directory(RESULTS_DIR, filename)


@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    """Returns actual empirical model metrics from model_metrics.json."""
    if os.path.exists(METRICS_PATH):
        with open(METRICS_PATH, 'r') as f:
            data = json.load(f)
        return jsonify(data)
    else:
        return jsonify({
            "test_accuracy": 0.0,
            "test_loss": 0.0,
            "total_parameters": 0,
            "epochs_trained": 0,
            "classification_report": {},
            "confusion_matrix": []
        }), 200


@app.route('/predict', methods=['POST'])
def predict():
    """
    Receives canvas base64 image, validates, preprocesses, and runs CNN inference.
    Returns:
      - predicted_digit (0-9)
      - confidence (0.0 - 1.0)
      - probabilities (list of 10 floats)
      - inference_time_ms
      - preprocessed_preview (base64)
    """
    start_time = time.time()

    data = request.get_json(silent=True)
    if not data or 'image' not in data:
        return jsonify({"success": False, "error": "No image data provided in request body."}), 400

    image_b64 = data.get('image', '').strip()
    if not image_b64:
        return jsonify({"success": False, "error": "Drawing canvas is empty. Please draw a digit before predicting."}), 400

    # Preprocess canvas image
    input_tensor, preview_b64, error_msg = preprocess_canvas_image(image_b64)
    if error_msg:
        return jsonify({"success": False, "error": error_msg}), 400

    # Ensure model is loaded
    cnn = get_model()
    if cnn is None:
        return jsonify({
            "success": False,
            "error": "Trained CNN model file not found. Please run train_model.py first."
        }), 500

    # Run inference
    probs = cnn.predict(input_tensor, verbose=0)[0]
    predicted_digit = int(np.argmax(probs))
    confidence = float(probs[predicted_digit])
    all_probabilities = [float(p) for p in probs]

    inference_time_ms = round((time.time() - start_time) * 1000, 2)

    return jsonify({
        "success": True,
        "predicted_digit": predicted_digit,
        "confidence": confidence,
        "probabilities": all_probabilities,
        "inference_time_ms": inference_time_ms,
        "preprocessed_preview": preview_b64
    })


@app.route('/api/health', methods=['GET'])
def health():
    """Simple health check endpoint."""
    return jsonify({
        "status": "healthy",
        "model_loaded": model is not None or os.path.exists(MODEL_PATH),
        "results_exist": os.path.exists(os.path.join(RESULTS_DIR, 'confusion_matrix.png'))
    })


if __name__ == '__main__':
    # Initialize model on startup
    get_model()
    print("Starting Flask server on http://127.0.0.1:5000 ...")
    app.run(host='127.0.0.1', port=5000, debug=False)

