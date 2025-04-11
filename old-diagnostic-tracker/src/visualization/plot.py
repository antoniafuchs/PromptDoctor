import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

def plot_shap_values(model, X, feature_names):
    """
    Plots SHAP values to visualize the influence of features on model predictions.

    Args:
        model: The trained model used for predictions.
        X: The input data for which SHAP values are calculated.
        feature_names: The names of the features in the input data.
    """
    explainer = shap.Explainer(model)
    shap_values = explainer(X)

    # Create a summary plot
    shap.summary_plot(shap_values, X, feature_names=feature_names)

def plot_accuracy_over_time(log_data):
    """
    Plots the diagnostic accuracy over time based on logged data.

    Args:
        log_data: A DataFrame containing timestamps and accuracy metrics.
    """
    plt.figure(figsize=(10, 5))
    plt.plot(log_data['timestamp'], log_data['accuracy'], marker='o')
    plt.title('Diagnostic Accuracy Over Time')
    plt.xlabel('Time')
    plt.ylabel('Accuracy')
    plt.xticks(rotation=45)
    plt.grid()
    plt.tight_layout()
    plt.show()

def plot_feedback_distribution(feedback_data):
    """
    Plots the distribution of user feedback on model outputs.

    Args:
        feedback_data: A DataFrame containing user feedback.
    """
    feedback_counts = feedback_data['feedback'].value_counts()
    plt.figure(figsize=(8, 5))
    feedback_counts.plot(kind='bar', color=['green', 'red'])
    plt.title('User Feedback Distribution')
    plt.xlabel('Feedback')
    plt.ylabel('Count')
    plt.xticks(rotation=0)
    plt.grid(axis='y')
    plt.tight_layout()
    plt.show()