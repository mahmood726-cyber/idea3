#!/usr/bin/env python3
"""
Generate publication-ready figures for Synthesis section
Two figures total for 1000-word version
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.patches import Rectangle

# Set publication-quality style
plt.style.use('seaborn-v0_8-paper')
sns.set_palette("colorblind")
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 9
plt.rcParams['figure.titlesize'] = 13

# Load data
benchmark = pd.read_csv('benchmark_FINAL.csv')
effect_modifiers = pd.read_csv('effect_modifiers_FINAL.csv')
sensitivity = pd.read_csv('sensitivity_analysis_FINAL.csv')

# =============================================================================
# FIGURE 1: Method Comparison
# =============================================================================

fig1, axes = plt.subplots(1, 3, figsize=(14, 4.5))
fig1.suptitle('Figure 1: Comparative Performance of Treatment Effect Estimation Methods',
              fontsize=13, fontweight='bold', y=1.02)

# Define colors for each method
colors = {
    'Constant ATE': '#d62728',  # red
    'Linear + Study FE': '#2ca02c',  # green
    'T-Learner': '#ff7f0e',  # orange
    'S-Learner': '#9467bd',  # purple
    'Causal Forest + Study': '#1f77b4'  # blue
}

methods = benchmark['label'].values
method_colors = [colors[m] for m in methods]

# Panel A: PEHE (Precision in Estimation of Heterogeneous Effects)
ax1 = axes[0]
bars1 = ax1.barh(methods, benchmark['PEHE'], color=method_colors, alpha=0.8, edgecolor='black', linewidth=0.5)
ax1.set_xlabel('PEHE (lower is better)', fontweight='bold')
ax1.set_title('A. Precision in Effect Estimation', fontweight='bold', pad=10)
ax1.invert_yaxis()
ax1.axvline(x=0.8, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='Target threshold')
ax1.grid(axis='x', alpha=0.3, linestyle=':')

# Add value labels
for i, (method, val) in enumerate(zip(methods, benchmark['PEHE'])):
    ax1.text(val + 0.05, i, f'{val:.3f}', va='center', fontsize=8)

# Highlight best performers
best_pehe = benchmark['PEHE'].min()
for i, val in enumerate(benchmark['PEHE']):
    if val < best_pehe + 0.05:  # Within 5% of best
        ax1.add_patch(Rectangle((0, i-0.4), val, 0.8, fill=False,
                                edgecolor='darkgreen', linewidth=2, linestyle='-'))

# Panel B: R² (Explained Variance in Treatment Effect Heterogeneity)
ax2 = axes[1]
r2_values = benchmark['R²_heterogeneity'].values
bars2 = ax2.barh(methods, r2_values, color=method_colors, alpha=0.8, edgecolor='black', linewidth=0.5)
ax2.set_xlabel('R² (higher is better)', fontweight='bold')
ax2.set_title('B. Explained Treatment Effect Variance', fontweight='bold', pad=10)
ax2.invert_yaxis()
ax2.set_yticks([])
ax2.axvline(x=0.7, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='Good performance')
ax2.grid(axis='x', alpha=0.3, linestyle=':')

# Add value labels
for i, (method, val) in enumerate(zip(methods, r2_values)):
    ax2.text(val + 0.03, i, f'{val:.3f}', va='center', fontsize=8)

# Highlight best performers
best_r2 = r2_values.max()
for i, val in enumerate(r2_values):
    if val > best_r2 - 0.05:  # Within 5% of best
        ax2.add_patch(Rectangle((0, i-0.4), val, 0.8, fill=False,
                                edgecolor='darkgreen', linewidth=2, linestyle='-'))

# Panel C: Correlation between Predicted and True Effects
ax3 = axes[2]
corr_values = benchmark['Correlation'].values
bars3 = ax3.barh(methods, corr_values, color=method_colors, alpha=0.8, edgecolor='black', linewidth=0.5)
ax3.set_xlabel('Correlation (higher is better)', fontweight='bold')
ax3.set_title('C. Prediction-Truth Correlation', fontweight='bold', pad=10)
ax3.invert_yaxis()
ax3.set_yticks([])
ax3.axvline(x=0.85, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='Strong correlation')
ax3.grid(axis='x', alpha=0.3, linestyle=':')

# Add value labels
for i, (method, val) in enumerate(zip(methods, corr_values)):
    if val < 0:  # Handle negative/zero correlation (constant ATE)
        ax3.text(0.05, i, f'{val:.3f}', va='center', fontsize=8, color='red')
    else:
        ax3.text(val + 0.03, i, f'{val:.3f}', va='center', fontsize=8)

# Highlight best performers
best_corr = corr_values.max()
for i, val in enumerate(corr_values):
    if val > best_corr - 0.05:  # Within 5% of best
        ax3.add_patch(Rectangle((0, i-0.4), val, 0.8, fill=False,
                                edgecolor='darkgreen', linewidth=2, linestyle='-'))

plt.tight_layout()
plt.savefig('synthesis_figure1_methods_comparison.png', dpi=300, bbox_inches='tight')
print("✓ Figure 1 saved: synthesis_figure1_methods_comparison.png")

# =============================================================================
# FIGURE 2: Effect Modifiers and Sensitivity Analysis
# =============================================================================

fig2, axes = plt.subplots(1, 2, figsize=(14, 5))
fig2.suptitle('Figure 2: Effect Modification Patterns and Sensitivity Analysis',
              fontsize=13, fontweight='bold', y=1.00)

# Panel A: Effect Modifier Importance (SHAP values)
ax1 = axes[0]

# Select top 6 effect modifiers for clarity
top_modifiers = effect_modifiers.nlargest(6, 'SHAP_Importance')
features = top_modifiers['Feature'].values
importance = top_modifiers['SHAP_Importance'].values

# Create color gradient based on importance
cmap = plt.cm.Blues
norm = plt.matplotlib.colors.Normalize(vmin=0, vmax=importance.max())
bar_colors = [cmap(norm(val)) for val in importance]

bars = ax1.barh(features, importance, color=bar_colors, alpha=0.85, edgecolor='black', linewidth=0.5)
ax1.set_xlabel('SHAP Importance (Mean |SHAP Value|)', fontweight='bold')
ax1.set_title('A. Treatment Effect Modifiers', fontweight='bold', pad=10)
ax1.invert_yaxis()
ax1.grid(axis='x', alpha=0.3, linestyle=':')

# Add value labels
for i, (feat, val) in enumerate(zip(features, importance)):
    ax1.text(val + 0.02, i, f'{val:.3f}', va='center', fontsize=9, fontweight='bold')

# Add interpretation markers
age_importance = importance[0]
ax1.axvline(x=age_importance/2, color='red', linestyle='--', linewidth=1,
           alpha=0.5, label='50% of max importance')

# Add text annotation for dominant modifier
ax1.annotate('Dominant\nModifier',
            xy=(age_importance, 0), xytext=(age_importance-0.15, 0.8),
            arrowprops=dict(arrowstyle='->', color='darkred', lw=1.5),
            fontsize=9, color='darkred', fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.3))

ax1.legend(loc='lower right', fontsize=8)

# Panel B: Sensitivity Analysis
ax2 = axes[1]

# Prepare sensitivity data
# Extract different parameter configurations
n_trees_data = sensitivity[sensitivity['label'].str.contains('n_trees')]
min_leaf_data = sensitivity[sensitivity['label'].str.contains('min_leaf')]

# Create grouped bar chart
x_pos = np.arange(len(n_trees_data))
width = 0.35

# Extract values
n_trees_labels = ['40 trees', '100 trees', '200 trees']
n_trees_pehe = n_trees_data['PEHE'].values

min_leaf_labels = ['leaf=5', 'leaf=10', 'leaf=20']
min_leaf_pehe = min_leaf_data['PEHE'].values

# Plot bars
bars1 = ax2.bar(x_pos - width/2, n_trees_pehe, width, label='Number of Trees',
               color='steelblue', alpha=0.8, edgecolor='black', linewidth=0.5)
bars2 = ax2.bar(x_pos + width/2, min_leaf_pehe, width, label='Min Leaf Size',
               color='coral', alpha=0.8, edgecolor='black', linewidth=0.5)

ax2.set_ylabel('PEHE (lower is better)', fontweight='bold')
ax2.set_title('B. Robustness to Hyperparameters', fontweight='bold', pad=10)
ax2.set_xticks(x_pos)
ax2.set_xticklabels(['Config 1', 'Config 2', 'Config 3'], fontsize=9)
ax2.legend(loc='upper right', fontsize=9)
ax2.grid(axis='y', alpha=0.3, linestyle=':')
ax2.set_ylim(0.7, 0.9)

# Add value labels on bars
for i, (bar1, bar2) in enumerate(zip(bars1, bars2)):
    height1 = bar1.get_height()
    height2 = bar2.get_height()
    ax2.text(bar1.get_x() + bar1.get_width()/2., height1 + 0.005,
            f'{height1:.3f}', ha='center', va='bottom', fontsize=7, fontweight='bold')
    ax2.text(bar2.get_x() + bar2.get_width()/2., height2 + 0.005,
            f'{height2:.3f}', ha='center', va='bottom', fontsize=7, fontweight='bold')

# Add horizontal line for reference (default configuration)
default_pehe = n_trees_data[n_trees_data['label'] == 'n_trees=100']['PEHE'].values[0]
ax2.axhline(y=default_pehe, color='green', linestyle='--', linewidth=1.5,
           alpha=0.7, label=f'Default config (PEHE={default_pehe:.3f})')

# Add shaded region for acceptable performance
ax2.axhspan(0.75, 0.85, alpha=0.1, color='green', label='Acceptable range')

# Add detailed configuration info as text box
config_text = (
    f"Number of Trees:\n"
    f"  40: PEHE={n_trees_pehe[0]:.3f}\n"
    f"  100: PEHE={n_trees_pehe[1]:.3f}\n"
    f"  200: PEHE={n_trees_pehe[2]:.3f}\n"
    f"\n"
    f"Min Leaf Size:\n"
    f"  5: PEHE={min_leaf_pehe[0]:.3f}\n"
    f"  10: PEHE={min_leaf_pehe[1]:.3f}\n"
    f"  20: PEHE={min_leaf_pehe[2]:.3f}"
)
ax2.text(0.02, 0.98, config_text, transform=ax2.transAxes,
        fontsize=7, verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

ax2.legend(loc='upper left', fontsize=7, framealpha=0.9)

plt.tight_layout()
plt.savefig('synthesis_figure2_modifiers_sensitivity.png', dpi=300, bbox_inches='tight')
print("✓ Figure 2 saved: synthesis_figure2_modifiers_sensitivity.png")

print("\n" + "="*70)
print("SYNTHESIS FIGURES GENERATION COMPLETE")
print("="*70)
print("\nGenerated files:")
print("  1. synthesis_figure1_methods_comparison.png")
print("     - Panel A: PEHE comparison across methods")
print("     - Panel B: R² (explained variance) comparison")
print("     - Panel C: Prediction-truth correlation")
print("\n  2. synthesis_figure2_modifiers_sensitivity.png")
print("     - Panel A: Top effect modifiers (SHAP importance)")
print("     - Panel B: Sensitivity analysis (hyperparameters)")
print("\nBoth figures are publication-ready at 300 DPI")
print("="*70)

plt.close('all')
