# Desenvolvimento do projeto

Este documento conta como o projeto foi construído, em que estado ele está, o que ainda falta e
como contribuir. Para instalar e usar, veja o [README principal](../README.md); para a visão
técnica, a [arquitetura](ARQUITETURA.md).

## 1. Resumo do estado

| Item | Situação |
|---|---|
| Requisitos funcionais (RF01–RF05) | Implementados |
| Requisitos não funcionais (RNF01–RNF03) | Implementados |
| Provedor **Gemini** | Implementado e validado com a API real (visão, transcrição e voz) |
| Provedor **OpenAI** | Implementado e coberto por testes, **ainda não validado com a API real** (veja a seção 6) |
| Conversas salvas e barra lateral | Implementadas (nova, abrir, continuar, buscar, atualizar e apagar) |
| Interface | Navegação por páginas (Assistente, Diagnóstico, Ajustes e Ajuda), tela cheia e tema próprio |
| Testes automatizados | 169 aprovados, sem rede, câmera ou microfone |
| Teste manual completo (janela + webcam + microfone) | Roteiro pronto em [REGISTRO_DE_TESTES.md](REGISTRO_DE_TESTES.md); falta registrar a execução |

**O projeto está completo para o escopo proposto**: ele faz o fluxo inteiro (ouvir a pergunta,
fotografar, enviar ao modelo, mostrar e falar a resposta) e trata as falhas previstas. O que resta
são validações e melhorias, listadas na seção 4.

## 2. Como foi construído

O desenvolvimento seguiu a ordem em que o fluxo acontece, uma camada por vez, sempre com testes
junto:

1. **Base:** configuração por `.env` (a chave nunca vai para o código — RNF01), hierarquia de erros
   com mensagens em português (RNF02) e logs em arquivo.
2. **Entrada e saída físicas:** captura da webcam com OpenCV (`camera.py`) e microfone com detecção
   de silêncio por energia, mais reprodução de áudio (`audio.py`), via `sounddevice`.
3. **Serviços de IA:** transcrição, modelo de visão e síntese de voz em `openai_service.py`. Toda
   exceção do SDK é traduzida em um único ponto (`api_errors`) para a interface nunca quebrar.
4. **Fluxo:** `pipeline.Assistant` orquestra tudo sem conhecer Qt nem o provedor, usando interfaces
   (`Protocol`). Isso permitiu testar o fluxo inteiro com dublês.
5. **Interface:** PyQt5, com o trabalho pesado em `QThread` para a janela nunca travar (RNF03) e uma
   barra de etapas que mostra o estado atual (RF05).
6. **Acabamento:** voz offline de reserva (`pyttsx3`), registro das interações em disco e
   `--diagnostico`, que checa chave, câmera, microfone, alto-falante e conexão.
7. **Gemini:** como a chave da OpenAI exige créditos, o Gemini foi adicionado como alternativa
   (seção 3).
8. **Conversas:** cada pergunta passou a ser salva na conversa atual, com uma barra lateral para
   começar uma nova, reabrir, continuar, buscar, atualizar e apagar
   ([README_CONVERSAS.md](README_CONVERSAS.md)).
9. **Usabilidade:** rolagem de textos longos (inclusive com a roda do mouse sobre o texto), janela
   ajustada à área útil da tela, ícones vetoriais e tema cinza e branco com detalhes em laranja.
10. **Navegação:** barra de navegação com as páginas Assistente, Diagnóstico, Ajustes e Ajuda, e tela
    cheia com F11 ([README_INTERFACE.md](README_INTERFACE.md)).

## 3. Suporte ao Gemini

Usar o Gemini não exigiu reescrever o fluxo, só trocar as implementações de três serviços:

- **Visão:** o Gemini tem um endpoint compatível com o SDK da OpenAI. Basta apontar o `base_url`
  para ele e reaproveitar o `VisionAssistant`.
