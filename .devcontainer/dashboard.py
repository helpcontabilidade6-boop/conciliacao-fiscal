# ==================================================
# COMPARAÇÃO FISCAL X CONTÁBIL
# ==================================================

import streamlit as st
import pandas as pd
import re

# ==================================================
# CONFIG
# ==================================================

st.set_page_config(
    page_title="Conciliação Fiscal x Contábil",
    layout="wide"
)

st.title("📊 Conciliação Fiscal x Contábil")

# ==================================================
# LIMPAR VALORES
# ==================================================

def limpar_valor(coluna):

    coluna = (
        coluna.astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.replace("R$", "", regex=False)
        .str.strip()
    )

    return pd.to_numeric(
        coluna,
        errors="coerce"
    )

# ==================================================
# EXTRAIR NOTA
# ==================================================

def extrair_nota(texto):

    texto = str(texto).upper()

    resultado = re.search(
        r"NFE\s*0*(\d+)",
        texto
    )

    if resultado:

        return resultado.group(1)

    return None

# ==================================================
# TRATAR CONTÁBIL
# ==================================================

def tratar_contabil(arquivo):

    bruto = pd.read_excel(
        arquivo,
        header=4
    )

    bruto.columns = [

        "Data",
        "Est",
        "CR",
        "Historico",
        "Vazio",
        "Chave",
        "Debito",
        "Credito",
        "Saldo"

    ]

    # ==========================================
    # PEGAR SOMENTE NFE
    # ==========================================

    bruto = bruto[
        bruto["Historico"]
        .astype(str)
        .str.contains(
            "NFE",
            case=False,
            na=False
        )
    ].copy()

    # ==========================================
    # EXTRAIR NOTA
    # ==========================================

    bruto["Nota"] = bruto[
        "Historico"
    ].apply(extrair_nota)

    # ==========================================
    # VALOR
    # ==========================================

    bruto["Valor Contábil"] = limpar_valor(
        bruto["Credito"]
    )

    # ==========================================
    # DATA
    # ==========================================

    bruto["Data Contábil"] = pd.to_datetime(
        bruto["Data"],
        errors="coerce",
        dayfirst=True
    )

    # ==========================================
    # RESULTADO FINAL
    # ==========================================

    df = bruto[[

        "Nota",
        "Valor Contábil",
        "Data Contábil"

    ]]

    return df

# ==================================================
# TRATAR FISCAL
# ==================================================

def tratar_fiscal(arquivo):

    fiscal = pd.read_excel(arquivo)

    fiscal_final = pd.DataFrame()

    fiscal_final["Nota"] = (

        fiscal["Nr. Inicial"]
        .astype(str)
        .str.extract(r'(\d+)')[0]
        .str.lstrip("0")

    )

    fiscal_final["Valor Fiscal"] = limpar_valor(
        fiscal["Valor Total"]
    )

    fiscal_final["Data Fiscal"] = pd.to_datetime(
        fiscal["Emissão"],
        errors="coerce",
        dayfirst=True
    )

    return fiscal_final

# ==================================================
# UPLOAD
# ==================================================

fiscal = st.file_uploader(
    "📂 Envie o Fiscal",
    type=["xlsx"]
)

contabil = st.file_uploader(
    "📂 Envie o Razão Contábil",
    type=["xlsx"]
)

# ==================================================
# PROCESSAMENTO
# ==================================================

if fiscal and contabil:

    try:

        # ==========================================
        # TRATAR BASES
        # ==========================================

        df_fiscal = tratar_fiscal(fiscal)

        df_contabil = tratar_contabil(contabil)

        # ==========================================
        # MOSTRAR BASES TRATADAS
        # ==========================================

        st.subheader("📋 Fiscal Tratado")
        st.dataframe(df_fiscal.head(20))

        st.subheader("📋 Contábil Tratado")
        st.dataframe(df_contabil.head(20))

        # ==========================================
        # COMPARAÇÃO
        # ==========================================

        comparativo = pd.merge(

            df_fiscal,

            df_contabil,

            on="Nota",

            how="outer",

            indicator=True

        )

        # ==========================================
        # DIFERENÇA
        # ==========================================

        comparativo["Diferença"] = (

            comparativo["Valor Contábil"].fillna(0)

            - comparativo["Valor Fiscal"].fillna(0)

        ).round(2)

        # ==========================================
        # FILTROS
        # ==========================================

        faltando_fiscal = comparativo[
            comparativo["_merge"] == "right_only"
        ]

        faltando_contabil = comparativo[
            comparativo["_merge"] == "left_only"
        ]

        valores_diferentes = comparativo[
            comparativo["Diferença"] != 0
        ]

        # ==========================================
        # KPIS
        # ==========================================

        st.subheader("📈 Indicadores")

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Faltando no Fiscal",
            len(faltando_fiscal)
        )

        c2.metric(
            "Faltando no Contábil",
            len(faltando_contabil)
        )

        c3.metric(
            "Valores Divergentes",
            len(valores_diferentes)
        )

        # ==========================================
        # RESULTADOS
        # ==========================================

        st.subheader("⚠️ Não Encontradas no Fiscal")
        st.dataframe(faltando_fiscal)

        st.subheader("⚠️ Não Encontradas no Contábil")
        st.dataframe(faltando_contabil)

        st.subheader("💰 Valores Divergentes")
        st.dataframe(valores_diferentes)

        # ==========================================
        # STATUS FINAL
        # ==========================================

        if (
            len(faltando_fiscal) == 0
            and len(faltando_contabil) == 0
            and len(valores_diferentes) == 0
        ):

            st.success(
                "✅ Conciliação realizada com sucesso"
            )

        else:

            st.error(
                "⚠️ Existem divergências"
            )

    except Exception as erro:

        st.error(
            f"Erro encontrado: {erro}"
        )

else:

    st.info(
        "📂 Envie os dois arquivos Excel"
    )