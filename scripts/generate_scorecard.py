import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def generate_scorecard():
    # Data Definition
    data = {
        "Benchmark": [
            "Exact Macro F1 (5-class)",
            "Pathogenic F1",
            "Likely Pathogenic F1",
            "Uncertain (VUS) F1",
            "Likely Benign F1",
            "Benign F1"
        ],
        "Description": [
            "Average F1 across all 5 clinical classes",
            "Detection of Pathogenic variants",
            "Detection of Likely Pathogenic variants",
            "Resolution of Uncertain Significance",
            "Detection of Likely Benign variants",
            "Detection of Benign variants"
        ],
        "Gemini 3 Pro": [65.4, 73.7, 57.6, 78.1, 50.0, 67.5],
        "Claude Opus 4.5": [56.0, 57.4, 64.7, 76.2, 53.4, 28.6],
        "GPT-5.2": [12.2, 1.8, 0.0, 53.3, 2.6, 3.3],
        "BIAS-2015": [53.0, 64.1, 16.5, 78.4, 35.4, 70.6],
        "InterVar": [40.2, 45.9, 33.5, 60.1, 44.8, 17.0]
    }

    df = pd.DataFrame(data)
    
    # Setup Plot
    # Increase height to accommodate rows comfortably
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.axis('off')
    
    # Constants
    header_height = 0.08
    row_height = 0.08
    # Columns: Benchmark, Description, Gemini, Claude, GPT, BIAS, InterVar
    col_widths = [0.20, 0.25, 0.13, 0.13, 0.09, 0.10, 0.10] 
    
    # Colors
    gemini_bg_color = "#e8f0fe" # Light blue
    line_color = "#e0e0e0"
    text_color = "#333333"
    
    # Calculate x positions
    total_width_units = sum(col_widths)
    norm_widths = [w / total_width_units for w in col_widths]
    x_pos = [0]
    for w in norm_widths:
        x_pos.append(x_pos[-1] + w)

    # Draw Gemini Background (Column index 2)
    # Background should extend from top to bottom of the data area
    # y-range: logic relies on counting rows
    num_rows = len(df)
    # Shift table down slightly to accommodate AIVA header
    table_top = 0.80 
    table_bottom = table_top - (num_rows + 1) * row_height # +1 for header
    
    # Draw Background for all AIVA Models (Gemini, Claude, GPT)
    # Spanning columns 2, 3, 4
    aiva_bg_width = norm_widths[2] + norm_widths[3] + norm_widths[4]
    
    rect = plt.Rectangle(
        (x_pos[2], table_bottom), 
        aiva_bg_width, 
        (table_top - table_bottom) + (row_height * 0.4), # extend slightly up
        color=gemini_bg_color, 
        zorder=0,
        transform=ax.transAxes
    )
    ax.add_patch(rect)

    # Function to draw text
    def draw_cell(text, x, y, width, height, align='left', weight='normal', size=12, color=text_color, va='center'):
        if align == 'left':
            x_text = x + 0.015
            ha = 'left'
        elif align == 'center':
            x_text = x + width / 2
            ha = 'center'
        elif align == 'right':
            x_text = x + width - 0.015
            ha = 'right'
        
        ax.text(
            x_text, y + height/2, text, 
            ha=ha, va=va, 
            fontsize=size, fontweight=weight, color=color,
            transform=ax.transAxes
        )
    
    # Draw AIVA Super Header
    # Spanning Gemini, Claude, GPT (cols 2, 3, 4)
    aiva_x_start = x_pos[2]
    aiva_width = norm_widths[2] + norm_widths[3] + norm_widths[4]
    aiva_y = table_top + 0.01
    
    # Draw colored bar for AIVA
    ax.add_patch(plt.Rectangle((aiva_x_start, aiva_y), aiva_width, header_height * 0.6, color="#e8f0fe", transform=ax.transAxes, zorder=0))
    draw_cell("AIVA", aiva_x_start, aiva_y, aiva_width, header_height * 0.6, align='center', weight='bold', size=14, color="#1a73e8", va='bottom')
    
    # Draw Baselines Super Header
    # Spanning BIAS, InterVar (cols 5, 6)
    base_x_start = x_pos[5]
    base_width = norm_widths[5] + norm_widths[6]
    
    # Draw colored bar for Baselines
    ax.add_patch(plt.Rectangle((base_x_start, aiva_y), base_width, header_height * 0.6, color="#f1f3f4", transform=ax.transAxes, zorder=0))
    draw_cell("Others", base_x_start, aiva_y, base_width, header_height * 0.6, align='center', weight='bold', size=14, color="#5f6368", va='bottom')

    # Vertical thick divider between AIVA and Baselines
    divider_x = x_pos[5]
    ax.plot([divider_x, divider_x], [table_bottom - row_height, table_top + header_height], color='#888888', linewidth=2, linestyle='-', transform=ax.transAxes)

    # Draw Headers
    headers = list(df.columns)
    current_y = table_top - row_height # Move down for first row (header is a 'row')

    
    # Header Line (Top)
    # ax.plot([0, 1], [table_top, table_top], color='black', linewidth=1, transform=ax.transAxes)

    for i, header in enumerate(headers):
        draw_cell(
            header, x_pos[i], current_y, norm_widths[i], header_height, 
            align='left' if i < 2 else 'left', 
            weight='bold',
            color='#666666',
            size=11
        )
    
    # Header Line (Bottom of header)
    ax.plot([0, 1], [current_y, current_y], color='#dddddd', linewidth=1, transform=ax.transAxes)
    
    # Draw Rows
    models = ["Gemini 3 Pro", "Claude Opus 4.5", "GPT-5.2", "BIAS-2015", "InterVar"]
    
    for idx, row in df.iterrows():
        current_y -= row_height
        
        # Benchmark Name
        draw_cell(row['Benchmark'], x_pos[0], current_y, norm_widths[0], row_height, weight='bold', size=11)
        
        # Description
        draw_cell(row['Description'], x_pos[1], current_y, norm_widths[1], row_height, size=10, color='#666666')
        
        # Values
        values = [row[m] for m in models]
        max_val = max(values)
        
        for i, model in enumerate(models):
            val = row[model]
            is_winner = (val == max_val)
            col_idx = i + 2
            
            text_weight = 'bold' if is_winner else 'normal'
            val_size = 13 if is_winner else 12
            
            val_str = f"{val:.1f}%"
            
            draw_cell(
                val_str, x_pos[col_idx], current_y, norm_widths[col_idx], row_height, 
                align='left', 
                weight=text_weight,
                size=val_size
            )
            
        # Divider Line
        ax.plot([0, 1], [current_y, current_y], color=line_color, linewidth=0.5, transform=ax.transAxes)

    # Add Footer
    current_y -= row_height
    ax.text(
        0, current_y + row_height/2, 
        "Source: Internal Benchmark (n=500 variants). Evaluation date: Jan 10, 2026.", 
        ha='left', va='center', fontsize=10, color='#888888', transform=ax.transAxes
    )

    plt.tight_layout()
    output_path = "figures/figure11_scorecard.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Scorecard saved to {output_path}")

if __name__ == "__main__":
    generate_scorecard()
