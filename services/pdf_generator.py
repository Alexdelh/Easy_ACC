import os
import tempfile
import datetime
from io import BytesIO
import plotly.graph_objects as go
from fpdf import FPDF
import streamlit as st

class BilanPDF(FPDF):
    def __init__(self, project_name="Easy ACC"):
        super().__init__()
        self.project_name = project_name
        
    def header(self):
        # Arial bold 15
        self.set_font("Arial", "B", 15)
        # Move to the right
        self.cell(80)
        # Title
        self.cell(30, 10, f"Rapport Bilan - {self.project_name}", align="C")
        # Line break
        self.ln(20)

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Arial italic 8
        self.set_font("Arial", "I", 8)
        # Text color in gray
        self.set_text_color(128)
        # Page number
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

def generate_bilan_pdf(
    state: dict,
    fig_donut_main: go.Figure,
    fig_prod_donut: go.Figure,
    fig_surplus_donut: go.Figure,
    fig_conso_donut: go.Figure,
    fig_acc_donut: go.Figure,
    fig_conso_line: go.Figure,
    fig_prod_line: go.Figure
) -> bytes:
    """
    Generate a formatted PDF report with project details and Plotly charts.
    """
    pdf = BilanPDF(project_name=state.get("project_name", "Projet Anonyme"))
    pdf.add_page()
    
    # 1. Project Information Section
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "1. Informations du Projet", ln=True)
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"Nom : {state.get('project_name', 'N/A')}", ln=True)
    pdf.cell(0, 8, f"Code Postal : {state.get('postal_code', 'N/A')}", ln=True)
    pdf.cell(0, 8, f"Type d'Opération : {state.get('operation_type', 'N/A')}", ln=True)
    pdf.cell(0, 8, f"Contrainte de Distance : {state.get('distance_constraint', 'N/A')}", ln=True)
    
    start_date = state.get("start_date", "N/A")
    end_date = state.get("end_date", "N/A")
    pdf.cell(0, 8, f"Période d'Étude : {start_date} au {end_date}", ln=True)
    pdf.ln(5)

    # Temporary directory to save image buffers because FPDF reads image files
    with tempfile.TemporaryDirectory() as tmpdirname:
        
        # Helper to safely export figures
        def save_fig(fig, filename, width=600, height=400):
            path = os.path.join(tmpdirname, filename)
            # Kaleido engine binary patched locally to support folder spaces
            fig.write_image(path, width=width, height=height, engine="kaleido")
            return path
            
        # 2. Main KPI - Couverture Donut
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "2. Taux de Couverture (Production vs Consommation)", ln=True)
        pdf.ln(5)
        
        don_main_path = save_fig(fig_donut_main, "donut_main.png", width=500, height=300)
        pdf.image(don_main_path, x=20, w=150)
        pdf.ln(5)
        
        # 3. Répartition - Small Donuts
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "3. Répartition de la Production et Consommation", ln=True)
        
        # 2 rows of 2 donuts
        don_p_path = save_fig(fig_prod_donut, "prod.png", width=400, height=400)
        don_s_path = save_fig(fig_surplus_donut, "surp.png", width=400, height=400)
        don_c_path = save_fig(fig_conso_donut, "cons.png", width=400, height=400)
        don_a_path = save_fig(fig_acc_donut, "acc.png", width=400, height=400)
        
        y_pos = pdf.get_y() + 10
        pdf.image(don_p_path, x=10, y=y_pos, w=90)
        pdf.image(don_s_path, x=110, y=y_pos, w=90)
        
        y_pos += 95
        pdf.image(don_c_path, x=10, y=y_pos, w=90)
        pdf.image(don_a_path, x=110, y=y_pos, w=90)
        
        # Move Y to bottom of charts
        pdf.set_y(y_pos + 95)
        
        # 4. Evolution Mensuelle
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "4. Évolution Mensuelle", ln=True)
        
        line_p_path = save_fig(fig_prod_line, "line_p.png", width=800, height=400)
        line_c_path = save_fig(fig_conso_line, "line_c.png", width=800, height=400)
        
        pdf.image(line_p_path, x=10, w=180)
        pdf.ln(5)
        pdf.image(line_c_path, x=10, w=180)

        # Build byte array of PDF
        pdf_bytes = pdf.output(dest='S')
        return pdf_bytes
