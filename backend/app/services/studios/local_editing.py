"""Bounded Portuguese edit rules; unsupported/ambiguous requests never guess targets.

No model inference takes place here. All results still pass the same proposal
validator, revision check and journal as LLM-generated commands.
"""

import re


def targeted_edit(contract, text, instruction, selected_ids):
    layers = contract.composition.pages[0].layers
    if not layers:
        return None
    literal = re.search(r'["“]([^"”]+)["”]', instruction)
    # Quoted replacement text is data, not another editing instruction.
    text = re.sub(r'["“][^"”]*["”]', "", text)
    intent = re.sub(r'["“][^"”]*["”]', "", instruction)
    literal_edit = bool(
        literal and re.search(r"\b(?:mude|altere|troque|substitua)\b", text) and ("titulo" in text or "texto" in text)
    )
    ordinals = {
        name: index
        for index, name in enumerate(
            ("primeira", "segunda", "terceira", "quarta", "quinta", "sexta", "setima", "oitava", "nona", "decima"), 1
        )
    }
    scene = re.search(r"(?:\bcena\s*([+-]?\d+)\b|\b(" + "|".join(ordinals) + r")\s+cena)", text)
    candidates = list(layers)
    if selected_ids:
        candidates = [layer for layer in candidates if layer.id in selected_ids]
    if scene:
        index = int(scene[1]) if scene[1] else ordinals[scene[2]]
        scenes = contract.composition.narrative.get("localProduction", {}).get("scenes", [])
        if not 1 <= index <= len(scenes):
            return [], "A cena solicitada não existe neste projeto."
        ids = scenes[index - 1].get("layerIds", [])
        candidates = [layer for layer in candidates if layer.id in ids]

    words = "palavra por palavra" in text
    font = "fonte" in text or "negrito" in text
    transition = "transicao" in text or "suav" in text
    dynamic = "dinamic" in text
    shadow = "sombra" in text
    movement = "esquerda" in text and "direita" in text
    color = re.search(r"#[0-9a-fA-F]{6}\b", intent)
    colors = {"coral": "#FF7F50", "tangerina": "#F28500", "branco": "#FFFFFF", "preto": "#000000", "cinza": "#808080"}
    color_value = color[0] if color else next((value for name, value in colors.items() if name in text), None)
    color_edit = bool(color_value and (color or any(word in text for word in ("cor", "titulo", "cart", "texto"))))
    if not color_value and re.search(r"\b(?:mude|altere|troque)\b.*\bcor\b", text):
        return [], "Informe a nova cor em #RRGGBB ou uma cor da marca, por exemplo coral ou tangerina."
    if (
        not literal
        and re.search(r"\b(?:mude|altere|troque|substitua)\b", text)
        and any(word in text for word in ("titulo", "texto"))
        and not any((words, font, transition, dynamic, shadow, movement, color_edit, "duracao" in text))
    ):
        return [], 'Informe o novo texto entre aspas, por exemplo: Altere o título para "Inove hoje".'
    duration_edit = "duracao" in text and (
        selected_ids or scene or any(word in text for word in ("animacao", "elemento", "camada"))
    )
    if any(word in text for word in ("duracao do projeto", "duracao do video", "duracao do motion")):
        duration_edit = False
    if not any((literal_edit, words, font, transition, dynamic, shadow, movement, color_edit, duration_edit)):
        return None
    if "fundo" in text and color_value:
        return None  # Existing explicit page-background rule.
    if literal_edit or words or font or "titulo" in text or "texto" in text:
        candidates = [layer for layer in candidates if layer.kind == "text"]
    elif "cart" in text:
        candidates = [layer for layer in candidates if layer.kind == "shape" and "accent" not in layer.id]
    if not candidates:
        return [], "Nenhum elemento compatível foi encontrado na seleção/cena."
    if any(layer.locked for layer in candidates):
        return [], "Há elementos bloqueados no alvo. Desbloqueie-os ou refine a seleção."
    if literal_edit and "primeiro" in text and not selected_ids and not scene:
        candidates = candidates[:1]
    # Explicit plural categories or scene/selection define scope. Singular asks
    # for clarification rather than modifying an arbitrary title across scenes.
    plural = any(word in text for word in ("titulos", "textos", "cartoes", "elementos", "todos", "todas", "cenas"))
    if len(candidates) > 1 and not (scene or selected_ids or plural or transition):
        return [], "Selecione o elemento ou indique a cena; existem vários alvos possíveis."
    if font and not any(word in text for word in ("sistema", "segoe", "regular", "negrito")):
        return [], "Escolha a fonte do sistema (Segoe UI), regular ou negrito. Não baixamos fontes externas."
    timeline = contract.composition.media_timeline
    if (words or transition or dynamic or movement or duration_edit) and not timeline:
        return [], "Animação exige um projeto de vídeo/motion. A imagem estática foi preservada."
    commands = []
    for target in candidates:
        layer = target.model_dump(mode="json", by_alias=True)
        style = layer["properties"]
        length = style.get("durationFrames") or (timeline.duration_frames if timeline else 1)
        if literal_edit:
            style["text"] = literal[1]
        if font:
            style.update(fontFamily="system", fontWeight=400 if "regular" in text or "sem negrito" in text else 700)
        if color_edit:
            if target.kind == "image":
                return [], "Cor de imagem usa os ajustes visuais; selecione um texto ou uma forma."
            style["color" if target.kind == "text" else "fill"] = color_value
        if shadow:
            style["shadow"] = not any(word in text for word in ("remova", "retire", "sem sombra"))
        if words:
            count = len(style.get("text", "").split())
            if not 1 <= count <= 32 or length < count:
                return [], "Texto longo demais para a revelação local; reduza a 32 palavras ou aumente a duração."
            style.update(textReveal="words", wordStaggerFrames=min(6, max(1, (length - 1) // count)))
        keys = style.get("keyframes", [])
        if duration_edit:
            match = re.search(r"(\d{1,3}(?:[.,]\d{1,2})?)\s*(?:segundos?|s\b)", text)
            if not match:
                return [], "Informe a duração da animação em segundos, por exemplo: para 2 segundos."
            desired = round(
                float(match[1].replace(",", ".")) * timeline.frame_rate.numerator / timeline.frame_rate.denominator
            )
            if re.search(r"(?:em|mais)\s*$", text[: match.start()]):
                desired = length + (-desired if any(word in text for word in ("reduza", "diminua")) else desired)
            available = timeline.duration_frames - style.get("startFrame", 0)
            if not 1 <= desired <= available:
                return (
                    [],
                    "A animação precisa caber no projeto. Ajuste primeiro a duração total sem selecionar camadas.",
                )
            ratio = desired / length
            retimed = {
                (key["property"], min(desired, round(key["frame"] * ratio))): {
                    **key,
                    "frame": min(desired, round(key["frame"] * ratio)),
                }
                for key in keys
            }
            keys = list(retimed.values())
            style["durationFrames"] = desired
            if style.get("textReveal") == "words":
                style["wordStaggerFrames"] = max(1, min(120, round(style.get("wordStaggerFrames", 6) * ratio)))
            length = desired

        def replace_keys(property, points):
            nonlocal keys
            keys = [key for key in keys if key["property"] != property] + [
                {"property": property, "frame": frame, "value": value, "easing": "ease-in-out"}
                for frame, value in sorted(dict(points).items())
            ]

        if transition:
            fade = max(1, min(18, length // 3))
            replace_keys("opacity", [(0, 0), (fade, 1), (length - fade, 1), (length, 0)])
        if movement:
            replace_keys("x", [(0, -40), (length, 40)])
        if dynamic:
            replace_keys("scale", [(0, 0.96), (min(18, length // 2), 1), (length, 1.025)])
            replace_keys("rotation", [(0, -1), (length, 1)])
        style["keyframes"] = keys
        commands.append({"id": "layer.upsert", "params": {"layer": layer}})
    return commands, (
        f"Editar {len(commands)} elemento(s) por regras locais, preservando os demais. "
        "Transformações 2D; não é inferência nem perspectiva 3D."
    )
