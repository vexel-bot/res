# Inspeção espacial ligada à revisão e ao MP4

03/10/2026; projeto original `C:/Users/edugu/Downloads/res`. Resultado deste incremento: parâmetros espaciais persistidos e blur central calculado pela API aparecem no inspetor; um comando aplicado pela interface muda a revisão e produz um MP4 correspondente. [Compatibilidade](SPATIAL_INSPECTION_COMPATIBILITY.md), [recibo verificável](spatial-inspection-receipt.json) e [fontes congeladas](spatial-inspection-browser/qualified-sources.json).

O leitor alterado é `src/studios/EditorInspectionPanel.tsx`. Mostra sombra canônica x/y/blur/color/opacity, depth e a track `blur_px` no frame escolhido, além de samples/shutter solicitados pela receita temporal. O valor central não é a média dos subframes; redução de samples em repouso pertence ao recibo do renderer. Cena e camada ganharam nomes acessíveis explícitos. Não houve mudança no contrato, versão ou execução do renderer native.12, nem interpolação paralela no frontend.

## Percurso real

Workspace `5419fc09-7062-4bc7-8703-13c85ad70dc6`; documento `34db527a-5b46-48a2-87e6-5e187bb5706f`. Conta local própria, login normal na UI e API existente na porta 8000. As primeiras observações usaram a UI compartilhada na porta 3000. Ela recarregava ao gravar evidências e perdia seleção; a conclusão usou a mesma aplicação em 3317, com a opção existente de HMR desativado. [Origem e hashes](spatial-inspection-browser/runtime-origin.json); nenhum servidor compartilhado foi interrompido, nenhuma resposta foi mockada.

1. Inspeção da revisão/plano 2: combo tem blur estático 4, sombra azul x32/y12/blur4/opacidade0,5; zero conserva sombra explicitamente transparente. Animated tem blur central 0 no frame 0 e 16 nos frames 1/4, obtidos da API; exposição solicita 8 samples/180°.
2. Botão **Renderizar esta revisão** submete job real para revisão 2. O MP4 e checksum aparecem no painel.
3. Na camada sharp, **Valor** muda de 0 para 4 no frame local 0 e **Salvar keyframe** aplica o comando existente. Recibo `9dcb5e69-cae1-417c-a7a4-c21fc3da204f`: revisão/plano 2→3, novo digest de documento/grafo/composição, autoria autenticada. A inspeção mostra `position_x = 4`; o MP4 anterior deixa de estar associado à revisão inspecionada.
4. Novo clique em **Renderizar esta revisão** produz job da revisão 3; o painel associa seu novo checksum. Os sete layers authored e parâmetros espaciais permanecem iguais; a mudança fica na track canônica. O histórico conserva a pendência de avaliação humana.

| Revisão | Job | MP4 / SHA-256 | Render local |
|---|---|---|---|
| 2 | `d52e8e0d-55b0-4bd1-8aa6-8b47c1437ce5` | [preview-revision-2.mp4](spatial-inspection-browser/preview-revision-2.mp4) · `7aa65337b026adb24884f9e19178a59004f6924de44b800f2579239947bdf6a8` | 14.266 ms |
| 3 | `29ee062f-c760-4357-acaa-6c642013d3b9` | [preview-revision-3.mp4](spatial-inspection-browser/preview-revision-3.mp4) · `c3434e6e9e938ac9246fd9cbf22372a4f83026a21862421be59d3df83956a9a4` | 12.984 ms |

Ambos são draft, 320×320, 30 fps, 1 s, H.264/AAC, QC técnico passed, provider `4.0.527-native.12`, Chromium swangle, CRF28. Dois tempos locais não medem p95. Esses drafts não substituem a qualificação high de Gaussian/exposição no [recibo native.12](SPATIAL_EFFECTS_RECEIPT.md).

## Conferência e limites

`npm run lint` (`tsc --noEmit`) passou com os mesmos bytes de UI; Ruff passou nos dois scripts. `python scripts/validation/editor-spatial-inspection-receipt.py` verifica fontes atuais/renderer, nove grupos obrigatórios de observação em painel visível, histórico, inspeções API, snapshots/hashes de manifesto, checksums e 12 probes RGB decodificados dos MP4s. A captura contém 12 grupos DOM no total; dois registraram o painel montado após o fluxo selecionar automaticamente a aba Saída e estão identificados como tal, seguidos por observações com Revisão visível.

Geometria no frame 0: sharp x32→36. Pixel (34,54): branco255→preto2; (90,54): preto0→branco255. No frame29, x34 permanece branco e x90 preto nas duas revisões. Limites definidos pelo verificador são branco>220/preto<30 em cada canal, próprios desta prova draft de movimento. Não são as tolerâncias Gaussian do incremento anterior. Nenhuma nota humana foi criada.

Capturas: [combo estático](spatial-inspection-browser/combo-revision3.png), [blur central e exposição](spatial-inspection-browser/animated-revision3.png), [MP4 vinculado](spatial-inspection-browser/render-revision3.png). A área central do VideoStudio ainda é uma prévia de material, com dimensões/placeholder desse fluxo; a composição efetivamente renderizada está no vídeo do inspetor. Este incremento não qualifica esse canvas central como prévia da composição canônica.

Próximo incremento técnico: exposição + matte sob pai externo animado, com pixels e diagnóstico. Continuam pendentes os três estudos dirigidos com notas/preferência humanas e três briefs novos de autonomia. Nenhum repositório adicional foi baixado nesta rodada. A limpeza anterior permanece pendente porque a aprovação automática rejeitou a exclusão recursiva; a rejeição não foi contornada.
