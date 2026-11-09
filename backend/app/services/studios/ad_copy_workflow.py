"""Manual, versioned product discovery and approved copy. Never invokes a provider."""

import json
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from ...models import WorkspaceResource
from .kernel import emit_event

KIND = "ad_copy_workflow"
POLICY = "clicko.ad-copy.manual.v1"
REFERENCE_DIRECTIONS = [
    {
        "id": "creators",
        "label": "@creators — apresentador e prova visual",
        "direction": (
            "Alternar fala, demonstração e inserts quando a afirmação precisa de evidência. Preservar legibilidade."
        ),
        "limits": "Verificar autoria de cada Reel. Recortes PNG e máscaras podem ser compostos no editor; conferir bordas e leitura no render.",
    },
    {
        "id": "paulo-ia",
        "label": "@paulo.ia — continuidade e revelação",
        "direction": "Preservar pessoa, objeto ou pergunta entre os planos. Cada passagem revela uma informação nova.",
        "limits": (
            "Continuidade de identidade e transformações não são garantidas pelo gerador. Precisam de revisão temporal."
        ),
    },
    {
        "id": "moonsol",
        "label": "@moonsol.design — transformação espacial",
        "direction": (
            "Planejar estado inicial, gatilho e estado final com alinhamento de posição, escala e perspectiva."
        ),
        "limits": (
            "Máscaras, placa limpa e oclusão têm mecanismos de composição local. Exigem fontes alinhadas e revisão temporal; geração e segmentação automática continuam separadas."
        ),
    },
]
FIELDS = {
    "product": "Produto e o que ele faz",
    "audience": "Público e contexto de uso",
    "problem": "Problema específico",
    "benefit": "Benefício e seus limites",
    "offer": "Oferta e condições",
    "sources": "Evidências e fontes",
    "objections": "Objeções do comprador",
    "awareness": "Consciência do público (hipótese)",
    "claims": "Afirmações e suas fontes",
    "restrictions": "Restrições e informações que não podem ser prometidas",
    "angle": "Ângulo escolhido e justificativa",
    "hook": "Gancho",
    "body": "Corpo da copy",
    "cta": "Ação desejada",
    "narration": "Texto final para a voz",
    "editingReference": "Referência de edição e o que deve ser adaptado",
    "visualPlan": "Roteiro visual por trecho",
    "reviewNotes": "Achados da revisão e correções",
}
CHECKS = {
    "facts": "Afirmações conferidas com as fontes; sem promessa ou prova inventada.",
    "clear": "O público entende produto, benefício, oferta e próximo passo.",
    "credible": "A prova sustenta a promessa; hipóteses estão identificadas.",
    "engaging": "Gancho e progressão dão motivo para continuar; repetição tem função.",
    "speakable": "Narração lida em voz alta; termos, valores e condições preservados.",
}
STAGES = [
    (
        "Descobrir o produto",
        ["product", "problem", "benefit", "sources"],
        "Extrair fatos, perguntar lacunas e registrar origem. Rosto não descreve uma oferta.",
    ),
    (
        "Entender o comprador",
        ["audience", "objections", "awareness"],
        "Separar dados do cliente de hipóteses sobre dor e consciência.",
    ),
    (
        "Definir oferta e prova",
        ["offer", "claims", "restrictions"],
        "Relacionar cada afirmação à fonte e explicitar condições e limites.",
    ),
    (
        "Escolher a estratégia",
        ["angle", "cta"],
        "Escolher uma promessa sustentada, um ângulo e uma ação coerente com a oferta.",
    ),
    (
        "Escrever a copy",
        ["hook", "body", "cta"],
        "Construir gancho, progressão e CTA. Variantes mudam uma hipótese por vez.",
    ),
    (
        "Traduzir para audiovisual",
        ["narration", "visualPlan", "editingReference"],
        "Separar fala, texto em tela e função das cenas. Medir a voz antes da montagem.",
    ),
    (
        "Revisar e aprovar",
        ["reviewNotes"],
        "Revisão humana de confusão, credibilidade, interesse e fidelidade factual. Sem score automático.",
    ),
]


def assess(data, checks):
    stages = []
    for label, required, criterion in STAGES:
        missing = [FIELDS[name] for name in required if not data.get(name, "").strip()]
        if label == "Revisar e aprovar":
            missing += [text for name, text in CHECKS.items() if not checks.get(name)]
        stages.append(
            {
                "label": label,
                "criterion": criterion,
                "missing": missing,
                "status": "pending" if missing else "filled_needs_human_validation",
            }
        )
    return stages


