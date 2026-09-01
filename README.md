# Game Contábil PRO

Aplicação educacional em Streamlit para praticar lançamentos contábeis, acompanhar
XP, conferir se o Balanço Patrimonial fecha e baixar o ranking da sessão em PDF.

## Rodar localmente

O projeto requer Python 3.10 ou superior.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

O ranking é mantido somente na sessão atual do aplicativo. Não há integração com
Google Sheets, Excel, banco de dados ou qualquer outro serviço externo.
Por isso, cada sessão do navegador mantém sua própria classificação; o PDF é a
forma de levar ou compartilhar o resultado.

Quando o Balanço Patrimonial fechar, informe o nome do aluno e clique em
**Adicionar ao ranking**. A classificação aparece na tela e o botão **Baixar
ranking em PDF** gera o arquivo `ranking-game-contabil-pro.pdf`.

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

O app não exige secrets para funcionar. Não coloque credenciais ou tokens no
código, no README ou no repositório.
