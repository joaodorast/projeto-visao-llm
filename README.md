# Projeto 1 — Visão e Interpretação do Ambiente com LLM

Aplicação em Python que **ouve uma pergunta pelo microfone, tira uma foto pela webcam no momento
da pergunta, envia imagem e pergunta a um modelo multimodal (Gemini ou OpenAI) e responde em voz
alta**, mostrando na tela a foto usada, a pergunta e a resposta.

![Interface](docs/img/interface.png)

> Exemplo: o usuário pergunta *"O que está sobre a mesa?"* e o assistente responde *"Vejo um
> notebook e uma garrafa sobre a mesa."*

**Destaques**

- **Conversa por voz com um clique**: o app percebe quando você começa e termina de falar,
  responde e volta a ouvir sozinho, até você dizer "encerrar conversa" (ou clicar em Encerrar).
- Respostas em poucos segundos: cerca de 4 s até o texto e 7 s até a voz começar.
- Também aceita pergunta digitada.
- Dois provedores: **Gemini** (tem camada gratuita) e **OpenAI**, trocáveis sem mudar código.
- Conversas salvas automaticamente, com barra lateral para reabrir, continuar, buscar e apagar.
- Páginas de **Diagnóstico**, **Ajustes** e **Ajuda** dentro do app, e tela cheia com **F11**.
- Câmera que pode ser desligada: as perguntas passam a ir sem foto.
- Falhas de câmera, microfone, rede e API tratadas sem fechar o app.
- Visual em cinza e branco, com poucos detalhes em laranja.

---

## 1. Requisitos

| Item | Versão / observação |
|---|---|
| Python | 3.10 ou superior (desenvolvido e testado no 3.14, Windows 11) |
| Webcam e microfone | Qualquer dispositivo reconhecido pelo sistema |
| Chave de API | **Gemini** (camada gratuita): <https://aistudio.google.com/apikey> · **OpenAI** (exige créditos): <https://platform.openai.com/api-keys> |
| Somente Linux | `sudo apt install libportaudio2 espeak-ng` (áudio e voz offline) |

Assinar o ChatGPT **não** dá acesso à API da OpenAI; a chave da API é cobrada à parte.

## 2. Instalação

```bash
# 1. Baixe o projeto
git clone https://github.com/joaodorast/projeto-visao-llm.git
cd projeto-visao-llm

# 2. Crie e ative um ambiente virtual
python -m venv .venv
.venv\Scripts\activate            # Windows
source .venv/bin/activate         # Linux/macOS

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Crie o arquivo de configuração (a chave nunca vai no código — RNF01)
copy .env.example .env            # Windows
cp .env.example .env              # Linux/macOS
```

Abra o `.env`, deixe `PROVEDOR=gemini` (ou `openai`) e cole a chave em `GEMINI_API_KEY` (ou
`OPENAI_API_KEY`). Depois de abrir o app, isso também pode ser feito na página **Ajustes**.

Para conferir se está tudo pronto: `python main.py --diagnostico`.

## 3. Execução

```bash
python main.py                     # abre o app
python main.py --diagnostico       # confere chave, câmera, microfone, alto-falante e conexão, e sai
python main.py --provedor openai   # usa outro provedor nesta execução
python main.py --modelo NOME       # usa outro modelo de visão nesta execução
python main.py --camera 1          # usa a segunda webcam
python main.py --camera foto.jpg   # usa uma imagem ou vídeo no lugar da webcam (demonstração)
python main.py --sem-voz           # mostra as respostas sem falar
python main.py --env outro.env     # usa outro arquivo de configuração
```

As opções valem para aquela execução e têm prioridade sobre o `.env`. Se você salvar a página
**Ajustes** durante essa execução, os valores em uso (inclusive os das opções) passam a ficar
gravados no `.env`.

## 4. Como usar

1. Clique **uma vez** em **🎤 Começar conversa** (ou `Ctrl+Espaço`). A partir daí é só falar: o
   app percebe quando você começa a falar e, quando você fica em silêncio, entende que a pergunta
   terminou.
2. No instante em que você termina de falar, a câmera tira a foto que vai junto com a pergunta.
3. A resposta aparece na tela e é falada; em seguida, o app **volta a ouvir sozinho**, com o
   contexto das últimas trocas. Para cortar uma resposta falada, aperte `Esc`.
