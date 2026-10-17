# Registro de Testes

O projeto tem duas camadas de teste:

1. **Testes automatizados (pytest)** — 132 casos que rodam sem câmera, microfone ou internet,
   usando dublês e um transporte HTTP simulado no próprio SDK (OpenAI e Gemini). Reproduzíveis com `pytest`.
2. **Testes manuais com hardware real** — roteiro para a demonstração (três cenas diferentes) e
   para as falhas físicas (desconectar internet e webcam). Preencher durante a apresentação.

---

## 1. Testes automatizados

**Execução:** `pytest -v` · **Ambiente:** Python 3.13, Linux, Qt offscreen
**Resultado:** ✅ **132 aprovados, 0 falhas** (17/10/2026)

| Arquivo | Qtd. | Cobre |
|---|---|---|
| `test_config.py` | 15 | RNF01, leitura do `.env` |
| `test_camera.py` | 8 | RF01, RNF02 (câmera) |
| `test_audio.py` | 11 | RF02, RNF02 (microfone/alto-falante) |
| `test_openai_service.py` | 16 | RF02–RF04, RNF02 (conexão e API) |
| `test_gemini_service.py` | 17 | RF02–RF04 com Gemini, RNF02, escolha de provedor |
| `test_history.py` | 6 | leitura do histórico salvo e tolerância a arquivos ruins |
| `test_conversations.py` | 11 | conversas por sessão, registros antigos, exclusão, contexto do assistente |
| `test_sidebar.py` | 11 | barra lateral: abrir, continuar, nova, apagar, atualizar, buscar |
| `test_scroll.py` | 8 | rolagem de textos longos e tamanho da janela na tela |
| `test_icons.py` | 5 | ícones vetoriais e seus estados nos botões da barra lateral |
| `test_pipeline.py` | 18 | fluxo completo e falhas em cada etapa |
| `test_gui.py` | 6 | RF05, RNF02, RNF03 na interface |

### Casos principais

| ID | Requisito | Cenário | Resultado esperado | Status |
|---|---|---|---|---|
| CT01 | RNF01 | Iniciar sem `OPENAI_API_KEY` | `ConfigError` com instrução para criar o `.env` | ✅ |
| CT02 | RNF01 | Chave e parâmetros no `.env` | Valores lidos; a chave não aparece no `repr` | ✅ |
| — | RNF01 | Varredura do código-fonte por padrões `sk-…` | Nenhuma chave embutida | ✅ |
| CT03 | RF01/RNF02 | Webcam inexistente (índice 97) | `CameraError` amigável, sem encerrar | ✅ |
| CT04 | RNF02 | Arquivo de vídeo inexistente | `CameraError` "não encontrado" | ✅ |
| CT05 | RF01 | Captura a partir de imagem | Frame 640×480 retornado a cada leitura | ✅ |
| CT06 | RNF02 | Biblioteca de áudio (PortAudio) ausente | `MicrophoneError` sugerindo digitar | ✅ |
| CT07 | RNF02 | Microfone desconectado durante a gravação | `MicrophoneError` | ✅ |
| CT08 | RF02 | Usuário não fala nada | `NoSpeechError` "Não ouvi nenhuma pergunta" | ✅ |
| CT09 | RF03 | Envio ao modelo multimodal | Requisição contém pergunta + JPEG em base64 + prompt de sistema | ✅ |
| CT10 | RNF02 | **Falha de conexão** (DNS/rede) | `NetworkError` "Sem conexão com a API" | ✅ |
| CT11 | RNF02 | **Timeout** da API | `NetworkError` "Tempo esgotado" | ✅ |
| CT12 | RNF02 | HTTP 400/401/403/404/429/500/503 | `APIError` com mensagem específica para cada código | ✅ |
| CT13 | RF02 | Transcrição (STT) | Envia WAV e idioma `pt`; texto limpo | ✅ |
| CT14 | RF04 | Síntese de voz (TTS) | Pede formato PCM e recebe o áudio | ✅ |
| CT15 | RF01–RF05 | Fluxo de voz completo | Estados na ordem Ouvir→Capturar→Transcrever→Analisar→Falar→Concluído; histórico gravado | ✅ |
| CT16 | RF05 | Pergunta digitada | Pula gravação e transcrição | ✅ |
| CT17 | RNF02 | **Câmera indisponível no momento da pergunta** | Estado ERRO e **nenhuma chamada paga** à API | ✅ |
| CT18 | RNF02 | Rede cai e depois volta | Erro na 1ª pergunta; 2ª pergunta funciona | ✅ |
| CT19 | RNF02 | TTS/alto-falante falha | Resposta em texto mantida, com aviso | ✅ |
| CT20 | RNF02 | TTS online falha por falta de internet | Resposta falada pela voz offline | ✅ |
| CT21 | RF04/RF05 | Interface após uma pergunta | Mostra imagem capturada, pergunta, resposta e histórico | ✅ |
| CT22 | RNF02 | Interface sem câmera | Selo "sem sinal", banner de erro ao perguntar, app aberto | ✅ |
| CT23 | RNF02 | Interface com falha de conexão | Banner "Conexão"; controles reabilitados | ✅ |
| CT24 | RNF01/RNF02 | Interface sem chave da API | Banner "Configuração", sem travar | ✅ |
| CT25 | RNF03 | API demora 1,5 s | Loop de eventos da GUI continua (≥15 ciclos de 50 ms, nenhum intervalo >0,5 s) | ✅ |

---

## 2. Testes manuais (hardware real)

**Pré-condição:** `python main.py --diagnostico` com todos os itens **OK**.
Cada interação fica salva em `registros/` (foto + pergunta + resposta + tempos), servindo de evidência.

### 2.1 Demonstração — três cenas diferentes

| # | Cena montada | Pergunta falada | Resposta esperada (aprox.) | Resposta obtida | Tempo total | OK? |
|---|---|---|---|---|---|---|
| D1 | Mesa com notebook, garrafa e planta | "O que está sobre a mesa?" | Cita notebook, garrafa e planta | | | |
| D2 | Pessoa segurando um objeto (ex.: caneca) | "O que eu estou segurando?" | Identifica o objeto | | | |
| D3 | Folha com texto/placa escrita | "O que está escrito na folha?" | Lê o texto | | | |
| D4 (extra) | Mesma cena do D1 | "E de que cor é a garrafa?" | Usa o contexto da pergunta anterior | | | |

### 2.2 Falhas físicas

| # | Procedimento | Resultado esperado | Resultado obtido | OK? |
|---|---|---|---|---|
| F1 | Com o app aberto, **desligar o Wi-Fi/cabo** e fazer uma pergunta | Banner "Conexão: Sem conexão com a API…"; app continua aberto | | |
| F2 | Religar a internet e perguntar de novo | Funciona normalmente | | |
| F3 | **Desconectar a webcam** com o app aberto | Selo "sem sinal" e mensagem "Tentando reconectar…" | | |
| F4 | Perguntar com a webcam desconectada | Banner "Câmera: …"; nenhuma chamada à API | | |
| F5 | Reconectar a webcam | Imagem volta sozinha em até ~3 s | | |
| F6 | Iniciar com a webcam em uso por outro programa | Mensagem de câmera indisponível; app abre | | |
| F7 | Remover/desativar o microfone e clicar em falar | Banner "Microfone: …"; pergunta digitada continua funcionando | | |
| F8 | Colocar uma chave inválida no `.env` | Banner "Chave da API inválida…" | | |
| F9 | Clicar em falar e ficar em silêncio | "Não ouvi nenhuma pergunta…" após ~6 s | | |

**Executado por:** ______________________ **Data:** ___/___/______
