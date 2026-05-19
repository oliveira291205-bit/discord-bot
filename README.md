# Goku

Bot de Discord feito com `discord.py` e DeepSeek. Ele responde quando alguem menciona o bot, escreve `goku`, `kakaroto`, `rei`, `suzukawa`, usa comandos administrativos, ou quando a conversa pede uma reacao natural curta.

## Como Rodar

```bash
cd /home/alek/Documentos/aaa
./run.sh
```

Ou manualmente:

```bash
.venv/bin/python -m rei_suzukawa.bot
```

No Discord Developer Portal, mantenha `Message Content Intent` ativado.

## Rodar No Termux

No Android com Termux, use estes passos dentro da pasta do projeto:

```bash
pkg update -y
pkg install -y git python clang libjpeg-turbo zlib freetype libpng
./scripts/termux_install.sh
nano .env
./scripts/termux_run.sh
```

No `.env`, preencha pelo menos:

```env
DISCORD_TOKEN=seu_token_do_discord
DEEPSEEK_API_KEY=sua_chave_da_deepseek
```

Para deixar reiniciando sozinho enquanto a sessao Termux estiver aberta:

```bash
./scripts/termux_keepalive.sh
```

Arquivos locais como `.env`, `.venv/`, `data/` e `logs/` ficam fora do Git pelo `.gitignore`.

Se o Termux falhar tentando compilar `jiter`/`maturin`, atualize o repo. O bot nao depende mais do pacote `openai`; ele chama a DeepSeek por HTTP direto com `httpx`, que evita esse erro comum em Android/ARM.

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

O Goku nao depende de prefixo para pequenas reacoes sociais. Ele observa o contexto e pode comentar raramente quando detectar bug, conquista, estudo, meme, lore ou piada interna. Essas respostas usam templates locais por padrao, entao nao gastam DeepSeek para cada brincadeira.

Controles principais:

- `REI_NATURAL_REPLY_CHANCE=0.03`: chance base de resposta espontanea.
- `REI_NATURAL_COOLDOWN_SECONDS=300`: intervalo minimo entre respostas espontaneas.
- `REI_NATURAL_MAX_PER_HOUR=5`: limite global por hora.
- `REI_NATURAL_MAX_PER_CHANNEL_HOUR=3`: limite por canal por hora.
- `REI_NATURAL_AVOID_SERIOUS=true`: evita interromper canais/assuntos serios.
- `REI_NATURAL_USE_AI=false`: respostas espontaneas nao chamam DeepSeek por padrao.

Ele tambem entende frases naturais de preferencia, como `sem zoeira`, `pode zoar`, `fala serio`, `para de me chamar assim` e `me chama de...`, salvando isso na memoria segmentada do usuario.

## Comandos

- `!ajuda` mostra os comandos.
- `!ping` testa a latencia.
- `!status` mostra estado geral.
- `!perguntar texto` chama a DeepSeek.
- `!resumo` resume conversa recente.
- `!resenha` gera resenha do historico recente do canal.
- `!anexos` explica leitura de fotos, PDFs e arquivos.
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
