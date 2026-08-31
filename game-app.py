from collections import defaultdict
from datetime import datetime
from typing import Any
import random

import pandas as pd
import streamlit as st

try:
    from streamlit_gsheets import GSheetsConnection
except ImportError:
    # O jogo continua funcionando localmente/offline mesmo sem o pacote opcional.
    GSheetsConnection = None


st.set_page_config(
    page_title="Game Contábil PRO",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_TITLE = "Game Contábil PRO"
WORKSHEET = "Ranking"
RANKING_COLUMNS = ["nome", "xp", "nivel", "data"]

# Plano de contas didático. A natureza determina como o saldo da conta é calculado.
PLANO = {
    "Caixa": "Ativo",
    "Banco": "Ativo",
    "Estoque": "Ativo",
    "Clientes": "Ativo",
    "Fornecedores": "Passivo",
    "Empréstimos": "Passivo",
    "Capital Social": "PL",
    "Receita de Vendas": "Receita",
    "Receita de Serviços": "Receita",
    "Custo das Mercadorias": "Despesa",
    "Despesa com Salários": "Despesa",
    "Despesa com Aluguel": "Despesa",
}

INITIAL_ENTRIES = [
    {
        "desc": "Integralização do capital social",
        "debito": "Caixa",
        "credito": "Capital Social",
        "valor": 10_000.00,
    }
]

CHALLENGES = [
    {
        "title": "Pagamento de aluguel",
        "scenario": "O aluguel de R$ 800,00 foi pago à vista, mas alguém registrou apenas R$ 500,00.",
        "wrong": {"debito": "Despesa com Aluguel", "credito": "Caixa", "valor": 500.00},
        "correct": {"debito": "Despesa com Aluguel", "credito": "Caixa", "valor": 800.00},
    },
    {
        "title": "Compra de estoque à vista",
        "scenario": "Uma compra de estoque de R$ 1.200,00 foi registrada com as contas invertidas.",
        "wrong": {"debito": "Caixa", "credito": "Estoque", "valor": 1_200.00},
        "correct": {"debito": "Estoque", "credito": "Caixa", "valor": 1_200.00},
    },
    {
        "title": "Venda de serviços",
        "scenario": "A empresa recebeu R$ 900,00 por um serviço, mas a receita foi debitada.",
        "wrong": {"debito": "Receita de Serviços", "credito": "Caixa", "valor": 900.00},
        "correct": {"debito": "Caixa", "credito": "Receita de Serviços", "valor": 900.00},
    },
]


def reset_game() -> None:
    """Volta o jogo ao estado inicial, sem depender de dados externos."""
    st.session_state.lancamentos = [entry.copy() for entry in INITIAL_ENTRIES]
    st.session_state.xp = 0
    st.session_state.desafio_ativo = None
    st.session_state.flash = "Jogo reiniciado com o lançamento inicial."


def init_state() -> None:
    st.session_state.setdefault(
        "lancamentos", [entry.copy() for entry in INITIAL_ENTRIES]
    )
    st.session_state.setdefault("xp", 0)
    st.session_state.setdefault("desafio_ativo", None)
    st.session_state.setdefault("flash", "")


def brl(value: float) -> str:
    """Formata valores para o padrão monetário usado no Brasil."""
    formatted = f"R$ {value:,.2f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def calculate_balances(entries: list[dict[str, Any]]) -> dict[str, Any]:
    razonetes: defaultdict[str, dict[str, float]] = defaultdict(
        lambda: {"D": 0.0, "C": 0.0}
    )

    for entry in entries:
        razonetes[entry["debito"]]["D"] += float(entry["valor"])
        razonetes[entry["credito"]]["C"] += float(entry["valor"])

    receitas = sum(
        values["C"] - values["D"]
        for account, values in razonetes.items()
        if PLANO.get(account) == "Receita"
    )
    despesas = sum(
        values["D"] - values["C"]
        for account, values in razonetes.items()
        if PLANO.get(account) == "Despesa"
    )
    lucro = receitas - despesas
    ativo = sum(
        values["D"] - values["C"]
        for account, values in razonetes.items()
        if PLANO.get(account) == "Ativo"
    )
    passivo = sum(
        values["C"] - values["D"]
        for account, values in razonetes.items()
        if PLANO.get(account) == "Passivo"
    )
    pl_base = sum(
        values["C"] - values["D"]
        for account, values in razonetes.items()
        if PLANO.get(account) == "PL"
    )
    pl_total = pl_base + lucro
    diferenca = ativo - (passivo + pl_total)

    return {
        "razonetes": razonetes,
        "receitas": receitas,
        "despesas": despesas,
        "lucro": lucro,
        "ativo": ativo,
        "passivo": passivo,
        "pl_base": pl_base,
        "pl_total": pl_total,
        "diferenca": diferenca,
    }


def spreadsheet_configured() -> bool:
    """Detecta uma configuração real sem quebrar quando secrets.toml não existe."""
    settings = gsheets_settings()
    spreadsheet = str(settings.get("spreadsheet", "")).strip()
    if not spreadsheet or "SEU_ID_AQUI" in spreadsheet:
        return False

    # A conexão pública aceita somente URL. A conexão com service account
    # também pode localizar a planilha pelo nome.
    if is_service_account_configured():
        return True
    return spreadsheet.startswith("https://docs.google.com/spreadsheets/")


def gsheets_settings() -> dict[str, Any]:
    try:
        connections = st.secrets.get("connections", {})
        gsheets = connections.get("gsheets", {})
        return dict(gsheets)
    except Exception:
        return {}


def is_service_account_configured() -> bool:
    settings = gsheets_settings()
    return bool(
        settings.get("type") == "service_account"
        and settings.get("client_email")
        and settings.get("private_key")
    )


def empty_ranking() -> pd.DataFrame:
    return pd.DataFrame(columns=RANKING_COLUMNS)


def read_ranking() -> tuple[pd.DataFrame, str | None]:
    """Lê o ranking, mas mantém a experiência principal disponível offline."""
    if not spreadsheet_configured():
        return empty_ranking(), None
    if GSheetsConnection is None:
        return empty_ranking(), "Dependência do Google Sheets não instalada."

    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # URL pública usa a primeira aba (gid 0); service account usa o nome.
        worksheet = WORKSHEET if is_service_account_configured() else 0
        ranking = conn.read(worksheet=worksheet, ttl=60)
        if ranking is None or ranking.empty:
            return empty_ranking(), None

        ranking = ranking.copy()
        for column in RANKING_COLUMNS:
            if column not in ranking.columns:
                ranking[column] = ""
        ranking["xp"] = pd.to_numeric(ranking["xp"], errors="coerce").fillna(0)
        ranking["nome"] = ranking["nome"].fillna("").astype(str).str.strip()
        ranking = ranking[ranking["nome"] != ""]
        ranking["nivel"] = pd.to_numeric(
            ranking["nivel"], errors="coerce"
        ).fillna(1).astype(int)
        return ranking[RANKING_COLUMNS].sort_values(
            "xp", ascending=False, kind="stable"
        ), None
    except Exception as exc:
        return empty_ranking(), f"Não foi possível ler o ranking: {exc}"


def save_to_ranking(name: str, xp: int) -> tuple[bool, str]:
    if not spreadsheet_configured():
        return False, "Configure a URL do Google Sheets nos secrets do Streamlit."
    if not is_service_account_configured():
        return (
            False,
            "A planilha está em modo leitura. Adicione uma service account "
            "aos secrets para habilitar o ranking global.",
        )
    if GSheetsConnection is None:
        return False, "A dependência do Google Sheets não está disponível."

    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        current, _ = read_ranking()
        new_row = pd.DataFrame(
            [
                {
                    "nome": name.strip(),
                    "xp": int(xp),
                    "nivel": max(1, int(xp // 50) + 1),
                    "data": datetime.now().strftime("%d/%m/%Y"),
                }
            ]
        )
        final = pd.concat([current, new_row], ignore_index=True)
        final["xp"] = pd.to_numeric(final["xp"], errors="coerce").fillna(0).astype(int)
        final = final.sort_values("xp", ascending=False, kind="stable")
        conn.update(worksheet=WORKSHEET, data=final[RANKING_COLUMNS])
        return True, "Seu resultado foi salvo no ranking da turma."
    except Exception as exc:
        return False, f"Não foi possível salvar no Google Sheets: {exc}"


def challenge_is_correct(
    challenge: dict[str, Any], debit: str, credit: str, value: float
) -> bool:
    answer = challenge["correct"]
    return (
        debit == answer["debito"]
        and credit == answer["credito"]
        and abs(value - answer["valor"]) < 0.01
    )


init_state()

st.markdown(
    """
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 3rem; }
        [data-testid="stMetric"] {
            background: linear-gradient(135deg, #101828, #172554);
            border: 1px solid #334155;
            padding: 1rem;
            border-radius: 14px;
        }
        [data-testid="stMetricLabel"], [data-testid="stMetricValue"] { color: #f8fafc; }
        .hint {
            padding: 0.85rem 1rem;
            border-left: 4px solid #38bdf8;
            background: #eff6ff;
            border-radius: 6px;
            color: #0f172a;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if st.session_state.flash:
    st.success(st.session_state.flash)
    st.session_state.flash = ""

with st.sidebar:
    st.header("🎮 Controles")
    st.caption("Registre lançamentos, feche o balanço e acumule XP.")
    st.divider()
    if st.button("🔄 Reiniciar jogo", use_container_width=True):
        reset_game()
        st.rerun()
    st.divider()
    st.subheader("Como jogar")
    st.markdown(
        "1. Registre fatos no **Diário**.\n"
        "2. Confira a balança no **Balanço Patrimonial**.\n"
        "3. Resolva um desafio para ganhar XP.\n"
        "4. Salve seu resultado no ranking."
    )

st.title("🏆 Contabilidade Game PRO")
st.write("Aprenda lançamentos contábeis na prática, com feedback imediato.")

balances = calculate_balances(st.session_state.lancamentos)
level = max(1, st.session_state.xp // 50 + 1)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Seu XP", st.session_state.xp)
m2.metric("Nível", level)
m3.metric("Lançamentos", len(st.session_state.lancamentos))
m4.metric("Resultado", brl(balances["lucro"]))

st.header("🕵️ Modo Detetive")
st.caption("Encontre o lançamento correto e receba +50 XP.")

if st.button("🎲 Gerar desafio", type="secondary"):
    st.session_state.desafio_ativo = random.choice(CHALLENGES)
    st.session_state.challenge_error = ""
    st.rerun()

if st.session_state.desafio_ativo:
    challenge = st.session_state.desafio_ativo
    st.info(f"**{challenge['title']}** — {challenge['scenario']}")
    st.caption(
        "Registro encontrado: "
        f"D: {challenge['wrong']['debito']} · "
        f"C: {challenge['wrong']['credito']} · "
        f"Valor: {brl(challenge['wrong']['valor'])}"
    )
    with st.form("challenge_form"):
        c1, c2, c3 = st.columns([1.5, 1.5, 1])
        answer_debit = c1.selectbox("Débito correto", list(PLANO), key="challenge_debit")
        answer_credit = c2.selectbox(
            "Crédito correto", list(PLANO), index=4, key="challenge_credit"
        )
        answer_value = c3.number_input(
            "Valor correto (R$)", min_value=0.01, value=100.00, step=50.00
        )
        submitted = st.form_submit_button("Verificar resposta", type="primary")

    if submitted:
        if answer_debit == answer_credit:
            st.session_state.challenge_error = "Débito e crédito precisam ser contas diferentes."
        elif challenge_is_correct(
            challenge, answer_debit, answer_credit, float(answer_value)
        ):
            st.session_state.xp += 50
            st.session_state.desafio_ativo = None
            st.session_state.flash = "Resposta correta! Você ganhou +50 XP. 🎉"
            st.rerun()
        else:
            st.session_state.challenge_error = (
                "Ainda não. Revise a natureza das contas e tente novamente."
            )

    if st.session_state.get("challenge_error"):
        st.warning(st.session_state.challenge_error)

st.header("1️⃣ Diário")
st.markdown(
    '<div class="hint">Regra rápida: todo lançamento tem pelo menos um débito e um crédito de mesmo valor.</div>',
    unsafe_allow_html=True,
)

accounts = list(PLANO.keys())
with st.form("diario_form", clear_on_submit=True):
    d1, d2, d3, d4 = st.columns([2.2, 1.5, 1.5, 1])
    description = d1.text_input("Histórico", placeholder="Ex.: Compra de estoque a prazo")
    debit = d2.selectbox("Débito", accounts, index=2)
    credit = d3.selectbox("Crédito", accounts, index=4)
    value = d4.number_input("Valor (R$)", min_value=0.01, value=500.00, step=50.00)
    launch = st.form_submit_button("Lançar +10 XP", type="primary")

if launch:
    if not description.strip():
        st.error("Informe um histórico para o lançamento.")
    elif debit == credit:
        st.error("Débito e crédito não podem ser a mesma conta.")
    else:
        st.session_state.lancamentos.append(
            {
                "desc": description.strip(),
                "debito": debit,
                "credito": credit,
                "valor": round(float(value), 2),
            }
        )
        st.session_state.xp += 10
        st.session_state.flash = "Lançamento incluído! Você ganhou +10 XP."
        st.rerun()

ledger = pd.DataFrame(st.session_state.lancamentos)
ledger_display = ledger.rename(
    columns={
        "desc": "Histórico",
        "debito": "Débito",
        "credito": "Crédito",
        "valor": "Valor (R$)",
    }
)
ledger_display["Valor (R$)"] = ledger_display["Valor (R$)"].map(brl)
st.dataframe(
    ledger_display[["Histórico", "Débito", "Crédito", "Valor (R$)"]],
    use_container_width=True,
    hide_index=True,
)

if len(st.session_state.lancamentos) > 1:
    if st.button("Excluir último lançamento", type="secondary"):
        removed = st.session_state.lancamentos.pop()
        st.session_state.xp = max(0, st.session_state.xp - 10)
        st.session_state.flash = f"Lançamento “{removed['desc']}” excluído."
        st.rerun()

st.header("2️⃣ Balanço Patrimonial")
bp1, bp2 = st.columns(2)
with bp1:
    st.subheader("Ativo")
    st.metric("Total do Ativo", brl(balances["ativo"]))
with bp2:
    st.subheader("Passivo + Patrimônio Líquido")
    difference = balances["diferenca"]
    st.metric(
        "Total do Passivo + PL",
        brl(balances["passivo"] + balances["pl_total"]),
        delta=f"{brl(difference)} de diferença",
        delta_color="normal" if abs(difference) < 0.01 else "inverse",
    )

summary1, summary2, summary3 = st.columns(3)
summary1.metric("Receitas", brl(balances["receitas"]))
summary2.metric("Despesas", brl(balances["despesas"]))
summary3.metric("Lucro / Prejuízo", brl(balances["lucro"]))

if abs(difference) < 0.01:
    st.success("🏆 BP FECHOU! Você venceu esta fase.")
    st.progress(1.0)
else:
    st.error(f"BP não fecha. Diferença encontrada: {brl(difference)}.")
    st.progress(0.3)

st.header("🏅 Ranking da Turma")
ranking, ranking_error = read_ranking()

if ranking_error:
    st.warning(ranking_error)
elif not spreadsheet_configured():
    st.info(
        "Ranking local/offline ativo. Para compartilhar resultados, configure "
        "a URL da planilha em `.streamlit/secrets.toml` conforme o README."
    )

if abs(difference) < 0.01:
    with st.form("ranking_form"):
        name = st.text_input("Seu nome", max_chars=40, placeholder="Ex.: Ana")
        save = st.form_submit_button("Salvar no ranking global 🌍")
    if save:
        if not name.strip():
            st.error("Digite seu nome antes de salvar.")
        else:
            saved, message = save_to_ranking(name, st.session_state.xp)
            if saved:
                st.success(message)
                ranking, _ = read_ranking()
            else:
                st.error(message)

if ranking.empty:
    st.caption("Ainda não há pontuações publicadas.")
else:
    ranking_view = ranking.head(10).copy()
    ranking_view.insert(0, "Posição", range(1, len(ranking_view) + 1))
    ranking_view = ranking_view.rename(
        columns={"nome": "Nome", "xp": "XP", "nivel": "Nível", "data": "Data"}
    )
    st.dataframe(ranking_view, use_container_width=True, hide_index=True)
    chart_data = ranking.head(5).set_index("nome")[["xp"]].rename(columns={"xp": "XP"})
    st.bar_chart(chart_data)

with st.expander("📚 Natureza das contas"):
    nature = pd.DataFrame(
        [{"Conta": account, "Grupo": group} for account, group in PLANO.items()]
    )
    st.dataframe(nature, use_container_width=True, hide_index=True)
