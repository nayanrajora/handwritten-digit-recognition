"""
HANDWRITTEN DIGIT RECOGNITION SYSTEM USING CONVOLUTIONAL NEURAL NETWORK (CNN)
Module: Model Training Script (train_model.py)
B.Tech Capstone Project

This script performs:
1. Automated loading of the MNIST dataset (60,000 train, 10,000 test images).
2. Data normalization (0-255 -> 0.0-1.0) and 4D tensor reshaping (28, 28, 1).
3. Sample MNIST image visualization export.
4. Construction of an optimized Convolutional Neural Network (CNN) architecture.
5. Model compilation and training with validation monitoring and callbacks.
6. Real empirical accuracy and loss curve generation saved to results/.
7. Model export to `digit_model.keras`.
"""

import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Headless backend for server/script rendering
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.keras import layers, models, callbacks

# Set random seeds for reproducibility
np.random.seed(42)
tf.random.set_seed(42)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, 'results')
MODEL_PATH = os.path.join(BASE_DIR, 'digit_model.keras')
os.makedirs(RESULTS_DIR, exist_ok=True)


def load_and_preprocess_data():
    """
    Downloads and loads the MNIST dataset from Keras, normalizes pixel intensities,
    and reshapes images into 4D tensors suitable for Conv2D layers.
    """
    print("=" * 70)
    print("STEP 1: LOADING AND PREPROCESSING MNIST DATASET")
    print("=" * 70)

    # 1. Load MNIST dataset
    (x_train_raw, y_train_raw), (x_test_raw, y_test_raw) = tf.keras.datasets.mnist.load_data()
    print(f"Loaded raw training samples: {x_train_raw.shape}")
    print(f"Loaded raw testing samples:  {x_test_raw.shape}")

    # 2. Save sample images from dataset for inspection
    save_sample_images(x_train_raw, y_train_raw)

    # 3. Normalize pixel values from [0, 255] to [0.0, 1.0]
    x_train = x_train_raw.astype('float32') / 255.0
    x_test = x_test_raw.astype('float32') / 255.0

    # 4. Reshape to include the single channel dimension (28, 28, 1)
    x_train = np.expand_dims(x_train, axis=-1)
    x_test = np.expand_dims(x_test, axis=-1)

    # 5. Split training data into training (50,000) and validation (10,000)
    val_split = 10000
    x_val = x_train[-val_split:]
    y_val = y_train_raw[-val_split:]
    x_train = x_train[:-val_split:]
    y_train = y_train_raw[:-val_split:]

    print(f"Final Training Set:   {x_train.shape}, labels: {y_train.shape}")
    print(f"Final Validation Set: {x_val.shape}, labels: {y_val.shape}")
    print(f"Final Testing Set:    {x_test.shape}, labels: {y_test_raw.shape}")

    return (x_train, y_train), (x_val, y_val), (x_test, y_test_raw)


def save_sample_images(images, labels):
    """
    Generates and saves a grid of 10 sample digits from the dataset.
    """
    plt.figure(figsize=(10, 4), facecolor='#0b0f19')
    for i in range(10):
        plt.subplot(2, 5, i + 1)
        plt.imshow(images[i], cmap='gray')
        plt.title(f"Label: {labels[i]}", color='#f3f4f6', fontsize=12, pad=6)
        plt.axis('off')

    plt.suptitle("MNIST Dataset Samples (28x28 Grayscale)", color='#60a5fa', fontsize=14, y=1.02)
    plt.tight_layout()
    sample_path = os.path.join(RESULTS_DIR, 'samples.png')
    plt.savefig(sample_path, dpi=200, bbox_inches='tight', facecolor='#0b0f19')
    plt.close()
    print(f"Sample images saved to: {sample_path}")


def build_cnn_model():
    """
    Constructs a Convolutional Neural Network (CNN) architecture.
    Architecture:
      - Conv2D (32 filters, 3x3 kernel, ReLU)
      - MaxPooling2D (2x2)
      - Conv2D (64 filters, 3x3 kernel, ReLU)
      - MaxPooling2D (2x2)
      - Dropout (0.25)
      - Flatten
      - Dense (128 units, ReLU)
      - Dropout (0.50)
      - Dense (10 units, Softmax)
    """
    print("\n" + "=" * 70)
    print("STEP 2: BUILDING CONVOLUTIONAL NEURAL NETWORK ARCHITECTURE")
    print("=" * 70)

    model = models.Sequential([
        # First Convolutional Block
        layers.Input(shape=(28, 28, 1)),
        layers.Conv2D(32, kernel_size=(3, 3), activation='relu', padding='same', name='conv2d_1'),
        layers.BatchNormalization(name='batch_norm_1'),
        layers.MaxPooling2D(pool_size=(2, 2), name='maxpool_1'),

        # Second Convolutional Block
        layers.Conv2D(64, kernel_size=(3, 3), activation='relu', padding='same', name='conv2d_2'),
        layers.BatchNormalization(name='batch_norm_2'),
        layers.MaxPooling2D(pool_size=(2, 2), name='maxpool_2'),
        layers.Dropout(0.25, name='dropout_1'),

        # Fully Connected Classification Head
        layers.Flatten(name='flatten'),
        layers.Dense(128, activation='relu', name='dense_feature'),
        layers.Dropout(0.50, name='dropout_2'),
        layers.Dense(10, activation='softmax', name='softmax_output')
    ], name="MNIST_CNN_Classifier")

    # Compile model with Adam optimizer and sparse categorical crossentropy
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )

    model.summary()
    return model


