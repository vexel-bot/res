# Receptor local de XML do Alight — descoberta

Este aplicativo próprio recebe o XML compartilhado pelo Alight através de
`ACTION_SEND` e da concessão temporária de leitura do Android. Não concede acesso
ao armazenamento privado do Alight, não solicita permissões e não usa rede.
Aceita apenas XML de `com.alightcreative.app.motion.fileprovider`, até 1 MiB.

Cada recebimento cria `exports/<UUID>/project.xml` e `receipt.json` na pasta
externa própria do pacote `org.res.alightbridge`. O recibo registra SHA-256,
tamanho, versão do Alight e horário. A recuperação por ADB deve verificar esse
checksum e conservar o UUID; nunca selecionar um arquivo anterior como resultado
de um job. O receptor não executa jobs nem qualifica o motor.

## Build reproduzível

`build.py` exige caminhos explícitos para Java, ferramentas e saída. Não baixa
dependências nem instala software. Na prova de 02/10/2026 foram usados Android
platform 28 r06, build-tools 34 e Eclipse ECJ 3.37.0, com checksums conferidos
contra as distribuições oficiais. `download-receipt.json` deve acompanhar as
ferramentas locais. O script compila Java 8, gera DEX, empacota e verifica a
assinatura do APK. `cryptography` é necessário para o certificado de desenvolvimento.

```powershell
python workers/alight-motion/android-bridge/build.py --java <java.exe> --tools <pasta> --output output/alight-discovery-20261002/android-bridge
```

A identidade de assinatura é gerada na saída local, ignorada pelo Git. Não é uma
chave de publicação. Mantenha o mesmo keystore para atualizar a instalação de
descoberta; não versionar APK, keystore ou senha.

## Evidência e limites

O receptor instalado recuperou um XML real de 912 bytes em 02/10/2026. O arquivo
de referência e a proveniência estão em `../references/5.0.273.1028425/`.
As interações de edição e exportação foram dirigidas pelo agente fora do worker.
O recebimento comprova transporte de um arquivo compartilhado, não render
automático, licença de entrega, qualidade visual nem disponibilidade do provider.
