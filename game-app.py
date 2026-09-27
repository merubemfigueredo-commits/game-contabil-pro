from collections import defaultdict
from datetime import datetime
from typing import Any
import random
import re
import time
import unicodedata

from fpdf import FPDF
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Game Contábil PRO",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_TITLE = "Game Contábil PRO"
RANKING_COLUMNS = ["nome", "pontos", "nivel", "data"]

# Plano de contas didático. A natureza determina como o saldo da conta é calculado.
PLANO = {
    "Caixa": "Ativo",
    "Banco": "Ativo",
    "Bancos Conta Movimento": "Ativo",
    "Estoque": "Ativo",
    "Estoque de Mercadorias": "Ativo",
    "Estoques": "Ativo",
    "Clientes": "Ativo",
    "Clientes (Duplicatas a Receber)": "Ativo",
    "Veículos": "Ativo",
    "Equipamentos (Imobilizado)": "Ativo",
    "Adiantamento de Salários (Ativo)": "Ativo",
    "Fornecedores": "Passivo",
    "Empréstimos": "Passivo",
    "Empréstimos Bancários a Pagar": "Passivo",
    "Contas a Pagar": "Passivo",
    "Financiamento": "Passivo",
    "Salários a Pagar": "Passivo",
    "Títulos a Pagar (Promissórias)": "Passivo",
    "Promissórias a Pagar": "Passivo",
    "Capital Social": "PL",
    "Receitas": "Receita",
    "Receita de Vendas": "Receita",
    "Receita de Serviços": "Receita",
    "Receita de Serviços de Consultoria": "Receita",
    "Receita de Vendas de Mercadorias": "Receita",
    "Aplicação Financeira": "Receita",
    "Custo das Mercadorias": "Despesa",
    "Despesa com Salários": "Despesa",
    "Despesa de Salários": "Despesa",
    "Despesa com Aluguel": "Despesa",
    "Materiais de consumo": "Despesa",
    "Despesa com material de limpeza": "Despesa",
    "Despesa de Equipamentos": "Despesa",
    "Despesa de Depreciação": "Despesa",
    "Despesa de Juros": "Despesa",
    "Depreciação Acumulada": "Ativo",
    "Depreciação Acumulada (Instalações)": "Ativo",
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
        "scenario": "O aluguel de 800,00 foi pago à vista, mas alguém registrou apenas 500,00.",
        "wrong": {"debito": "Despesa com Aluguel", "credito": "Caixa", "valor": 500.00},
        "correct": {"debito": "Despesa com Aluguel", "credito": "Caixa", "valor": 800.00},
    },
    {
        "title": "Compra de mercadorias à vista",
        "scenario": "Uma compra de estoque de 1.200,00 foi registrada com as contas invertidas.",
        "wrong": {"debito": "Caixa", "credito": "Estoque", "valor": 1_200.00},
        "correct": {"debito": "Estoque", "credito": "Caixa", "valor": 1_200.00},
    },
    {
        "title": "Venda de serviços",
        "scenario": "A empresa recebeu 900,00 por um serviço, mas a receita foi debitada.",
        "wrong": {"debito": "Receita de Serviços", "credito": "Caixa", "valor": 900.00},
        "correct": {"debito": "Caixa", "credito": "Receita de Serviços", "valor": 900.00},
    },
      {
        "title": "Pagamento de Fornecedores",
        "scenario": "Pagamento de fornecedores em dinheiro no valor de 850,00. O lançamento foi feito invertidamente.",
        "wrong": {"debito": "Clientes", "credito": "Banco", "valor": 850.00},
        "correct": {"debito": "Fornecedores", "credito": "Caixa", "valor": 850.00},
    },
    {
        "title": "Venda a prazo invertida",
        "scenario": "Venda de mercadorias a prazo no valor de 3.000,00. O lançamento foi feito debitando Receita de Vendas e creditando Clientes por 3.100,00.",
        "wrong": {"debito": "Contas a Pagar", "credito": "Fornecedores", "valor": 3100.00},
        "correct": {"debito": "Clientes", "credito": "Receita de Vendas", "valor": 3000.00},
    },
    {
        "title": "Pagamento de aluguel",
        "scenario": "Pagamento de despesa de aluguel por meio do banco no valor de 1.500,00. O lançamento foi feito usando as contas Caixa e Despesas com aluguel 1.000,00.",
        "wrong": {"debito": "Contas a Pagar", "credito": "Caixa", "valor": 1000.00},
        "correct": {"debito": "Despesa com Aluguel", "credito": "Banco", "valor": 1500.00},
    },
    {
        "title": "Saque de Aplicação direto para o Caixa",
        "scenario": "Resgate de aplicação financeira com transferência para o Caixa no valor de 5.000,00. O lançamento foi feito de forma invertida.",
        "wrong": {"debito": "Receitas", "credito": "Caixa", "valor": 5000.00},
        "correct": {"debito": "Caixa", "credito": "Aplicação Financeira", "valor": 5000.00},
    },
     {
        "title": "Compra de veículo a prazo",
        "scenario": "Aquisição de um veículo, a prazo, para uso da empresa por 45.000,00. O lançamento foi feito debitando Clientes e creditando Veículos.",
        "wrong": {"debito": "Estoque", "credito": "Banco", "valor": 45000.00},
        "correct": {"debito": "Veículos", "credito": "Financiamento", "valor": 45000.00},
    },
    {
        "title": "Aquisição, à prazo, de material de consumo",
        "scenario": "Compra de material de escritório a prazo no valor de R$ 600,00. Faça o lançamento corretamente.",
        "wrong": {"debito": "Caixa", "credito": "Contas a Pagar", "valor": 600.00},
        "correct": {"debito": "Materiais de consumo", "credito": "Contas a Pagar", "valor": 600.00},
    },
    {
        "title": "Aquisição de material de consumo",
        "scenario": "Recebimento de duplicata de cliente via banco no valor de 2.400,00. Lançamento invertido de débito e crédito entre ‘Clientes’ e ‘Banco’, registrando Débito: Clientes / Crédito: Banco.",
        "wrong": {"debito": "Clientes", "credito": "Banco", "valor": 2400.00},
        "correct": {"debito": "Banco", "credito": "Clientes", "valor": 2400.00},
    },
    {
        "title": "Venda de mercadorias à vista",
        "scenario": "Erro de lançamento. O lançamento foi feito em conta indevida. Faça o lançamento correto.",
        "wrong": {"debito": "Estoque", "credito": "Banco", "valor": 8000.00},
        "correct": {"debito": "Caixa", "credito": "Receita de Vendas", "valor": 8000.00},
    },
    {
        "title": "Prestação de serviços a prazo",
        "scenario": "Recebimento de serviços prestados, à prazo, no valor de 6.000,00. as contas foram lançadas erradas",
        "wrong": {"debito": "Caixa", "credito": "Fornecedores", "valor": 6000.00},
        "correct": {"debito": "Clientes", "credito": "Receita de Serviços", "valor": 6000.00},
    },
     {
        "title": "Compra de material de limpeza em dinheiro. valor 400,00",
        "scenario": "As contas foram lançadas erradas",
        "wrong": {"debito": "Fornecedores", "credito": "Caixa", "valor": 400.00},
        "correct": {"debito": "Despesa com material de limpeza", "credito": "Caixa", "valor": 400.00},
    },
]