4. Para terminar, diga **"encerrar conversa"** (também valem "pode parar", "tchau", "era só isso"…)
   ou clique em **■ Encerrar conversa**. O app se despede e para de ouvir.

Também dá para digitar a pergunta e apertar `Enter`. Quem preferir clicar a cada pergunta pode
desligar **Conversa contínua** em Ajustes: aí o botão vira **🎤 Clique para falar** e cada clique
faz uma pergunta.

A barra de etapas mostra em tempo real: **Ouvir → Capturar → Transcrever → Analisar → Falar**
(RF05). Perguntas e respostas longas ganham barra de rolagem na própria caixa.

**Câmera:** o botão **Desligar câmera** (no cartão da câmera, ou `Ctrl+Shift+C`) para a captura.
Desligada, as perguntas vão sem foto: o modelo responde normalmente e avisa quando a pergunta
depende da imagem. **Ligar câmera** volta ao normal.

### Páginas do app

A barra de ícones à esquerda leva às páginas (também por `Ctrl+1` a `Ctrl+4`):

| Página | Para que serve |
|---|---|
| **Assistente** | Fazer perguntas, ver a foto, a resposta e as conversas |
| **Diagnóstico** | Conferir chave, câmera, microfone, alto-falante e conexão, com dicas quando algo falha |
| **Ajustes** | Trocar provedor, chave, modelos, câmera, voz e gravação; salva no `.env` e aplica sem reiniciar |
| **Ajuda** | Como usar, atalhos de teclado e informações do app |

**F11** (ou o botão **Tela cheia**) alterna a tela cheia; `Esc` também sai dela. Detalhes em
[docs/README_INTERFACE.md](docs/README_INTERFACE.md).

### Conversas

Cada pergunta é salva automaticamente na conversa atual. A barra **Conversas** lista todas,
agrupadas por dia e com busca:

- **Nova conversa** (`Ctrl+N`) começa um chat novo e zera o contexto; as anteriores continuam salvas.
- Clique em uma conversa para reabri-la; novas perguntas **continuam nela**.
- **↻** relê o que está salvo em disco.
- **Apagar conversa** (ou botão direito sobre ela) remove os registros e as fotos, com confirmação.

Tudo fica em `registros/` (`interacoes.jsonl` e as fotos em `registros/AAAA-MM-DD/`). Detalhes em
[docs/README_CONVERSAS.md](docs/README_CONVERSAS.md).

### Atalhos

| Tecla | Ação |
|---|---|
| `Ctrl+Espaço` | Começa a conversa por voz; de novo, encerra |
| `Enter` | Envia a pergunta digitada |
| `Esc` | Corta a resposta falada; ouvindo, encerra a conversa; sai da tela cheia |
| `Ctrl+N` | Nova conversa |
| `Ctrl+1` … `Ctrl+4` | Assistente, Diagnóstico, Ajustes e Ajuda |
| `F11` | Tela cheia |
| `Ctrl+Shift+C` | Liga e desliga a câmera |

## 5. Configuração (`.env`)

Quase tudo pode ser alterado pela página **Ajustes**, que atualiza o `.env` preservando o restante
do arquivo. Referência completa:

