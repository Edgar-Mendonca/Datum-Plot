"""Bayes factors beside the usual P values (B37, 0.4.4), with the default priors of the Bayesian t-test and ANOVA
literature, so the numbers agree with other software that uses them:

- t-tests: the JZS Bayes factor (Rouder et al. 2009): a Cauchy prior on the standardised effect δ with scale r
  (medium √2/2, wide 1, ultrawide √2), written as δ | g ~ N(0, g), g ~ inverse-gamma(1/2, r²/2), integrated over g.
- One-way ANOVA (independent groups): the same prior on the group effects in the J − 1 sum-to-zero directions (Rouder
  et al. 2012; scale medium 1/2, wide √2/2, ultrawide 1), worked out from the group means, sizes and the within-group
  sum of squares. With two groups it equals the unpaired t-test's Bayes factor at scale √2·r.
- Correlation: the exact Bayes factor for Pearson's r with a uniform prior on ρ (Ly, Verhagen & Wagenmakers 2016,
  κ = 1).

BF₁₀ > 1 favours a difference (or a correlation), < 1 favours none; the words follow Lee & Wagenmakers (2013)."""
import math

import numpy as np

WIDTH = {"medium": (math.sqrt(2) / 2, 0.5), "wide": (1.0, math.sqrt(2) / 2), "ultrawide": (math.sqrt(2), 1.0)}  # (t-test r, ANOVA r)


def _over_g(logf, r):
    """log ∫ exp(logf(g)) p(g) dg with g ~ inverse-gamma(1/2, r²/2), integrated over u = log g around its peak."""
    from scipy.integrate import quad
    from scipy.optimize import minimize_scalar

    def h(u):  # log integrand in u = log g (the Jacobian dg = g du included)
        gg = math.exp(u)
        return logf(gg) + math.log(r) - 0.5 * math.log(2 * math.pi) - 1.5 * u - r * r / (2 * gg) + u

    peak = minimize_scalar(lambda u: -h(u), bounds=(-40, 40), method="bounded").x
    top = h(peak)
    # The integrand falls at least as fast as e^(−|u − peak|/2) on both sides: ±40 around the peak leaves < 1e-8 out.
    v, _ = quad(lambda u: math.exp(h(u) - top), peak - 40, peak + 40, points=[peak], limit=400)
    return top + math.log(v)


def t_bf(t, n_eff, df, r=math.sqrt(2) / 2):
    """JZS BF₁₀ from a t statistic: n_eff = n (one sample, paired) or n₁n₂/(n₁+n₂) (two groups), df its degrees of freedom."""
    if not (math.isfinite(t) and n_eff > 0 and df > 0):
        return float("nan")
    a = -(df + 1) / 2
    null = a * math.log1p(t * t / df)
    return math.exp(_over_g(lambda gg: -0.5 * math.log1p(n_eff * gg) + a * math.log1p(t * t / ((1 + n_eff * gg) * df)), r) - null)


def anova_bf(n, means, ssw, r=0.5):
    """BF₁₀ of a one-way design (independent groups) from the group sizes, means and the within-group sum of squares."""
    n, m = np.asarray(n, float), np.asarray(means, float)
    J, N = len(n), float(n.sum())
    if J < 2 or ssw <= 0 or N - J < 1:
        return float("nan")
    P = np.eye(J) - 1.0 / J  # the effects live in the J − 1 sum-to-zero directions
    one = np.ones(J)

    def logm(gg):  # log marginal likelihood (up to a constant shared with the null, g = 0)
        C = np.diag(1 / n) + gg * P
        try:
            Ci = np.linalg.inv(C)
        except np.linalg.LinAlgError:
            return -np.inf
        s = float(one @ Ci @ one)
        q = float(m @ Ci @ m) - float(one @ Ci @ m) ** 2 / s
        return -0.5 * np.linalg.slogdet(C)[1] - 0.5 * math.log(s) - (N - 1) / 2 * math.log(ssw + q)

    null = logm(0.0)
    return math.exp(_over_g(lambda gg: logm(gg) - null, r))


def corr_bf(r, n, kappa=1.0):
    """BF₁₀ of Pearson's r from n pairs, prior ρ ~ stretched beta(1/κ, 1/κ) (κ = 1: uniform); Ly et al. (2016), with the
    hypergeometric function rewritten by Euler's transformation so large samples stay finite."""
    from scipy.special import betaln, gammaln, hyp2f1
    if n < 3 or not math.isfinite(r):
        return float("nan")
    z = min(r * r, 1 - 1e-15)
    a, c = (n - 1) / 2, 1 / kappa + n / 2
    log2f1 = (c - 2 * a) * math.log1p(-z) + math.log(hyp2f1(c - a, c - a, c, z))
    lb = (kappa - 2) / kappa * math.log(2) + 0.5 * math.log(math.pi) - betaln(1 / kappa, 1 / kappa) \
        + gammaln((2 + (n - 1) * kappa) / (2 * kappa)) - gammaln((2 + n * kappa) / (2 * kappa)) + log2f1
    return math.exp(min(lb, 700.0))


def words(bf):
    """The strength of evidence of BF₁₀ in plain words (Lee & Wagenmakers 2013)."""
    if not math.isfinite(bf) or bf <= 0:
        return "—"
    b, side = (bf, "for a difference") if bf >= 1 else (1 / bf, "for no difference")
    level = "no real evidence either way" if b < 1.5 else "anecdotal evidence" if b < 3 else "moderate evidence" if b < 10 else "strong evidence" if b < 30 \
        else "very strong evidence" if b < 100 else "extreme evidence"
    return level if b < 1.5 else f"{level} {side}"


def text(bf):
    """BF₁₀ written for a table."""
    if not math.isfinite(bf):
        return "—"
    return f"{bf:.4g}" if 1e-3 <= bf < 1e4 else f"{bf:.3e}"


def rows(bf, width, what="difference"):
    """Summary rows: BF₁₀, BF₀₁ and the words."""
    w = words(bf).replace("difference", what)
    return [["Bayes factor BF₁₀", text(bf)], ["BF₀₁ (= 1 / BF₁₀)", text(1 / bf) if bf and math.isfinite(bf) else "—"], ["Evidence", f"{w} (prior width: {width})"]]
