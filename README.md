# Game Contábil PRO

Aplicação educacional em Streamlit para praticar lançamentos contábeis, acompanhar
XP e conferir se o Balanço Patrimonial fecha.

## Rodar localmente

O projeto requer Python 3.10 ou superior.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

O jogo funciona sem nenhuma conta externa. O ranking fica offline até que o Google
Sheets seja configurado.

## Ativar o ranking no Google Sheets

1. Crie uma planilha no Google Sheets e uma aba chamada `Ranking`.
2. Copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml`.
3. Substitua `SEU_ID_AQUI` pela URL da planilha. Com esse formato, a primeira
   aba é lida em modo público.
4. Para permitir gravação no ranking, crie uma **service account** no Google
   Cloud, troque `spreadsheet` pelo nome da planilha, descomente/preencha os
   campos da service account no arquivo de secrets e compartilhe a planilha
   com o `client_email` dessa conta com permissão de editor.

O arquivo `secrets.toml` está no `.gitignore` e não deve ser enviado ao GitHub.
Se a planilha não estiver configurada, o aplicativo continua utilizável offline.

## Publicar no GitHub

No diretório do projeto:

```bash
git init
git add .
git commit -m " publica Game Contábil PRO "
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/game-contabil-pro.git
git push -u origin main
```

Crie o repositório vazio no GitHub antes de executar o último comando. Troque
`SEU_USUARIO` pelo seu usuário.

## Deploy no Streamlit Community Cloud

1. Acesse `share.streamlit.io` e entre com o GitHub.
2. Selecione o repositório e a branch `main`.
3. Informe `app.py` como arquivo principal.
4. Clique em **Deploy**.
5. Se for usar o ranking global, abra **Settings > Secrets** e cole o conteúdo
   de `.streamlit/secrets.toml.example`, substituindo a URL da planilha.

Não coloque credenciais ou tokens no código, no README ou no repositório.