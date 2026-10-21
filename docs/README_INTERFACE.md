# Interface do app

Como a interface está organizada: navegação entre páginas, tela cheia, as páginas Assistente,
Diagnóstico, Ajustes e Ajuda, e o visual. Para instalar e usar, veja o
[README principal](../README.md); as conversas e a barra lateral têm um documento próprio,
[README_CONVERSAS.md](README_CONVERSAS.md).

![Interface](img/interface.png)

## 1. Visão geral

A janela tem três partes:

```
┌────┬──────────────┬──────────────────────────────────────────┐
│ VI │  Conversas   │  Página atual                            │
│    │  (só na      │  (Assistente, Diagnóstico, Ajustes ou    │
│ 🗨 │   página     │   Ajuda)                                 │
│ 〰 │   Assistente)│                                          │
│ ⚙ │              │                                          │
│ ? │              │                                          │
│ ⛶ │              │                                          │
└────┴──────────────┴──────────────────────────────────────────┘
 barra de navegação
```

- **Barra de navegação** (à esquerda): a marca do app, um botão por página e o botão de tela cheia.
- **Conversas**: lista das conversas salvas, visível na página Assistente.
- **Página atual**: o conteúdo escolhido na barra.

## 2. Navegação e atalhos

| Página | Botão | Atalho | Para que serve |
|---|---|---|---|
| Assistente | balão | `Ctrl+1` | Fazer perguntas e ver as respostas |
| Diagnóstico | pulso | `Ctrl+2` | Conferir se tudo está pronto para usar |
| Ajustes | engrenagem | `Ctrl+3` | Trocar provedor, chave, modelos, câmera, voz e gravação |
| Ajuda | interrogação | `Ctrl+4` | Como usar, atalhos e informações do app |

A página aberta fica com o botão destacado e o ícone em laranja.

Outros atalhos:

| Tecla | Ação |
|---|---|
| `Ctrl+Espaço` | Começa a ouvir a pergunta; de novo, para e envia |
| `Enter` | Envia a pergunta digitada |
| `Ctrl+N` | Nova conversa |
| `F11` | Entra e sai da tela cheia |
| `Esc` | Interrompe a gravação ou a fala; se não houver nenhuma, sai da tela cheia |
| `Ctrl+Shift+C` | Liga e desliga a câmera |

## 3. Tela cheia

Use **F11** ou o botão **Tela cheia** no pé da barra de navegação. Na tela cheia o botão passa a se
chamar **Sair**. Para sair, aperte F11 de novo, clique em **Sair** ou use `Esc`. A janela volta ao
estado anterior: maximizada, se estava maximizada, ou no tamanho normal.

## 4. Página Assistente

É a tela de uso: câmera ao vivo, botão para falar, foto usada, pergunta, resposta e as perguntas da
conversa atual. O funcionamento das conversas está em [README_CONVERSAS.md](README_CONVERSAS.md).

- **Textos longos:** pergunta e resposta ficam em caixas com barra de rolagem, que aparece só
  quando o texto não cabe. A roda do mouse rola com o ponteiro sobre o próprio texto.
- **Espaço para a resposta:** a caixa da resposta é a maior; a da pergunta é compacta.
- **Tamanho da janela:** ao abrir, a janela respeita a área útil da tela, sem ficar atrás da barra
  de tarefas.
- **Indicador da câmera:** "● ao vivo" em laranja quando há imagem; "● sem sinal" em vermelho
  quando a câmera cai (o app tenta reconectar sozinho); "● desligada" em cinza quando foi desligada.
- **Desligar câmera:** o botão no cartão da câmera (ou `Ctrl+Shift+C`) para a captura e libera a
  webcam. Com ela desligada, as perguntas vão **sem foto**: o modelo recebe só o texto, responde
  normalmente e, se a pergunta depender da imagem, avisa que a câmera está desligada. A conversa
  registra a pergunta sem foto. **Ligar câmera** retoma a captura. No Diagnóstico, a câmera aparece
  como "desligada no app".

## 5. Página Diagnóstico

Confere, dentro do app, se o ambiente está pronto. Na primeira vez que a página é aberta, o
diagnóstico roda sozinho; depois, use **Executar novamente**.

| Verificação | O que confere |
|---|---|
| Chave da API | Se a chave do provedor escolhido está configurada |
| Câmera | Se há imagem chegando (fonte e resolução) |
| Microfone | Se existe um dispositivo de entrada de áudio |
| Alto-falante | Qual é a saída de áudio padrão |
| Conexão com o provedor | Se a API responde com essa chave e se os modelos configurados existem |

Cada item mostra um selo: **—** (ainda não verificado), **…** (verificando), **OK** ou **FALHA**.
O resumo no topo diz se está tudo pronto ou quantos itens precisam de atenção, com o horário da
verificação.

