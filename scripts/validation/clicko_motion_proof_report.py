"""Create a local comparison sheet, a blinded review packet, and a proof index."""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import random
import shutil
from statistics import median
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont


MODES = ("baseline", "knowledge", "orchestrated")
LABELS = {"baseline": "Atual", "knowledge": "Fichas", "orchestrated": "Orquestrado"}


def sample(file, time):
    raw = subprocess.check_output([
        "ffmpeg", "-v", "error", "-ss", str(time), "-i", str(file), "-frames:v", "1",
        "-vf", "scale=204:300:force_original_aspect_ratio=decrease", "-f", "image2pipe", "-vcodec", "png", "pipe:1"
    ])
    return Image.open(BytesIO(raw)).convert("RGB")


def contact(root, brief_id, results):
    times = (.65, 3.6, 5.1, 9.35)
    width, height = 204, 136 if brief_id == "06" else 320
    sheet = Image.new("RGB", (width*len(times), height*len(MODES)), "#172420")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for row, mode in enumerate(MODES):
        if mode not in results:
            continue
        for col, time in enumerate(times):
            frame = sample(root/results[mode]["renderResult"]["file"], time)
            sheet.paste(frame, (col*width+(width-frame.width)//2, row*height))
            draw.text((col*width+8,row*height+height-18), f"{LABELS[mode]} | {time:g}s", fill="#ffffff", font=font)
    name = f"quadros-{brief_id}.jpg"
    sheet.save(root/name, quality=88)
    return name


def blind(root, briefs, state):
    complete = [b for b in briefs if all(
        state["cases"].get(b["id"], {}).get(mode, {}).get("renderResult") for mode in MODES
    )]
    if not complete:
        return
    folder = root/"avaliacao-cega"
    rng = random.Random(state["run"])
    mapping = {}
    arms = [[], [], []]
    for brief in complete:
        brief_id = brief["id"]
        ordering = list(MODES)
        rng.shuffle(ordering)
        for arm, mode in enumerate(ordering):
            row = state["cases"][brief_id][mode]
            code = sha256((state["run"]+brief_id+mode).encode()).hexdigest()[:10]
            filename = code+".mp4"
            media = folder/f"grupo-{arm+1}"/"videos"
            media.mkdir(parents=True, exist_ok=True)
            dst = media/filename
            if not dst.exists() or sha256(dst.read_bytes()).hexdigest() != row["renderResult"]["fileHash"]:
                shutil.copyfile(root/row["renderResult"]["file"], dst)
            mapping[code] = {"briefId":brief_id,"variant":mode,"group":arm+1}
            arms[arm].append((code,filename))
    for arm, rows in enumerate(arms, 1):
        rng.shuffle(rows)
        lines = [
            f"# Avaliação cega · grupo {arm}", "",
            "Assista a cada vídeo uma vez no celular, com som. Registre a primeira resposta antes de voltar ao vídeo.",
            "Responda sem consultar outros grupos. Use apenas um código anônimo.", "",
            "| Vídeo | O que aconteceu ou mudou? | Qual era o produto ou a ação? | Leitura (1–5) | Acabamento (1–5) |",
            "|---|---|---|---|---|"
        ]
        lines += [f"| [{code}](videos/{filename}) |  |  |  |  |" for code, filename in rows]
        (folder/f"grupo-{arm}"/"instrucoes.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    (root/"chave-privada-da-avaliacao.json").write_text(json.dumps(mapping,indent=2),encoding="utf-8")


def main(root):
    state = json.loads((root/"receipts.json").read_text(encoding="utf-8"))
    briefs = json.loads((root/"briefs-e-gabaritos.json").read_text(encoding="utf-8"))
    table = ["| Brief | Atual | Fichas | Orquestrado | Quadros |", "|---|---|---|---|---|"]
    count = 0
    preview_passes = 0
    times = {mode: [] for mode in MODES}
    for brief in briefs:
        brief_id = brief["id"]
        results = {mode:row for mode,row in state["cases"].get(brief_id, {}).items() if row.get("renderResult")}
        count += len(results)
        preview_passes += int(results.get("orchestrated",{}).get("task",{}).get("result",{}).get("editorial",{})
                              .get("preview",{}).get("status") == "passed_technical")
        links = []
        for mode in MODES:
            row = results.get(mode)
            if not row:
                links.append("Pendente")
                continue
            result = row["renderResult"]
            assert row["task"]["externalCostUsd"] == 0 and result["externalCostUsd"] == 0
            assert result["checksumSha256"] == result["fileHash"]
            times[mode].append((row["task"]["result"]["planningTimeMs"] / 1000, result["processingSeconds"]))
            file = row["renderResult"]["file"].replace(chr(92), "/")
            links.append(f"[MP4]({file}) · [Editar](http://127.0.0.1:3000/studios/video/motion?document={row['documentId']})")
        image = f"[Amostras]({contact(root,brief_id,results)})" if results else "Pendente"
        table.append("| "+brief_id+" · "+brief["name"]+" | "+" | ".join(links+[image])+" |")
    blind(root,briefs,state)
    timings = ["| Braço | Mediana do planejamento | Mediana da exportação |", "|---|---:|---:|"]
    for mode, measured in times.items():
        if measured:
            planning, rendering = zip(*measured, strict=True)
            timings.append(f"| {LABELS[mode]} | {median(planning):.2f} s | {median(rendering):.2f} s |")
    refinement = []
    if state.get("refined"):
        refinement = [
            "A inspeção visual inicial encontrou a marca cortada. A Clicko passou a usar a proporção do arquivo para enquadrar logos e capturas. "
            "Os braços com fichas e orquestração dos casos 01 e 06 foram exportados novamente com a mesma fonte. "
            "As versões anteriores estão em `antes-da-correcao/`. A correção aconteceu antes da avaliação com espectadores.", ""
        ]
    lines = [
        "# Laboratório de edição da Clicko", "",
        f"**{count}/18 exportações locais concluídas**. As propostas, projetos e renders usam a Clicko. Custo adicional de API **US$ 0,00**.",
        "",
        "O fluxo atual aplica a regra local de transição aos títulos. Os outros braços consultam fichas. O terceiro também planeja a revisão, renderiza a prévia e executa as verificações disponíveis. A prova fixa mídia, copy, trilha, motor e duração por brief.",
        "",
        *table, "",
        *refinement,
        f"Prévia aprovada pelas verificações técnicas em **{preview_passes}/6** casos orquestrados. "
        f"Reexecução idempotente {'verificada' if state.get('replay') else 'pendente'}. "
        f"Recusa de revisão desatualizada {'verificada' if state.get('staleCheck') else 'pendente'}.",
        "",
        *timings, "",
        "O tempo de planejamento do braço orquestrado inclui a prévia e a revisão técnica. Os três braços têm uma proposta inicial por brief, com até um reparo localizado dentro da revisão orquestrada.", "",
        "As amostras e verificações técnicas demonstram execução. A compreensão e a preferência permanecem inconclusivas até a rodada cega. A avaliação contém três pastas separadas. Distribua apenas a pasta do grupo atribuído, com uma versão por brief. Mantenha a chave com quem coordena, separada de quem corrige.",
        "",
        "Antes da coleta, atribua cada participante aleatoriamente a um dos três grupos em blocos balanceados. Um avaliador sem a chave marca a compreensão espontânea de cada resposta usando os dois elementos do gabarito. Ambos presentes valem 1. Menos que isso vale 0. Registre também artefatos e comentários. Para preferência, use uma segunda rodada com ordem de apresentação alternada após a etapa de compreensão.",
        "",
        "Os seis briefs constituem uma prova exploratória. Para uma decisão de promoção, use 16 briefs inéditos como ponto de partida, dimensione espectadores e briefs com a variância do piloto, fixe a amostra e análise antes de coletar. Compare orquestrado versus atual com intervalo de 95% agrupado por brief. O critério é ganho de pelo menos 15 pontos percentuais, intervalo excluindo zero e ausência de falha grave de leitura ou identidade.",
        "",
        "[Recibos e controles](receipts.json) · [Gabaritos](briefs-e-gabaritos.json) · [Grupo 1](avaliacao-cega/grupo-1/instrucoes.md) · [Grupo 2](avaliacao-cega/grupo-2/instrucoes.md) · [Grupo 3](avaliacao-cega/grupo-3/instrucoes.md)", ""
    ]
    (root/"relatorio.md").write_text("\n".join(lines),encoding="utf-8")
    print(f"{count}/18 local exports indexed")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
