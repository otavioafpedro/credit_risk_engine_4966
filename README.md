# Motor de Risco de Crédito e Gestão de Portfólio 🏦📊

> **ECL, Modelagem IRB, Alocação Setorial e Estratégia de Originação**

## Visão Geral

Este projeto implementa um motor completo de modelagem de risco de crédito e gestão de portfólio em Python. O sistema é conceitualmente alinhado à **Resolução CMN 4.966/21** e inspirado no framework **IRB (Internal Ratings-Based)**.

Ao longo do desenvolvimento da minha trajetória, já trabalhei com dados reais provenientes de fontes como IPEA, Receita Federal, Banco Central e outras bases econômicas e financeiras relevantes. Por questões de tempo e foco deste projeto, essas integrações ainda não estão implementadas nesta versão, que utiliza dados sintéticos para fins de demonstração estruturada. A incorporação dessas bases reais está prevista como evolução natural do projeto e listada na seção de *Future Enhancements*.

## Objetivo do Projeto

Construir um sistema integrado que permita:

- **Estimar risco de crédito** no nível individual (PD, LGD, EAD).
- **Calcular perdas esperadas** (ECL - Expected Credit Loss).
- **Incorporar visão forward-looking** via cenários macroeconômicos.
- **Modelar a dinâmica de risco** ao longo do tempo (lifetime).
- **Analisar concentração** e estrutura da carteira.
- **Identificar oportunidades** de diversificação (hedge natural).
- **Apoiar decisões** de originação e precificação.

---

## Arquitetura do Projeto

A estrutura de diretórios foi desenhada para manter a modularidade e facilitar a manutenção dos diferentes componentes do motor de risco.

```text
risk_4966_irb_project/
│
├── main.py
├── config.py
├── requirements.txt
│
├── data/
│   └── outputs/
│
├── src/
│   ├── data_generation.py
│   ├── feature_engineering.py
│   ├── pd_model.py
│   ├── lgd_model.py
│   ├── ead_model.py
│   ├── staging.py
│   ├── ecl_engine.py
│   ├── stress_testing.py
│   ├── validation.py
│   ├── sector_risk.py
│   ├── portfolio_policy.py
│   └── reporting.py
│
└── notebooks/
    └── exploration.ipynb
```

---

## Componentes Principais

### 1. Modelagem de Risco de Crédito

A base do cálculo de perdas esperadas é formada pelos três pilares clássicos de risco:

- **PD (Probabilidade de Inadimplência):** Utiliza regressão logística considerando variáveis comportamentais e macroeconômicas. A saída é a PD de 12 meses.
- **LGD (Loss Given Default):** Modelo baseado em árvores de decisão. Considera o valor do colateral, o tipo de produto e o perfil do cliente.
- **EAD (Exposure at Default):** Inclui o saldo devedor atual mais a exposição não sacada (aplicando o CCF - Credit Conversion Factor), capturando a dinâmica de utilização das linhas de crédito.

### 2. Perda Esperada (ECL)

O motor calcula a Perda Esperada de Crédito (ECL) considerando o horizonte de tempo apropriado para cada operação:

- **Stage 1:** ECL de 12 meses.
- **Stage 2 e 3:** ECL ao longo da vida (lifetime).

A fórmula base utilizada é:

$$ECL = PD \times LGD \times EAD \text{ (ajustada a valor presente)}$$

O cálculo inclui o desconto financeiro, a aproximação via *hazard rate* e a agregação mensal de default marginal.

### 3. Classificação por Estágios (4.966 / IFRS 9)

O enquadramento das operações segue as diretrizes regulatórias de *staging*:

- **Stage 1:** Risco estável.
- **Stage 2:** Aumento significativo do risco (SICR).
- **Stage 3:** Inadimplência (Default).

Os critérios para transição de estágio incluem os dias de atraso (DPD) e o aumento relativo da PD desde a originação.

### 4. Forward-Looking e Cenários

A modelagem incorpora expectativas macroeconômicas para projetar o risco futuro, utilizando variáveis como **desemprego**, **taxa de juros (proxy)** e **crescimento do PIB**.

O sistema avalia três cenários distintos:
1. Base
2. Adverso
3. Severo

Para cada cenário, o motor recalcula os parâmetros de risco (PD, LGD, EAD), a distribuição de estágios da carteira e a ECL total.

### 5. Validação dos Modelos

Garante a robustez e confiabilidade das estimativas através de métricas consagradas:

| Métrica | Propósito |
| :--- | :--- |
| **AUC** | Avalia o poder de discriminação do modelo. |
| **Brier Score** | Mede a precisão (calibração) das probabilidades estimadas. |
| **Tabela de Calibração** | Compara a taxa de default observada com a PD estimada. |
| **PSI** | Population Stability Index para medir a estabilidade populacional ao longo do tempo. |

Isso permite o monitoramento contínuo de performance, detecção de *concept drift* e análise geral de robustez.

---

## Camada de Portfólio (Diferencial do Projeto)

Além da visão individualizada por contrato, o projeto se destaca por sua robusta camada de gestão de portfólio.

### 6. Análise Setorial

Para cada setor econômico presente na carteira, o sistema consolida:

- EAD e ECL totais.
- PD e LGD médias.
- Participação percentual na carteira.
- Custo de risco.

Também é calculado o **HHI (Herfindahl-Hirschman Index)** para monitorar e quantificar a concentração do portfólio.

### 7. Correlação entre Setores

O modelo constrói séries temporais de risco por setor e gera uma **matriz de correlação**. Isso permite identificar setores que se movem de forma conjunta (pró-cíclicos), setores descorrelacionados e potenciais oportunidades de diversificação.

### 8. Hedge Natural (Diversificação Estrutural)

Setores com correlação baixa ou negativa são identificados automaticamente como candidatos a **hedge natural** na composição da carteira. Vale ressaltar que este não é um hedge realizado com instrumentos derivativos, mas sim um hedge via diversificação inteligente da exposição de crédito.

---

## Índice de Atratividade Setorial

### Objetivo
Avaliar de forma sistemática quais setores são mais interessantes para direcionar novas originações de crédito.

### Componentes e Impacto

O índice combina diferentes fatores para gerar um score consolidado. A fórmula conceitual considera:

| Fator | Impacto na Atratividade |
| :--- | :--- |
| **Spread** | Positivo (+) |
| **PD** | Negativo (-) |
| **LGD** | Negativo (-) |
| **Concentração** | Negativo (-) |
| **Correlação com a carteira** | Negativo (-) |

### Saída e Interpretação Estratégica

Cada setor recebe um score de atratividade, uma posição no ranking e uma classificação estratégica que guia a atuação comercial:

| Categoria Estratégica | Interpretação |
| :--- | :--- |
| `expand_selectively` | Expandir com seletividade. |
| `neutral_monitoring` | Manter a exposição atual e monitorar. |
| `restrict_or_reprice` | Restringir novas originações ou reprecificar (aumentar spread). |

O ponto central desta abordagem é que **um setor não é atrativo apenas pelo seu risco individual, mas pela sua contribuição marginal para o risco total da carteira**. O modelo permite identificar concentrações excessivas, reduzir o risco agregado, melhorar a diversificação e alinhar o apetite de risco com a estratégia comercial.

---

## Outputs do Sistema

Ao ser executado, o sistema gera um conjunto completo de saídas:

- Resultados detalhados de ECL.
- Comparação dos impactos entre diferentes cenários macroeconômicos.
- Análise setorial profunda.
- Matriz de correlação entre setores.
- Identificação de pares para hedge natural.
- Ranking de atratividade setorial.
- Relatórios completos de validação dos modelos.

Tudo é exportado de forma estruturada em planilhas Excel e acompanhado de gráficos elucidativos.

---

## Limitações Atuais

- Utilização de dados sintéticos.
- Cálculo de PD *lifetime* simplificado.
- Regras de *staging* simplificadas.
- Ausência de uma estrutura formal de governança de modelos.
- Não inclui o cálculo de capital regulatório pelo método IRB.
- Não incorpora LGD *downturn*.
- Sem trilha completa de auditoria de dados.

## Future Enhancements (Próximos Passos)

- **Integração com bases de dados reais:** IPEA, Banco Central, Receita Federal e dados internos anonimizados.
- Implementação de **modelos de survival** (análise de sobrevivência) para a projeção da PD.
- Uso de **matriz de transição (Cadeias de Markov)** para evolução dos ratings.
- Inclusão de **análise por safra (vintage analysis)**.
- Estudo de correlação específica em **regime de estresse**.
- Cálculo de **Unexpected Loss (UL)** e capital econômico.
- Integração com sistemas de **pricing em tempo real**.

---

## Stack Tecnológica

O projeto foi construído utilizando as principais ferramentas do ecossistema de dados em Python:

- **Python** (Linguagem base)
- **Pandas / NumPy** (Manipulação e cálculos vetoriais)
- **Scikit-learn** (Modelagem de machine learning e validação)
- **Matplotlib** (Visualização de dados)
- **Excel** (Exportação de relatórios)
