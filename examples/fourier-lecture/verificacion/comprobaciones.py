#!/usr/bin/env python3
"""Comprobación numérica de cada par y propiedad que afirman las piezas (D2, D4, D6).

Convención del curso (estilo.md):
    X(w) = ∫ x(t) e^{-jwt} dt,   x(t) = (1/2π) ∫ X(w) e^{jwt} dw,   sinc(x) = sin(x)/x.

Estructura (D6). Toda comprobación es una función `f(error=False)`:
  - `f()` compara la fórmula que escriben las piezas con un cálculo numérico;
  - `f(error=True)` hace lo mismo con la fórmula que tiene el error típico que
    esa comprobación vigila (signo, factor 2π, valor absoluto, orientación...).
El script exige las dos cosas: `f()` pasa y `f(error=True)` FALLA. Si el error
pasa, la comprobación es ciega y el script sale con 1. Una comprobación que no
acepte `error` hace fallar el script, salvo que esté en EXENTAS con su razón.
No hay una lista de mutantes que mantener: el mutante es la misma función.

Los pares que solo existen como distribuciones (delta, escalón, coseno) se
comprueban por su límite: una familia de funciones ordinarias que converge.

Uso: python3 verificacion/comprobaciones.py   (sale con 1 si algo falla o es ciego)
"""
import inspect
import sys
import numpy as np
from scipy.integrate import quad

TOL = 1e-6
W = [-7.3, -2.0, -0.5, 0.0, 0.4, 1.0, 3.7]

# Comprobaciones que no pueden tener versión con error, con su razón. Hoy, ninguna.
EXENTAS = {}


def sinc(x):
    x = np.asarray(x, dtype=float)
    return np.where(x == 0, 1.0, np.sin(x) / np.where(x == 0, 1, x))


def ft(x, w, a=-np.inf, b=np.inf, **kw):
    """Transformada numérica de una x(t) real o compleja en un w."""
    re = quad(lambda t: (x(t) * np.exp(-1j * w * t)).real, a, b, limit=400, **kw)[0]
    im = quad(lambda t: (x(t) * np.exp(-1j * w * t)).imag, a, b, limit=400, **kw)[0]
    return re + 1j * im


def _q(f, peso, w):
    """∫_0^∞ f(t) peso(|w| t) dt para una f compleja, parte real e imaginaria aparte."""
    if peso is None:
        return quad(lambda t: complex(f(t)).real, 0, np.inf)[0] + 1j * quad(lambda t: complex(f(t)).imag, 0, np.inf)[0]
    r = quad(lambda t: complex(f(t)).real, 0, np.inf, weight=peso, wvar=abs(w))[0]
    i = quad(lambda t: complex(f(t)).imag, 0, np.inf, weight=peso, wvar=abs(w))[0]
    return r + 1j * i


def ft_lenta(par, impar, w):
    """Transformada de f = par + impar (cada parte puede ser compleja y decaer lento,
    como 1/t), por la cuadratura de Fourier de QUADPACK:
    X(w) = 2∫_0^∞ par(t) cos(wt) dt - 2j sgn(w) ∫_0^∞ impar(t) sin(|w|t) dt."""
    if w == 0:
        return 2 * _q(par, None, w)
    return 2 * _q(par, "cos", w) - 2j * np.sign(w) * _q(impar, "sin", w)


def cerca(a, b, tol=TOL):
    return abs(a - b) <= tol * max(1.0, abs(b))


# Señal de prueba sin ninguna simetría (D4).
def x0(t):
    return np.exp(-0.5 * (t - 0.3)**2) * (1 + 0.4 * t)


def X0(w):
    return ft(x0, w)


# ---------- pares ----------

def par_rect(error=False):
    """rect(t/T) <-> T sinc(wT/2). Error: la otra convención de sinc (con π)."""
    T = 1.6
    s = (lambda x: np.sinc(x)) if error else sinc
    return all(cerca(ft(lambda t: 1.0, w, -T / 2, T / 2), T * s(w * T / 2)) for w in W)


