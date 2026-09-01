from collections import defaultdict
from datetime import datetime
from typing import Any
import random

from fpdf import FPDF
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Game Contábil PRO",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_TITLE = "Game Contábil PRO"
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
    st.session_state.setdefault("ranking", [])


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


def empty_ranking() -> pd.DataFrame:
    return pd.DataFrame(columns=RANKING_COLUMNS)


def ranking_dataframe() -> pd.DataFrame:
    """Transforma o ranking da sessão em uma tabela ordenada."""
    if not st.session_state.ranking:
        return empty_ranking()
    ranking = pd.DataFrame(st.session_state.ranking, columns=RANKING_COLUMNS)
    return ranking.sort_values("xp", ascending=False, kind="stable").reset_index(
        drop=True
    )


def ranking_pdf(ranking: pd.DataFrame) -> bytes:
    """Gera um PDF pronto para o download do aluno."""
    pdf = FPDF()
    pdf.set_title("Ranking - Game Contábil PRO")
    pdf.set_author(APP_TITLE)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, text="Game Contábil PRO", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 9, text="Ranking da turma", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(
        0,
        7,
        text=f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(6)

    widths = [18, 78, 28, 28, 38]
    headers = ["Pos.", "Nome", "XP", "Nível", "Data"]
    pdf.set_fill_color(23, 37, 84)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 10)
    for width, header in zip(widths, headers):
        pdf.cell(width, 9, text=header, border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_text_color(15, 23, 42)
    pdf.set_font("Helvetica", "", 10)
    for position, (_, row) in enumerate(ranking.iterrows(), start=1):
        values = [
            str(position),
            str(row["nome"]),
            str(int(row["xp"])),
            str(int(row["nivel"])),
            str(row["data"]),
        ]
        for index, (width, value) in enumerate(zip(widths, values)):
            pdf.cell(width, 8, text=value, border=1, align="C" if index != 1 else "L")
        pdf.ln()

    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(
        0,
        6,
        text="Ranking gerado pelo Game Contábil PRO.",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    return bytes(pdf.output())


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
        "4. Adicione seu resultado e baixe o ranking em PDF."
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
ranking = ranking_dataframe()

if abs(difference) < 0.01:
    with st.form("ranking_form"):
        name = st.text_input("Seu nome", max_chars=40, placeholder="Ex.: Ana")
        add_to_ranking = st.form_submit_button("Adicionar ao ranking")
    if add_to_ranking:
        if not name.strip():
            st.error("Digite seu nome antes de adicionar.")
        else:
            st.session_state.ranking.append(
                {
                    "nome": name.strip(),
                    "xp": int(st.session_state.xp),
                    "nivel": level,
                    "data": datetime.now().strftime("%d/%m/%Y"),
                }
            )
            st.session_state.flash = "Resultado adicionado ao ranking da sessão."
            st.rerun()

if ranking.empty:
    st.caption("Adicione um resultado acima para montar o ranking.")
else:
    ranking_view = ranking.head(10).copy()
    ranking_view.insert(0, "Posição", range(1, len(ranking_view) + 1))
    ranking_view = ranking_view.rename(
        columns={"nome": "Nome", "xp": "XP", "nivel": "Nível", "data": "Data"}
    )
    st.dataframe(ranking_view, use_container_width=True, hide_index=True)
    chart_data = ranking.head(5).set_index("nome")[["xp"]].rename(columns={"xp": "XP"})
    st.bar_chart(chart_data)
    st.download_button(
        "📄 Baixar ranking em PDF",
        data=ranking_pdf(ranking),
        file_name="ranking-game-contabil-pro.pdf",
        mime="application/pdf",
        type="primary",
        help="Baixa a classificação atual desta sessão em formato PDF.",
    )

with st.expander("📚 Natureza das contas"):
    nature = pd.DataFrame(
        [{"Conta": account, "Grupo": group} for account, group in PLANO.items()]
    )
    st.dataframe(nature, use_container_width=True, hide_index=True)