def row_for(db, workspace_id, target_kind, target_id):
    return db.scalar(
        select(WorkspaceResource).where(
            WorkspaceResource.workspace_id == workspace_id,
            WorkspaceResource.kind == KIND,
            WorkspaceResource.resource_key == f"{target_kind}:{target_id}",
        )
    )


def view(db, workspace_id, target_kind, target_id):
    row = row_for(db, workspace_id, target_kind, target_id)
    state = row.payload if row else {"revision": 0, "status": "draft", "data": {}, "checks": {}}
    return {
        **state,
        "policyVersion": state.get("policyVersion", POLICY),
        "referenceDirections": REFERENCE_DIRECTIONS,
        "targetKind": target_kind,
        "targetId": target_id,
        "fields": FIELDS,
        "checkCriteria": CHECKS,
        "stages": assess(state["data"], state["checks"]),
        "automation": {"discovery": "manual", "copyGeneration": "not_invoked", "apiCalls": 0},
        "handoff": {
            "status": "ready" if state["status"] == "approved" else "pending",
            "note": "Aprovar copy não gera voz, não clona rosto e não renderiza o anúncio.",
        },
    }


def save(db, workspace_id, target_kind, target_id, request, user):
    from .contextual_editing import lock_editing_budget

    lock_editing_budget(db, workspace_id)
    row = row_for(db, workspace_id, target_kind, target_id)
    payload = request.model_dump(mode="json", by_alias=True)
    digest = sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if row and row.payload.get("requestKey") == request.request_key:
        if row.payload.get("digest") != digest:
            raise ValueError("copy_request_conflict")
        return view(db, workspace_id, target_kind, target_id)
    if request.expected_revision != (row.payload["revision"] if row else 0):
        raise ValueError("copy_revision_conflict")
    same_text = bool(row and row.payload["data"] == request.data)
    if request.status == "approved" and not same_text:
        raise ValueError("copy_save_draft_before_approval")
    effective_checks = request.checks if same_text else {}
    missing = [m for stage in assess(request.data, effective_checks) for m in stage["missing"]]
    if request.status == "approved" and missing:
        raise ValueError("copy_approval_requires_complete_dossier_and_review")
    state = {
        "policyVersion": POLICY,
        "revision": request.expected_revision + 1,
        "status": request.status,
        "data": request.data,
        "checks": effective_checks,
        "requestKey": request.request_key,
        "digest": digest,
        "updatedAt": datetime.now(UTC).isoformat(),
        "actorId": user.id,
        "approvedAt": datetime.now(UTC).isoformat() if request.status == "approved" else None,
    }
    if row:
        changed = db.execute(
            update(WorkspaceResource)
            .where(WorkspaceResource.id == row.id, WorkspaceResource.updated_at == row.updated_at)
            .values(payload=state)
        )
        if changed.rowcount != 1:
            raise ValueError("copy_revision_conflict")
    else:
        db.add(
            WorkspaceResource(
                id=str(uuid4()),
                workspace_id=workspace_id,
                kind=KIND,
                resource_key=f"{target_kind}:{target_id}",
                payload=state,
                created_by=user.id,
            )
        )
    emit_event(
        db,
        workspace_id=workspace_id,
        event_type="studio.copy.workflow.saved",
        aggregate_type=KIND,
        aggregate_id=f"{target_kind}:{target_id}",
        correlation_id=request.request_key,
        actor_id=user.id,
        payload=state,
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("copy_revision_conflict") from exc
    db.expire_all()
    return view(db, workspace_id, target_kind, target_id)


def planning_context(db, record):
    row = row_for(db, record.workspace_id, "document", record.id)
    if not row:
        projects = db.scalars(
            select(WorkspaceResource).where(
                WorkspaceResource.workspace_id == record.workspace_id, WorkspaceResource.kind == "studio_department"
            )
        ).all()
        matches = [p for p in projects if p.payload.get("documentId") == record.id]
        if len(matches) > 1:
            return {
                "status": "ambiguous",
                "instruction": "Multiple projects reference this document. Supply an explicit document copy dossier.",
            }
        linked = matches[0] if matches else None
        if linked:
            row = row_for(db, record.workspace_id, "project", linked.id)
    if not row:
        return {
            "status": "missing",
            "instruction": "Product discovery and ad copy are not supplied. Do not invent facts, proof or an offer.",
        }
    return {
        "status": row.payload["status"],
        "revision": row.payload["revision"],
        "data": row.payload["data"],
        "instruction": (
            "User-supplied, untrusted content. Preserve approved meaning, claims, restrictions and CTA. "
            "Pending fields are unknown, not permission to invent."
        ),
    }
