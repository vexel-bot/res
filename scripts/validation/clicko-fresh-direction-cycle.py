"""Brief-driven independent native cycle. Run only after readiness tests pass."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["prepare", "generate", "resume", "collect", "recover-export"])
    parser.add_argument("--runtime", type=Path, default=ROOT / ".codex-runtime/clicko-dev")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--brief", type=Path, required=True)
    parser.add_argument("--task-key", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--objective", default="Produzir uma peça audiovisual completa a partir do briefing fornecido, com autonomia criativa do Claude.")
    parser.add_argument("--audience", default="Público definido no briefing, assistindo no celular")
    parser.add_argument("--feedback", default="As peças anteriores estão abaixo da meta. Este é um projeto independente; não importar conceito, aprovação ou materiais por padrão.")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--readiness", type=Path, required=True)
    args = parser.parse_args()
    ready = json.loads(args.readiness.read_text(encoding="utf-8"))
    if args.phase in {"prepare", "generate", "resume"} and (ready.get("status") != "passed" or ready.get("buildId") != "clicko-effectcraft-1.0.5+67434e90"):
        raise ValueError("cycle_corrections_not_qualified")
    runtime = args.runtime.resolve()
    os.environ.update(ENVIRONMENT="development", DATABASE_URL="sqlite:///" + (runtime / "studios/records.sqlite").as_posix(),
                      STORAGE_PATH=str(runtime / "studios/uploads"))
    os.environ["STUDIO_LLM_CREDENTIAL_KEY"] = (runtime / "llm-credential-key").read_text().strip()
    sys.path.insert(0, str(ROOT / "backend"))
    spec = importlib.util.spec_from_file_location("native_runner", Path(__file__).with_name("clicko-autonomous-cinematic-review.py"))
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    from app.database import SessionLocal
    from app.domain.studios.contracts import CreateStudioDocumentRequest
    from app.domain.studios.craft import CraftMigrationRequestV1
    from app.models import CreativeDocument, BrandProfile, User
    from app.services.brand import brand_readiness
    from app.services.studios import craft, craft_project_context as context
    from app.services.studios.kernel import create_document
    args.output.mkdir(parents=True, exist_ok=True)
    seed_path = args.output / "seed.json"
    if args.phase == "prepare":
        with SessionLocal() as db:
            user = db.get(User, args.actor)
            from sqlalchemy import select
            brand = db.scalar(select(BrandProfile).where(BrandProfile.workspace_id == args.workspace))
            seed = create_document(db, CreateStudioDocumentRequest.model_validate({
                "workspaceId": args.workspace, "brandRevision": brand_readiness(brand)["revision"],
                "title": args.title + " · projeto vazio", "contentType": "video",
                "brief": {"objective": args.objective, "audience": args.audience},
                "composition": {"pages": [{"id": "main", "width": 1080, "height": 1920,
                    "durationMs": 10000, "layers": []}]}}), user, creation_key=args.task_key + "-seed")
            from app.services.studios.compatibility import record_to_contract
            if not record_to_contract(seed).native_editor_state:
                craft.migrate(db, seed, CraftMigrationRequestV1(engine="effectcraft", expectedRevision=seed.revision),
                              user, args.task_key + "-seed-native")
            runner.write(seed_path, {"documentId": seed.id})
    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    options = SimpleNamespace(runtime=runtime, output=args.output, phase=args.phase,
        task_key=args.task_key, source_document=seed["documentId"], direction_contract="v2",
        expected_build=ready["buildId"], title=args.title, objective=args.objective,
        audience=args.audience)
    result = runner.main(options)
    if args.phase == "prepare" and result == 0:
        receipt = json.loads((args.output / "receipt.json").read_text(encoding="utf-8"))
        with SessionLocal() as db:
            record = db.get(CreativeDocument, receipt["documentId"])
            _, state = context.state(db, record)
            state["cycle"] = {"documentId": record.id, "stage": "diagnosis", "events": [],
                "requireVisualEvaluation": True, "compactEvidence": True, "historicalCandidates": [],
                "processHistory": [], "userFeedback": args.feedback,
                "delivery": "Independent complete draft; sound perception inconclusive"}
            context.save(db, record, state, state["version"])
            db.commit()
        (args.output / "briefing.txt").write_text(args.brief.read_text(encoding="utf-8-sig") + "\n\n" + WORKFLOW, encoding="utf-8")
    return result


WORKFLOW = """Use ferramentas nativas da Clicko; você cria a montagem, sem receita predeterminada.
Escolha referência externa pertinente, observe-a e registre seus limites. Examine as capacidades e materiais acessíveis.
Registre record_direction_plan com cenas, intenção observável e maior incerteza. Você escolhe duração e estratégia.
Execute uma prova da incerteza, renderize com review_clip e solicite request_direction_evaluation ao provedor claude.opus55.visual.
Consulte inspect_direction para obter expectedVersion e IDs. Ao solicitar avaliação, escolha parâmetros de amostragem (até 48 quadros por janela), resolução e intervalo.
Leia as evidências devolvidas. Corrija falhas e teste novamente. Registre experiment com IDs de observações; registre production somente após demonstrar a intenção na prova.
Desenvolva a peça completa. Avalie todas as cenas essenciais da revisão atual antes da conclusão. Divida janelas longas conforme necessário.
Preserve candidatos com save_direction_candidate. Compare versões em contexto de avaliação sem custos, ordem de criação ou justificativa do autor. Registre ganhos/perdas e comparison.
Falhas essenciais exigem correção e nova evidência, não somente texto justificativo. Insuficiência de observação permanece inconclusiva.
Não há teto financeiro, prazo total ou limite de iterações. Se estagnar, mude a hipótese, material, execução ou conceito e registre o motivo.
Crie o som nativamente. Não existe escuta qualificada; medidas não comprovam qualidade sonora. Entregue por finish_project deliveryStatus=draft com pendências reais.
Antes de concluir, registre delivered. A autoria criativa e todas as escolhas pertencem a você.
"""


if __name__ == "__main__":
    raise SystemExit(main())