def par_exp_causal(error=False):
    """e^{-at}u(t), a>0 <-> 1/(a+jw). Error: 1/(a-jw)."""
    a, sg = 0.8, (-1 if error else 1)
    return all(cerca(ft(lambda t: np.exp(-a * t), w, 0, np.inf), 1 / (a + sg * 1j * w)) for w in W)


def par_exp_bilateral(error=False):
    """e^{-a|t|}, a>0 <-> 2a/(a^2+w^2). Error: sin el factor 2."""
    a, k = 1.3, (1 if error else 2)
    return all(cerca(ft(lambda t: np.exp(-a * abs(t)), w, -60, 60, points=[0]), k * a / (a**2 + w**2), 1e-5) for w in W)


def par_gaussiana(error=False):
    """e^{-a t^2} <-> sqrt(pi/a) e^{-w^2/(4a)}. Error: e^{-w^2/(2a)}."""
    a, d = 0.7, (2 if error else 4)
    return all(cerca(ft(lambda t: np.exp(-a * t * t), w), np.sqrt(np.pi / a) * np.exp(-w * w / (d * a))) for w in W)


def par_delta(error=False):
    """delta(t) <-> 1, por el límite de gaussianas de área 1 y ancho s -> 0: para cada
    s la transformada es e^{-w^2 s^2/2} (se comprueba con integral) y tiende a 1.
    Error: confundir el factor de la inversa y escribir delta(t) <-> 2pi."""
    objetivo = 2 * np.pi if error else 1.0
    dist = []
    for s in (1e-2, 1e-3, 1e-4):
        g = lambda t, s=s: np.exp(-t * t / (2 * s * s)) / (s * np.sqrt(2 * np.pi))
        for w in W:
            if not cerca(ft(g, w, -20 * s, 20 * s), np.exp(-w * w * s * s / 2), 1e-6):
                return False
        dist.append(max(abs(objetivo - np.exp(-w * w * s * s / 2)) for w in W))
    return dist[0] > dist[1] > dist[2] and dist[2] < 1e-6


def par_escalon(error=False):
    """u(t) <-> pi delta(w) + 1/(jw), como límite de e^{-et}u(t) <-> 1/(e+jw), cuya
    fórmula se comprueba aquí con integral para un e fijo. La parte imaginaria
    tiende a la de 1/(jw); la real tiene área pi para todo e.
    Error: -1/(jw) (signo)."""
    e0 = 0.5
    if not all(cerca(ft(lambda t: np.exp(-e0 * t), w, 0, np.inf), 1 / (e0 + 1j * w)) for w in W):
        return False
    termino = (lambda w: -1 / (1j * w)) if error else (lambda w: 1 / (1j * w))
    e = 1e-4
    for w in [x for x in W if x != 0]:
        if not cerca((1 / (e + 1j * w)).imag, termino(w).imag, 1e-6):
            return False
    area = 2 * (quad(lambda w: e / (e * e + w * w), 0, 1)[0] + quad(lambda w: e / (e * e + w * w), 1, np.inf)[0])
    return cerca(area, np.pi, 1e-6)


def par_signo(error=False):
    """(1/2) sgn(t) <-> 1/(jw), por el límite de (1/2) sgn(t) e^{-e|t|} <-> -jw/(e^2+w^2),
    fórmula que se comprueba con integral para un e fijo. Error: -1/(jw)."""
    e2 = 0.7
    f = lambda t: 0.5 * np.sign(t) * np.exp(-e2 * abs(t))
    if not all(cerca(ft(f, w, -60, 60, points=[0]), -1j * w / (e2 * e2 + w * w), 1e-5) for w in W):
        return False
    termino = (lambda w: -1 / (1j * w)) if error else (lambda w: 1 / (1j * w))
    e = 1e-3
    return all(cerca(-1j * w / (e * e + w * w), termino(w), 1e-5) for w in W if w != 0)


