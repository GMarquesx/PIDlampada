"""
plant_id - identificacao da planta termica e sintonia do PI.

Le o CSV que o firmware do PIDlampada emite pela serial, extrai um modelo
de primeira ordem com atraso (FOPDT), sugere ganhos e simula a malha
fechada com as mesmas nao-linearidades do firmware (saturacao do duty e
anti-windup por clamping condicional).

Funcoes puras, sem estado global: o notebook so orquestra.

Formato esperado do CSV (cabecalho emitido pelo firmware):
    t_s,T_c,setpoint_c,duty,erro_c,vbat_v,modo
Linhas iniciadas por '#' sao comentarios e devem ser ignoradas.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

__all__ = [
    "FOPDT",
    "TuningRule",
    "carregar_ensaio",
    "identificar_fopdt",
    "validar_modelo",
    "sintonizar",
    "simular_malha_fechada",
    "metricas_resposta",
    "gerar_config_h",
]


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class FOPDT:
    """Modelo de primeira ordem com atraso de transporte.

        G(s) = K * exp(-theta*s) / (tau*s + 1)

    K      : ganho estatico em degC por unidade de duty (duty em [0,1])
    tau_s  : constante de tempo em segundos
    theta_s: atraso de transporte em segundos
    T0_c   : temperatura inicial (ambiente) do ensaio
    duty   : degrau de duty aplicado no ensaio
    """

    K: float
    tau_s: float
    theta_s: float
    T0_c: float
    duty: float = 1.0

    def __str__(self) -> str:
        return (
            f"G(s) = {self.K:.2f} * exp(-{self.theta_s:.0f}s) / "
            f"({self.tau_s:.0f}s + 1)   [degC / duty]"
        )


@dataclass(frozen=True)
class TuningRule:
    """Ganhos no formato padrao (Kc, Ti) e no formato do firmware (Kp, Ki)."""

    nome: str
    Kc: float          # ganho proporcional
    Ti_s: float        # tempo integral em segundos
    observacao: str = ""

    @property
    def Kp(self) -> float:
        """Identico a Kc - o firmware usa forma paralela."""
        return self.Kc

    @property
    def Ki(self) -> float:
        """u = Kp*e + Ki*integral(e)  =>  Ki = Kc / Ti."""
        return self.Kc / self.Ti_s if self.Ti_s > 0 else 0.0


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------
def carregar_ensaio(caminho: str) -> pd.DataFrame:
    """Le o CSV da serial, descarta comentarios e normaliza as colunas."""
    df = pd.read_csv(caminho, comment="#")
    df.columns = [c.strip() for c in df.columns]

    obrigatorias = {"t_s", "T_c", "duty"}
    faltando = obrigatorias - set(df.columns)
    if faltando:
        raise ValueError(f"colunas ausentes no CSV: {sorted(faltando)}")

    df = df.dropna(subset=["t_s", "T_c"]).reset_index(drop=True)
    df["t_s"] = df["t_s"].astype(float)
    df["T_c"] = df["T_c"].astype(float)
    return df


# ---------------------------------------------------------------------------
# Identificacao
# ---------------------------------------------------------------------------
def _instante_em_fracao(t: np.ndarray, y: np.ndarray, y0: float,
                        yf: float, fracao: float) -> float:
    """Primeiro instante em que y cruza y0 + fracao*(yf-y0), com interpolacao."""
    alvo = y0 + fracao * (yf - y0)
    idx = np.argmax(y >= alvo)
    if idx == 0:
        return float(t[0])
    # interpolacao linear entre idx-1 e idx
    t0, t1 = t[idx - 1], t[idx]
    y_0, y_1 = y[idx - 1], y[idx]
    if y_1 == y_0:
        return float(t1)
    return float(t0 + (alvo - y_0) * (t1 - t0) / (y_1 - y_0))


def identificar_fopdt(df: pd.DataFrame, duty: float | None = None,
                      janela_base: int = 1, janela_regime: int = 5,
                      metodo: str = "sundaresan",
                      avisar: bool = True) -> FOPDT:
    """
    Extrai K, tau e theta de um ensaio de degrau em malha aberta.

    metodo:
      "63"          - metodo classico dos 63,2 %. Simples, mas confunde
                      atraso com constante de tempo quando ha theta.
      "sundaresan"  - dois pontos (35,3 % e 85,3 %), separa tau de theta.
                      Padrao, e o que se deve usar quando ha atraso.

    janela_base  : amostras iniciais promediadas para estimar T0. Mantenha
                   em 1 se o degrau comeca na primeira amostra - promediar
                   um trecho que ja esta subindo infla T0 e reduz K.
    janela_regime: amostras finais promediadas para estimar o valor final.
    """
    t = df["t_s"].to_numpy(dtype=float)
    y = df["T_c"].to_numpy(dtype=float)

    if duty is None:
        duty = float(df["duty"].iloc[len(df) // 2]) if "duty" in df else 1.0
    if duty <= 0:
        raise ValueError("duty do degrau precisa ser > 0")

    T0 = float(np.mean(y[: max(1, janela_base)]))
    Tf = float(np.mean(y[-janela_regime:]))
    delta = Tf - T0
    if delta <= 0:
        raise ValueError("a temperatura nao subiu - o ensaio nao e' um degrau")

    # O ensaio chegou ao regime? Se as ultimas amostras ainda sobem, K sai
    # subestimado e toda a sintonia herda o erro.
    if avisar and len(y) > 2 * janela_regime:
        inclinacao = (np.mean(y[-janela_regime:]) - np.mean(y[-2 * janela_regime:-janela_regime]))
        if abs(inclinacao) > 0.02 * delta:
            print(
                f"AVISO: a temperatura ainda varia {inclinacao:+.2f} degC nas ultimas "
                f"{janela_regime} amostras. O ensaio provavelmente terminou antes do "
                f"regime - K e tau sairao subestimados. Rode por pelo menos 5*tau."
            )

    K = delta / duty

    if metodo == "63":
        t63 = _instante_em_fracao(t, y, T0, Tf, 0.632)
        tau = max(t63 - t[0], 1e-6)
        theta = 0.0
    elif metodo == "sundaresan":
        # Sundaresan & Krishnaswamy: tau = 0,67*(t85 - t35); theta = 1,3*t35 - 0,29*t85
        t35 = _instante_em_fracao(t, y, T0, Tf, 0.353)
        t85 = _instante_em_fracao(t, y, T0, Tf, 0.853)
        tau = max(0.67 * (t85 - t35), 1e-6)
        theta = max(1.3 * t35 - 0.29 * t85, 0.0)
    else:
        raise ValueError("metodo deve ser '63' ou 'sundaresan'")

    return FOPDT(K=K, tau_s=tau, theta_s=theta, T0_c=T0, duty=duty)


def validar_modelo(df: pd.DataFrame, m: FOPDT) -> tuple[np.ndarray, dict]:
    """
    Reconstroi a resposta ao degrau pelo modelo e compara com o ensaio.

    Retorna (y_modelo, metricas) com RMSE, erro maximo e R^2.
    """
    t = df["t_s"].to_numpy(dtype=float)
    y = df["T_c"].to_numpy(dtype=float)

    t_rel = np.maximum(t - t[0] - m.theta_s, 0.0)
    y_hat = m.T0_c + m.K * m.duty * (1.0 - np.exp(-t_rel / m.tau_s))
    y_hat[t - t[0] < m.theta_s] = m.T0_c

    resid = y - y_hat
    ss_res = float(np.sum(resid ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))

    metricas = {
        "rmse_c": float(np.sqrt(np.mean(resid ** 2))),
        "erro_max_c": float(np.max(np.abs(resid))),
        "r2": 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan"),
    }
    return y_hat, metricas


# ---------------------------------------------------------------------------
# Sintonia
# ---------------------------------------------------------------------------
def sintonizar(m: FOPDT, Ts_s: float = 60.0,
               lam_fator: float = 1.0) -> list[TuningRule]:
    """
    Regras de sintonia PI para FOPDT.

    O atraso efetivo soma theta do processo com Ts/2 do segurador de ordem
    zero (ZOH): amostrar a cada Ts s equivale, em media, a meio periodo de
    atraso adicional. Ignorar isso superestima a margem de fase.

    lam_fator escala o lambda (tau_c) do SIMC: maior = mais conservador.
    """
    theta_ef = m.theta_s + Ts_s / 2.0
    K, tau = m.K, m.tau_s

    regras: list[TuningRule] = []

    # --- SIMC / Skogestad (lambda = tau_c) -----------------------------------
    tau_c = max(lam_fator * theta_ef, 1e-6)
    Kc = (1.0 / K) * (tau / (tau_c + theta_ef))
    Ti = min(tau, 4.0 * (tau_c + theta_ef))
    regras.append(TuningRule(
        "SIMC (Skogestad)", Kc, Ti,
        "robusto, pouco sobressinal - recomendado para atuador so-aquece",
    ))

    # --- IMC classico --------------------------------------------------------
    lam = max(lam_fator * max(0.8 * theta_ef, 0.1 * tau), 1e-6)
    Kc_imc = (1.0 / K) * (tau + theta_ef / 2.0) / (lam + theta_ef / 2.0)
    Ti_imc = tau + theta_ef / 2.0
    regras.append(TuningRule(
        "IMC", Kc_imc, Ti_imc,
        "parecido com SIMC; lambda controla o compromisso velocidade/robustez",
    ))

    # --- Ziegler-Nichols malha aberta ---------------------------------------
    if theta_ef > 0:
        Kc_zn = 0.9 * tau / (K * theta_ef)
        Ti_zn = 3.33 * theta_ef
        regras.append(TuningRule(
            "Ziegler-Nichols (MA)", Kc_zn, Ti_zn,
            "agressivo: ~25 % de sobressinal por projeto - ruim aqui",
        ))

    # --- CHR 0 % de sobressinal, seguimento de setpoint ----------------------
    if theta_ef > 0:
        Kc_chr = 0.35 * tau / (K * theta_ef)
        Ti_chr = 1.17 * tau
        regras.append(TuningRule(
            "CHR 0 % sobressinal", Kc_chr, Ti_chr,
            "projetado para nao ultrapassar o setpoint",
        ))

    return regras


# ---------------------------------------------------------------------------
# Simulacao da malha fechada (espelha o firmware)
# ---------------------------------------------------------------------------
def simular_malha_fechada(m: FOPDT, regra: TuningRule, setpoint_c: float,
                          Ts_s: float = 60.0, t_final_s: float = 14400.0,
                          T_inicial_c: float | None = None,
                          duty_max: float = 1.0,
                          duty_inicial: float | None = None,
                          perturbacao_c: float = 0.0,
                          t_perturbacao_s: float = 0.0) -> pd.DataFrame:
    """
    Simula PI discreto + planta de 1a ordem, com saturacao e anti-windup
    identicos aos de lib/control/pi_controller.cpp.

    Reproduz tambem a assimetria do atuador: duty >= 0 (so aquece). O
    resfriamento acontece apenas pela constante de tempo natural.

    duty_inicial: pre-carrega a integral para o sistema partir ja em regime.
    Use ao testar um degrau pequeno de setpoint a partir de uma temperatura
    estabilizada - sem isso o transitorio inicial mascara a comparacao.

    perturbacao_c: degrau na temperatura ambiente aplicado em t_perturbacao_s
    (negativo = esfriou). E' o cenario que melhor diferencia as sintonias,
    porque nele o atuador raramente satura.
    """
    n = int(t_final_s / Ts_s) + 1
    T = m.T0_c if T_inicial_c is None else T_inicial_c
    Kp, Ki = regra.Kp, regra.Ki

    atraso_passos = int(round(m.theta_s / Ts_s))
    fila = [0.0] * max(atraso_passos, 0)

    integral = 0.0
    if duty_inicial is not None and Ki > 0:
        integral = duty_inicial / Ki
        fila = [duty_inicial] * max(atraso_passos, 0)
    linhas = []

    for k in range(n):
        t_atual = k * Ts_s
        T_amb = m.T0_c + (perturbacao_c if t_atual >= t_perturbacao_s else 0.0)
        erro = setpoint_c - T

        integral_try = integral + erro * Ts_s
        u_try = Kp * erro + Ki * integral_try
        u = min(max(u_try, 0.0), duty_max)

        # anti-windup: so acumula se nao empurra contra a saturacao
        empurra_cima = (u_try > duty_max) and (erro > 0.0)
        empurra_baixo = (u_try < 0.0) and (erro < 0.0)
        if not (empurra_cima or empurra_baixo):
            integral = integral_try

        # atraso de transporte
        if atraso_passos > 0:
            fila.append(u)
            u_planta = fila.pop(0)
        else:
            u_planta = u

        linhas.append({"t_s": t_atual, "T_c": T, "duty": u,
                       "erro_c": erro, "setpoint_c": setpoint_c,
                       "T_amb_c": T_amb})

        # planta: tau*dT/dt = -(T - T_amb) + K*duty   (Euler explicito)
        alvo = T_amb + m.K * u_planta
        T += (Ts_s / m.tau_s) * (alvo - T)

    return pd.DataFrame(linhas)


def metricas_resposta(sim: pd.DataFrame, setpoint_c: float,
                      faixa_acomodacao: float = 0.02) -> dict:
    """Sobressinal, tempo de acomodacao, erro em regime e duty final."""
    T = sim["T_c"].to_numpy()
    t = sim["t_s"].to_numpy()
    T0 = float(T[0])

    pico = float(np.max(T))
    salto = setpoint_c - T0
    sobressinal = 100.0 * (pico - setpoint_c) / salto if salto > 0 else 0.0

    tol = faixa_acomodacao * abs(salto)
    fora = np.where(np.abs(T - setpoint_c) > tol)[0]
    t_acom = float(t[fora[-1] + 1]) if len(fora) and fora[-1] + 1 < len(t) else float("nan")

    return {
        "sobressinal_pct": max(sobressinal, 0.0),
        "t_acomodacao_s": t_acom,
        "t_acomodacao_min": t_acom / 60.0 if np.isfinite(t_acom) else float("nan"),
        "erro_regime_c": float(T[-1] - setpoint_c),
        "duty_regime": float(sim["duty"].iloc[-1]),
        "pico_c": pico,
    }


# ---------------------------------------------------------------------------
# Saida para o firmware
# ---------------------------------------------------------------------------
def gerar_config_h(m: FOPDT, regra: TuningRule) -> str:
    """Trecho pronto para colar em include/config.h."""
    return f"""\
// ---- valores obtidos do ensaio de degrau + sintonia {regra.nome} ----
// Modelo identificado: {m}
constexpr float PI_KP = {regra.Kp:.6f}f;   // 1/degC
constexpr float PI_KI = {regra.Ki:.8f}f;   // 1/(degC*s)   (Ti = {regra.Ti_s:.0f} s)

constexpr float PLANT_TAU_S     = {m.tau_s:.1f}f;
constexpr float PLANT_GAIN_C    = {m.K:.2f}f;
constexpr float PLANT_AMBIENT_C = {m.T0_c:.1f}f;"""
