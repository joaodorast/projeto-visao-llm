# Conversas e barra lateral

Como funcionam as conversas salvas e a barra lateral do app: o que ela faz, como usar, onde os
dados ficam e como isso foi implementado. Para instalar e usar o app, veja o
[README principal](../README.md).

## 1. Visão geral

Cada pergunta é salva **automaticamente** na conversa atual (no modo conversa por voz, cada
rodada é salva assim que termina). A barra à esquerda lista todas as
conversas salvas, no estilo dos chats de IA: você pode começar uma conversa nova, reabrir uma
antiga e continuar nela, buscar, atualizar a lista e apagar.

| Recurso | Como usar | O que acontece |
|---|---|---|
| **Salvar** | automático | Cada interação (pergunta, resposta, foto e tempos) é gravada na conversa atual |
| **Listar** | barra lateral | Conversas agrupadas por dia (Hoje, Ontem, data), da mais recente para a mais antiga |
| **Nova conversa** | botão **Nova conversa** ou `Ctrl+N` | Limpa a tela e o contexto e começa um chat novo; as conversas anteriores continuam salvas |
| **Abrir e continuar** | clicar na conversa | Volta com as perguntas, fotos e respostas; novas perguntas entram nela |
| **Buscar** | caixa "Buscar conversas…" | Filtra pelo texto das perguntas **e** das respostas |
| **Atualizar** | botão **↻** (topo da barra) | Relê o disco de verdade e mostra uma animação curta de carregamento |
| **Apagar** | botão **Apagar conversa** (lixeira) ou botão direito na conversa | Pede confirmação e remove os registros e as fotos |

## 2. Usando

### Nova conversa

Clique em **Nova conversa** ou use `Ctrl+N`. A tela é limpa e o modelo deixa de receber o
contexto da conversa anterior. A nova conversa aparece na lista como **"Nova conversa"** e passa a
ter o título da sua primeira pergunta assim que ela é respondida. As conversas anteriores não são
alteradas.

### Abrir e continuar uma conversa

Clique em uma conversa da lista. O painel mostra a última pergunta com a foto e a resposta, e a
lista "Perguntas desta conversa" traz todas; clique em uma delas para rever a foto e a resposta
daquela pergunta (a foto vem do arquivo salvo em disco).

Ao fazer uma nova pergunta, ela é gravada **nessa mesma conversa**, e o modelo recebe as **três
últimas trocas** como contexto, então perguntas de seguimento ("e de que cor é?") funcionam como
se a conversa nunca tivesse sido interrompida.

### Título e agrupamento

- O título é a **primeira pergunta** da conversa, resumida em até 48 caracteres.
- O agrupamento por dia usa a data da **última atividade** da conversa.
- Registros antigos, de antes das conversas existirem, não têm identificador; viram **uma conversa
  por dia** (`dia-AAAA-MM-DD`).

### Buscar

A busca filtra a lista enquanto você digita e procura nas perguntas e respostas de todas as
interações da conversa, sem diferenciar maiúsculas de minúsculas.

### Atualizar (↻)

O botão **relê o arquivo de registros do disco a cada clique**; a animação (cerca de 0,6 s) é só o
retorno visual de que a atualização aconteceu. É útil quando:

- outra janela do app gravou uma conversa nova;
- outra janela fez perguntas na conversa que você está vendo: elas são incluídas na tela;
- você apagou ou moveu arquivos de `registros/` por fora do app.

Se o app estiver processando uma pergunta, a conversa aberta não é recarregada nesse momento (a
lista da barra é atualizada normalmente).

### Apagar

Use o botão **Apagar conversa** (com a conversa selecionada) ou o botão direito sobre ela. Uma
janela pede confirmação, com a quantidade de perguntas, e avisa que **não há como desfazer**.

Ao confirmar:

- as linhas da conversa saem de `registros/interacoes.jsonl`;
- as fotos dela são apagadas, e a pasta do dia também, se ficar vazia;
- se era a conversa aberta, o app começa uma conversa nova.

O botão fica desativado para a "Nova conversa" ainda sem perguntas, pois não há nada salvo.

### Regras enquanto o app trabalha

Enquanto uma pergunta está sendo gravada, transcrita, analisada ou falada, **não é possível**
trocar de conversa, começar outra nem apagar. Clicar em outra conversa nesse momento mantém a
atual selecionada.

## 3. Onde ficam os dados

Tudo fica na pasta `registros/` do projeto (configurável por `PASTA_HISTORICO`), que **não vai para
o git**:

