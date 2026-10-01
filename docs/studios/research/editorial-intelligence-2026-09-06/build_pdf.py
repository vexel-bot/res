"""Print edition from the canonical research source, without browser rendering."""
from pathlib import Path
import html
import re
import json
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUTPUT = ROOT / "output/pdf/res-inteligencia-editorial-2026-09-06.pdf"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))
pdfmetrics.registerFont(TTFont("ArialBold", "C:/Windows/Fonts/arialbd.ttf"))
pdfmetrics.registerFontFamily("Arial",normal="Arial",bold="ArialBold",italic="Arial",boldItalic="ArialBold")
INK, ACCENT, MUTED = HexColor("#192b36"), HexColor("#087e83"), HexColor("#52656f")
styles = {
 "body":ParagraphStyle("body",fontName="Arial",fontSize=10.2,leading=15,textColor=INK,spaceAfter=10,splitLongWords=True),
 "h1":ParagraphStyle("h1",fontName="ArialBold",fontSize=30,leading=35,textColor=INK,spaceAfter=20),
 "h2":ParagraphStyle("h2",fontName="ArialBold",fontSize=18,leading=23,textColor=ACCENT,spaceBefore=22,spaceAfter=13,keepWithNext=True),
 "h3":ParagraphStyle("h3",fontName="ArialBold",fontSize=12,leading=17,textColor=INK,spaceBefore=14,spaceAfter=9,keepWithNext=True),
 "small":ParagraphStyle("small",fontName="Arial",fontSize=9,leading=13,textColor=MUTED,spaceAfter=9),
 "cell":ParagraphStyle("cell",fontName="Arial",fontSize=8.2,leading=11.3,textColor=INK,splitLongWords=True),
 "th":ParagraphStyle("th",fontName="ArialBold",fontSize=8.2,leading=11.3,textColor=HexColor("#134b56")),
 "list":ParagraphStyle("list",fontName="Arial",fontSize=10.2,leading=15,textColor=INK,leftIndent=15,firstLineIndent=-15,spaceAfter=10),
}
def inline(text):
    text = text.replace("—","-").replace("–","-").replace("‑","-").replace("→"," > ").replace("•"," | ")
    held = []
    def stash(value):
        held.append(value)
        return f"@@TOKEN{len(held)-1}@@"
    text = re.sub(r"`([^`]+)`", lambda m: stash('<font size="8.2">'+html.escape(m[1])+"</font>"), text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: stash('<link href="'+html.escape(m[2],quote=True)+'" color="#076b77">'+html.escape(m[1])+"</link>"),text)
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*",r"<b>\1</b>",text)
    for i,value in enumerate(held):
        text=text.replace(f"@@TOKEN{i}@@",value)
    return text

source=(HERE/"report-source.md").read_text(encoding="utf-8")
story=[Spacer(1,25),Paragraph("RES / PESQUISA E REVISÃO",styles["small"]),Spacer(1,18),Paragraph("De recursos de edição a decisões com intenção",styles["h1"]),Paragraph("Inteligência editorial, análise das referências e capacidades do sistema",styles["h3"]),Spacer(1,18),Paragraph("6 de setembro de 2026",styles["small"]),Paragraph("6 casos reobservados no navegador do GPT<br/>25 técnicas candidatas em três grupos<br/>9 achados prioritários no código",styles["body"]),Spacer(1,20),Paragraph("<b>Conclusão:</b> o res já tem operações úteis, mas precisa conectar compreensão, repertório e construção de cenas para demonstrar edição profissional contextual.",styles["body"]),Paragraph("Preparação para o modo planejamento. A pesquisa não certifica edição universal nem substitui a avaliação de vídeos reais. Áudio dos Reels não verificado por audição.",styles["small"]),Spacer(1,18)]
sections=re.findall(r"^## (.+)$",source,re.M)
story.append(Paragraph("Conteúdo",styles["h3"]))
for title in sections:
    story.append(Paragraph(inline(title),styles["small"]))
story.append(PageBreak())
lines=source.splitlines();i=0
while i<len(lines):
    line=lines[i].strip()
    if not line or line.startswith("# ") or line.startswith("Pesquisa e revisão técnica"):
        i+=1;continue
    heading=re.match(r"^(#{2,3}) (.+)$",line)
    if heading:
        story.append(Paragraph(inline(heading[2]),styles["h2" if len(heading[1])==2 else "h3"]))
        i+=1
    elif line.startswith("|"):
        rows=[]
        while i<len(lines) and lines[i].strip().startswith("|"):
            cells=[c.strip() for c in lines[i].strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-+:?",c) for c in cells):rows.append(cells)
            i+=1
        count=len(rows[0]);width=A4[0]-84
        ratios={3:[.20,.36,.44],4:[.19,.27,.25,.29]}.get(count,[1/count]*count)
        data=[[Paragraph(inline(c),styles["th" if row==0 else "cell"]) for c in cells] for row,cells in enumerate(rows)]
        table=Table(data,colWidths=[width*r for r in ratios],repeatRows=1,hAlign="LEFT")
        table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),HexColor("#e6f1f1")),("ROWBACKGROUNDS",(0,1),(-1,-1),[white,HexColor("#f5f8f9")]),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),("LINEBELOW",(0,0),(-1,-1),.35,HexColor("#d5e1e5"))]))
        story.extend([Spacer(1,5),table,Spacer(1,12)])
    elif re.match(r"^\d+\. ",line):
        story.append(Paragraph(inline(line),styles["list"]));i+=1
    else:
        paragraph=[line];i+=1
        while i<len(lines) and lines[i].strip() and not re.match(r"^(#|\||\d+\. )",lines[i]):
            paragraph.append(lines[i].strip());i+=1
        story.append(Paragraph(inline(" ".join(paragraph)),styles["body"]))

def furniture(c,doc):
    c.saveState();c.setStrokeColor(HexColor("#d5e1e5"));c.line(42,38,A4[0]-42,38)
    c.setFont("Arial",8);c.setFillColor(MUTED)
    c.drawString(42,25,"res | inteligência editorial | 06/09/2026")
    c.drawRightString(A4[0]-42,25,str(doc.page))
    if doc.page>1:
        c.setFont("Arial",7.5);c.drawString(42,A4[1]-28,"PESQUISA E REVISÃO / EDIÇÃO DE VÍDEO")
    c.restoreState()

doc=SimpleDocTemplate(str(OUTPUT),pagesize=A4,leftMargin=42,rightMargin=42,topMargin=46,bottomMargin=52,title="res - Inteligência e repertório para edição de vídeo",author="res | Pesquisa e revisão",pageCompression=1)
doc.build(story,onFirstPage=furniture,onLaterPages=furniture)
print(json.dumps({"pdf":str(OUTPUT),"bytes":OUTPUT.stat().st_size},ensure_ascii=False))
