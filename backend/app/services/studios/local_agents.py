"""Cost-zero planning adapters. Template execution is explicit; it is not LLM inference."""

import re
import unicodedata

from ...domain.studios.agents import AgentOutput
from ...domain.studios.contracts import CreativeCompositionV1, CreativeDocumentV1
from .local_editing import targeted_edit


def normalized(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c))


def history_undo(contract, instruction, versions, selected_ids=()):
    """Propose the immediately preceding saved composition; never mutate here.

    This is a versioned restore, not a model or an invented browser undo stack.
    The orchestrator applies the normal revision, locks, asset and scope checks.
    """
    if not re.fullmatch(
        r"(?:por favor[, ]*)?(?:desfaca|desfazer)\s+(?:a\s+)?ultima\s+(?:alteracao|edicao)[.!]?",
        normalized(instruction).strip(),
    ):
        return None
    if selected_ids:
        return AgentOutput(
            commands=[], rationale="Desmarque a seleção para restaurar a última versão salva do projeto."
        )
    if not versions:
        return AgentOutput(commands=[], rationale="Não há uma versão salva anterior para desfazer.")
    previous = CreativeDocumentV1.model_validate(versions[-1].get("canonicalDocument", {}))
    if (
        previous.document_id != contract.document_id
        or previous.workspace_id != contract.workspace_id
        or previous.content_type != contract.content_type
        or previous.native_editor_state
    ):
        raise ValueError("agent_history_snapshot_invalid")
    return AgentOutput(
        commands=[
            {"id": "composition.replace", "params": {"composition": previous.composition.model_dump(by_alias=True)}}
        ],
        rationale=(
            "Restaurar a composição da versão salva anterior, após sua revisão e aplicação. "
            "Uma nova revisão será criada, sem apagar as versões ou exportações existentes."
        ),
    )


def visual_card(identifier, name, x, y, width, height, color, start, length, z):
    """The image role supplies editable graphic elements to the audiovisual role."""
    return {
        "id": identifier,
        "kind": "shape",
        "name": name,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "zIndex": z,
        "properties": {
            "schemaVersion": "studio.local-layer.v1",
            "fill": color,
            "radius": 18,
            "startFrame": start,
            "durationFrames": length,
            "keyframes": [
                {"property": "x", "frame": 0, "value": -35},
                {"property": "x", "frame": min(18, length), "value": 0, "easing": "ease-out"},
            ],
        },
    }


class ImageAgent:
    role = "image"

    def __init__(self):
        self.requests = []

    def card(self, *args):
        self.requests.append({"operation": "shape.plan", "elementId": args[0]})
        return visual_card(*args)

    def plan(self, contract, instruction, selected_ids=()):
        return plan(contract, instruction, self.role, self, selected_ids)


class AudiovisualAgent:
    role = "audiovisual"

    def __init__(self, image_agent):
        self.image_agent = image_agent

    def plan(self, contract, instruction, selected_ids=()):
        return plan(contract, instruction, self.role, self.image_agent, selected_ids)


