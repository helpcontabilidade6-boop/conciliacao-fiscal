import streamlit as st
import pandas as pd
import re
from io import BytesIO

# ==================================================
# CONFIGURAÇÃO
# ==================================================

st.set_page_config(
    page_title="Conciliação Fiscal x Razão Contábil",
    layout="wide"
)

st.title("📊 Conciliação Fiscal x Razão Contábil")

# ==================================================
# LIMPAR VALORES
# ==================================================

def limpar_valor(coluna):

    coluna = coluna.astype(str)

    coluna = coluna.str.strip()

    coluna = coluna.str.replace(
        "R$",
        "",
        regex=False
    )

    coluna = coluna.str.replace(
        " ",
        "",
        regex=False
    )

    # troca vírgula por ponto
    coluna = coluna.str.replace(
        ",",
        ".",
        regex=False
    )

    coluna = pd.to_numeric(
        coluna,
        errors="coerce"
    )

    return coluna.fillna(0).round(2)

# ==================================================
# EXTRAIR NOTA
# ==================================================

def extrair_nota(texto):

    texto = str(texto).upper()

    padroes = [

        r"NFE\s*0*(\d+)",
        r"NFCE\s*0*(\d+)",
        r"NF-E\s*0*(\d+)",
        r"NF\s*0*(\d+)",
        r"\b0*(\d{4,})\b"

    ]

    for padrao in padroes:

        resultado = re.search(
            padrao,
            texto
        )

        if resultado:

            return resultado.group(1).lstrip("0")

    return None

# ==================================================
# TRATAR FISCAL
# ==================================================

def tratar_fiscal(arquivo):

    df = pd.read_excel(arquivo)

    df.columns = df.columns.astype(str).str.strip()

    coluna_nota = None
    coluna_valor = None

    for col in df.columns:

        c = col.lower()

        if (

            "nota" in c
            or "numero" in c
            or "número" in c
            or "nr" in c
            or "inicial" in c

        ):

            coluna_nota = col

        elif (

            "valor" in c
            or "total" in c

        ):

            coluna_valor = col

    if coluna_nota is None:

        st.error(
            "Não encontrei coluna da nota no Fiscal."
        )

        st.stop()

    if coluna_valor is None:

        st.error(
            "Não encontrei coluna de valor no Fiscal."
        )

        st.stop()

    fiscal = pd.DataFrame()

    fiscal["nota"] = (

        df[coluna_nota]

        .astype(str)

        .str.extract(r'(\d+)')[0]

        .str.lstrip("0")

    )

    fiscal["valor_fiscal"] = limpar_valor(
        df[coluna_valor]
    )

    fiscal = fiscal.dropna(
        subset=["nota"]
    )

    fiscal = fiscal.groupby(
        "nota",
        as_index=False
    ).agg({

        "valor_fiscal": "sum"

    })

    fiscal["valor_fiscal"] = (
        fiscal["valor_fiscal"]
        .round(2)
    )

    return fiscal

# ==================================================
# TRATAR RAZÃO CONTÁBIL
# ==================================================

def tratar_razao(arquivo):

    bruto = pd.read_excel(
        arquivo,
        header=None
    )

    # ==========================================
    # LOCALIZA CABEÇALHO
    # ==========================================

    header_idx = None

    for i, row in bruto.iterrows():

        linha = [

            str(v).strip().lower()

            for v in row

            if pd.notna(v)

        ]

        if (
            any("hist" in x for x in linha)
            and any("cr" in x for x in linha)
        ):

            header_idx = i
            break

    if header_idx is None:

        st.error(
            "Cabeçalho do Razão Contábil não encontrado."
        )

        st.stop()

    # ==========================================
    # LÊ PLANILHA
    # ==========================================

    df = pd.read_excel(
        arquivo,
        header=header_idx
    )

    df.columns = df.columns.astype(str).str.strip()

    # ==========================================
    # IDENTIFICA COLUNAS
    # ==========================================

    coluna_historico = None
    coluna_credito = None

    for col in df.columns:

        c = col.lower()

        if "hist" in c:

            coluna_historico = col

        elif "créd" in c or "cred" in c:

            coluna_credito = col

    # ==========================================
    # VALIDAÇÕES
    # ==========================================

    if coluna_historico is None:

        st.error(
            "Não encontrei coluna Histórico no Razão Contábil."
        )

        st.stop()

    if coluna_credito is None:

        st.error(
            "Não encontrei coluna Crédito no Razão Contábil."
        )

        st.stop()

    st.write(
        f"📌 Coluna de Crédito utilizada: {coluna_credito}"
    )

    # ==========================================
    # EXTRAI NOTA
    # ==========================================

    df["nota"] = df[
        coluna_historico
    ].apply(extrair_nota)

    # remove linhas sem nota
    df = df[
        df["nota"].notna()
    ].copy()

    # ==========================================
    # VALOR DO CRÉDITO
    # ==========================================

    df["valor_razao"] = limpar_valor(
        df[coluna_credito]
    )

    # remove valores zerados
    df = df[
        df["valor_razao"] > 0
    ].copy()

    # ==========================================
    # AGRUPA POR NOTA
    # ==========================================

    razao = df.groupby(
        "nota",
        as_index=False
    ).agg({

        "valor_razao": "sum"

    })

    razao["valor_razao"] = (
        razao["valor_razao"]
        .round(2)
    )

    return razao

