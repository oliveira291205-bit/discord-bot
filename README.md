# Goku

Bot de Discord feito com `discord.py` e DeepSeek. Ele responde quando alguem menciona o bot, escreve `goku`, `cacaroto` ou `kakaroto`, usa comandos administrativos, ou continua um fluxo recente iniciado com ele.

## Como Rodar

```bash
cd /home/alek/Documentos/aaa
./run.sh
```

Ou manualmente:

```bash
.venv/bin/python -m rei_suzukawa.bot
```

No Discord Developer Portal, mantenha `MESSAGE CONTENT INTENT` e `SERVER MEMBERS INTENT` ativados. Sem `SERVER MEMBERS INTENT`, o bot pode nao conseguir sincronizar todos os membros para marcar pelo ID real.

## Rodar No Termux

No Android com Termux, o guia completo esta em [README_TERMUX.md](README_TERMUX.md).

Fluxo curto dentro da pasta do projeto:

```bash
chmod +x install_termux.sh
./install_termux.sh
```

Depois, para iniciar normalmente:

```bash
./run_bot.sh
```

O instalador pede `DISCORD_TOKEN` e `DEEPSEEK_API_KEY` no terminal e salva apenas no `.env` local do Android. Arquivos locais como `.env`, `.venv/`, `data/` e `logs/` ficam fora do Git pelo `.gitignore`.

## Memoria SQLite

O fluxo principal nao usa mais Obsidian. A memoria agora e local, gratuita e persistente em:

```text
data/memory.sqlite3
```

O cerebro separa tudo por escopo:

- `global`: regras e informacoes gerais.
- `guild`: memoria do servidor atual.
- `channel`: memoria do canal atual.
- `user`: memoria do usuario pelo `discord_id`.
- `user_channel`: memoria daquele usuario naquele canal especifico.
- `session`: contexto recente pequeno, mantido em RAM.

O Goku nunca envia o banco inteiro para a DeepSeek. Ele busca memorias relevantes no SQLite usando FTS5 quando disponivel, ou fallback local por palavras-chave. Por padrao entram no prompt no maximo 10 memorias, com 250 caracteres cada.

## Economia De Tokens

Antes de toda chamada para DeepSeek, o `PromptBudgetManager` limita:

- prompt total: `DEEPSEEK_MAX_TOTAL_PROMPT_CHARS=24000`;
- estimativa de tokens: `DEEPSEEK_MAX_TOTAL_ESTIMATED_TOKENS=6000`;
- system prompt: `DEEPSEEK_MAX_SYSTEM_PROMPT_CHARS=4000`;
- bloco de memoria: `DEEPSEEK_MAX_MEMORY_CONTEXT_CHARS=5000`;
- contexto recente: `DEEPSEEK_MAX_RECENT_CONTEXT_CHARS=4000`;
- mensagem atual: `DEEPSEEK_MAX_USER_MESSAGE_CHARS=3000`;
- hard limit: `DEEPSEEK_HARD_BLOCK_CHARS=32000`.

Se passar do limite, o bot reduz memorias, corta contexto recente e cai em fallback seguro com apenas personalidade essencial e mensagem atual. Ele nao manda dumps, historicos completos, banco inteiro, Markdown inteiro ou anexos gigantes para a IA.

## Configuracao

```env
REI_NATURAL_INTERACTIONS_ENABLED=true
REI_NATURAL_ALLOW_SPONTANEOUS=true
REI_NATURAL_REPLY_CHANCE=0.03
REI_NATURAL_COOLDOWN_SECONDS=300
REI_NATURAL_MAX_PER_HOUR=5
REI_NATURAL_MAX_PER_CHANNEL_HOUR=3
REI_NATURAL_AVOID_SERIOUS=true
REI_NATURAL_USE_AI=false

REI_MEMORY_ENABLED=true
REI_MEMORY_SQLITE_PATH=data/memory.sqlite3
REI_MEMORY_USE_OBSIDIAN=false
REI_MEMORY_USE_EMBEDDINGS=false
REI_MEMORY_USE_AI_EXTRACTION=false
REI_MEMORY_USE_AI_SUMMARY=false
REI_MEMORY_MAX_INJECTED=10
REI_MEMORY_MAX_CHARS=250
REI_MEMORY_RECENT_CONTEXT_LIMIT=10

DEEPSEEK_MAX_TOTAL_PROMPT_CHARS=24000
DEEPSEEK_MAX_TOTAL_ESTIMATED_TOKENS=6000
DEEPSEEK_HARD_BLOCK_CHARS=32000
DEEPSEEK_HARD_BLOCK_ESTIMATED_TOKENS=8000
DEEPSEEK_DEBUG_PROMPT_SIZE=true
```