def motion_composition(contract, instruction, image_agent):
    current = contract.composition
    page = current.pages[0]
    fps = 24
    match = re.search(r"(\d{1,3})\s*(?:segundos?|s\b)", normalized(instruction))
    seconds = int(match[1]) if match else 12
    if not 3 <= seconds <= 120:
        raise ValueError("agent_template_duration_between_3_and_120_seconds")
    quoted = re.findall(r'["“]([^"”]{1,120})["”]', instruction)
    topic = re.search(r"sobre\s+(.+?)(?:,|\.|\s+com\s|$)", instruction, re.I)
    subject = (topic[1].strip() if topic else contract.title)[:70]
    headings = quoted[:3] or [subject, "Da ideia à ação", "Crie o próximo passo"]
    total = seconds * fps
    layers, scenes = [], []
    for index, title in enumerate(headings):
        start = round(total * index / len(headings))
        end = round(total * (index + 1) / len(headings))
        length = end - start
        prefix = f"scene-{index + 1}"
        layers.append(
            image_agent.card(
                prefix + "-card",
                f"Cartão · cena {index + 1}",
                page.width * 0.08,
                page.height * 0.14,
                page.width * 0.84,
                page.height * 0.70,
                "#161616",
                start,
                length,
                index * 4,
            )
        )
        card = layers[-1]
        card["properties"].update(gradientEnd="#242424", shadow=True)
        card["properties"]["keyframes"] += [
            {"property": "opacity", "frame": 0, "value": 0},
            {"property": "opacity", "frame": min(12, length // 3), "value": 1, "easing": "ease-in-out"},
            {"property": "opacity", "frame": length - min(12, length // 3), "value": 1},
            {"property": "opacity", "frame": length, "value": 0, "easing": "ease-in-out"},
        ]
        layers.append(
            image_agent.card(
                prefix + "-accent",
                f"Destaque · cena {index + 1}",
                page.width * 0.12,
                page.height * 0.24,
                page.width * 0.12,
                max(8, page.height * 0.018),
                "#FF7F50",
                start,
                length,
                index * 4 + 1,
            )
        )
        text = {
            "id": prefix + "-title",
            "kind": "text",
            "name": f"Título · cena {index + 1}",
            "x": page.width * 0.12,
            "y": page.height * 0.36,
            "width": page.width * 0.74,
            "height": page.height * 0.32,
            "zIndex": index * 4 + 2,
            "properties": {
                "schemaVersion": "studio.local-layer.v1",
                "text": title,
                "fontFamily": "system",
                "fontSize": round(min(page.width / 16, page.height / 9)),
                "color": "#FFFFFF",
                "startFrame": start,
                "durationFrames": length,
                "keyframes": [
                    {"property": "y", "frame": 0, "value": 26},
                    {"property": "y", "frame": 18, "value": 0, "easing": "ease-out"},
                    {"property": "opacity", "frame": 0, "value": 0},
                    {"property": "opacity", "frame": 12, "value": 1},
                    {"property": "opacity", "frame": max(13, length - 12), "value": 1},
                    {"property": "opacity", "frame": length, "value": 0},
                ],
            },
        }
        layers.append(text)
        scenes.append(
            {
                "id": prefix,
                "title": title,
                "startFrame": start,
                "durationFrames": length,
                "layerIds": [prefix + suffix for suffix in ("-card", "-accent", "-title")],
            }
        )
    composition = current.model_dump(mode="json", by_alias=True)
    composition["pages"] = [
        {
            **page.model_dump(mode="json", by_alias=True),
            "layers": layers,
            "background": "#000000",
            "durationMs": seconds * 1000,
        }
    ]
    composition["mediaTimeline"] = {
        "frameRate": {"numerator": fps, "denominator": 1},
        "durationFrames": total,
        "tracks": [],
    }
    composition["narrative"] = {
        **composition["narrative"],
        "localProduction": {
            "kind": "motion",
            "planning": "deterministic_template",
            "scenes": scenes,
            "brief": instruction,
            "delegations": ["audiovisual", "image"],
        },
    }
    return CreativeCompositionV1.model_validate(composition)


def plan(contract, instruction, role, image_agent, selected_ids=()):
    text = normalized(instruction)
    text = re.sub(r'["“][^"”]*["”]', "", text)
    commands, explanation = [], ""
    page = contract.composition.pages[0]
    layers = page.layers
    editing = targeted_edit(contract, text, instruction, selected_ids)
    if re.match(r"^(?:qual\b|quais\b|como\b|o que\b|por que\b|explique\b|me explique\b)", text.strip()):
        explanation = "O modo local prepara edições por regras. Informe uma ação explícita para alterar o projeto."
    elif "remov" in text and "fundo" in text:
        explanation = "Remoção automática de fundo depende de um modelo ainda indisponível."
    elif any(word in text for word in ("cinematograf", "gere uma foto", "gere uma imagem", "gerar cena")):
        explanation = (
            "Geração visual por IA não está disponível neste ambiente; use imagens próprias ou composição local."
        )
    elif (
        contract.content_type == "video"
        and not layers
        and not any(
            getattr(track, "clips", []) or getattr(track, "cues", [])
            for track in contract.composition.media_timeline.tracks
        )
        and any(word in text for word in ("motion", "animad", "crie", "criar"))
    ):
        composition = motion_composition(contract, instruction, image_agent)
        commands = [{"id": "composition.replace", "params": {"composition": composition.model_dump(by_alias=True)}}]
        explanation = (
            "Modelo local de motion com cenas, cartões e títulos editáveis. "
            "Texto organizado por regras, sem inferência de IA."
        )
    elif editing is not None:
        commands, explanation = editing
    elif "duracao" in text:
        match = re.search(r"(\d{1,3})\s*(?:segundos?|s\b)", text)
        if match:
            if selected_ids:
                explanation = "Desmarque a camada para alterar a duração de todo o projeto."
            else:
                commands = [{"id": "project.duration", "params": {"seconds": int(match[1])}}]
                explanation = "Ajustar proporcionalmente a duração das cenas e dos keyframes locais."
    elif re.search(r"#[0-9a-fA-F]{6}\b", instruction):
        color = re.search(r"#[0-9a-fA-F]{6}\b", instruction)[0]
        if "fundo" in text:
            if selected_ids:
                explanation = "Desmarque a camada para alterar o fundo de todo o projeto."
            else:
                commands = [{"id": "project.background", "params": {"color": color}}]
        else:
            for layer in layers:
                if layer.kind == "text" and not layer.locked and (not selected_ids or layer.id in selected_ids):
                    data = layer.model_dump(by_alias=True)
                    data["properties"] = {**data["properties"], "color": color}
                    commands.append({"id": "layer.upsert", "params": {"layer": data}})
        explanation = explanation or "Aplicar a cor hexadecimal solicitada aos elementos disponíveis."
    elif role == "image" and not layers and any(word in text for word in ("crie", "criar", "composicao", "cartao")):
        title = (re.search(r'["“]([^"”]+)["”]', instruction) or [None, contract.title])[1]
        card = image_agent.card(
            "card",
            "Cartão",
            page.width * 0.08,
            page.height * 0.08,
            page.width * 0.84,
            page.height * 0.84,
            "#161616",
            0,
            1,
            0,
        )
        card["properties"] = {"schemaVersion": "studio.local-layer.v1", "fill": "#161616", "radius": 18}
        title_layer = {
            "id": "title",
            "kind": "text",
            "name": "Título",
            "x": page.width * 0.14,
            "y": page.height * 0.30,
            "width": page.width * 0.72,
            "height": page.height * 0.48,
            "zIndex": 1,
            "properties": {
                "schemaVersion": "studio.local-layer.v1",
                "text": title[:120],
                "fontSize": round(page.width / 16),
            },
        }
        commands = [{"id": "layer.upsert", "params": {"layer": layer}} for layer in [card, title_layer]]
        explanation = "Composição local de formas e texto; os elementos continuam editáveis."
    return AgentOutput.model_validate(
        {
            "commands": commands,
            "rationale": explanation
            or (
                "Esse comando não faz parte das regras locais. "
                "Use os controles de propriedades ou configure um LLM local."
            ),
        }
    )