# Os 13 lançamentos abaixo foram transcritos do PDF fornecido. O campo
# "wrong" mantém o contraexemplo do material para que o feedback explique
# exatamente o erro cometido.
LANCAMENTOS = [
    {
        "numero": 1,
        "titulo": "Constituição de Capital Social",
        "scenario": 'A empresa foi constituída com capital social de R$ 100.000,00, depositado diretamente no banco.',
        "correct": {"debito": "Bancos Conta Movimento", "credito": "Capital Social", "valor": 100000.00},
        "wrong": {"debito": "Capital Social", "credito": "Caixa", "valor": 100000.00},
    },
    {
        "numero": 2,
        "titulo": "Compra de Mercadorias à Vista",
        "scenario": "Compra de mercadorias para revenda por R$ 15.000,00, paga imediatamente por transferência bancária.",
        "correct": {"debito": "Estoque de Mercadorias", "credito": "Bancos Conta Movimento", "valor": 15000.00},
        "wrong": {"debito": "Bancos Conta Movimento", "credito": "Estoque de Mercadorias", "valor": 15000.00},
    },
    {
        "numero": 3,
        "titulo": "Compra de Mercadorias a Prazo",
        "scenario": "Compra de mercadorias para estoque por R$ 22.000,00, com pagamento ao fornecedor em 60 dias.",
        "correct": {"debito": "Estoques", "credito": "Fornecedores", "valor": 22000.00},
        "wrong": {"debito": "Fornecedores", "credito": "Estoques", "valor": 22000.00},
    },
    {
        "numero": 4,
        "titulo": "Pagamento de Despesa de Aluguel",
        "scenario": "Quitação da despesa de aluguel do mês, no valor de R$ 3.500,00, retirada diretamente do caixa.",
        "correct": {"debito": "Despesa de Aluguel", "credito": "Caixa", "valor": 3500.00},
        "wrong": {"debito": "Caixa", "credito": "Despesa de Aluguel", "valor": 3500.00},
    },
    {
        "numero": 5,
        "titulo": "Reconhecimento de Despesa de Salários",
        "scenario": "Reconhecimento da folha de pagamento de R$ 18.000,00, com pagamento no mês seguinte.",
        "correct": {"debito": "Despesa de Salários", "credito": "Salários a Pagar", "valor": 18000.00},
        "wrong": {"debito": "Despesa de Salários", "credito": "Bancos Conta Movimento", "valor": 18000.00},
    },
    {
        "numero": 6,
        "titulo": "Aquisição de Imobilizado a Prazo",
        "scenario": "Aquisição de equipamentos de informática por R$ 25.000,00, com promissórias para 120 dias.",
        "correct": {"debito": "Equipamentos (Imobilizado)", "credito": "Títulos a Pagar (Promissórias)", "valor": 25000.00},
        "wrong": {"debito": "Despesa de Equipamentos", "credito": "Promissórias a Pagar", "valor": 25000.00},
    },
    {
        "numero": 7,
        "titulo": "Recebimento de Receita de Serviços",
        "scenario": "Serviço de consultoria recebido à vista no valor de R$ 9.000,00, depositado no caixa.",
        "correct": {"debito": "Caixa", "credito": "Receita de Serviços de Consultoria", "valor": 9000.00},
        "wrong": {"debito": "Receita de Serviços", "credito": "Caixa", "valor": 9000.00},
    },
    {
        "numero": 8,
        "titulo": "Pagamento de Fornecedor em Dinheiro",
        "scenario": "Pagamento em dinheiro de duplicata de fornecedor no valor de R$ 5.000,00.",
        "correct": {"debito": "Fornecedores", "credito": "Caixa", "valor": 5000.00},
        "wrong": {"debito": "Caixa", "credito": "Fornecedores", "valor": 5000.00},
    },
    {
        "numero": 9,
        "titulo": "Reconhecimento de Depreciação",
        "scenario": "Reconhecimento da depreciação das instalações no valor de R$ 4.200,00.",
        "correct": {"debito": "Despesa de Depreciação", "credito": "Depreciação Acumulada (Instalações)", "valor": 4200.00},
        "wrong": {"debito": "Depreciação Acumulada", "credito": "Caixa", "valor": 4200.00},
    },
    {
        "numero": 10,
        "titulo": "Obtenção de Empréstimo Bancário",
        "scenario": "Empréstimo bancário de R$ 50.000,00 integralmente creditado na conta corrente da empresa.",
        "correct": {"debito": "Bancos Conta Movimento", "credito": "Empréstimos Bancários a Pagar", "valor": 50000.00},
        "wrong": {"debito": "Empréstimos Bancários a Pagar", "credito": "Bancos Conta Movimento", "valor": 50000.00},
    },
    {
        "numero": 11,
        "titulo": "Adiantamento de Salário a Funcionário",
        "scenario": "Adiantamento salarial de R$ 1.200,00 pago por cheque da conta corrente da empresa.",
        "correct": {"debito": "Adiantamento de Salários (Ativo)", "credito": "Bancos Conta Movimento", "valor": 1200.00},
        "wrong": {"debito": "Despesa de Salários", "credito": "Bancos Conta Movimento", "valor": 1200.00},
    },
    {
        "numero": 12,
        "titulo": "Despesa de Juros por Atraso",
        "scenario": "Juros de mora de R$ 150,00 pagos junto com um boleto de fornecedor. Considere somente os juros.",
        "correct": {"debito": "Despesa de Juros", "credito": ["Caixa", "Banco"], "valor": 150.00},
        "wrong": {"debito": "Fornecedores", "credito": "Despesa de Juros", "valor": 150.00},
    },
    {
        "numero": 13,
        "titulo": "Venda de Mercadorias a Prazo",
        "scenario": "Venda de mercadorias a prazo por R$ 30.000,00, com recebimento em 30 dias.",
        "correct": {"debito": "Clientes (Duplicatas a Receber)", "credito": "Receita de Vendas de Mercadorias", "valor": 30000.00},
        "wrong": {"debito": "Receita de Vendas", "credito": "Clientes", "valor": 30000.00},
    },
]

