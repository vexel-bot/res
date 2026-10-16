# Inspeção de efeitos espaciais — contrato antes da UI

03/10/2026; projeto Downloads/res. Alteração restrita ao leitor EditorInspectionPanel. Não alterar CreativeDocumentV1, MotionGraphV1, editor-inspection.v1, provider native.12, versões de renderer/compilador ou fontes qualificados no recibo espacial.

Mostrar os campos persistidos editorialShadow x/y/blur/color/opacity e editorialDepth blurPx/opacity/parallax como autoria; o desfoque no instante central vem de evaluatedLocalValue da track blur_px retornada pela API, ou do valor estático na ausência de track. Não interpolar outra lista no frontend. Valores de autoria não são prova de cobertura/pixels. Opacity/parallax de depth são autoria; a inspeção não mede a consequência composta.

Exposição temporal selecionada deve apresentar parâmetros solicitados e intervalo, distinguindo instante central de subframes. Não confundir temporalSamples com amostras efetivamente usadas/redução em repouso. Não criar comandos manuais novos para efeitos nem controles que só alterem uma prévia local.

Auditoria inicial corrigida: a hipótese de tracks/pivot ausentes não foi reproduzida; a API real normaliza defaults para receitas. Preservar esse contrato, sem correção fictícia de crash. A interface pode descrever receitas sem tracks como inspeção, mantendo ajustes existentes para choreography/rig.

Prova: workspace local isolado, autenticação normal pela UI, API real com plano aplicado; selecionar camadas com sombra/blur estático e animado, scrubbing 0/1/4, persistência de revisão/digest e novo render real. Inspeção center-frame não substitui pixels do MP4. Verificar comandos de edição existentes e novo render/revisão vinculados, além de TypeScript. Não atribuir notas humanas.