def plot_and_save_learning_curves(history):
    """
    Plots high-contrast, publication-quality training & validation accuracy
    and loss curves, saving them as accuracy.png and loss.png.
    """
    epochs = range(1, len(history.history['accuracy']) + 1)
    acc = history.history['accuracy']
    val_acc = history.history['val_accuracy']
    loss = history.history['loss']
    val_loss = history.history['val_loss']

    # 1. Accuracy Plot
    plt.figure(figsize=(8, 5), facecolor='#0b0f19')
    ax1 = plt.axes()
    ax1.set_facecolor('#111827')
    plt.plot(epochs, acc, 'o-', color='#3b82f6', linewidth=2.5, label='Training Accuracy')
    plt.plot(epochs, val_acc, 's--', color='#10b981', linewidth=2.5, label='Validation Accuracy')
    plt.title('CNN Training & Validation Accuracy', color='#f3f4f6', fontsize=14, pad=12, fontweight='bold')
    plt.xlabel('Epoch', color='#94a3b8', fontsize=11)
    plt.ylabel('Accuracy', color='#94a3b8', fontsize=11)
    plt.grid(True, linestyle='--', alpha=0.3, color='#475569')
    plt.tick_params(colors='#94a3b8')
    plt.legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f3f4f6', loc='lower right')
    acc_path = os.path.join(RESULTS_DIR, 'accuracy.png')
    plt.savefig(acc_path, dpi=200, bbox_inches='tight', facecolor='#0b0f19')
    plt.close()
    print(f"Accuracy graph saved to: {acc_path}")

    # 2. Loss Plot
    plt.figure(figsize=(8, 5), facecolor='#0b0f19')
    ax2 = plt.axes()
    ax2.set_facecolor('#111827')
    plt.plot(epochs, loss, 'o-', color='#ef4444', linewidth=2.5, label='Training Loss')
    plt.plot(epochs, val_loss, 's--', color='#f59e0b', linewidth=2.5, label='Validation Loss')
    plt.title('CNN Training & Validation Loss', color='#f3f4f6', fontsize=14, pad=12, fontweight='bold')
    plt.xlabel('Epoch', color='#94a3b8', fontsize=11)
    plt.ylabel('Cross-Entropy Loss', color='#94a3b8', fontsize=11)
    plt.grid(True, linestyle='--', alpha=0.3, color='#475569')
    plt.tick_params(colors='#94a3b8')
    plt.legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f3f4f6', loc='upper right')
    loss_path = os.path.join(RESULTS_DIR, 'loss.png')
    plt.savefig(loss_path, dpi=200, bbox_inches='tight', facecolor='#0b0f19')
    plt.close()
    print(f"Loss graph saved to: {loss_path}")


def train_cnn():
    """
    Main routine: Loads data, builds CNN, trains model, logs metrics, and exports artifacts.
    """
    # 1. Load data
    (x_train, y_train), (x_val, y_val), (x_test, y_test) = load_and_preprocess_data()

    # 2. Build model
    model = build_cnn_model()

    # 3. Callbacks
    early_stop = callbacks.EarlyStopping(
        monitor='val_loss',
        patience=3,
        restore_best_weights=True,
        verbose=1
    )
    reduce_lr = callbacks.ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=2,
        min_lr=1e-5,
        verbose=1
    )

    # 4. Train Model
    print("\n" + "=" * 70)
    print("STEP 3: TRAINING CNN MODEL")
    print("=" * 70)
    batch_size = 128
    epochs = 10

    history = model.fit(
        x_train, y_train,
        batch_size=batch_size,
        epochs=epochs,
        validation_data=(x_val, y_val),
        callbacks=[early_stop, reduce_lr],
        verbose=1
    )

    # 5. Save learning curves
    plot_and_save_learning_curves(history)

    # 6. Save trained model
    print("\n" + "=" * 70)
    print(f"STEP 4: SAVING TRAINED MODEL TO {MODEL_PATH}")
    print("=" * 70)
    model.save(MODEL_PATH)
    print(f"Model successfully saved to: {MODEL_PATH}")

    return model, history


if __name__ == '__main__':
    train_cnn()