Quando um item falha, aparece uma dica logo abaixo dele:

| Falha | Dica |
|---|---|
| Chave da API | Colar a chave na página Ajustes (ou definir no `.env`) |
| Câmera | Fechar outros apps que usam a webcam ou escolher outra câmera em Ajustes |
| Microfone | Conectar um microfone; enquanto isso, dá para digitar |
| Alto-falante | Conferir a saída de áudio do sistema; a resposta continua na tela |
| Conexão | Verificar a internet, a chave e os modelos em Ajustes, ou os créditos da conta |

Detalhes:

- As verificações rodam em segundo plano: a janela não trava enquanto a conexão é testada.
- A câmera é verificada pela que o app já está usando, porque abrir a mesma webcam duas vezes
  costuma falhar no Windows.
- Se os ajustes mudarem, os itens voltam para "ainda não verificado" e a verificação de conexão
  passa a citar o novo provedor.
- O mesmo diagnóstico existe no terminal: `python main.py --diagnostico`.

## 6. Página Ajustes

Troca as configurações pela interface. **Salvar alterações** grava no arquivo `.env` e aplica na
hora, sem reiniciar. **Descartar** volta aos valores em uso.

| Cartão | Campos |
|---|---|
| Provedor de IA | Provedor (Gemini ou OpenAI) e chave da API |
| Modelos | Visão, transcrição da fala, voz (síntese) e nome da voz, com **Restaurar padrões** |
| Câmera e microfone | Câmera (`0`, `1`… ou caminho de vídeo/imagem), silêncio que encerra a pergunta (0,3 a 5 s) e duração máxima da pergunta (3 a 60 s) |
| Voz e conversas | Interruptores: falar as respostas, usar a voz do computador se a online falhar, salvar as conversas |

### A chave da API

- A chave atual **nunca é exibida**. O campo fica vazio, com o aviso "configurada — deixe vazio
  para manter".
- Para trocar, cole a nova chave e salve. Depois de salvar, o campo volta a ficar vazio.
- Cada provedor tem a sua chave (`GEMINI_API_KEY` e `OPENAI_API_KEY`). Trocar de provedor não
  apaga a chave do outro, e voltar ao anterior usa a chave dele de novo.
- Se o provedor escolhido não tiver chave, a página mostra onde gerar uma.

### Modelos e troca de provedor

- Ao trocar de provedor, os campos que estavam no padrão do provedor anterior passam para o padrão
  do novo. Modelos que você personalizou são mantidos.
- **Restaurar padrões** coloca os modelos padrão do provedor escolhido.
- Modelos iguais ao padrão ficam **vazios** no `.env`. Assim, se o provedor for trocado depois
  (inclusive editando o `.env` à mão), o app usa os modelos certos do novo provedor.

### O que é gravado no `.env`

`PROVEDOR`, `MODELO_VISAO`, `MODELO_STT`, `MODELO_TTS`, `VOZ_TTS`, `CAMERA`, `SILENCIO_SEG`,
`GRAVACAO_MAX_SEG`, `TTS_ATIVO`, `TTS_OFFLINE_FALLBACK`, `SALVAR_HISTORICO` e, só se você digitar
uma nova, a chave do provedor.

O arquivo é atualizado com cuidado:

- só essas linhas mudam; comentários, ordem e o restante do arquivo ficam como estão;
- uma configuração que só existia comentada (como `#MODELO_VISAO=`) é ativada no mesmo lugar;
- valores com espaço ou `#` (por exemplo, um caminho de vídeo) são gravados entre aspas;
- a gravação é atômica: o arquivo é escrito em um temporário e trocado de uma vez, então nunca fica
  pela metade.

### Aplicação sem reiniciar

Ao salvar:

- a próxima pergunta já usa o novo provedor, os novos modelos e a nova voz;
- se a câmera mudou, a captura é reiniciada com a nova fonte;
- o subtítulo da janela, o Diagnóstico e a Ajuda passam a mostrar a nova configuração;
- a barra de conversas passa a avisar quando a gravação está desligada.

Se o app foi aberto com opções de linha de comando (por exemplo, `--sem-voz` ou `--camera 1`),
salvar a página grava os valores em uso, inclusive os dessas opções.

Enquanto uma pergunta está em andamento, salvar é recusado com o aviso "Aguarde a pergunta atual
terminar". Se o `.env` não puder ser gravado (por exemplo, sem permissão), os ajustes valem até
fechar o app e a página explica o motivo.

## 7. Página Ajuda

Reúne, dentro do app:

