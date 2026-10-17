# Comprovação da clonagem integral

Os três editores estão importados por inteiro nas revisões fixadas, com as
interfaces originais desktop e web, motores, recursos, documentação, testes,
empacotamento, licenças e atribuições. As dependências Git compartilhadas e a
revisão FilmCraft exigida pelo EffectCraft também estão completas.

| Fontes | Revisão | Arquivos |
|---|---|---:|
| PhotoCraft | `a7f26522` | 1.569 |
| FilmCraft | `0800a8b0` | 1.236 |
| EffectCraft | `67434e90` | 1.016 |
| craft-libs | `5c874d51` | 41 |
| craft-fonts | `abb83316` | 25 |
| FilmCraft de compatibilidade | `2c5ba7a7` | 951 |
| Total | | **4.838** |

`CRAFT_SOURCE_COMPLETENESS.json` é o recibo versionado da auditoria. Todos os
arquivos e seus modos Git correspondem às árvores originais. A verificação não
encontrou submódulos pendentes nem ponteiros LFS sem materialização nas revisões
importadas. Dependências de registry têm versões e checksums em `Cargo.lock`;
as dependências Git têm seus fontes integrais importados. As quatro fontes do
manifesto externo foram verificadas por SHA-256, com suas licenças presentes.

O projeto principal em `C:/Users/edugu/Downloads/res` contém os cinco mirrors Git
e bundles portáveis em `.codex-runtime/craft/upstream`. Eles preservam histórico,
branches, tags e demais referências anunciadas pelo upstream. Referências
retiradas upstream são retidas como histórico; referências próprias garantem
que as revisões fixadas continuem nos backups. Não há clones rasos, filtros de
clone parcial, promessas de objetos ou dependência de objetos de outro checkout.
`mirrors.json` registra a comparação remota e o checksum de cada bundle.

Para reproduzir a comprovação no checkout principal:

```powershell
python scripts/craft/mirror.py --bundle
python scripts/craft/full_clone_audit.py
python scripts/craft/test_mirror.py
```

Para restaurar os mirrors a partir dos bundles de outro checkout e buscar
as referências upstream atuais:

```powershell
python scripts/craft/mirror.py --bundle --seed-from C:/caminho/upstream
```

Os fontes estão em `third_party/craft`. As interfaces originais ficam em
`apps/<editor>`, `apps/<editor>-web` e `crates/ui-egui`; a interface compartilhada
fica em `craft-libs/crates/ui`. Screenshots e seus checksums estão indexados no
recibo. Temas, layouts, ícones, painéis e recursos dessas interfaces permanecem
disponíveis para o próximo planejamento visual, sem iniciar um redesign nesta
etapa.

Os Studios locais continuam usando os três motores e os adaptadores Clicko.
A qualificação funcional está em `CRAFT_INTEGRATION_STATUS.md`: inclui builds
nativos/WASM, salvamento, reabertura, exportação, cancelamento e migração. As
interfaces desktop upstream ainda precisam de qualificação própria; 30 projetos
migrados exigem revisão de fidelidade. A validação com LLM real foi adiada pelo
usuário. Essas pendências estão registradas junto aos originais preservados.
