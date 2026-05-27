import streamlit as st
import pandas as pd

# -----------------------------------
# CONFIGURAÇÃO
# -----------------------------------
st.set_page_config(
    page_title="Conciliação Fiscal x Contábil",
    layout="wide"
)

st.title("📊 Conciliação Fiscal x Contábil")

# -----------------------------------
# FUNÇÃO PARA LER EXCEL
# -----------------------------------
def ler_excel_unico(arquivo):

    # Ler sem cabeçalho
    df = pd.read_excel(
        arquivo,
        header=None
    )

    # Primeira linha como cabeçalho
    cabecalho = df.iloc[0]

    nomes = []
    contador = {}

    # Corrigir nomes duplicados
    for col in cabecalho:

        col = str(col).strip()

        if col in contador:

            contador[col] += 1

            nomes.append(
                f"{col}_{contador[col]}"
            )

        else:

            contador[col] = 0

            nomes.append(col)

    # Remover linha do cabeçalho
    df = df[1:]

    # Aplicar nomes
    df.columns = nomes

    return df

# -----------------------------------
# FUNÇÃO LIMPAR VALORES
# -----------------------------------
def limpar_valor(coluna):

    coluna = (
        coluna
        .astype(str)
        .str.replace("R$", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.replace(" ", "", regex=False)
        .str.strip()
    )

    return pd.to_numeric(
        coluna,
        errors="coerce"
    )

# -----------------------------------
# UPLOAD DOS ARQUIVOS
# -----------------------------------
fiscal = st.file_uploader(
    "📂 Envie a planilha FISCAL",
    type=["xlsx"]
)

contabil = st.file_uploader(
    "📂 Envie a planilha CONTÁBIL",
    type=["xlsx"]
)

# -----------------------------------
# PROCESSAMENTO
# -----------------------------------
if fiscal is not None and contabil is not None:

    try:

        # -----------------------------------
        # LER PLANILHAS
        # -----------------------------------
        df_fiscal = ler_excel_unico(fiscal)

        df_contabil = ler_excel_unico(contabil)

        # -----------------------------------
        # MOSTRAR DADOS
        # -----------------------------------
        st.subheader("📋 Fiscal")
        st.dataframe(df_fiscal.head())

        st.subheader("📋 Contábil")
        st.dataframe(df_contabil.head())

        # -----------------------------------
        # CONFIGURAÇÃO
        # -----------------------------------
        st.subheader("⚙️ Configuração")

        col1, col2 = st.columns(2)

        with col1:

            fiscal_nota = st.selectbox(
                "Número da Nota Fiscal",
                list(df_fiscal.columns)
            )

            fiscal_valor = st.selectbox(
                "Valor Fiscal",
                list(df_fiscal.columns)
            )

            fiscal_data = st.selectbox(
                "Data Fiscal",
                list(df_fiscal.columns)
            )

        with col2:

            contabil_nota = st.selectbox(
                "Número da Nota Contábil",
                list(df_contabil.columns)
            )

            contabil_valor = st.selectbox(
                "Valor Contábil",
                list(df_contabil.columns)
            )

            contabil_data = st.selectbox(
                "Data Contábil",
                list(df_contabil.columns)
            )

        # -----------------------------------
        # LIMPAR VALORES
        # -----------------------------------
        df_fiscal[fiscal_valor] = limpar_valor(
            df_fiscal[fiscal_valor]
        )

        df_contabil[contabil_valor] = limpar_valor(
            df_contabil[contabil_valor]
        )

        # -----------------------------------
        # CONVERTER DATAS
        # -----------------------------------
        df_fiscal[fiscal_data] = pd.to_datetime(
            df_fiscal[fiscal_data],
            errors="coerce",
            dayfirst=True
        )

        df_contabil[contabil_data] = pd.to_datetime(
            df_contabil[contabil_data],
            errors="coerce",
            dayfirst=True
        )

        # -----------------------------------
        # TRANSFORMAR NOTAS EM TEXTO
        # -----------------------------------
        df_fiscal[fiscal_nota] = (
            df_fiscal[fiscal_nota]
            .astype(str)
            .str.strip()
        )

        df_contabil[contabil_nota] = (
            df_contabil[contabil_nota]
            .astype(str)
            .str.strip()
        )

        # -----------------------------------
        # DUPLICADAS
        # -----------------------------------
        fiscal_duplicadas = df_fiscal[
            df_fiscal.duplicated(
                subset=[fiscal_nota],
                keep=False
            )
        ]

        contabil_duplicadas = df_contabil[
            df_contabil.duplicated(
                subset=[contabil_nota],
                keep=False
            )
        ]

        # -----------------------------------
        # BASE FISCAL
        # -----------------------------------
        fiscal_base = pd.DataFrame({

            "Nota Fiscal":
                df_fiscal[fiscal_nota].values,

            "Valor Fiscal":
                df_fiscal[fiscal_valor].values,

            "Data Fiscal":
                df_fiscal[fiscal_data].values

        })

        # -----------------------------------
        # BASE CONTÁBIL
        # -----------------------------------
        contabil_base = pd.DataFrame({

            "Nota Contábil":
                df_contabil[contabil_nota].values,

            "Valor Contábil":
                df_contabil[contabil_valor].values,

            "Data Contábil":
                df_contabil[contabil_data].values

        })

        # -----------------------------------
        # MERGE
        # -----------------------------------
        comparativo = pd.merge(
            fiscal_base,
            contabil_base,
            left_on="Nota Fiscal",
            right_on="Nota Contábil",
            how="outer",
            indicator=True
        )

        # -----------------------------------
        # GARANTIR NÚMEROS
        # -----------------------------------
        comparativo["Valor Fiscal"] = pd.to_numeric(
            comparativo["Valor Fiscal"],
            errors="coerce"
        )

        comparativo["Valor Contábil"] = pd.to_numeric(
            comparativo["Valor Contábil"],
            errors="coerce"
        )

        comparativo["Valor Fiscal"] = (
            comparativo["Valor Fiscal"]
            .fillna(0)
        )

        comparativo["Valor Contábil"] = (
            comparativo["Valor Contábil"]
            .fillna(0)
        )

        # -----------------------------------
        # DIFERENÇA
        # -----------------------------------
        comparativo["Diferença Valor"] = (
            comparativo["Valor Contábil"]
            - comparativo["Valor Fiscal"]
        )

        # -----------------------------------
        # DATAS DIFERENTES
        # -----------------------------------
        comparativo["Data Diferente"] = (
            comparativo["Data Fiscal"]
            != comparativo["Data Contábil"]
        )

        # -----------------------------------
        # FILTROS
        # -----------------------------------
        faltando_fiscal = comparativo[
            comparativo["_merge"] == "right_only"
        ]

        faltando_contabil = comparativo[
            comparativo["_merge"] == "left_only"
        ]

        valores_diferentes = comparativo[
            comparativo["Diferença Valor"] != 0
        ]

        datas_diferentes = comparativo[
            comparativo["Data Diferente"] == True
        ]

        # -----------------------------------
        # KPIs
        # -----------------------------------
        st.subheader("📈 Indicadores")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Notas Fiscal",
            len(df_fiscal)
        )

        c2.metric(
            "Notas Contábil",
            len(df_contabil)
        )

        c3.metric(
            "Valores Divergentes",
            len(valores_diferentes)
        )

        c4.metric(
            "Duplicadas",
            len(fiscal_duplicadas)
            + len(contabil_duplicadas)
        )

        # -----------------------------------
        # RESULTADOS
        # -----------------------------------
        st.subheader("⚠️ Notas Faltando no Fiscal")
        st.dataframe(faltando_fiscal)

        st.subheader("⚠️ Notas Faltando no Contábil")
        st.dataframe(faltando_contabil)

        st.subheader("💰 Valores Divergentes")
        st.dataframe(valores_diferentes)

        st.subheader("📅 Datas Divergentes")
        st.dataframe(datas_diferentes)

        st.subheader("🔁 Notas Duplicadas no Fiscal")
        st.dataframe(fiscal_duplicadas)

        st.subheader("🔁 Notas Duplicadas no Contábil")
        st.dataframe(contabil_duplicadas)

        # -----------------------------------
        # RESULTADO FINAL
        # -----------------------------------
        if (
            len(faltando_fiscal) == 0
            and len(faltando_contabil) == 0
            and len(valores_diferentes) == 0
        ):

            st.success(
                "✅ Fiscal e Contábil conciliados."
            )

        else:

            st.error(
                "⚠️ Foram encontradas divergências."
            )

    except Exception as erro:

        st.error(
            f"Erro encontrado: {erro}"
        )

else:

    st.info(
        "📂 Envie os dois arquivos Excel."
    )