Para desligar memoria:

```env
REI_MEMORY_ENABLED=false
```

## Interacoes Naturais

O Goku nao entra mais em conversas soltas. Ele so responde quando alguem chama `Goku`, `Cacaroto` ou `Kakaroto`, menciona o bot diretamente, responde uma mensagem dele, ou continua um fluxo recente dentro da janela configurada.

Exemplos:

- `fala serio`: fica quieto.
- `Goku, fala serio`: responde.
- `Cacaroto, marca o Cauã`: tenta resolver o membro localmente e menciona o ID real.

As respostas sociais usam templates locais por padrao, entao nao gastam DeepSeek para cada brincadeira.

Controles principais:

- `REI_NATURAL_REPLY_CHANCE=0.03`: chance base de resposta espontanea.
- `REI_NATURAL_COOLDOWN_SECONDS=300`: intervalo minimo entre respostas espontaneas.
- `REI_NATURAL_MAX_PER_HOUR=5`: limite global por hora.
- `REI_NATURAL_MAX_PER_CHANNEL_HOUR=3`: limite por canal por hora.
- `REI_NATURAL_AVOID_SERIOUS=true`: evita interromper canais/assuntos serios.
- `REI_NATURAL_USE_AI=false`: respostas espontaneas nao chamam DeepSeek por padrao.
- `REI_WAKE_WORDS=goku,cacaroto,kakaroto`: nomes de ativacao.
- `REI_ACTIVE_CONVERSATION_SECONDS=120`: janela curta para continuar um fluxo ja iniciado.

Ele tambem entende frases naturais de preferencia, como `sem zoeira`, `pode zoar`, `fala serio`, `para de me chamar assim` e `me chama de...`, salvando isso na memoria segmentada do usuario.

Essas frases so disparam resposta quando o bot for chamado ou quando forem parte de um fluxo ativo.

## Membros Do Servidor

O bot cria um cache local em SQLite na tabela `guild_members`. Ele salva apenas dados publicos necessarios para resolver mencoes:

- `guild_id`
- `user_id`
- `username`
- `global_name`
- `display_name`
- `nick`
- `mention`
- estado ativo

Ele nunca envia a lista completa de membros para a DeepSeek. A resolucao de nomes acontece localmente por ID, mention, username, display name, nick, texto parcial e nome sem acento.

Frases naturais, sempre chamando o bot:

- `Goku, atualiza os membros`
- `Goku, sincroniza o servidor`
- `Goku, status dos membros`
- `Cacaroto, marca o Cauã`
- `Kakaroto, avisa o João pra olhar o grupo`

Protecoes:

- nao marca `@everyone`;
- nao marca `@here`;
- nao marca todo mundo;
- se achar varias pessoas parecidas, pede escolha;
- sincronizacao manual exige permissao de admin/moderador.

## GIFs

GIFs usam uma lista local gratuita por padrao, sem API externa paga. O bot decide primeiro se deve responder; so depois decide se manda GIF.

Configs:

```env
REI_GIFS_ENABLED=true
REI_GIF_REPLY_CHANCE=0.22
REI_GIF_MIN_CHANCE=0.20
REI_GIF_MAX_CHANCE=0.25
REI_GIF_COOLDOWN_SECONDS=300
REI_GIF_MAX_PER_CHANNEL_HOUR=4
REI_GIF_MAX_PER_USER_HOUR=3
REI_GIF_USE_EXTERNAL_API=false
REI_GIF_USE_LOCAL_POOL=true
```

Ele nao manda GIF em modo serio, assunto delicado, cooldown ativo, canal saturado ou quando a mensagem nem deveria receber resposta.

## Recursos Locais

O bot tem respostas locais para economizar tokens. Ele nao chama DeepSeek para cumprimentos simples, agradecimentos, risadas curtas, sucesso basico, status e erros conhecidos.

Detector de erros coberto:

- `Traceback`
- `SyntaxError`
- `ModuleNotFoundError`
- `ImportError`
- `Permission denied`
- `No such file or directory`
- erros comuns de `pip`, `git`, `.env`, SQLite e Tesseract/OCR

Status natural:

```text
goku status
status do bot
diagnostico
o bot ta online?
```

