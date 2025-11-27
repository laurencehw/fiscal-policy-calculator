"""
Reporting and Visualization Module

Generates formatted reports and visualizations for fiscal policy analysis.
"""

from dataclasses import dataclass
import numpy as np
from typing import Optional, Literal
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from .scoring import ScoringResult
from .baseline import BaselineProjection


class BudgetReport:
    """
    Generate comprehensive budget reports for fiscal policy analysis.
    """
    
    def __init__(self, result: ScoringResult):
        self.result = result
        self.years = result.years
    
    def generate_text_report(self) -> str:
        """Generate a detailed text report."""
        lines = []
        
        # Header
        lines.append("=" * 70)
        lines.append("FISCAL POLICY SCORING REPORT")
        lines.append("=" * 70)
        lines.append("")
        
        # Policy summary
        lines.append("POLICY SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Name: {self.result.policy.name}")
        lines.append(f"Description: {self.result.policy.description}")
        lines.append(f"Effective: {self.result.policy.start_year} - "
                    f"{self.result.policy.start_year + self.result.policy.duration_years - 1}")
        lines.append("")
        
        # Key metrics
        lines.append("KEY BUDGET METRICS ($ billions)")
        lines.append("-" * 40)
        lines.append(f"10-Year Static Cost:        {self.result.total_static_cost:>12,.1f}")
        lines.append(f"Behavioral Offset:          {np.sum(self.result.behavioral_offset):>12,.1f}")
        if self.result.is_dynamic:
            lines.append(f"Economic Feedback:          {self.result.revenue_feedback_10yr:>12,.1f}")
        lines.append(f"10-Year Net Cost:           {self.result.total_10_year_cost:>12,.1f}")
        lines.append("")
        lines.append(f"Uncertainty Range (90% CI): {np.sum(self.result.low_estimate):>10,.1f} to "
                    f"{np.sum(self.result.high_estimate):,.1f}")
        lines.append("")
        
        # Year-by-year table
        lines.append("YEAR-BY-YEAR EFFECTS ($ billions)")
        lines.append("-" * 70)
        
        header = f"{'Year':>6} {'Revenue':>10} {'Spending':>10} {'Static':>10} "
        if self.result.is_dynamic:
            header += f"{'Feedback':>10} "
        header += f"{'Final':>10} {'Range':>20}"
        lines.append(header)
        lines.append("-" * 70)
        
        for i, year in enumerate(self.years):
            row = f"{year:>6} "
            row += f"{self.result.static_revenue_effect[i]:>10,.1f} "
            row += f"{self.result.static_spending_effect[i]:>10,.1f} "
            row += f"{self.result.static_deficit_effect[i]:>10,.1f} "
            if self.result.is_dynamic:
                row += f"{self.result.dynamic_effects.revenue_feedback[i]:>10,.1f} "
            row += f"{self.result.final_deficit_effect[i]:>10,.1f} "
            row += f"{self.result.low_estimate[i]:>8,.1f} to {self.result.high_estimate[i]:>8,.1f}"
            lines.append(row)
        
        lines.append("-" * 70)
        total_row = f"{'TOTAL':>6} "
        total_row += f"{np.sum(self.result.static_revenue_effect):>10,.1f} "
        total_row += f"{np.sum(self.result.static_spending_effect):>10,.1f} "
        total_row += f"{self.result.total_static_cost:>10,.1f} "
        if self.result.is_dynamic:
            total_row += f"{self.result.revenue_feedback_10yr:>10,.1f} "
        total_row += f"{self.result.total_10_year_cost:>10,.1f} "
        total_row += f"{np.sum(self.result.low_estimate):>8,.1f} to {np.sum(self.result.high_estimate):>8,.1f}"
        lines.append(total_row)
        lines.append("")
        
        # Economic effects if dynamic
        if self.result.is_dynamic:
            lines.append("ECONOMIC EFFECTS")
            lines.append("-" * 40)
            de = self.result.dynamic_effects
            lines.append(f"Average GDP Effect:     {np.mean(de.gdp_percent_change):>10.2f}%")
            lines.append(f"Peak GDP Effect:        {np.max(de.gdp_percent_change):>10.2f}%")
            lines.append(f"Avg Employment Change:  {np.mean(de.employment_change):>10,.0f} thousand")
            lines.append(f"Cumulative GDP Effect:  ${np.sum(de.gdp_level_change):>10,.0f}B")
            lines.append("")
        
        # Notes
        lines.append("NOTES")
        lines.append("-" * 40)
        lines.append("- Positive values indicate increases in deficit/costs")
        lines.append("- Revenue effects are shown as changes from baseline")
        lines.append("- Uncertainty range represents 90% confidence interval")
        if self.result.is_dynamic:
            lines.append("- Economic feedback includes GDP effects on revenues")
        lines.append("")
        
        return "\n".join(lines)
    
    def plot_budget_effects(self, 
                           save_path: Optional[str] = None,
                           show: bool = True) -> plt.Figure:
        """
        Create visualization of budget effects over time.
        """
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(f"Budget Effects: {self.result.policy.name}", 
                    fontsize=14, fontweight='bold')
        
        # 1. Deficit effect over time with uncertainty
        ax1 = axes[0, 0]
        ax1.fill_between(self.years, self.result.low_estimate, 
                        self.result.high_estimate, alpha=0.3, color='blue',
                        label='90% CI')
        ax1.plot(self.years, self.result.final_deficit_effect, 
                'b-', linewidth=2, label='Central estimate')
        ax1.plot(self.years, self.result.static_deficit_effect, 
                'g--', linewidth=1.5, label='Static estimate')
        ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax1.set_xlabel('Year')
        ax1.set_ylabel('Deficit Effect ($ billions)')
        ax1.set_title('Annual Deficit Impact')
        ax1.legend(loc='best')
        ax1.yaxis.set_major_formatter(mticker.StrMethodFormatter('${x:,.0f}'))
        ax1.grid(True, alpha=0.3)
        
        # 2. Cumulative effect
        ax2 = axes[0, 1]
        cumulative = np.cumsum(self.result.final_deficit_effect)
        cumulative_low = np.cumsum(self.result.low_estimate)
        cumulative_high = np.cumsum(self.result.high_estimate)
        
        ax2.fill_between(self.years, cumulative_low, cumulative_high, 
                        alpha=0.3, color='red')
        ax2.plot(self.years, cumulative, 'r-', linewidth=2)
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax2.set_xlabel('Year')
        ax2.set_ylabel('Cumulative Effect ($ billions)')
        ax2.set_title('Cumulative Deficit Impact')
        ax2.yaxis.set_major_formatter(mticker.StrMethodFormatter('${x:,.0f}'))
        ax2.grid(True, alpha=0.3)
        
        # 3. Components breakdown
        ax3 = axes[1, 0]
        width = 0.35
        x = np.arange(len(self.years))
        
        ax3.bar(x - width/2, self.result.static_spending_effect, width, 
               label='Spending', color='red', alpha=0.7)
        ax3.bar(x + width/2, -self.result.static_revenue_effect, width,
               label='Revenue Change', color='green', alpha=0.7)
        ax3.set_xlabel('Year')
        ax3.set_ylabel('$ billions')
        ax3.set_title('Revenue vs Spending Effects')
        ax3.set_xticks(x)
        ax3.set_xticklabels(self.years)
        ax3.legend()
        ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax3.grid(True, alpha=0.3, axis='y')
        
        # 4. Economic effects (if dynamic) or summary pie
        ax4 = axes[1, 1]
        if self.result.is_dynamic:
            ax4_twin = ax4.twinx()
            
            ax4.bar(self.years, self.result.dynamic_effects.gdp_percent_change,
                   color='purple', alpha=0.6, label='GDP Effect (%)')
            ax4_twin.plot(self.years, self.result.dynamic_effects.employment_change,
                         'o-', color='orange', linewidth=2, label='Employment')
            
            ax4.set_xlabel('Year')
            ax4.set_ylabel('GDP Effect (%)', color='purple')
            ax4_twin.set_ylabel('Employment Change (thousands)', color='orange')
            ax4.set_title('Economic Effects')
            ax4.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            
            # Combined legend
            lines1, labels1 = ax4.get_legend_handles_labels()
            lines2, labels2 = ax4_twin.get_legend_handles_labels()
            ax4.legend(lines1 + lines2, labels1 + labels2, loc='best')
        else:
            # Summary breakdown
            labels = ['Static\nRevenue', 'Static\nSpending', 'Behavioral\nOffset']
            values = [
                abs(np.sum(self.result.static_revenue_effect)),
                np.sum(self.result.static_spending_effect),
                abs(np.sum(self.result.behavioral_offset))
            ]
            colors = ['green', 'red', 'blue']
            
            # Filter out zero values
            non_zero = [(l, v, c) for l, v, c in zip(labels, values, colors) if v > 0]
            if non_zero:
                labels, values, colors = zip(*non_zero)
                ax4.pie(values, labels=labels, colors=colors, autopct='%1.1f%%',
                       startangle=90)
                ax4.set_title('Cost Components')
            else:
                ax4.text(0.5, 0.5, 'No significant components', 
                        ha='center', va='center', transform=ax4.transAxes)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        if show:
            plt.show()
        
        return fig
    
    def plot_comparison(self, 
                       other_results: list[ScoringResult],
                       labels: Optional[list[str]] = None,
                       save_path: Optional[str] = None) -> plt.Figure:
        """
        Compare multiple policy scoring results.
        """
        all_results = [self.result] + other_results
        n_policies = len(all_results)
        
        if labels is None:
            labels = [r.policy.name for r in all_results]
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # 1. 10-year totals comparison
        ax1 = axes[0]
        x = np.arange(n_policies)
        totals = [r.total_10_year_cost for r in all_results]
        lows = [np.sum(r.low_estimate) for r in all_results]
        highs = [np.sum(r.high_estimate) for r in all_results]
        
        colors = plt.cm.Set2(np.linspace(0, 1, n_policies))
        bars = ax1.bar(x, totals, color=colors)
        ax1.errorbar(x, totals, 
                    yerr=[np.array(totals) - np.array(lows), 
                          np.array(highs) - np.array(totals)],
                    fmt='none', color='black', capsize=5)
        
        ax1.set_xlabel('Policy')
        ax1.set_ylabel('10-Year Cost ($ billions)')
        ax1.set_title('Total 10-Year Budget Impact')
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels, rotation=45, ha='right')
        ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax1.yaxis.set_major_formatter(mticker.StrMethodFormatter('${x:,.0f}'))
        
        # Add value labels
        for bar, total in zip(bars, totals):
            height = bar.get_height()
            ax1.annotate(f'${total:,.0f}B',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=9)
        
        # 2. Time series comparison
        ax2 = axes[1]
        for i, (result, label) in enumerate(zip(all_results, labels)):
            ax2.plot(result.years, result.final_deficit_effect, 
                    '-', linewidth=2, label=label, color=colors[i])
        
        ax2.set_xlabel('Year')
        ax2.set_ylabel('Annual Deficit Effect ($ billions)')
        ax2.set_title('Year-by-Year Comparison')
        ax2.legend(loc='best')
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax2.yaxis.set_major_formatter(mticker.StrMethodFormatter('${x:,.0f}'))
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        plt.show()
        return fig
    
    def export_to_csv(self, filepath: str):
        """Export results to CSV file."""
        df = self.result.to_dataframe()
        df.to_csv(filepath, index=False)
        print(f"Results exported to {filepath}")
    
    def export_to_excel(self, filepath: str):
        """Export results to Excel file with multiple sheets."""
        import pandas as pd
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Main results
            df = self.result.to_dataframe()
            df.to_excel(writer, sheet_name='Budget Effects', index=False)
            
            # Summary
            summary = pd.DataFrame({
                'Metric': [
                    '10-Year Static Cost',
                    'Behavioral Offset',
                    'Revenue Feedback' if self.result.is_dynamic else 'N/A',
                    '10-Year Net Cost',
                    'Low Estimate',
                    'High Estimate',
                ],
                'Value ($ billions)': [
                    self.result.total_static_cost,
                    np.sum(self.result.behavioral_offset),
                    self.result.revenue_feedback_10yr if self.result.is_dynamic else 0,
                    self.result.total_10_year_cost,
                    np.sum(self.result.low_estimate),
                    np.sum(self.result.high_estimate),
                ]
            })
            summary.to_excel(writer, sheet_name='Summary', index=False)
            
            # Economic effects if available
            if self.result.is_dynamic:
                econ = pd.DataFrame({
                    'Year': self.years,
                    'GDP Effect ($B)': self.result.dynamic_effects.gdp_level_change,
                    'GDP Effect (%)': self.result.dynamic_effects.gdp_percent_change,
                    'Employment (thousands)': self.result.dynamic_effects.employment_change,
                    'Revenue Feedback ($B)': self.result.dynamic_effects.revenue_feedback,
                })
                econ.to_excel(writer, sheet_name='Economic Effects', index=False)
        
        print(f"Results exported to {filepath}")


def create_comparison_table(results: list[ScoringResult]) -> str:
    """Create a text comparison table for multiple policies."""
    lines = []
    lines.append("POLICY COMPARISON TABLE")
    lines.append("=" * 80)
    
    # Header
    header = f"{'Policy':<30} {'10-Yr Cost':>12} {'Avg/Year':>12} {'Dynamic':>8}"
    lines.append(header)
    lines.append("-" * 80)
    
    for r in results:
        name = r.policy.name[:28] + ".." if len(r.policy.name) > 30 else r.policy.name
        row = f"{name:<30} ${r.total_10_year_cost:>10,.1f}B ${r.average_annual_cost:>10,.1f}B "
        row += "Yes" if r.is_dynamic else "No"
        lines.append(row)
    
    lines.append("-" * 80)
    
    # Totals if multiple
    if len(results) > 1:
        total_cost = sum(r.total_10_year_cost for r in results)
        lines.append(f"{'COMBINED TOTAL':<30} ${total_cost:>10,.1f}B")
    
    return "\n".join(lines)

