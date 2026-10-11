# Ensaios

Cada ensaio gera um CSV capturado do monitor serial, com o cabecalho:

```
t_s,T_c,setpoint_c,duty,erro_c,vbat_v,modo
```

## Como capturar

```powershell
pio device monitor -e esp32dev | Tee-Object -FilePath docs\ensaios\2026-10-11_degrau_01.csv
```

## Convencao de nome

`AAAA-MM-DD_<tipo>_<n>.csv` — tipos: `degrau`, `malhafechada`, `disturbio`.

## Registro

| Data | Arquivo | Tipo | T_amb | Observacoes |
|------|---------|------|-------|-------------|
|      |         |      |       |             |
