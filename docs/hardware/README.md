# Hardware

| Arquivo | Conteudo |
|---------|----------|
| `Proposta_Camara_Termica_ESP32.pdf` | Folha A4 de proposta — vista isometrica, BOM, cadeia de potencia |
| `Esquema_Eletrico_Camara_Termica.pdf` | Esquema eletrico Rev. A — seis blocos, pinagem, notas de projeto |
| `esquema_eletrico.svg` | Mesmo esquema em vetor |
| `esquema_schemdraw.py` | Script Python que gera o esquema (SchemDraw) |

Para regerar o esquema apos uma alteracao:

```powershell
pip install schemdraw
python docs\hardware\esquema_schemdraw.py
```

## Pendencia aberta

O esquema Rev. A traz o DS18B20. A proposta entregue ao professor especifica
LM35DZ. A Rev. B precisa trocar o bloco [4]:

- LM35 exige **4 a 30 V** de alimentacao — vai no **+5 V**, nao no +3V3
- Filtro recomendado pela TI na saida: **75 ohms em serie + 1 uF** para GND
- Remover R1 (pull-up de 4,7 k do 1-Wire)
- Entrada no **GPIO32** (ADC1_CH4)