GAME_DURATION_SECONDS = 3 * 60
ACCOUNT_OPTIONS = sorted(
    {
        account
        for launch in LANCAMENTOS
        for side in ("debito", "credito")
        for account in (
            launch["correct"][side]
            if isinstance(launch["correct"][side], list)
            else [launch["correct"][side]]
        )
    }
    | {
        account
        for launch in LANCAMENTOS
        for side in ("debito", "credito")
        for account in (
            launch["wrong"][side]
            if isinstance(launch["wrong"][side], list)
            else [launch["wrong"][side]]
        )
    }
    | set(PLANO)
)


def reset_game() -> None:
    """Volta o jogo ao estado inicial, sem depender de dados externos."""
    st.session_state.lancamentos = [entry.copy() for entry in INITIAL_ENTRIES]
    st.session_state.pontos = 0
    st.session_state.desafio_ativo = None
    st.session_state.rodada = []
    st.session_state.rodada_index = 0
    st.session_state.lancamentos_usados = []
    st.session_state.game_started_at = None
    st.session_state.game_over = False
    st.session_state.respostas_corretas = 0
    st.session_state.respostas_respondidas = 0
    st.session_state.flash = "Jogo reiniciado com o lançamento inicial."


def init_state() -> None:
    st.session_state.setdefault(
        "lancamentos", [entry.copy() for entry in INITIAL_ENTRIES]
    )
    st.session_state.setdefault("pontos", 0)
    st.session_state.setdefault("desafio_ativo", None)
    st.session_state.setdefault("rodada", [])
    st.session_state.setdefault("rodada_index", 0)
    st.session_state.setdefault("lancamentos_usados", [])
    st.session_state.setdefault("game_started_at", None)
    st.session_state.setdefault("game_over", False)
    st.session_state.setdefault("respostas_corretas", 0)
    st.session_state.setdefault("respostas_respondidas", 0)
    st.session_state.setdefault("challenge_error", "")
    st.session_state.setdefault("player_name", "")
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
    return ranking.sort_values("pontos", ascending=False, kind="stable").reset_index(
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
    headers = ["Pos.", "Nome", "Pontos", "Nível", "Data"]
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
            str(int(row["pontos"])),
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
    accepted_credits = (
        answer["credito"] if isinstance(answer["credito"], list) else [answer["credito"]]
    )
    return (
        debit == answer["debito"]
        and credit in accepted_credits
        and abs(value - answer["valor"]) < 0.01
    )


def account_text(value: str | list[str]) -> str:
    """Mostra uma conta ou as alternativas aceitas no material didático."""
    if isinstance(value, list):
        return " ou ".join(value)
    return value


def safe_filename(name: str) -> str:
    """Cria um nome de arquivo válido, preservando a leitura em português."""
    normalized = unicodedata.normalize("NFC", name).strip()
    normalized = re.sub(r"[^\w-]+", "_", normalized, flags=re.UNICODE).strip("_")
    return normalized or "jogador"


def pdf_text(value: str) -> str:
    """Adapta texto livre para as fontes padrão do PDF (Latin-1)."""
    return unicodedata.normalize("NFKD", str(value)).encode(
        "latin-1", "replace"
    ).decode("latin-1")


def score_pdf(name: str) -> bytes:
    """Gera o comprovante individual que é baixado no fim da partida."""
    pdf = FPDF()
    pdf.set_title("Score - Game Contabil PRO")
    pdf.set_author(APP_TITLE)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_text_color(15, 23, 42)

    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, text="Game Contabil PRO", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 9, text="Score do jogador", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, text=pdf_text(f"Jogador: {name}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        0,
        8,
        text=f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(8)

    pdf.set_fill_color(23, 37, 84)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(63, 10, text="Pontuação final", border=1, fill=True)
    pdf.cell(63, 10, text="Desafios respondidos", border=1, fill=True)
    pdf.cell(63, 10, text="Acertos", border=1, fill=True)
    pdf.ln()
    pdf.set_text_color(15, 23, 42)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(63, 10, text=str(st.session_state.pontos), border=1, align="C")
    pdf.cell(63, 10, text=str(st.session_state.respostas_respondidas), border=1, align="C")
    pdf.cell(63, 10, text=str(st.session_state.respostas_corretas), border=1, align="C")
    pdf.ln(18)

    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(
        0,
        7,
        text="Cada lançamento correto vale +10 pontos; cada resposta incorreta vale -10 pontos.",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    return bytes(pdf.output())


def game_expired() -> bool:
    started_at = st.session_state.game_started_at
    return bool(
        started_at
        and not st.session_state.game_over
        and time.time() - started_at >= GAME_DURATION_SECONDS
    )


def finish_game() -> None:
    st.session_state.game_over = True
    st.session_state.desafio_ativo = None
    st.session_state.flash = "Fim de jogo! O tempo de 3 minutos terminou."


def launch_batch() -> None:
    """Sorteia até três lançamentos ainda não usados, sem repetir nenhum."""
    if not st.session_state.player_name.strip():
        st.session_state.challenge_error = "Informe o nome do jogador antes de começar."
        return
    if st.session_state.game_over:
        return

    available = [
        launch
        for launch in LANCAMENTOS
        if launch["numero"] not in st.session_state.lancamentos_usados
    ]
    if not available:
        st.session_state.challenge_error = "Os 13 lançamentos já foram utilizados nesta partida."
        return

    if st.session_state.game_started_at is None:
        st.session_state.game_started_at = time.time()

    batch = random.sample(available, min(3, len(available)))
    st.session_state.rodada = batch
    st.session_state.rodada_index = 0
    st.session_state.desafio_ativo = batch[0]
    st.session_state.challenge_error = ""


def remaining_seconds() -> int:
    if st.session_state.game_started_at is None:
        return GAME_DURATION_SECONDS
    return max(
        0,
        int(GAME_DURATION_SECONDS - (time.time() - st.session_state.game_started_at)),
    )


def render_timer() -> None:
    """Exibe o contador no navegador e recarrega a página ao chegar a zero."""
    seconds = max(
        0.0,
        GAME_DURATION_SECONDS
        - (time.time() - st.session_state.game_started_at),
    )
    components.html(
        f"""
        <div id="game-timer" style="font:600 20px sans-serif;color:#0f172a;
             padding:10px 14px;border:1px solid #bae6fd;border-radius:10px;
             background:#f0f9ff;text-align:center">
          Tempo restante: <span id="countdown"></span>
        </div>
        <script>
          const endAt = Date.now() + {seconds * 1000};
          const countdown = document.getElementById("countdown");
          function updateTimer() {{
            const left = Math.max(0, endAt - Date.now());
            const total = Math.ceil(left / 1000);
            const minutes = Math.floor(total / 60);
            const secs = String(total % 60).padStart(2, "0");
            countdown.textContent = `${{minutes}}:${{secs}}`;
            if (left <= 0) {{
              countdown.textContent = "0:00";
              window.parent.location.reload();
            }}
          }}
          updateTimer();
          setInterval(updateTimer, 250);
        </script>
        """,
        height=62,
    )


init_state()

if game_expired():
    finish_game()

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
    st.caption("Resolva lançamentos contábeis em uma partida de 3 minutos.")
    st.divider()
    if st.button("🔄 Reiniciar jogo", use_container_width=True):
        reset_game()
        st.rerun()
    st.divider()
    st.subheader("Como jogar")
    st.markdown(
        "1. Informe seu nome.\n"
        "2. Clique em **Lançar Desafio**.\n"
        "3. Responda ao lançamento sorteado.\n"
        "4. Baixe o score ao final da partida."
    )

st.title("🏆 Contabilidade Game PRO")
st.write("Aprenda lançamentos contábeis na prática, com feedback imediato.")

st.header("1️⃣ Nome do jogador")
st.text_input(
    "Nome do jogador",
    max_chars=40,
    placeholder="Ex.: Rubem Alves Figueredo",
    disabled=st.session_state.game_started_at is not None,
    key="player_name",
)

balances = calculate_balances(st.session_state.lancamentos)
level = max(1, st.session_state.pontos // 50 + 1)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Seus pontos", st.session_state.pontos)
m2.metric("Nível", level)
m3.metric("Lançamentos", len(st.session_state.lancamentos))
m4.metric("Resultado", brl(balances["lucro"]))

st.header("2️⃣ Lançar Desafio")
if st.session_state.game_started_at is not None and not st.session_state.game_over:
    render_timer()

if st.session_state.game_over:
    st.error("⏱️ Fim de jogo! O tempo terminou e a partida está travada.")
elif st.session_state.desafio_ativo is None:
    button_label = (
        "🎲 Lançar Desafio"
        if not st.session_state.lancamentos_usados
        else "🎲 Lançar próximo desafio"
    )
    if st.button(button_label, type="primary"):
        launch_batch()
        if st.session_state.desafio_ativo is not None:
            st.rerun()

if st.session_state.challenge_error:
    st.warning(st.session_state.challenge_error)

st.header("3️⃣ Lançar +10 pontos")
st.caption(
    "O programa sorteia três lançamentos por rodada. Eles não se repetem; "
    "cada resposta correta vale +10 e cada resposta incorreta vale -10."
)

challenge = st.session_state.desafio_ativo
if challenge is not None and not st.session_state.game_over:
    launch_labels = [
        f"Lançamento {launch['numero']} — {launch['titulo']}" for launch in LANCAMENTOS
    ]
    current_label = f"Lançamento {challenge['numero']} — {challenge['titulo']}"
    st.selectbox(
        "Lançamento sorteado (lista dos 13 lançamentos)",
        launch_labels,
        index=launch_labels.index(current_label),
        disabled=True,
        key=f"selected_launch_{challenge['numero']}",
    )
    st.info(f"**{challenge['titulo']}** — {challenge['scenario']}")
    st.caption(
        "Contraexemplo do material: "
        f"D: {challenge['wrong']['debito']} · "
        f"C: {account_text(challenge['wrong']['credito'])} · "
        f"Valor: {brl(challenge['wrong']['valor'])}"
    )

    with st.form(f"launch_points_form_{challenge['numero']}_{st.session_state.rodada_index}"):
        c1, c2, c3 = st.columns([1.5, 1.5, 1])
        answer_debit = c1.selectbox(
            "Débito correto",
            ACCOUNT_OPTIONS,
            index=0,
            key=f"answer_debit_{challenge['numero']}_{st.session_state.rodada_index}",
        )
        answer_credit = c2.selectbox(
            "Crédito correto",
            ACCOUNT_OPTIONS,
            index=0,
            key=f"answer_credit_{challenge['numero']}_{st.session_state.rodada_index}",
        )
        answer_value = c3.number_input(
            "Valor correto (R$)",
            min_value=0.01,
            value=0.01,
            step=50.00,
            key=f"answer_value_{challenge['numero']}_{st.session_state.rodada_index}",
        )
        submitted = st.form_submit_button("Lançar +10 pontos", type="primary")

    if submitted:
        correct = challenge_is_correct(
            challenge, answer_debit, answer_credit, float(answer_value)
        )
        st.session_state.respostas_respondidas += 1
        st.session_state.lancamentos_usados.append(challenge["numero"])

        if correct:
            st.session_state.pontos += 10
            st.session_state.respostas_corretas += 1
            correct_credit = challenge["correct"]["credito"]
            if isinstance(correct_credit, list):
                correct_credit = correct_credit[0]
            st.session_state.lancamentos.append(
                {
                    "desc": f"Lançamento {challenge['numero']}: {challenge['titulo']}",
                    "debito": challenge["correct"]["debito"],
                    "credito": correct_credit,
                    "valor": challenge["correct"]["valor"],
                }
            )
            st.session_state.flash = "Resposta correta! Você ganhou +10 pontos. 🎉"
        else:
            st.session_state.pontos -= 10
            st.session_state.flash = (
                "Resposta incorreta: -10 pontos. "
                f"O correto era D: {challenge['correct']['debito']} · "
                f"C: {account_text(challenge['correct']['credito'])} · "
                f"Valor: {brl(challenge['correct']['valor'])}."
            )

        next_index = st.session_state.rodada_index + 1
        if next_index < len(st.session_state.rodada):
            st.session_state.rodada_index = next_index
            st.session_state.desafio_ativo = st.session_state.rodada[next_index]
        else:
            st.session_state.rodada = []
            st.session_state.rodada_index = 0
            st.session_state.desafio_ativo = None
        st.rerun()

if st.session_state.game_over:
    score_filename = f"score_de_{safe_filename(st.session_state.player_name)}.pdf"
    st.download_button(
        "📄 Baixar score em PDF",
        data=score_pdf(st.session_state.player_name.strip()),
        file_name=score_filename,
        mime="application/pdf",
        type="primary",
        help="Baixa o score final desta partida em formato PDF.",
    )

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

if len(st.session_state.lancamentos) > 1 and not st.session_state.game_over:
    if st.button("Excluir último lançamento", type="secondary"):
        removed = st.session_state.lancamentos.pop()
        st.session_state.pontos = max(0, st.session_state.pontos - 10)
        st.session_state.flash = f"Lançamento “{removed['desc']}” excluído."
        st.rerun()

show_balance_sheet = st.checkbox(
    "Exibir 2️⃣ Balanço Patrimonial",
    value=False,
    key="show_balance_sheet",
)

# O cálculo permanece disponível para o Ranking, mesmo quando o BP está oculto.
difference = balances["diferenca"]

if show_balance_sheet:
    st.header("2️⃣ Balanço Patrimonial")
    bp1, bp2 = st.columns(2)
    with bp1:
        st.subheader("Ativo")
        st.metric("Total do Ativo", brl(balances["ativo"]))
    with bp2:
        st.subheader("Passivo + Patrimônio Líquido")
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
        add_to_ranking = st.form_submit_button("Adicionar ao ranking")
    if add_to_ranking:
        if not st.session_state.player_name.strip():
            st.error("Digite o nome do jogador no início antes de adicionar.")
        else:
            st.session_state.ranking.append(
                {
                    "nome": st.session_state.player_name.strip(),
                    "pontos": int(st.session_state.pontos),
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
        columns={"nome": "Nome", "pontos": "Pontos", "nivel": "Nível", "data": "Data"}
    )
    st.dataframe(ranking_view, use_container_width=True, hide_index=True)
    chart_data = ranking.head(5).set_index("nome")[["pontos"]].rename(columns={"pontos": "Pontos"})
    st.bar_chart(chart_data)
    st.download_button(
        "📄 Baixar ranking em PDF",
        data=ranking_pdf(ranking),
        file_name="ranking-game-contabil-pro.pdf",
        mime="application/pdf",
        type="primary",
        help="Baixa a classificação atual desta sessão em formato PDF.",
    )

with st.expander("📚 Classificação das contas"):
    nature = pd.DataFrame(
        [{"Conta": account, "Grupo": group} for account, group in PLANO.items()]
    )
    st.dataframe(nature, use_container_width=True, hide_index=True)