def par_coseno(error=False):
    """cos(w0 t) <-> pi[delta(w-w0) + delta(w+w0)], por el límite con ventana gaussiana:
    el espectro se concentra en ±w0 con área pi alrededor de cada uno.
    Error: área 2pi (el factor de 1 <-> 2pi delta aplicado a cada impulso)."""
    w0, e = 3.0, 0.02
    X = lambda w: np.sqrt(np.pi) / (2 * e) * (np.exp(-(w - w0)**2 / (4 * e * e)) + np.exp(-(w + w0)**2 / (4 * e * e)))
    for w in (w0, w0 + 0.03):
        if not cerca(ft(lambda t: np.cos(w0 * t) * np.exp(-(e * t)**2), w, -400, 400, points=[0]), X(w), 1e-5):
            return False
    return cerca(quad(X, w0 - 1, w0 + 1, points=[w0])[0], 2 * np.pi if error else np.pi, 1e-6)


def par_dualidad_lorentz(error=False):
    """Dualidad con el par par: 2a/(a^2+t^2) <-> 2pi e^{-a|w|}. Error: sin el 2pi.
    (El signo de x(-w) lo vigila par_dualidad_asimetrica: aquí la señal es par.)"""
    a, k = 1.1, (1 if error else 2 * np.pi)
    return all(cerca(ft_lenta(lambda t: 2 * a / (a * a + t * t), lambda t: 0.0, w), k * np.exp(-a * abs(w)), 1e-6) for w in W)


def par_dualidad_asimetrica(error=False):
    """Dualidad con señal sin simetría: e^{-at}u(t) <-> 1/(a+jw), luego
    1/(a+jt) <-> 2pi e^{aw} u(-w). Error: 2pi x(+w) en vez de 2pi x(-w)."""
    a = 0.9
    # 1/(a+jt) = a/(a^2+t^2) - j t/(a^2+t^2): parte par real, parte impar imaginaria
    X = lambda w: ft_lenta(lambda t: a / (a * a + t * t), lambda t: -1j * t / (a * a + t * t), w)
    esperado = (lambda w: 2 * np.pi * np.exp(-a * w) * (w > 0)) if error else (lambda w: 2 * np.pi * np.exp(a * w) * (w < 0))
    return all(cerca(X(w), esperado(w), 1e-5) for w in W if w != 0)


def par_serie_muestras(error=False):
    """Sección 1: c_k = X(k w0)/T0, con una señal sin simetría: periodo T0 = 4 cuyo
    periodo es e^{-t} en [0, 1). c_k por integral sobre un periodo, sin ft().
    Error: el exponente de los coeficientes con signo +."""
    T0 = 4.0
    w0, sg = 2 * np.pi / T0, (1 if error else -1)
    X = lambda w: (1 - np.exp(-(1 + 1j * w))) / (1 + 1j * w)
    for k in range(-3, 4):
        if k == 0:
            continue
        re = quad(lambda t: (np.exp(-t) * np.exp(sg * 1j * k * w0 * t)).real, 0, 1)[0]
        im = quad(lambda t: (np.exp(-t) * np.exp(sg * 1j * k * w0 * t)).imag, 0, 1)[0]
        if not cerca((re + 1j * im) / T0, X(k * w0) / T0):
            return False
    return True


# ---------- propiedades ----------

def prop_linealidad(error=False):
    """a x + b y <-> a X + b Y. Error: el signo de b."""
    y = lambda t: np.exp(-abs(t))
    b = 3 if error else -3
    return all(cerca(ft(lambda t: 2 * x0(t) - 3 * y(t), w), 2 * X0(w) + b * ft(y, w), 1e-5) for w in W)


def prop_desplazamiento(error=False):
    """x(t - t0) <-> e^{-jw t0} X(w). Error: e^{+jw t0}."""
    t0, sg = 1.7, (1 if error else -1)
    return all(cerca(ft(lambda t: x0(t - t0), w), np.exp(sg * 1j * w * t0) * X0(w)) for w in W)


def prop_escala(error=False):
    """x(at) <-> (1/|a|) X(w/a), también con a < 0. Error: 1/a sin valor absoluto."""
    k = (lambda a: 1 / a) if error else (lambda a: 1 / abs(a))
    return all(cerca(ft(lambda t: x0(a * t), w), X0(w / a) * k(a)) for a in (2.5, -0.6) for w in W)