Mostra apenas estado seguro: DeepSeek configurado ou nao, SQLite, OCR/Tesseract, ambiente, uptime e versao do Python. Tokens nunca sao exibidos.

## Leitura Do Proprio Codigo

O Goku sabe que e um bot de Discord feito em Python e brinca que talvez esteja vivo. Ele tambem consegue ler o proprio codigo em modo seguro, mas nao tem comandos para editar, apagar, sobrescrever ou reparar arquivos sozinho.

Comandos:

- `!codigo` mostra um mapa curto do projeto.
- `!codigo listar` lista arquivos seguros.
- `!codigo arquivo rei_suzukawa/bot.py` mostra um arquivo em modo somente leitura.

Por seguranca, a leitura bloqueia `.env`, bancos SQLite, logs, imagens, PDFs, caches, venv, `.git` e caminhos que tentem sair da pasta do projeto.

## XP E Conquistas

O XP usa o mesmo SQLite local (`data/memory.sqlite3`) e cria as tabelas `user_xp` e `user_achievements`.

Recompensas com cooldown:

- estudo: `+5 XP`
- ajuda de programacao: `+10 XP`
- erro resolvido: `+15 XP`
- tarefa concluida: `+20 XP`
- calculo: `+25 XP`
- Termux/Git/Python em contexto de aprendizado: `+30 XP`

Titulos:

- Nivel 1: Saiyajin Iniciante
- Nivel 3: Aluno do Mestre Kame
- Nivel 5: Dev em Treinamento
- Nivel 8: Cacador de Bugs
- Nivel 10: Mestre do Termux
- Nivel 15: Guerreiro do Codigo
- Nivel 20: Super Saiyajin Dev

Configs:

```env
FUN_ENABLED=true
FUN_USE_AI=false
FUN_REPLY_CHANCE=0.03
FUN_COOLDOWN_SECONDS=300
FUN_MAX_PER_CHANNEL_HOUR=5
FUN_SAFE_ROASTS_ONLY=true
XP_ENABLED=true
XP_COOLDOWN_SECONDS=180
XP_MAX_PER_USER_HOUR=100
LOCAL_REPLIES_ENABLED=true
LOCAL_REPLIES_CALL_AI_ONLY_WHEN_NEEDED=true
```

## Comandos

- `!ajuda` mostra os comandos.
- `!ping` testa a latencia.
- `!status` mostra estado geral.
- `!perguntar texto` chama a DeepSeek.
- `!resumo` resume conversa recente.
- `!resenha` gera resenha do historico recente do canal.
- `!anexos` explica leitura de fotos, PDFs e arquivos.
- `!codigo` mostra/le arquivos seguros do proprio projeto sem editar nada.
- `!chamar @usuario assunto` marca alguem e puxa assunto.
- `!lembrar texto` salva memoria manual no SQLite.
- `!memorias` mostra suas memorias.
- `!perfil` mostra sua memoria de usuario.
- `!esquecer` limpa memoria temporaria e desativa memorias suas.
- `!limpar` limpa contexto recente do canal.

Comandos do novo cerebro:

- `!memoria status`
- `!memoria minha`
- `!memoria canal`
- `!memoria servidor`
- `!memoria esquecer_minha`
- `!memoria esquecer_canal`
- `!memoria esquecer_servidor`
- `!memoria exportar`
- `!memoria debug texto`

`!cerebro` continua como atalho legado, mas agora mostra o status do SQLite.

## Frases Naturais

O Goku entende:

- `me chama de Ale`
- `sem zoeira`
- `pode zoar`
- `fala serio agora`
- `para de me chamar assim`
- `lembra disso`
- `guarda isso`
- `salva isso na sua memoria`
- `nao guarda isso`
- `esquece isso`
- `o que voce lembra de mim?`
- `o que voce lembra deste canal?`
- `limpa minha memoria`
- `limpa a memoria deste canal`

Dados sensiveis como senhas, tokens, API keys, CPF, RG, cartao, dados bancarios e endereco completo sao bloqueados.

## Migrar Obsidian Antigo

A migracao e opcional e nao apaga arquivos originais:

```bash
.venv/bin/python scripts/import_obsidian_to_sqlite.py /home/alek/bsidian/rei-suzukawa-cerebro --sqlite-path data/memory.sqlite3
```

O bot funciona mesmo sem migrar nada.

## Anexos

PDFs com texto sao lidos direto. Imagens usam OCR quando o sistema tiver `tesseract`; se nao houver texto legivel, o bot guarda metadados curtos e nao inventa detalhes visuais.
