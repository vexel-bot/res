"""Executable canonical compositions, selected from product purpose and prepared materials.

These recipes compose supplied assets. They never synthesize a new world/person/event,
nor treat a material uploaded by a customer as independent proof of a claim.
"""

import json
from pathlib import Path

from ...domain.studios.contracts import MediaTimelineV1
from .ad_material_roles import ROLES

REQUIREMENTS = {
    "action_progression": ["demo", "demo"],
    "motif_continuity": ["state_before", "state_after"],
    "gesture_occlusion_reveal": ["state_before", "state_after", "occluder"],
    "moving_variant_mask": ["state_before", "state_after", "matte"],
    "subject_occluded_typography": ["presenter", "subject_cutout"],
    "windowed_content_scroll": ["scroll_content", "window_frame"],
    "interface_evidence_overlay": ["presenter", "interface"],
    "world_to_world_identity": ["state_before", "state_after"],
    "localized_generated_event": ["clean_plate", "event_cutout"],
    "layer_inventory_animation": ["clean_plate", "product_cutout", "product_cutout"],
    "continuous_panel_canvas": ["panorama"],
    "cutout_object_stack": ["clean_plate", "product_cutout", "product_cutout"],
}
LABELS = {
    "action_progression": "Demonstração em sequência",
    "motif_continuity": "Continuidade do produto",
    "gesture_occlusion_reveal": "Revelação com oclusor",
    "moving_variant_mask": "Troca de variante por máscara",
    "subject_occluded_typography": "Texto atrás do apresentador",
    "windowed_content_scroll": "Conteúdo rolando dentro de uma janela",
    "interface_evidence_overlay": "Interface como evidência",
    "world_to_world_identity": "Passagem entre mundos preparados",
    "localized_generated_event": "Evento composto em cenário preservado",
    "layer_inventory_animation": "Inventário animado em camadas",
    "continuous_panel_canvas": "Percurso em painel contínuo",
    "cutout_object_stack": "Montagem de produtos recortados",
}
GOALS = {
    "demonstrate": {"action_progression", "interface_evidence_overlay", "windowed_content_scroll"},
    "explain": {"subject_occluded_typography", "interface_evidence_overlay", "continuous_panel_canvas"},
    "variants": {"moving_variant_mask", "motif_continuity", "gesture_occlusion_reveal"},
    "showcase": {"cutout_object_stack", "layer_inventory_animation", "continuous_panel_canvas"},
    "transformation": {"gesture_occlusion_reveal", "world_to_world_identity", "localized_generated_event"},
}
CHECKS = {
    "action_progression": ["Cada corte avança a ação", "Antes e depois são compreensíveis", "Cortes preservam o sentido da demonstração"],
    "motif_continuity": ["O mesmo produto/assunto é reconhecível", "Posição e escala têm continuidade", "O segundo plano acrescenta informação"],
    "gesture_occlusion_reveal": ["A revelação acompanha o oclusor", "Não há vazamento nas bordas", "O resultado da transformação fica visível"],
    "moving_variant_mask": ["Fontes e máscara permanecem alinhadas", "Rótulo e forma do produto são preservados", "A variante está legível ao final"],
    "subject_occluded_typography": ["Texto permanece atrás do assunto", "Bordas não tremem nem criam halos", "A mensagem é compreensível e rosto/mãos ficam preservados"],
    "windowed_content_scroll": ["Moldura fica imóvel e sem vazamentos", "Texto importante permanece dentro da janela", "A rolagem termina em informação relevante"],
    "interface_evidence_overlay": ["Captura corresponde à afirmação ao lado", "Texto é legível no celular", "A montagem não inventa uma funcionalidade"],
    "world_to_world_identity": ["Identidade reconhecível nos dois estados", "Figurino, escala e movimento coerentes", "Mudança de mundo serve ao conceito"],
    "localized_generated_event": ["Cenário e câmera permanecem coerentes", "Evento tem entrada e consequência visíveis", "Escala, contato e sombras são plausíveis"],
    "layer_inventory_animation": ["Cada objeto mantém forma e rótulo", "Trajetórias e ordem das camadas são coerentes", "Movimento destaca o produto sem esconder a mensagem"],
    "continuous_panel_canvas": ["Motivo visual permanece contínuo", "Rostos e textos respeitam as áreas seguras", "Percurso entre os painéis é compreensível"],
    "cutout_object_stack": ["Recortes sem bordas indesejadas", "Sobreposição e profundidade são coerentes", "Produtos permanecem reconhecíveis e legíveis"],
}