| Variável | Padrão | Descrição |
|---|---|---|
| `PROVEDOR` | `openai` (o `.env.example` já vem com `gemini`) | `gemini` ou `openai` |
| `GEMINI_API_KEY` / `OPENAI_API_KEY` | — | Chave do provedor escolhido (**obrigatória**) |
| `MODELO_VISAO` | `gemini-3.5-flash` · `gpt-4.1-mini` | Modelo multimodal (imagem + pergunta) |
| `MODELO_STT` | `gemini-3.5-flash-lite` · `gpt-4o-mini-transcribe` | Transcrição da fala |
| `MODELO_TTS` | `gemini-3.8-flash-tts` · `gpt-4o-mini-tts` | Síntese de voz |
| `VOZ_TTS` | `Kore` · `alloy` | Nome da voz |
| `IDIOMA` | `pt` | Idioma da transcrição |
| `CAMERA` | `0` | Índice da webcam (`0`, `1`…) ou caminho de vídeo/imagem |
| `IMAGEM_LADO_MAX` | `1024` | Maior lado da foto enviada, em pixels |
| `SILENCIO_SEG` | `1.3` | Segundos de silêncio que encerram a gravação |
| `GRAVACAO_MAX_SEG` | `15` | Duração máxima da pergunta, em segundos |
| `SEM_FALA_SEG` | `6` | Segundos sem fala até avisar "Não ouvi nenhuma pergunta" |
| `TIMEOUT_REQUISICAO` | `30` | Tempo máximo de cada chamada à API, em segundos |
| `TENTATIVAS_API` | `2` | Novas tentativas em falhas temporárias da API |
| `CONVERSA_CONTINUA` | `true` | Um clique inicia a conversa e o app fica ouvindo; `false` = um clique por pergunta |
| `TTS_ATIVO` | `true` | Falar as respostas |
| `TTS_OFFLINE_FALLBACK` | `true` | Usar a voz do computador (pyttsx3) se a voz online falhar |
| `SALVAR_HISTORICO` | `true` | Salvar as conversas |
| `PASTA_HISTORICO` / `PASTA_LOGS` | `registros/` / `logs/` | Onde ficam as conversas e os logs |
| `OPENAI_BASE_URL` | — | Endereço alternativo da API (avançado) |

Nas colunas com dois valores, o primeiro é o padrão do Gemini e o segundo, o da OpenAI. Deixe os
`MODELO_*` e `VOZ_TTS` vazios para usar o padrão do provedor escolhido.

Os nomes de modelos mudam com o tempo: se o Diagnóstico disser que um modelo não está disponível
para a sua conta, troque-o em **Ajustes** por um modelo atual com suporte a imagem.

## 6. Trocando de provedor (Gemini ⇄ OpenAI)

O projeto funciona com os dois, sem mudança de código. A forma mais simples é a página **Ajustes**:
escolha o provedor, cole a chave dele (se ainda não houver) e salve. Os modelos padrão são trocados
juntos, e a mudança vale na próxima pergunta.

Pelo `.env`, mude `PROVEDOR` e preencha a chave correspondente; se tiver definido `MODELO_*` ou
`VOZ_TTS` à mão, ajuste-os também.

## 7. Testes

```bash
pytest
```

**209 testes automatizados**, sem usar rede, câmera ou microfone reais (dublês e transporte HTTP
simulado). Cobrem o fluxo completo, falha de conexão, timeout, erros HTTP da API, câmera
indisponível, microfone ausente, falha de voz, responsividade da interface, conversas, navegação,
Diagnóstico e Ajustes. Os testes nunca gravam no seu `.env`. Detalhes e o roteiro de testes
manuais em [docs/REGISTRO_DE_TESTES.md](docs/REGISTRO_DE_TESTES.md).

## 8. Estrutura

```
projeto-visao-llm/
├── main.py                      # atalho: python main.py
├── requirements.txt
├── .env.example                 # modelo de configuração (copie para .env)
├── visao_llm/
│   ├── __main__.py              # opções de linha de comando
│   ├── config.py                # leitura do .env e padrões por provedor (RNF01)
│   ├── env_file.py              # atualização segura do .env (página Ajustes)
│   ├── errors.py                # erros com mensagens amigáveis (RNF02)
│   ├── models.py                # estados da interface e resultado de uma interação
│   ├── camera.py                # webcam via OpenCV; redimensiona e gera JPEG (RF01)
│   ├── audio.py                 # microfone com detecção de silêncio; reprodução (RF02/RF04)
│   ├── openai_service.py        # transcrição, visão e voz da OpenAI + tradução de erros
│   ├── gemini_service.py        # transcrição e voz do Gemini (a visão reaproveita a anterior)
│   ├── speaker.py               # fala a resposta; usa a voz offline se a online falhar
│   ├── pipeline.py              # orquestra o fluxo e as conversas, sem depender da interface
│   ├── history.py               # salva, agrupa em conversas, relê e apaga registros
│   ├── factory.py               # monta os serviços do provedor escolhido
│   ├── diagnostics.py           # verificações do ambiente (terminal e página)
│   ├── logging_setup.py         # logs em console e em logs/app.log
│   └── gui/                     # interface PyQt5 (RF05/RNF03)
│       ├── app.py               # inicialização do Qt
│       ├── main_window.py       # janela, páginas, atalhos, tela cheia, aplicação dos ajustes
│       ├── navigation.py        # barra de navegação
│       ├── sidebar.py           # barra de conversas
│       ├── diagnostics_page.py  # página Diagnóstico
│       ├── settings_page.py     # página Ajustes
│       ├── help_page.py         # página Ajuda
│       ├── workers.py           # câmera e perguntas em threads separadas
│       ├── widgets.py           # cartões, imagens, textos roláveis, interruptor
│       ├── icons.py             # ícones vetoriais
│       └── style.py             # tema (paleta e folha de estilo)
├── tests/                       # pytest
└── docs/                        # documentação (veja a seção 11)
```