def prop_modulacion(error=False):
    """x(t) cos(w0 t) <-> (1/2)[X(w - w0) + X(w + w0)]. Error: sin el 1/2."""
    w0, k = 4.0, (1.0 if error else 0.5)
    return all(cerca(ft(lambda t: x0(t) * np.cos(w0 * t), w), k * (X0(w - w0) + X0(w + w0))) for w in W)


def prop_derivada(error=False):
    """dx/dt <-> jw X(w). Error: -jw."""
    dx = lambda t: np.exp(-0.5 * (t - 0.3)**2) * (0.4 - (t - 0.3) * (1 + 0.4 * t))
    sg = -1 if error else 1
    return all(cerca(ft(dx, w), sg * 1j * w * X0(w)) for w in W)


def prop_conjugado_real(error=False):
    """x real -> X(-w) = conj(X(w)). Error: X(-w) = X(w)."""
    g = (lambda z: z) if error else np.conj
    return all(cerca(X0(-w), g(X0(w))) for w in W)


def prop_convolucion(error=False):
    """(x * h)(t) <-> X(w) H(w), con x = e^{-t}u(t), h = e^{-2t}u(t): x*h se calcula
    con la integral de convolución (no se escribe a mano) y se transforma.
    Error: el producto con los espectros conjugados."""
    def y(t):
        return quad(lambda s: np.exp(-s) * np.exp(-2 * (t - s)), 0, t)[0] if t > 0 else 0.0
    H = (lambda w: 1 / ((1 - 1j * w) * (2 - 1j * w))) if error else (lambda w: 1 / ((1 + 1j * w) * (2 + 1j * w)))
    return all(cerca(ft(y, w, 0, 40), H(w), 1e-5) for w in (-2.0, -0.5, 0.0, 1.0, 3.7))


def prop_convolucion_directa(error=False):
    """La convolución de e^{-t}u(t) y e^{-2t}u(t), con h(t - tau), es (e^{-t} - e^{-2t}) u(t).
    Error: h(tau - t) (orientación invertida)."""
    for t in (0.2, 1.0, 3.5):
        arg = (lambda s: s - t) if error else (lambda s: t - s)
        h = lambda u: np.exp(-2 * u) * (u >= 0)
        c = quad(lambda s: np.exp(-s) * h(arg(s)), 0, max(t, 0) + 30, points=[t])[0]
        if not cerca(c, np.exp(-t) - np.exp(-2 * t)):
            return False
    return True


def prop_parseval(error=False):
    """∫|x|^2 dt = (1/2pi) ∫|X|^2 dw, con x = e^{-at}u(t): 1/(2a) en ambos lados.
    |X|^2 se calcula desde X = 1/(a+jw), no se escribe a mano.
    Error: X^2 en vez de |X|^2 (quitar el valor absoluto)."""
    a = 0.9
    X = lambda w: 1 / (a + 1j * w)
    dens = (lambda w: (X(w)**2).real) if error else (lambda w: abs(X(w))**2)
    izq = quad(lambda t: abs(np.exp(-a * t))**2, 0, np.inf)[0]
    der = quad(dens, -np.inf, np.inf)[0] / (2 * np.pi)
    return cerca(izq, 1 / (2 * a)) and cerca(der, 1 / (2 * a))


def prop_inversa(error=False):
    """x(t) = (1/2pi) ∫ X(w) e^{jwt} dw, con X = 2a/(a^2+w^2) -> e^{-a|t|}.
    Error: sin el 1/2pi. (El signo del exponente lo vigila prop_inversa_asimetrica.)"""
    a, k = 1.3, (1 if error else 2 * np.pi)
    return all(cerca(ft_lenta(lambda w: 2 * a / (a * a + w * w), lambda w: 0.0, t) / k, np.exp(-a * abs(t)), 1e-5) for t in (0.0, 0.5, -1.2))


def prop_inversa_asimetrica(error=False):
    """Inversa con X sin simetría: X = 1/(1+jw) -> e^{-t}u(t).
    Error: e^{-jwt} en la inversa (saldría e^{t}u(-t))."""
    for t in (0.6, 1.5, -0.8, -2.0):
        # (1/2pi) ∫ X(w) e^{±jwt} dw: la ft de X con t -> ∓t
        # X = 1/(1+jw) = 1/(1+w^2) - j w/(1+w^2)
        v = ft_lenta(lambda w: 1 / (1 + w * w), lambda w: -1j * w / (1 + w * w), t if error else -t) / (2 * np.pi)
        if not cerca(v, np.exp(-t) * (t > 0), 1e-5):
            return False
    return True