- **Transcrição:** esse endpoint não tem `/audio/transcriptions`. O áudio é enviado como
  `input_audio` em uma chamada de chat que pede a transcrição (`GeminiSpeechToText`).
- **Voz:** também não existe no endpoint compatível. É usada a API nativa `generateContent` com
  resposta em áudio, e o WAV devolvido é convertido em PCM de 24 kHz (`GeminiTextToSpeech`).

Dois detalhes foram descobertos nos testes com a API real:

- Os modelos antigos (`gemini-2.5-flash`) não estão mais disponíveis para contas novas.
- O `gemini-3.8-flash` levava de 15 a 36 s por etapa e, com frequência, devolvia erro 503 (alta
  demanda). Medidos com a API real, os modelos 3.5 respondem em cerca de 1 a 2 s por etapa, por isso
  os padrões são `gemini-3.5-flash` (visão) e `gemini-3.5-flash-lite` (transcrição); a voz usa
  `gemini-3.8-flash-tts` (cerca de 3 s).
- O Gemini 3 "pensa" antes de responder, e esses tokens contam no limite, o que cortava a resposta
  no meio. Por isso as chamadas enviam `reasoning_effort="low"`.

O provedor é escolhido por `PROVEDOR` no `.env`, pela página **Ajustes** ou por `--provedor`. A
escolha das implementações fica toda em `factory.py`.

## 4. O que falta

Por prioridade:

1. **Registrar o teste manual completo** com webcam e microfone reais, preenchendo as colunas vazias
   do roteiro em `REGISTRO_DE_TESTES.md` (evidência para a demonstração).
2. **Validar o provedor OpenAI com a API real** (seção 6). A troca pode ser feita na página Ajustes.
3. **Gravar a pergunta antes da voz**, para não perdê-la se o app cair durante a fala (seção 5).
4. **Integração contínua:** um workflow no GitHub Actions rodando `pytest` em cada PR, e então exigir
   esse check na proteção da `main`.
5. **Teste de integração opcional com a API real**, desligado por padrão e ativado por variável de
   ambiente, para detectar mudanças de modelo (que já aconteceram — veja a seção 3).
6. **Melhorias de produto** (ideias, fora do escopo atual): escolher o microfone na interface (hoje é
   usado o padrão do sistema), voz em streaming para responder mais rápido e renomear conversas na
   barra lateral.

## 5. Limitações conhecidas

### Pergunta pode não ser salva se o app cair durante a voz

**Comportamento:** em `pipeline.Assistant._answer`, a interação só é gravada em
`registros/interacoes.jsonl` no **fim** do fluxo, depois de exibir a resposta e de falá-la:

```
modelo responde → resposta aparece na tela → voz (gerar + tocar) → store.save()  ← só aqui
```

**Quando a pergunta se perde:**

| Situação | Resultado |
|---|---|
| Fechar o app durante a **reprodução** da voz | Salva. `AudioPlayer.stop()` interrompe o áudio e o fluxo chega ao `save` |
| Fechar o app durante a **geração** da voz (chamada de rede, não interrompível) | **Perde.** `MainWindow.shutdown` espera as threads só 3 s, e o processo encerra antes do `save` |
| Travamento, encerramento forçado ou queda de energia antes do fim da fala | **Perde** |
| Falha na voz (sem rede, sem créditos de TTS) | Salva; o aviso de voz é gravado junto |

Só a pergunta em andamento é afetada; o que já estava gravado permanece.

**Por que foi assim:** o registro inclui os tempos de cada etapa (inclusive a voz) e o aviso de
falha de voz, que só existem no fim.

**Correção planejada:** gravar a interação logo depois que a resposta é obtida (antes da voz) e, ao
final, atualizar essa mesma linha com o tempo e o aviso de voz. Exige um identificador por interação
e uma operação de atualização em `HistoryStore`, mais testes de que fechar durante a voz mantém a
pergunta salva. Está listada em "O que falta".

### Outras