```
registros/
├── interacoes.jsonl            # uma linha por pergunta
└── 2026-10-17/
    └── 030909_301.jpg          # foto usada na pergunta (HHMMSS_mmm.jpg)
```

Cada linha do `interacoes.jsonl` é um JSON:

```json
{"sessao": "20261017-030800-a1b2c3", "data_hora": "2026-10-17T03:09:09", "origem": "voz",
 "pergunta": "o que é chat GPT?", "resposta": "O ChatGPT é um modelo de inteligência artificial…",
 "imagem": "2026-10-17\\030909_301.jpg", "tempos_s": {"gravacao": 3.32, "stt": 30.97, "llm": 36.09},
 "aviso_voz": null}
```

- `sessao` identifica a conversa: todas as linhas com o mesmo valor pertencem a ela.
- Para **desligar a gravação**, desligue "Salvar as conversas automaticamente" em **Ajustes** ou
  use `SALVAR_HISTORICO=false` no `.env`. Nesse caso nenhuma conversa
  é salva e a barra lateral mostra um aviso.
- Como são arquivos simples, dá para copiar a pasta `registros/` para fazer backup.

## 4. Limitação conhecida

A interação só é gravada **no fim do fluxo**, depois da resposta e da voz. Se o app for fechado
durante a *geração* da voz (chamada de rede), travar ou for encerrado à força antes disso, a
pergunta em andamento não fica salva. Fechar durante a *reprodução* da voz salva normalmente.
Detalhes e a correção planejada em [README_DESENVOLVIMENTO.md](README_DESENVOLVIMENTO.md#5-limitações-conhecidas).

## 5. Como foi implementado

| Parte | Arquivo | Papel |
|---|---|---|
| Identificador da conversa | `visao_llm/models.py` | `new_session_id()` e o campo `sessao` em `InteractionResult` |
| Conversa atual e retomada | `visao_llm/pipeline.py` | `Assistant.session_id`, `new_session()` e `load_session()` (restaura as últimas trocas como contexto) |
| Gravar, agrupar, ler e apagar | `visao_llm/history.py` | `HistoryStore.save()`, `load()`, `conversations()` e `delete_conversation()` |
| Barra lateral | `visao_llm/gui/sidebar.py` | Lista, busca, botões e animação; só emite sinais |
| Integração | `visao_llm/gui/main_window.py` | Carrega, continua, cria, apaga (com confirmação) e atualiza conversas |
| Estilo | `visao_llm/gui/style.py` | Aparência da barra lateral |

Decisões de projeto:

- **A barra lateral não conhece o disco nem o assistente.** Ela emite sinais (`new_requested`,
  `conversation_selected`, `delete_requested`, `refresh_requested`) e a janela principal decide o que
  fazer. Isso a mantém simples de testar.
- **O contexto do modelo é sincronizado antes de cada pergunta** (`_sync_assistant`): se a conversa
  na tela é diferente da que o assistente conhece, ele recarrega as últimas trocas dela. Assim,
  continuar uma conversa antiga e começar uma nova sempre enviam o contexto certo.
- **Apagar é atômico:** o arquivo é reescrito em um temporário e trocado de uma vez
  (`os.replace`), então uma falha no meio não deixa o histórico pela metade. Linhas ilegíveis que já
  existiam são preservadas, pois não dá para saber a que conversa pertencem.
- **Leitura tolerante:** linhas corrompidas são ignoradas, caminhos de foto gravados com `\` (Windows)
  são normalizados, e uma foto apagada não impede de abrir a conversa (mostra "Imagem não encontrada
  no disco").
- **A animação não finge o trabalho:** o clique no **↻** dispara a releitura imediatamente; os cerca
  de 0,6 s de animação (11 quadros de 55 ms) apenas sinalizam que ocorreu.

## 6. Testes

Os testes não usam rede, câmera nem microfone (a interface roda em modo `offscreen`).

| Arquivo | Qtd. | Cobre |
|---|---|---|
| `tests/test_history.py` | 6 | leitura do histórico, ordem, limite, linhas corrompidas, foto apagada, caminhos do Windows |
| `tests/test_conversations.py` | 11 | agrupamento por conversa, registros antigos, título, apagar (inclusive casos de borda) e contexto do assistente |
| `tests/test_sidebar.py` | 11 | listar, abrir, continuar, nova conversa, apagar com confirmação, atualizar com dados novos, animação e busca |

```bash
pytest tests/test_history.py tests/test_conversations.py tests/test_sidebar.py
```
