"""The curve-fitting model library: equation (in X), its parameters, a first guess from the data,
and a plain description. Equations use numpy names (exp, log, log10, sqrt…); fitting is lmfit's."""
import numpy as np

R = 8.314462618  # J/(mol·K)


def _span(x, y):
    i = np.argsort(x)
    return x[i], y[i], float(np.min(y)), float(np.max(y)), float(np.ptp(x)) or 1.0


def g_decay(x, y):
    x, y, lo, hi, w = _span(x, y)
    return {"Y0": y[0], "Plateau": y[-1], "K": 3 / w}


def g_growth(x, y):
    x, y, lo, hi, w = _span(x, y)
    pos = y[y > 0]
    k = np.log(pos[-1] / pos[0]) / w if len(pos) > 1 and pos[0] > 0 else 1 / w
    return {"Y0": max(y[0], 1e-9), "K": k}


def g_power(x, y):
    m = (x > 0) & (y > 0)
    if m.sum() >= 2:
        b, a = np.polyfit(np.log(x[m]), np.log(y[m]), 1)
        return {"A": float(np.exp(a)), "B": float(b)}
    return {"A": 1.0, "B": 1.0}


def g_log(x, y):
    m = x > 0
    if m.sum() >= 2:
        b, a = np.polyfit(np.log(x[m]), y[m], 1)
        return {"A": float(a), "B": float(b)}
    return {"A": 0.0, "B": 1.0}


def g_sigmoid(x, y):
    x, y, lo, hi, w = _span(x, y)
    mid = x[np.argmin(np.abs(y - (lo + hi) / 2))]
    return {"Bottom": lo, "Top": hi, "X50": mid, "Slope": 4 / w}


def g_dose(x, y):
    x, y, lo, hi, w = _span(x, y)
    pos = x[x > 0]
    mid = x[np.argmin(np.abs(y - (lo + hi) / 2))]
    return {"Bottom": lo, "Top": hi, "EC50": mid if mid > 0 else (float(np.median(pos)) if len(pos) else 1.0), "Hill": 1.0}


def g_peak(x, y):
    i = int(np.argmax(y))
    x2, y2, lo, hi, w = _span(x, y)
    return {"Amplitude": float(y[i]) - lo, "Center": float(x[i]), "Width": w / 6, "Baseline": lo}


def g_sat(x, y):
    x, y, lo, hi, w = _span(x, y)
    half = x[np.argmin(np.abs(y - hi / 2))]
    return {"Ymax": hi * 1.1, "K": float(half) if half > 0 else w / 4}


def g_arrh(x, y):
    m = (x > 0) & (y > 0)
    if m.sum() >= 2:
        b, a = np.polyfit(1 / x[m], np.log(y[m]), 1)
        return {"A": float(np.exp(a)), "Ea": float(-b * R)}
    return {"A": 1.0, "Ea": 50000.0}


def g_avrami(x, y):
    x, y, lo, hi, w = _span(x, y)
    return {"k": (1 / w) ** 2, "n": 2.0}


def g_freund(x, y):
    p = g_power(x, y)
    return {"Kf": p["A"], "n": 1 / p["B"] if p["B"] else 1.0}


MODELS = {
    "exp_decay": ("Exponential decay (one phase)", "(Y0 - Plateau)*exp(-K*X) + Plateau", g_decay, "Falls from Y0 to a plateau at rate K; half-life ln(2)/K."),
    "exp_growth": ("Exponential growth", "Y0*exp(K*X)", g_growth, "Grows from Y0 at rate K; doubling time ln(2)/K."),
    "exp_decay2": ("Exponential decay (two phases)", "Plateau + SpanFast*exp(-KFast*X) + SpanSlow*exp(-KSlow*X)",
                   lambda x, y: {**{"Plateau": float(np.min(y))}, "SpanFast": float(np.ptp(y)) / 2, "SpanSlow": float(np.ptp(y)) / 2, "KFast": 10 / (float(np.ptp(x)) or 1), "KSlow": 1 / (float(np.ptp(x)) or 1)},
                   "Two exponential phases with rates KFast and KSlow."),
    "power": ("Power law", "A*X**B", g_power, "Y = A·X^B, a straight line on log–log axes (creep, fatigue, scaling laws)."),
    "log": ("Logarithmic", "A + B*log(X)", g_log, "Y = A + B·ln(X)."),
    "logistic": ("Logistic (sigmoid)", "Bottom + (Top - Bottom)/(1 + exp(-Slope*(X - X50)))", g_sigmoid, "S-shaped curve between Bottom and Top, half-way at X50."),
    "gompertz": ("Gompertz growth", "Bottom + (Top - Bottom)*exp(-exp(-Slope*(X - X50)))", g_sigmoid, "An asymmetric S-shaped growth curve."),
    "dose4": ("Dose-response, 4 parameters (X is concentration)", "Bottom + (Top - Bottom)/(1 + (EC50/X)**Hill)", g_dose, "Response between Bottom and Top, half-way at EC50, steepness Hill."),
    "gauss": ("Gaussian peak", "Baseline + Amplitude*exp(-0.5*((X - Center)/Width)**2)", g_peak, "A bell-shaped peak; FWHM = 2.355·Width."),
    "lorentz": ("Lorentzian peak", "Baseline + Amplitude/(1 + ((X - Center)/Width)**2)", g_peak, "A peak with wider tails; FWHM = 2·Width."),
    "mm": ("Michaelis-Menten (saturation)", "Ymax*X/(K + X)", g_sat, "Rises to Ymax; half of Ymax at X = K."),
    "langmuir": ("Langmuir isotherm", "Ymax*K*X/(1 + K*X)", lambda x, y: {"Ymax": float(np.max(y)) * 1.1, "K": 1 / (g_sat(x, y)["K"] or 1)}, "Monolayer adsorption: capacity Ymax, affinity K."),
    "freundlich": ("Freundlich isotherm", "Kf*X**(1/n)", g_freund, "Adsorption on heterogeneous surfaces."),
    "arrhenius": ("Arrhenius (X is temperature in K)", "A*exp(-Ea/(8.314462618*X))", g_arrh, "Rate against temperature; Ea in J/mol."),
    "avrami": ("Avrami (JMAK) transformation", "1 - exp(-k*X**n)", g_avrami, "Fraction transformed against time; Avrami exponent n."),
}
