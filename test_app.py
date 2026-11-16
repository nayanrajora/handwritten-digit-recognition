"""
HANDWRITTEN DIGIT RECOGNITION SYSTEM - END-TO-END TEST SUITE
B.Tech Capstone Project

Validates:
1. Python dependencies and TensorFlow setup.
2. Model file integrity and inference capability.
3. Results assets (accuracy.png, loss.png, confusion_matrix.png, model_metrics.json).
4. Flask routing and HTML template rendering.
5. REST API: /api/metrics, /predict validation, error handling, and live inference accuracy.
"""

import os
import sys
import io
import json
import base64
import unittest
import numpy as np
from PIL import Image, ImageDraw

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app, get_model, preprocess_canvas_image


class TestHandwrittenDigitRecognition(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print("\n" + "=" * 70)
        print("RUNNING END-TO-END TEST SUITE FOR HANDWRITTEN DIGIT RECOGNITION")
        print("=" * 70)
        cls.client = app.test_client()
        cls.model = get_model()

    def test_01_model_loaded(self):
        """Test that the trained model loads properly and has expected architecture."""
        self.assertIsNotNone(self.model, "Model should not be None.")
        self.assertEqual(len(self.model.inputs), 1)
        self.assertEqual(self.model.inputs[0].shape[1:], (28, 28, 1))
        self.assertEqual(self.model.outputs[0].shape[1:], (10,))
        print("PASS: Model loaded with valid input shape (28, 28, 1) and output (10,).")

    def test_02_metrics_file(self):
        """Test that model_metrics.json exists and has valid empirical results."""
        metrics_file = os.path.join(BASE_DIR, 'model_metrics.json')
        self.assertTrue(os.path.exists(metrics_file), "model_metrics.json should exist.")
        with open(metrics_file, 'r') as f:
            data = json.load(f)

        self.assertIn('test_accuracy', data)
        self.assertGreater(data['test_accuracy'], 0.98, "Test accuracy should exceed 98%.")
        self.assertIn('confusion_matrix', data)
        self.assertEqual(len(data['confusion_matrix']), 10)
        print(f"PASS: model_metrics.json verified. Real test accuracy = {data['test_accuracy'] * 100:.2f}%.")

    def test_03_results_images(self):
        """Verify that accuracy, loss, and confusion matrix charts exist on disk."""
        results_dir = os.path.join(BASE_DIR, 'results')
        for filename in ['accuracy.png', 'loss.png', 'confusion_matrix.png', 'samples.png']:
            path = os.path.join(results_dir, filename)
            self.assertTrue(os.path.exists(path), f"File {filename} must exist.")
            self.assertGreater(os.path.getsize(path), 1000, f"File {filename} must not be empty.")
        print("PASS: All chart assets (accuracy, loss, confusion_matrix, samples) exist and are valid.")

    def test_04_home_route(self):
        """Test the home page '/' renders HTTP 200 with key elements."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Handwritten Digit", html)
        self.assertIn("digit-canvas", html)
        self.assertIn("predict-btn", html)
        self.assertIn("clear-btn", html)
        print("PASS: Home page '/' returned HTTP 200 with valid HTML and canvas elements.")

    def test_05_api_metrics_route(self):
        """Test the '/api/metrics' endpoint returns valid JSON."""
        res = self.client.get('/api/metrics')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('test_accuracy', data)
        self.assertIn('classification_report', data)
        print("PASS: Endpoint '/api/metrics' returned valid metric JSON.")

    def test_06_static_results_serving(self):
        """Test that static results are served via /results/<filename>."""
        res = self.client.get('/results/confusion_matrix.png')
        self.assertEqual(res.status_code, 200)
        self.assertIn('image/png', res.content_type)
        print("PASS: Endpoint '/results/confusion_matrix.png' served image/png successfully.")

    def test_07_predict_empty_canvas(self):
        """Test that sending an empty canvas or blank image returns an error."""
        # 1. Blank white image
        blank_img = Image.new('RGB', (280, 280), color='white')
        buf = io.BytesIO()
        blank_img.save(buf, format='PNG')
        b64_str = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode('utf-8')

        res = self.client.post('/predict', json={'image': b64_str})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data['success'])
        self.assertIn("empty", data['error'].lower())

        # 2. Empty string
        res2 = self.client.post('/predict', json={'image': ''})
        self.assertEqual(res2.status_code, 400)

        # 3. No body
        res3 = self.client.post('/predict', json={})
        self.assertEqual(res3.status_code, 400)
        print("PASS: Blank and empty canvas requests are correctly rejected with HTTP 400.")

    def test_08_predict_drawn_digit_one(self):
        """Test predicting a clearly drawn vertical stroke for digit 1."""
        img = Image.new('RGB', (280, 280), color='white')
        draw = ImageDraw.Draw(img)
        # Draw a clean vertical stroke like handwritten digit 1
        draw.line([(140, 40), (140, 240)], fill='black', width=22)
        draw.line([(110, 70), (140, 40)], fill='black', width=22)

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        b64_str = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode('utf-8')

        res = self.client.post('/predict', json={'image': b64_str})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['predicted_digit'], 1, f"Expected 1, got {data['predicted_digit']}")
        self.assertGreater(data['confidence'], 0.85)
        self.assertEqual(len(data['probabilities']), 10)
        self.assertIn('preprocessed_preview', data)
        print(f"PASS: Predicted digit 1 with {data['confidence'] * 100:.2f}% confidence in {data['inference_time_ms']} ms.")

    def test_09_predict_drawn_digit_zero(self):
        """Test predicting a clearly drawn oval for digit 0."""
        img = Image.new('RGB', (280, 280), color='white')
        draw = ImageDraw.Draw(img)
        # Draw an ellipse like handwritten digit 0
        draw.ellipse([(80, 50), (200, 230)], outline='black', width=22)

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        b64_str = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode('utf-8')

        res = self.client.post('/predict', json={'image': b64_str})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['predicted_digit'], 0, f"Expected 0, got {data['predicted_digit']}")
        self.assertGreater(data['confidence'], 0.85)
        print(f"PASS: Predicted digit 0 with {data['confidence'] * 100:.2f}% confidence in {data['inference_time_ms']} ms.")

    def test_10_health_endpoint(self):
        """Test /api/health endpoint."""
        res = self.client.get('/api/health')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['status'], 'healthy')
        self.assertTrue(data['model_loaded'])
        print("PASS: Health endpoint reported healthy and model loaded.")


if __name__ == '__main__':
    unittest.main(verbosity=2)

