# Rodar O Bot No Termux

Este guia roda o bot direto no Android pelo Termux, sem colocar token ou API key no Git.

## 1. Abrir O Termux

Abra o app Termux no Android.

Se for a primeira vez, atualize:

```bash
pkg update -y
pkg upgrade -y
```

## 2. Entrar Na Pasta Do Projeto

Para ver onde voce esta:

```bash
pwd
```

Para listar arquivos:

```bash
ls -la
```

Para entrar em uma pasta:

```bash
cd nome_da_pasta
```

Exemplo comum:

```bash
cd ~/discord-bot
```

## 3. Instalar Tudo

Dentro da pasta do projeto:

```bash
chmod +x install_termux.sh
./install_termux.sh
```

O instalador vai:

- atualizar pacotes do Termux;
- instalar Python, Git, Nano, OpenSSL e bibliotecas necessarias;
- tentar instalar `tesseract` para OCR de imagens;
- criar `.venv` quando possivel;
- instalar `requirements.txt`;
- criar/configurar `.env`;
- pedir suas keys no terminal;
- deixar `run_bot.sh` executavel.

## 4. Colar As Keys

Quando o script pedir:

```text
DISCORD_TOKEN:
DEEPSEEK_API_KEY:
```

Cole os valores e aperte Enter.

Por seguranca, o Termux pode nao mostrar nada enquanto voce digita. Isso e normal.

As keys ficam apenas no arquivo local `.env` do Android. Elas nao vao para o Git.

## 5. Iniciar O Bot

Depois da instalacao:

```bash
./run_bot.sh
```

Modo debug seguro:

```bash
./run_bot.sh --debug
```

O debug mostra apenas se as variaveis existem:

```text
DISCORD_TOKEN=OK
DEEPSEEK_API_KEY=OK
```

Ele nunca mostra o valor real das chaves.

## 6. Parar O Bot

Para parar:

```text
CTRL+C
```

## 7. Editar O .env

Se precisar trocar token, API key ou entrypoint:

```bash
nano .env
```

Salve no Nano:

```text
CTRL+O
Enter
CTRL+X
```

## 8. BOT_ENTRYPOINT

O bot usa:

```env
BOT_ENTRYPOINT=rei_suzukawa.bot
```

Se um dia o arquivo principal mudar, ajuste no `.env`.

Exemplos:

```env
BOT_ENTRYPOINT=main.py
BOT_ENTRYPOINT=bot.py
BOT_ENTRYPOINT=rei_suzukawa.bot
```

## 9. Evitar Que O Android Durma

Para manter o Termux acordado:

```bash
termux-wake-lock
```

Para liberar:

```bash
termux-wake-unlock
```

Se o comando nao existir, instale o app Termux:API e rode:

```bash
pkg install termux-api
```

## 10. Erros Comuns

Se o Termux disser que o Android bloqueou execucao, rode:

```bash
chmod +x install_termux.sh run_bot.sh
```

Se faltar `.env`:

```bash
python setup_env.py
```

Se dependencias quebrarem:

```bash
rm -rf .venv
./install_termux.sh
```

Para verificar memoria, PDF e OCR sem mostrar secrets:

```bash
./run_bot.sh --debug
```

ou:

```bash
python termux_check.py
```

Se aparecer `tesseract: FALTANDO`, rode:

```bash
pkg install tesseract
pkg install tesseract-lang-por
```

Se o pacote de portugues nao existir no seu Termux, o bot tenta OCR em ingles/padrao mesmo assim.

Se o bot nao achar arquivo principal, edite:

```bash
nano .env
```

E configure:

```env
BOT_ENTRYPOINT=rei_suzukawa.bot
```
