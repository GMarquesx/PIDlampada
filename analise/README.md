# analise/ — identificação da planta e sintonia do PI

Fecha o ciclo entre o ensaio de bancada e o firmware: lê o CSV da serial,
identifica o modelo, compara regras de sintonia e devolve os ganhos prontos
para colar em `include/config.h`.

| Arquivo | Conteúdo |
|---|---|
| `identificacao.ipynb` | notebook principal, já executado com dados de exemplo |
| `plant_id.py` | funções puras de identificação, sintonia e simulação |
| `exemplo_degrau.csv` | ensaio sintético, só para o notebook rodar de imediato |
| `requirements.txt` | dependências |

## Instalação

```powershell
cd analise
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
jupyter lab
```

## Uso

1. Capture o ensaio de degrau:

```powershell
pio device monitor -e esp32dev | Tee-Object -FilePath docs\ensaios\2026-10-11_degrau_01.csv
# na serial: r
```

2. No topo do notebook, aponte `ENSAIO` para esse arquivo.
3. Execute tudo. A última célula imprime o trecho do `config.h`.

## Nota sobre a simulação

`simular_malha_fechada()` reproduz o algoritmo de
`lib/control/pi_controller.cpp` — mesma amostragem, mesma saturação, mesmo
anti-windup. Se o notebook e o firmware divergirem, um dos dois está errado;
os testes de `test/test_control/` existem para pegar isso.