def cards(kit):
    research = json.loads(Path(__file__).with_name("instagram_editing_operations.v1.json").read_text(encoding="utf-8"))
    counts = {}
    for entry in kit.get("materials", []):
        counts[entry["role"]] = counts.get(entry["role"], 0) + 1
    answers = []
    for item in research["operations"]:
        identifier = item["id"]
        required = REQUIREMENTS[identifier]
        if identifier == "subject_occluded_typography" and counts.get("matte"):
            required = ["presenter", "matte"]
        needed = {role: required.count(role) for role in required}
        missing = [f"{ROLES[role]} ({amount - counts.get(role, 0)})" for role, amount in needed.items() if counts.get(role, 0) < amount]
        if identifier in {"motif_continuity", "world_to_world_identity", "gesture_occlusion_reveal", "moving_variant_mask", "subject_occluded_typography"}:
            roles = set(required)
            groups = {entry.get("alignmentGroup", "") for entry in kit.get("materials", []) if entry["role"] in roles}
            if len(groups) != 1 or not next(iter(groups), ""):
                missing.append("grupo de alinhamento/identidade comum declarado para as fontes")
        relevant = identifier in GOALS.get(kit.get("goal"), set())
        score = 2 if relevant else 0
        reason = "Serve ao objetivo informado e usa os materiais disponíveis." if relevant else "Não é a primeira escolha para o objetivo informado."
        if kit.get("category") in {"software", "service"} and identifier == "interface_evidence_overlay":
            score += 1
            reason = "A captura da interface pode demonstrar o serviço/software enquanto o apresentador mantém o contexto. Conferir se sustenta a afirmação."
        if kit.get("category") == "physical" and kit.get("goal") == "showcase" and identifier == "cutout_object_stack":
            score += 2
            reason = "Produto físico para apresentação: os recortes preservam rótulo e forma e permitem organizar as variantes em profundidade."
        if kit.get("goal") == "variants" and identifier == "moving_variant_mask":
            score += 2
            reason = "Comparação de variantes: uma máscara alinhada revela a diferença mantendo o enquadramento. Conferir registro e rótulos."
        answers.append({
            "id": identifier, "label": LABELS[identifier], "status": "blocked" if missing else "ready_to_compose",
            "missing": missing, "score": score, "reason": reason,
            "executionScope": "composition_of_supplied_assets",
            "engine": "ffmpeg.timeline-v1",
            "qualityStatus": "requires_render_review",
            "requirements": needed, "checks": CHECKS[identifier], "researchChecks": item["render_checks"], "rejectWhen": item["reject_when"],
            "sources": [f"https://www.instagram.com/reel/{reel}/" for reel in item["evidence_reels"]],
            "limitation": "Esta receita compõe os materiais preparados. Envie os arquivos ou use a preparação automática local quando disponível. Identidade, sentido, bordas e alegações exigem revisão do vídeo.",
        })
    return sorted(answers, key=lambda item: (item["status"] != "ready_to_compose", -item["score"], item["id"]))


def compose(identifier, kit, text, *, fps=24, seconds=6, width=1080, height=1920):
    card = next((item for item in cards(kit) if item["id"] == identifier), None)
    if not card or card["status"] != "ready_to_compose":
        raise ValueError("ad_recipe_materials_missing")
    by_role = {}
    for entry in kit["materials"]:
        by_role.setdefault(entry["role"], []).append(entry)
    n = fps * seconds
    tracks = []

    def clip(role, index=0, *, start=0, duration=None, transform=None, keys=None):
        entry = by_role[role][index]
        return {"id": f"item-{len(tracks)}-{role}-{index}", "assetId": entry["assetId"],
                "timeline": {"startFrame": start, "durationFrames": duration or n},
                "transform": {"originalAudioEnabled": False, **(transform or {})}, "keyframes": keys or []}

    def track(*items):
        tracks.append({"id": f"track-{len(tracks)}", "kind": "overlay", "clips": list(items)})
        return tracks[-1]["id"]

    def keys(prop, a, b):
        return [{"property": prop, "frame": 0, "value": a}, {"property": prop, "frame": n - 1, "value": b, "easing": "ease-in-out"}]

    if identifier == "action_progression":
        half = n // 2
        track(clip("demo", 0, duration=half), clip("demo", 1, start=half, duration=n-half))
    elif identifier in {"motif_continuity", "world_to_world_identity"}:
        half = n // 2
        track(clip("state_before", duration=half), clip("state_after", start=half, duration=n-half))
    elif identifier in {"gesture_occlusion_reveal", "moving_variant_mask"}:
        track(clip("state_before"))
        target = track(clip("state_after", keys=keys("revealProgress", 0, 1)))
        if identifier == "moving_variant_mask":
            tracks.append({"id": "variant-matte", "kind": "mask", "targetTrackId": target,
                           "artifactAssetId": by_role["matte"][0]["assetId"]})
        else:
            track(clip("occluder", keys=keys("x", -width*.5, width*.5)))
    elif identifier == "subject_occluded_typography":
        track(clip("presenter"))
        tracks.append({"id": "headline", "kind": "caption", "cues": [{"id": "headline-text", "text": text,
            "timeline": {"startFrame": 0, "durationFrames": n}, "style": {"fontSize": min(140, round(width*.22)), "fontFamily": "system", "color": "#ffffff"},
            "motion": {"y": -round(height*.5)}}]})
        if "matte" in by_role:
            target = track(clip("presenter"))
            tracks.append({"id":"subject-matte","kind":"mask","targetTrackId":target,"artifactAssetId":by_role["matte"][0]["assetId"]})
        else:
            track(clip("subject_cutout"))
    elif identifier == "windowed_content_scroll":
        track(clip("scroll_content", transform={"crop": {"height": 0.5}}, keys=keys("cropY", 0, 1)))
        track(clip("window_frame"))
    elif identifier == "interface_evidence_overlay":
        track(clip("presenter"))
        track(clip("interface", transform={"scale": 0.7, "y": round(height*.16), "fadeInFrames": 8}))
    elif identifier == "localized_generated_event":
        track(clip("clean_plate"))
        track(clip("event_cutout", keys=keys("x", -width*.5, 0)))
    elif identifier in {"layer_inventory_animation", "cutout_object_stack"}:
        track(clip("clean_plate"))
        track(clip("product_cutout", 0, transform={"scale": 0.65, "x": -width*.11}, keys=keys("y", height*.34, height*.05)))
        track(clip("product_cutout", 1, transform={"scale": 0.65, "x": width*.11}, keys=keys("y", -height*.34, -height*.05)))
    elif identifier == "continuous_panel_canvas":
        track(clip("panorama", transform={"crop": {"width": 0.333333}}, keys=keys("cropX", 0, 1)))
    return MediaTimelineV1.model_validate({"durationFrames": n, "frameRate": {"numerator": fps, "denominator": 1}, "tracks": tracks})