- O microfone usado é sempre o padrão do sistema.
- Ao salvar a página Ajustes, os valores em uso são gravados no `.env`, inclusive os que vieram de
  opções de linha de comando daquela execução (por exemplo, `--sem-voz`).

## 6. Depende de trocar o Gemini pela OpenAI depois

Hoje o projeto roda com o **Gemini**, porque é o provedor com chave disponível e camada gratuita. O
caminho da **OpenAI** existe e tem testes, mas, até ser executado com uma chave real, só foi
verificado com respostas simuladas. Para trocar:

1. Gere uma chave em <https://platform.openai.com/api-keys> (a conta precisa de créditos; assinar o
   ChatGPT **não** dá acesso à API).
2. Na página **Ajustes**, escolha **OpenAI**, cole a chave e salve. Os modelos padrão da OpenAI são
   preenchidos juntos, e não é preciso reiniciar. (Pelo `.env`: `PROVEDOR=openai` e
   `OPENAI_API_KEY`; se houver `MODELO_*` ou `VOZ_TTS` definidos para o Gemini, apague ou ajuste.)
3. Abra a página **Diagnóstico** (ou rode `python main.py --diagnostico`). Se um modelo aparecer
   como indisponível, troque-o em Ajustes.

## 7. Como contribuir

A `main` é protegida: **mudanças entram por Pull Request**. Quem administra o repositório pode fazer
push direto, mas o fluxo normal é o abaixo.

```bash
git clone https://github.com/joaodorast/projeto-visao-llm.git
cd projeto-visao-llm
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # Linux/macOS: cp .env.example .env  (preencha PROVEDOR e a chave)

git checkout -b feat/minha-mudanca
# ... altere o código e os testes ...
pytest
git push -u origin feat/minha-mudanca
# abra o Pull Request para a main
```

Combinados:

- **Testes:** toda mudança de comportamento vem com teste; `pytest` precisa passar. Os testes não
  usam rede, câmera nem microfone, e não podem gravar no `.env` real — mantenha assim.
- **Commits:** pequenos, com uma mudança coerente cada, no formato `tipo(escopo): descrição` em
  português (`feat`, `fix`, `docs`, `test`, `refactor`, `style`, `chore`, `build`).
- **Merge:** com merge commit, mantendo a branch, para o histórico completo ficar registrado.
- **Segredos:** nunca envie `.env`, chaves ou o conteúdo de `logs/` e `registros/` (já estão no
  `.gitignore`). Se uma chave vazar, revogue-a na hora.
- **Estilo:** siga o código existente (comentários e mensagens em português, erros como subclasses
  de `AppError` com texto pronto para o usuário, cores só em `gui/style.py`).
- **Documentação:** se mudar configuração ou comportamento, atualize o README e o documento da área
  (interface, conversas ou arquitetura).

## 8. Histórico das etapas

| Etapa | O que entrou |
|---|---|
| Projeto base | Fluxo completo com OpenAI, interface, testes e documentação |
| PR #1 | Suporte ao Gemini, escolha de provedor, testes e documentação |
| PR #2 | Este documento |
| PR #4 | Conversas salvas automaticamente e barra lateral (nova, abrir, continuar, apagar, atualizar) |
| PR #5 e #6 | Limitações conhecidas e README das conversas |
| PR #7 | Registro, sem alterar arquivos, da janela de histórico substituída pela barra lateral |
| PR #8 | Rolagem de textos longos e janela ajustada à tela |
| PR #9 | Ícones vetoriais e botão de apagar redesenhado |
| PR #10 | Tema cinza e branco com detalhes em laranja |
| PR #11 | Barra de navegação, página de Ajuda e tela cheia (F11) |
| PR #12 | Página de Diagnóstico dentro do app |
| PR #13 | Página Ajustes (salva no `.env` e aplica sem reiniciar) |
| PR #14 e #15 | Captura de tela atualizada e README da interface |
| PR #16 | Revisão completa da documentação |
