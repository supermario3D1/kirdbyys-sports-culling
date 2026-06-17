"""Export service for top selections, CSV, XLSX, XMP, PDF."""
import os
import shutil
import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from kirdbyys.config import settings

class ExportService:
    """Export selected images in various formats."""
    
    def __init__(self, project_id: int):
        self.project_id = project_id
        self.export_dir = settings.EXPORT_DIR / f"project_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.export_dir.mkdir(parents=True, exist_ok=True)
    
    def export_copy(self, images: List[Dict[str, Any]], destination: str) -> str:
        dest = Path(destination)
        dest.mkdir(parents=True, exist_ok=True)
        for img in images:
            src = img.get("original_path") or img.get("project_path")
            if src and Path(src).exists():
                shutil.copy2(src, dest / Path(src).name)
        return str(dest)
    
    def export_move(self, images: List[Dict[str, Any]], destination: str) -> str:
        dest = Path(destination)
        dest.mkdir(parents=True, exist_ok=True)
        for img in images:
            src = img.get("original_path") or img.get("project_path")
            if src and Path(src).exists():
                shutil.move(src, dest / Path(src).name)
        return str(dest)
    
    def export_csv(self, images: List[Dict[str, Any]], filename: str = "kirdbyys_export.csv") -> str:
        path = self.export_dir / filename
        if not images:
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["No images selected"])
            return str(path)
        
        keys = ["id", "filename", "rank", "final_score", "technical_score", "action_score", 
                "storytelling_score", "composition_score", "moments", "explanation", 
                "original_path", "selected"]
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            writer.writeheader()
            for img in images:
                row = {k: img.get(k) for k in keys}
                row["moments"] = ", ".join(img.get("moments", []))
                writer.writerow(row)
        return str(path)
    
    def export_xlsx(self, images: List[Dict[str, Any]], filename: str = "kirdbyys_export.xlsx") -> str:
        path = self.export_dir / filename
        if not images:
            wb = Workbook()
            wb.save(path)
            return str(path)
        
        rows = []
        for img in images:
            rows.append({
                "ID": img.get("id"),
                "Filename": img.get("filename"),
                "Rank": img.get("rank"),
                "Final Score": img.get("final_score"),
                "Technical": img.get("technical_score"),
                "Action": img.get("action_score"),
                "Storytelling": img.get("storytelling_score"),
                "Composition": img.get("composition_score"),
                "Moments": ", ".join(img.get("moments", [])),
                "Explanation": img.get("explanation", ""),
                "Original Path": img.get("original_path", ""),
                "Selected": img.get("selected", False)
            })
        df = pd.DataFrame(rows)
        df.to_excel(path, index=False, sheet_name="Kirdbyys Export")
        return str(path)
    
    def export_xmp(self, images: List[Dict[str, Any]], rating: bool = True, label: bool = True) -> str:
        xmp_dir = self.export_dir / "xmp"
        xmp_dir.mkdir(parents=True, exist_ok=True)
        for img in images:
            src = img.get("original_path") or img.get("project_path")
            if not src:
                continue
            base = Path(src).stem
            xmp_path = xmp_dir / f"{base}.xmp"
            star_rating = min(5, max(1, int(round(img.get("final_score", 50) / 20))))
            color = "Red" if img.get("selected") else "Yellow"
            xmp = f"""<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Kirdbyys Sports Culling Tool">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:xmp="http://ns.adobe.com/xap/1.0/"
    xmlns:xmpRating="http://ns.adobe.com/xap/1.0/">
    <xmp:Rating>{star_rating}</xmp:Rating>
    <xmp:Label>{color}</xmp:Label>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>"""
            with open(xmp_path, "w") as f:
                f.write(xmp)
        return str(xmp_dir)
    
    def export_pdf_report(self, images: List[Dict[str, Any]], project_name: str, filename: str = "kirdbyys_report.pdf") -> str:
        # Try reportlab; fallback to HTML if not installed
        path = self.export_dir / filename
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet
            
            doc = SimpleDocTemplate(str(path), pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            story.append(Paragraph(f"Kirdbyys Sports Culling Report — {project_name}", styles["Title"]))
            story.append(Paragraph(f"Generated: {datetime.now().isoformat()}", styles["Normal"]))
            story.append(Spacer(1, 12))
            
            data = [["Rank", "Filename", "Score", "Technical", "Action", "Story", "Comp", "Moments"]]
            for img in images[:50]:
                data.append([
                    img.get("rank"), img.get("filename")[:30], round(img.get("final_score", 0), 1),
                    round(img.get("technical_score", 0), 1), round(img.get("action_score", 0), 1),
                    round(img.get("storytelling_score", 0), 1), round(img.get("composition_score", 0), 1),
                    ", ".join(img.get("moments", []))[:25]
                ])
            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0F172A")),
                ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
                ("ALIGN", (0,0), (-1,-1), "CENTER"),
                ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F1F5F9")])
            ]))
            story.append(table)
            doc.build(story)
        except Exception as e:
            # Fallback: write HTML report
            html_path = self.export_dir / filename.replace(".pdf", ".html")
            rows = ""
            for img in images[:50]:
                rows += f"<tr><td>{img.get('rank')}</td><td>{img.get('filename')}</td><td>{img.get('final_score')}</td><td>{', '.join(img.get('moments', []))}</td></tr>"
            html = f"""<html><head><title>Kirdbyys Report</title></head><body>
<h1>Kirdbyys Report — {project_name}</h1>
<table border='1'><tr><th>Rank</th><th>Filename</th><th>Score</th><th>Moments</th></tr>{rows}</table>
</body></html>"""
            with open(html_path, "w") as f:
                f.write(html)
            path = html_path
        return str(path)
    
    def export(self, images: List[Dict[str, Any]], mode: str, destination: Optional[str] = None) -> str:
        if mode == "copy":
            return self.export_copy(images, destination or self.export_dir / "copies")
        elif mode == "move":
            return self.export_move(images, destination or self.export_dir / "moved")
        elif mode == "csv":
            return self.export_csv(images)
        elif mode == "xlsx":
            return self.export_xlsx(images)
        elif mode == "xmp":
            return self.export_xmp(images)
        elif mode == "pdf":
            return self.export_pdf_report(images, "Project")
        else:
            raise ValueError(f"Unsupported export mode: {mode}")