"""Lightroom integration: XMP sidecar generation, metadata sync, import/export."""
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from kirdbyys.config import settings

class LightroomService:
    """Generate Lightroom-compatible XMP sidecars and metadata."""
    
    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
    
    def score_to_stars(self, score: float) -> int:
        """Map 0-100 score to 1-5 star rating."""
        return min(5, max(1, int(round(score / 20.0))))
    
    def score_to_label(self, score: float, selected: bool) -> str:
        if selected:
            return "Red"  # Pick
        if score >= 70:
            return "Yellow"  # High potential
        if score >= 45:
            return "Green"  # Maybe
        return "Blue"  # Reject
    
    def generate_xmp_for_image(self, image: Dict[str, Any]) -> str:
        """Generate XMP sidecar XML string."""
        stars = self.score_to_stars(image.get("final_score", 0))
        label = self.score_to_label(image.get("final_score", 0), image.get("selected", False))
        # Also include Kirdbyys metadata as custom namespace
        moments = ", ".join(image.get("moments", []))
        explanation = image.get("explanation", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        xmp = f"""<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Kirdbyys Sports Culling Tool {settings.APP_VERSION}">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:xmp="http://ns.adobe.com/xap/1.0/"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/"
    xmlns:kirdbyys="http://kirdbyys.ai/ns/1.0/">
    <xmp:Rating>{stars}</xmp:Rating>
    <xmp:Label>{label}</xmp:Label>
    <xmp:CreatorTool>Kirdbyys Sports Culling Tool</xmp:CreatorTool>
    <photoshop:Headline>{moments}</photoshop:Headline>
    <dc:description><rdf:Alt><rdf:li xml:lang="x-default">{explanation}</rdf:li></rdf:Alt></dc:description>
    <kirdbyys:FinalScore>{image.get('final_score', 0)}</kirdbyys:FinalScore>
    <kirdbyys:TechnicalScore>{image.get('technical_score', 0)}</kirdbyys:TechnicalScore>
    <kirdbyys:ActionScore>{image.get('action_score', 0)}</kirdbyys:ActionScore>
    <kirdbyys:StorytellingScore>{image.get('storytelling_score', 0)}</kirdbyys:StorytellingScore>
    <kirdbyys:CompositionScore>{image.get('composition_score', 0)}</kirdbyys:CompositionScore>
    <kirdbyys:Moments>{moments}</kirdbyys:Moments>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>"""
        return xmp
    
    def write_sidecars(self, images: List[Dict[str, Any]], sidecar_dir: Optional[str] = None) -> List[str]:
        """Write XMP sidecar next to each image or to specified dir."""
        written = []
        for img in images:
            src = img.get("original_path") or img.get("project_path")
            if not src:
                continue
            base = Path(src).stem
            if sidecar_dir:
                xmp_path = Path(sidecar_dir) / f"{base}.xmp"
            else:
                xmp_path = Path(src).parent / f"{base}.xmp"
            xmp_path.parent.mkdir(parents=True, exist_ok=True)
            with open(xmp_path, "w", encoding="utf-8") as f:
                f.write(self.generate_xmp_for_image(img))
            written.append(str(xmp_path))
        return written
    
    def read_xmp_rating(self, xmp_path: str) -> Dict[str, Any]:
        """Parse simple XMP rating/label from sidecar."""
        result = {"rating": None, "label": None, "moments": None}
        if not Path(xmp_path).exists():
            return result
        try:
            content = Path(xmp_path).read_text(encoding="utf-8")
            import re
            rating_match = re.search(r"<xmp:Rating>(\d)</xmp:Rating>", content)
            label_match = re.search(r"<xmp:Label>([^<]+)</xmp:Label>", content)
            moments_match = re.search(r"<kirdbyys:Moments>([^<]+)</kirdbyys:Moments>", content)
            if rating_match:
                result["rating"] = int(rating_match.group(1))
            if label_match:
                result["label"] = label_match.group(1)
            if moments_match:
                result["moments"] = moments_match.group(1).split(", ")
        except Exception as e:
            print(f"[Kirdbyys] Error reading XMP {xmp_path}: {e}")
        return result
    
    def import_from_lightroom(self, xmp_folder: str) -> List[Dict[str, Any]]:
        """Read all XMP sidecars in a folder and return metadata."""
        folder = Path(xmp_folder)
        results = []
        for xmp in folder.rglob("*.xmp"):
            base = xmp.stem
            # Find corresponding image
            img_path = None
            for ext in settings.SUPPORTED_IMAGE_FORMATS + settings.SUPPORTED_RAW_FORMATS:
                candidate = xmp.parent / f"{base}{ext}"
                if candidate.exists():
                    img_path = str(candidate)
                    break
            meta = self.read_xmp_rating(str(xmp))
            if img_path:
                results.append({"original_path": img_path, "xmp_path": str(xmp), **meta})
        return results