#!/usr/bin/env python3
"""
ER Diagram Generator for Hotel Management System
This script creates a visual representation of the database schema.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
import numpy as np

def create_er_diagram():
    # Create figure and axis
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 12)
    ax.axis('off')
    
    # Define colors
    entity_color = '#E8F4FD'
    primary_key_color = '#FFE4B5'
    foreign_key_color = '#FFB6C1'
    
    # Entity positions
    entities = {
        'Guest': (3, 9),
        'Room': (13, 9),
        'Booking': (8, 6),
        'Payment': (3, 3),
        'MealTransaction': (13, 3)
    }
    
    # Entity definitions with their attributes
    entity_data = {
        'Guest': {
            'attributes': [
                ('id', 'PK'),
                ('name', ''),
                ('email', ''),
                ('phone', ''),
                ('address', ''),
                ('date_of_birth', ''),
                ('notes', '')
            ]
        },
        'Room': {
            'attributes': [
                ('id', 'PK'),
                ('number', ''),
                ('room_type', ''),
                ('capacity', ''),
                ('price', ''),
                ('is_available', '')
            ]
        },
        'Booking': {
            'attributes': [
                ('id', 'PK'),
                ('guest_id', 'FK'),
                ('room_id', 'FK'),
                ('status', ''),
                ('check_in', ''),
                ('check_out', ''),
                ('total_price', ''),
                ('payment_status', ''),
                ('created_at', ''),
                ('is_checked_in', ''),
                ('checked_out_at', '')
            ]
        },
        'Payment': {
            'attributes': [
                ('id', 'PK'),
                ('booking_id', 'FK'),
                ('amount', ''),
                ('payment_date', ''),
                ('payment_method', ''),
                ('transaction_id', '')
            ]
        },
        'MealTransaction': {
            'attributes': [
                ('id', 'PK'),
                ('booking_id', 'FK'),
                ('meal_name', ''),
                ('category', ''),
                ('quantity', ''),
                ('price_per_unit', ''),
                ('total_price', ''),
                ('transaction_date', '')
            ]
        }
    }
    
    # Draw entities
    for entity_name, (x, y) in entities.items():
        attributes = entity_data[entity_name]['attributes']
        
        # Calculate box height based on number of attributes
        box_height = len(attributes) * 0.3 + 0.5
        box_width = 2.5
        
        # Draw entity box
        entity_box = FancyBboxPatch(
            (x - box_width/2, y - box_height/2),
            box_width, box_height,
            boxstyle="round,pad=0.05",
            facecolor=entity_color,
            edgecolor='black',
            linewidth=1.5
        )
        ax.add_patch(entity_box)
        
        # Draw entity name
        ax.text(x, y + box_height/2 - 0.2, entity_name, 
                ha='center', va='center', fontsize=12, fontweight='bold')
        
        # Draw horizontal line under entity name
        line_y = y + box_height/2 - 0.4
        ax.plot([x - box_width/2 + 0.1, x + box_width/2 - 0.1], 
                [line_y, line_y], 'k-', linewidth=1)
        
        # Draw attributes
        for i, (attr_name, attr_type) in enumerate(attributes):
            attr_y = y + box_height/2 - 0.7 - (i * 0.3)
            
            # Color code attributes
            if attr_type == 'PK':
                color = primary_key_color
                attr_text = f"🔑 {attr_name}"
            elif attr_type == 'FK':
                color = foreign_key_color
                attr_text = f"🔗 {attr_name}"
            else:
                color = 'white'
                attr_text = attr_name
            
            # Draw attribute background
            attr_box = patches.Rectangle(
                (x - box_width/2 + 0.05, attr_y - 0.1),
                box_width - 0.1, 0.2,
                facecolor=color,
                edgecolor='gray',
                linewidth=0.5
            )
            ax.add_patch(attr_box)
            
            # Draw attribute text
            ax.text(x - box_width/2 + 0.1, attr_y, attr_text,
                   ha='left', va='center', fontsize=9)
    
    # Draw relationships
    relationships = [
        # (from_entity, to_entity, relationship_label, from_pos, to_pos)
        ('Guest', 'Booking', '1:N', 'right', 'left'),
        ('Room', 'Booking', '1:N', 'left', 'right'),
        ('Booking', 'Payment', '1:N', 'bottom-left', 'top'),
        ('Booking', 'MealTransaction', '1:N', 'bottom-right', 'top')
    ]
    
    for from_entity, to_entity, label, from_pos, to_pos in relationships:
        from_x, from_y = entities[from_entity]
        to_x, to_y = entities[to_entity]
        
        # Calculate connection points
        if from_pos == 'right':
            start_x, start_y = from_x + 1.25, from_y
        elif from_pos == 'left':
            start_x, start_y = from_x - 1.25, from_y
        elif from_pos == 'bottom-left':
            start_x, start_y = from_x - 0.5, from_y - 1.5
        elif from_pos == 'bottom-right':
            start_x, start_y = from_x + 0.5, from_y - 1.5
        
        if to_pos == 'left':
            end_x, end_y = to_x - 1.25, to_y
        elif to_pos == 'right':
            end_x, end_y = to_x + 1.25, to_y
        elif to_pos == 'top':
            end_x, end_y = to_x, to_y + 1.5
        
        # Draw relationship line
        ax.annotate('', xy=(end_x, end_y), xytext=(start_x, start_y),
                   arrowprops=dict(arrowstyle='->', lw=2, color='blue'))
        
        # Add relationship label
        mid_x = (start_x + end_x) / 2
        mid_y = (start_y + end_y) / 2
        ax.text(mid_x, mid_y + 0.2, label, ha='center', va='center', 
               fontsize=10, fontweight='bold', 
               bbox=dict(boxstyle="round,pad=0.2", facecolor='yellow', alpha=0.7))
    
    # Add title
    ax.text(8, 11.5, 'Hotel Management System - ER Diagram', 
           ha='center', va='center', fontsize=16, fontweight='bold')
    
    # Add legend
    legend_elements = [
        patches.Patch(color=primary_key_color, label='Primary Key (PK)'),
        patches.Patch(color=foreign_key_color, label='Foreign Key (FK)'),
        patches.Patch(color=entity_color, label='Entity'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.98, 0.98))
    
    # Add notes
    notes = [
        "Relationships:",
        "• Guest → Booking (One-to-Many): A guest can have multiple bookings",
        "• Room → Booking (One-to-Many): A room can have multiple bookings over time",
        "• Booking → Payment (One-to-Many): A booking can have multiple payments",
        "• Booking → MealTransaction (One-to-Many): A booking can have multiple meal transactions"
    ]
    
    for i, note in enumerate(notes):
        ax.text(0.5, 1.5 - i*0.2, note, ha='left', va='center', fontsize=9,
               fontweight='bold' if i == 0 else 'normal')
    
    plt.tight_layout()
    plt.savefig('/Users/macbookpro/hotel_demo_wednesday-1/hotel_er_diagram.png', 
                dpi=300, bbox_inches='tight', facecolor='white')
    plt.savefig('/Users/macbookpro/hotel_demo_wednesday-1/hotel_er_diagram.pdf', 
                bbox_inches='tight', facecolor='white')
    
    print("ER Diagram generated successfully!")
    print("Files created:")
    print("- hotel_er_diagram.png (High-resolution image)")
    print("- hotel_er_diagram.pdf (PDF format)")
    
    plt.show()

if __name__ == "__main__":
    create_er_diagram()