# ---------- ejemplos y problemas ----------

def ejemplo_pulso_desplazado(error=False):
    """rect((t-2)/4) <-> 4 sinc(2w) e^{-j2w}. Error: e^{+j2w}."""
    sg = 1 if error else -1
    return all(cerca(ft(lambda t: 1.0, w, 0, 4), 4 * sinc(2 * w) * np.exp(sg * 2j * w)) for w in W)


def ejemplo_salida_rc(error=False):
    """RC = 0.5, entrada e^{-t}u(t): Y = 2/((1+jw)(2+jw)), y = 2(e^{-t} - e^{-2t})u(t).
    Error: los espectros conjugados."""
    y = lambda t: 2 * (np.exp(-t) - np.exp(-2 * t))
    sg = -1 if error else 1
    return all(cerca(ft(y, w, 0, np.inf), 2 / ((1 + sg * 1j * w) * (2 + sg * 1j * w))) for w in W)


def ejemplo_escalon_par(error=False):
    """Sección 3: 1 <-> 2pi delta(w), así que 1/2 <-> pi delta. Límite: e^{-(et)^2} tiene
    transformada (sqrt(pi)/e) e^{-w^2/(4e^2)}, de área 2pi. Error: área pi."""
    e = 0.01
    X = lambda w: np.sqrt(np.pi) / e * np.exp(-w * w / (4 * e * e))
    if not cerca(ft(lambda t: np.exp(-(e * t)**2), 0.0, -600, 600), X(0.0), 1e-5):
        return False
    return cerca(quad(X, -1, 1, points=[0])[0], np.pi if error else 2 * np.pi, 1e-6)


def problema_exp_desplazada(error=False):
    """Problema 1: e^{-3|t-1|} <-> 6/(9+w^2) e^{-jw}. Error: e^{+jw}."""
    sg = 1 if error else -1
    return all(cerca(ft(lambda t: np.exp(-3 * abs(t - 1)), w, -40, 40, points=[1]), 6 / (9 + w * w) * np.exp(sg * 1j * w), 1e-5) for w in W)


def problema_salida_h3(error=False):
    """Problema 2: H = 1/(3+jw), x = e^{-t}u(t) -> y = (1/2)(e^{-t} - e^{-3t})u(t).
    Error: los espectros conjugados."""
    y = lambda t: 0.5 * (np.exp(-t) - np.exp(-3 * t))
    sg = -1 if error else 1
    return all(cerca(ft(y, w, 0, np.inf), 1 / ((1 + sg * 1j * w) * (3 + sg * 1j * w))) for w in W)


def problema_triangulo_convolucion(error=False):
    """Problema 3: rect(t) * rect(t) = tri(t). Error: base de ancho 4 (tri(t/2))."""
    tri = (lambda t: max(0.0, 1 - abs(t) / 2)) if error else (lambda t: max(0.0, 1 - abs(t)))
    for t in (-0.7, 0.0, 0.3, 1.4):
        c = quad(lambda s: 1.0 if abs(t - s) <= 0.5 else 0.0, -0.5, 0.5,
                 points=[p for p in (t - 0.5, t + 0.5) if -0.5 < p < 0.5] or None)[0]
        if not cerca(c, tri(t), 1e-6):
            return False
    return True


def problema_triangulo(error=False):
    """Problema 3: tri(t) <-> sinc^2(w/2). Error: sinc^2(w)."""
    d = 1 if error else 2
    return all(cerca(ft(lambda t: 1 - abs(t), w, -1, 1, points=[0]), sinc(w / d)**2) for w in W)


def problema_exp_coseno(error=False):
    """Problema 4: e^{-t}cos(5t)u(t) <-> (1+jw)/((1+jw)^2 + 25). Error: jw -> -jw."""
    sg = -1 if error else 1
    s = lambda w: 1 + sg * 1j * w
    return all(cerca(ft(lambda t: np.exp(-t) * np.cos(5 * t), w, 0, np.inf), s(w) / (s(w)**2 + 25), 1e-5) for w in W)