# ==================================================
# COMPARAÇÃO
# ==================================================

def comparar(fiscal, razao):

    resultado = pd.merge(

        fiscal,

        razao,

        on="nota",

        how="outer",

        indicator=True

    )

    resultado["valor_fiscal"] = (
        resultado["valor_fiscal"]
        .fillna(0)
        .round(2)
    )

    resultado["valor_razao"] = (
        resultado["valor_razao"]
        .fillna(0)
        .round(2)
    )

    resultado["diferenca"] = (

        resultado["valor_fiscal"]

        - resultado["valor_razao"]

    ).round(2)

    # ==========================================
    # STATUS
    # ==========================================

    def definir_status(row):

        if row["_merge"] == "left_only":

            return "SÓ NO FISCAL"

        elif row["_merge"] == "right_only":

            return "SÓ NO RAZÃO CONTÁBIL"

        elif abs(row["diferenca"]) <= 0.01:

            return "OK"

        else:

            return "VALOR DIFERENTE"

    resultado["status"] = resultado.apply(
        definir_status,
        axis=1
    )

    divergencias = resultado[
        resultado["status"] != "OK"
    ].copy()

    divergencias = divergencias.sort_values(
        by="nota"
    )

    return divergencias

# ==================================================
# GERAR EXCEL
# ==================================================

def gerar_excel(df):

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name="Divergencias"
        )

    output.seek(0)

    return output

# ==================================================
# UPLOAD
# ==================================================

arquivo_fiscal = st.file_uploader(

    "📂 Envie o arquivo Fiscal",

    type=["xlsx"]

)

arquivo_razao = st.file_uploader(

    "📂 Envie o arquivo Razão Contábil",

    type=["xlsx"]

)

# ==================================================
# PROCESSAR
# ==================================================

if arquivo_fiscal and arquivo_razao:

    try:

        st.info(
            "🔄 Comparando arquivos..."
        )

        fiscal = tratar_fiscal(
            arquivo_fiscal
        )

        razao = tratar_razao(
            arquivo_razao
        )

        divergencias = comparar(
            fiscal,
            razao
        )

        # ======================================
        # RESUMO
        # ======================================

        st.subheader("📈 Resumo")

        c1, c2, c3 = st.columns(3)

        c1.metric(

            "Só no Fiscal",

            len(
                divergencias[
                    divergencias["status"]
                    == "SÓ NO FISCAL"
                ]
            )

        )

        c2.metric(

            "Só no Razão Contábil",

            len(
                divergencias[
                    divergencias["status"]
                    == "SÓ NO RAZÃO CONTÁBIL"
                ]
            )

        )

        c3.metric(

            "Valor Diferente",

            len(
                divergencias[
                    divergencias["status"]
                    == "VALOR DIFERENTE"
                ]
            )

        )

        # ======================================
        # RESULTADO
        # ======================================

        st.subheader(
            "⚠️ Divergências Encontradas"
        )

        st.dataframe(
            divergencias,
            use_container_width=True
        )

        # ======================================
        # DOWNLOAD
        # ======================================

        excel = gerar_excel(
            divergencias
        )

        st.download_button(

            label="📥 Baixar Excel",

            data=excel,

            file_name="divergencias.xlsx",

            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        )

        st.success(
            "✅ Comparação finalizada."
        )

    except Exception as erro:

        st.error(
            f"Erro encontrado: {erro}"
        )

else:

    st.info(
        "📂 Envie os dois arquivos Excel."
    )