`registros/`, `logs/` e `.env` ficam fora do git.

## 9. Solução de problemas

Comece pela página **Diagnóstico**: ela mostra o que está falhando e o que fazer.

| Sintoma | O que fazer |
|---|---|
| "Câmera indisponível" | Feche outros apps que usam a webcam (Teams, Zoom, navegador) ou escolha outra câmera em Ajustes. O app reconecta sozinho a cada 3 s. |
| "Biblioteca de áudio indisponível" | Linux: `sudo apt install libportaudio2`. Enquanto isso, digite a pergunta. |
| "Não ouvi nenhuma pergunta" | Fale mais perto do microfone e confira o microfone padrão do sistema. |
| "Chave da API inválida" | Cole a chave certa em Ajustes (a do provedor escolhido). |
| "Limite de uso da API" | Muitas requisições ou sem créditos: aguarde ou confira a conta do provedor. |
| "Modelo não encontrado" | Use **Restaurar padrões** em Ajustes ou informe um modelo atual. |
| Resposta aparece, mas não é falada | O aviso amarelo explica o motivo; a resposta em texto continua válida. |

Logs completos ficam em `logs/app.log`.

## 10. Limitações conhecidas

- **A conversa é salva no fim do fluxo.** Cada pergunta só é gravada depois que a resposta é
  exibida **e** a voz termina (ou falha). Fechar o app durante a *reprodução* da voz ainda salva,
  pois a fala é interrompida e o fluxo conclui. Mas se o app for fechado durante a *geração* da
  voz (uma chamada de rede de alguns segundos), travar ou for encerrado à força antes do fim,
  **aquela pergunta não fica salva** (a resposta aparece na tela, mas não no histórico). As
  perguntas anteriores não são afetadas.
- Com `SALVAR_HISTORICO=false` (ou a opção desligada em Ajustes) nada é gravado, e a barra de
  conversas mostra um aviso.
- O microfone usado é sempre o padrão do sistema.
- A conversa é por turnos: enquanto o app fala, ele não ouve. Para interromper uma resposta,
  use `Esc` (ou **Encerrar conversa**); interromper falando por cima ainda não é possível.
- O "tempo real" é por rodadas rápidas (cerca de 4 s até o texto e 7 s até a voz), não por
  áudio contínuo em streaming.

Detalhes e a correção planejada em
[docs/README_DESENVOLVIMENTO.md](docs/README_DESENVOLVIMENTO.md#5-limitações-conhecidas).

## 11. Documentação

| Documento | Conteúdo |
|---|---|
| [docs/README_INTERFACE.md](docs/README_INTERFACE.md) | Navegação, tela cheia, páginas Assistente, Diagnóstico, Ajustes e Ajuda, e o visual |
| [docs/README_CONVERSAS.md](docs/README_CONVERSAS.md) | Conversas salvas e barra lateral: nova, abrir, continuar, buscar, atualizar e apagar |
| [docs/ARQUITETURA.md](docs/ARQUITETURA.md) | Requisitos, camadas, decisões de projeto e fluxo de dados |
| [docs/REGISTRO_DE_TESTES.md](docs/REGISTRO_DE_TESTES.md) | Testes automatizados e roteiro de testes manuais |
| [docs/README_DESENVOLVIMENTO.md](docs/README_DESENVOLVIMENTO.md) | Como o projeto foi construído, estado atual, o que falta e como contribuir |