def problema_energia_banda(error=False):
    """Problema 5: x = e^{-t}u(t). Energía total 1/2; en |w| <= 1, 1/4, la mitad.
    |X|^2 desde X = 1/(1+jw). Error: X^2 en vez de |X|^2."""
    X = lambda w: 1 / (1 + 1j * w)
    dens = (lambda w: (X(w)**2).real) if error else (lambda w: abs(X(w))**2)
    total = quad(dens, -np.inf, np.inf)[0] / (2 * np.pi)
    banda = quad(dens, -1, 1)[0] / (2 * np.pi)
    return cerca(total, 0.5) and cerca(banda, 0.25)


def problema_gauss_ancho(error=False):
    """Problema 6: para la gaussiana, sigma_t sigma_w = 1/2, con las desviaciones de
    |x|^2 y |X|^2. Error: usar |x| y |X| sin elevar al cuadrado (da 1)."""
    a = 0.7
    p = 1 if error else 2
    px = lambda t: np.exp(-a * t * t)**p
    pw = lambda w: (np.sqrt(np.pi / a) * np.exp(-w * w / (4 * a)))**p
    st = np.sqrt(quad(lambda t: t * t * px(t), -np.inf, np.inf)[0] / quad(px, -np.inf, np.inf)[0])
    sw = np.sqrt(quad(lambda w: w * w * pw(w), -np.inf, np.inf)[0] / quad(pw, -np.inf, np.inf)[0])
    return cerca(st * sw, 0.5)


def problema_cota_anchos(error=False):
    """Problema 6: sigma_t sigma_w >= 1/2. Se comprueba que tres formas no gaussianas dan
    más de 1/2 (no es una demostración de la cota). Error: la cota escrita como 1."""
    cota = 1.0 if error else 0.5

    def producto(px, pw):
        st = np.sqrt(quad(lambda t: t * t * px(t), -np.inf, np.inf)[0] / quad(px, -np.inf, np.inf)[0])
        sw = np.sqrt(quad(lambda w: w * w * pw(w), -np.inf, np.inf)[0] / quad(pw, -np.inf, np.inf)[0])
        return st * sw
    formas = [
        (lambda t: np.exp(-2 * abs(t)), lambda w: (2 / (1 + w * w))**2),                       # e^{-|t|}
        (lambda t: (1 - abs(t))**2 * (abs(t) <= 1), lambda w: sinc(w / 2)**4),               # triángulo
        (lambda t: 1 / (1 + t * t)**4, lambda w: (np.pi * (1 + abs(w)) * np.exp(-abs(w)) / 2)**2),  # 1/(1+t^2)^2
    ]
    return all(producto(px, pw) > cota + 1e-3 for px, pw in formas)


COMPROBACIONES = [v for k, v in list(globals().items())
                  if callable(v) and k.startswith(("par_", "prop_", "ejemplo_", "problema_"))]

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    malas = ciegas = sin_error = 0
    for f in COMPROBACIONES:
        ok = bool(f())
        malas += not ok
        if "error" in inspect.signature(f).parameters:
            detecta = not bool(f(error=True))
            ciegas += not detecta
            if not ok:
                marca = "(la fórmula falla: no se juzga si detecta su error)"
            else:
                marca = "detecta su error" if detecta else "CIEGA: su error pasa"
        elif f.__name__ in EXENTAS:
            marca = f"exenta: {EXENTAS[f.__name__]}"
        else:
            sin_error += 1
            marca = "SIN VERSIÓN CON ERROR (D6)"
        print(f"{'OK   ' if ok else 'FALLA'} {f.__name__:30s} {marca}")
    n = len(COMPROBACIONES)
    print(f"\n{n - malas}/{n} en OK · {n - ciegas - sin_error - len(EXENTAS)}/{n} detectan su error"
          f" · {ciegas} ciegas · {sin_error} sin versión con error · {len(EXENTAS)} exentas")
    sys.exit(1 if (malas or ciegas or sin_error) else 0)