- **Como usar**, em quatro passos: perguntar, a IA olhar, ela responder e continuar a conversa;
- **Atalhos de teclado**;
- **Conversas e dados**: onde ficam os registros e como desligar a gravação;
- **Sobre**: versão, provedor e modelos em uso (atualizado quando os ajustes mudam).

## 8. Visual

O tema é **cinza e branco, com poucos detalhes em laranja**. O laranja marca só o que pede
atenção; vermelho e âmbar ficam reservados para erros e avisos.

| Cor | Uso |
|---|---|
| Grafite `#1f1f23` | Barra de conversas, botão principal, selos de OK |
| Cinzas e branco (`#f3f3f4`, `#ffffff`, `#e4e4e7`) | Fundo, cartões, bordas |
| Laranja `#f97316` | Gravando, foco dos campos, conversa e página selecionadas, borda da resposta, etapa em andamento, câmera ao vivo, interruptores ligados |
| Vermelho | Erros, falhas do diagnóstico e o botão de apagar ao passar o mouse |
| Âmbar | Avisos, como "resposta exibida, mas não falada" |

- **Ícones vetoriais:** desenhados no próprio código, ficam nítidos em qualquer tela. Mudam de cor
  ao passar o mouse, quando desativados e (na navegação) quando a página está selecionada.
- **Interruptores:** as opções liga/desliga são interruptores desenhados no tema.
- **Paleta centralizada:** todas as cores ficam em constantes no topo de
  `visao_llm/gui/style.py`. Para mudar o tom do laranja ou dos cinzas, basta alterar ali; nenhum
  outro arquivo da interface tem cor fixa.

## 9. Como foi implementado

| Parte | Arquivo | Papel |
|---|---|---|
| Barra de navegação | `visao_llm/gui/navigation.py` | Botões de página, tela cheia; só emite sinais |
| Páginas e tela cheia | `visao_llm/gui/main_window.py` | Páginas empilhadas, atalhos, F11/Esc, aplicação dos ajustes |
| Diagnóstico (lógica) | `visao_llm/diagnostics.py` | Verificações compartilhadas entre o terminal e a página |
| Diagnóstico (tela) | `visao_llm/gui/diagnostics_page.py` | Execução em segundo plano, selos, resumo e dicas |
| Ajustes (tela) | `visao_llm/gui/settings_page.py` | Formulário, regras da chave e dos modelos |
| Atualização do `.env` | `visao_llm/env_file.py` | Altera só as chaves pedidas, de forma atômica |
| Ajuda | `visao_llm/gui/help_page.py` | Como usar, atalhos, dados e informações |
| Componentes | `visao_llm/gui/widgets.py` | Área rolável para textos longos, interruptor, cartões |
| Ícones | `visao_llm/gui/icons.py` | Ícones vetoriais com estados |
| Tema | `visao_llm/gui/style.py` | Paleta e folha de estilo |

Decisões de projeto:

- **Componentes só emitem sinais.** A barra de navegação, a barra de conversas e as páginas não
  conhecem umas às outras; a janela principal decide o que fazer. Isso deixa cada parte simples de
  testar.
- **Uma única lógica de diagnóstico** para o terminal e a página: a coleta dos resultados é separada
  da forma de mostrá-los.
- **Ajustes aplicados sem reiniciar:** o assistente é recriado na próxima pergunta com a nova
  configuração, em vez de exigir que o app seja fechado.
- **Segurança da chave:** ela não aparece na tela, não vai para os logs e só é gravada quando você
  digita uma nova.

## 10. Testes

Os testes não usam rede, câmera nem microfone reais; a interface roda em modo `offscreen`.

| Arquivo | Qtd. | Cobre |
|---|---|---|
| `tests/test_navigation.py` | 7 | Troca de página, atalhos, tela cheia (F11, botão e `Esc`) e conteúdo da Ajuda |
| `tests/test_diagnostics.py` | 7 | Coleta dos resultados, saída do terminal, página com sucesso e com falha, execução na primeira visita |
| `tests/test_settings.py` | 14 | Carregar, trocar provedor, chave, salvar, descartar, recusa durante pergunta, aplicação sem reiniciar, interruptor |
| `tests/test_env_file.py` | 6 | Preservar comentários, ativar chave comentada, aspas, criar arquivo, gravação atômica |
| `tests/test_scroll.py` | 8 | Rolagem de textos longos, roda do mouse sobre o texto, tamanho da janela |
| `tests/test_icons.py` | 5 | Ícones desenhados e seus estados |
| `tests/test_theme.py` | 3 | Destaque laranja, ausência de cores fixas fora do `style.py`, indicador da câmera |

Os testes são impedidos de gravar no `.env` real do projeto, onde fica a chave da API.

```bash
pytest tests/test_navigation.py tests/test_diagnostics.py tests/test_settings.py tests/test_env_file.py
```
