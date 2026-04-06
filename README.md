# Motor de Risco de Crédito e Gestão de Portfólio
ECL, Modelagem IRB, Alocação Setorial e Estratégia de Originação
Visão Geral

Este projeto implementa um motor completo de modelagem de risco de crédito e gestão de portfólio em Python, conceitualmente alinhado à Resolução CMN 4.966/21 e inspirado no framework IRB (Internal Ratings-Based).

Ao longo do desenvolvimento da minha trajetória, já trabalhei com dados reais provenientes de fontes como IPEA, Receita Federal, Banco Central e outras bases econômicas e financeiras relevantes.

Por questões de tempo e foco deste projeto, essas integrações ainda não estão implementadas nesta versão, que utiliza dados sintéticos para fins de demonstração estruturada.

A incorporação dessas bases reais está prevista como evolução natural do projeto e listada na seção de Future Enhancements.

Objetivo do Projeto

Construir um sistema integrado que permita:

- Estimar risco de crédito no nível individual (PD, LGD, EAD)
- Calcular perdas esperadas (ECL)
- Incorporar visão forward-looking via macroeconomia
- Modelar dinâmica de risco ao longo do tempo (lifetime)
- Analisar concentração e estrutura da carteira
- Identificar oportunidades de diversificação
- Apoiar decisões de originação e precificação

Arquitetura:
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

