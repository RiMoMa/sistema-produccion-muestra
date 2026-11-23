# Lecture 5 · The continuous-time Fourier transform

*Second-year Signals and Systems · lecture notes and tutorial sheet*

**The question this lecture answers:** a Fourier series describes a periodic
signal as a sum of harmonics. What plays that role for a signal that happens
once, such as a pulse, a decaying transient or a single echo?

## What you should be able to do after this lecture

1. Compute the Fourier transform of a pulse, a one-sided exponential and a
   Gaussian from the definition, and state the condition under which each
   integral exists.
2. Use the shift, scaling, modulation and differentiation properties to obtain
   new transforms without integrating.
3. Find the output of an LTI system by multiplying spectra, and return to the
   time domain by partial fractions.
4. Decide, for a given signal, whether its transform exists as an ordinary
   integral or only in the sense of distributions.
5. Compute the energy of a signal, and the energy in a frequency band, using
   Parseval's theorem.

**Notation used throughout the course.** Angular frequency $\omega$ in rad/s,
imaginary unit $j$, and

$$X(\omega) = \int_{-\infty}^{\infty} x(t)\,e^{-j\omega t}\,dt, \qquad x(t) = \frac{1}{2\pi}\int_{-\infty}^{\infty} X(\omega)\,e^{j\omega t}\,d\omega.$$

We write $x(t) \leftrightarrow X(\omega)$. In this course
$\mathrm{sinc}(x) = \sin(x)/x$, **without** a factor of $\pi$; some textbooks
define $\mathrm{sinc}(x) = \sin(\pi x)/(\pi x)$, and their tables differ from
ours by that factor. $\mathrm{rect}(t/T)$ is the pulse of height 1 and width $T$
centred on $t = 0$; $u(t)$ is the unit step.

---

## 1 · From series to transform

**The question.** If we stretch the period of a periodic signal until only one
copy remains, what happens to its Fourier series?

**The idea.** Take a pulse of width $T$ repeated every $T_0$ seconds. Its
Fourier coefficients are samples, spaced $\omega_0 = 2\pi/T_0$ apart, of one
fixed envelope:

$$c_k = \frac{1}{T_0}\int_{-T_0/2}^{T_0/2} x(t)\,e^{-jk\omega_0 t}\,dt = \frac{1}{T_0}\,X(k\omega_0).$$

As $T_0$ grows the samples crowd together and each one shrinks, but the
envelope $X(\omega)$ does not change. In the limit the sum over harmonics
becomes an integral over frequency: the line spacing $\omega_0$ becomes
$d\omega$, and $1/T_0 = \omega_0/2\pi$ becomes the $1/2\pi$ in front of the
inverse transform. The transform is the envelope that the series was sampling
all along.

**Definition and condition.** $X(\omega)$ exists as an ordinary integral for
every $\omega$ when $x$ is absolutely integrable,
$\int_{-\infty}^{\infty} |x(t)|\,dt < \infty$, because
$|x(t)\,e^{-j\omega t}| = |x(t)|$. This is sufficient, not necessary: signals
with finite energy also have transforms, in a mean-square sense. Signals such as
$u(t)$ and $\cos(\omega_0 t)$ satisfy neither condition; their transforms exist
only in the sense of distributions (section 3).

**Worked example: the rectangular pulse.** For $x(t) = \mathrm{rect}(t/T)$,

$$X(\omega) = \int_{-T/2}^{T/2} e^{-j\omega t}\,dt = \frac{e^{-j\omega T/2} - e^{j\omega T/2}}{-j\omega} = \frac{2\sin(\omega T/2)}{\omega} = T\,\mathrm{sinc}\!\left(\frac{\omega T}{2}\right).$$

The first zeros are at $\omega = \pm 2\pi/T$. A narrower pulse has a wider main
lobe: time width and bandwidth trade against each other. At $\omega = 0$ the
value is $T$, the area of the pulse; this holds in general, since
$X(0) = \int x(t)\,dt$.

**Common error.** Reading our pair with the other definition of
$\mathrm{sinc}$, that is, writing
$T\sin(\pi\omega T/2)/(\pi\omega T/2)$, which puts the first zeros at
$\omega = \pm 2/T$ instead of $\pm 2\pi/T$. *How to detect it:* check the area. $X(0)$
must equal $\int x(t)\,dt$, and the first zero must be where a whole number of
cycles of $e^{-j\omega t}$ fits inside the pulse, $\omega T = 2\pi$.

---

## 2 · Basic pairs

**The question.** Which transforms are worth knowing by heart, because the rest
follow from them by the properties of section 4?

**One-sided exponential.** For $x(t) = e^{-at}u(t)$ with $a > 0$,

$$X(\omega) = \int_0^{\infty} e^{-(a + j\omega)t}\,dt = \frac{1}{a + j\omega}.$$

The condition $a > 0$ is what makes the upper limit vanish. The magnitude
$1/\sqrt{a^2 + \omega^2}$ falls by a factor of $\sqrt{2}$ at $\omega = a$: the
faster the decay, the wider the spectrum.

**Two-sided exponential.** For $x(t) = e^{-a|t|}$, $a > 0$, splitting the
integral at $t = 0$ gives

$$X(\omega) = \frac{1}{a + j\omega} + \frac{1}{a - j\omega} = \frac{2a}{a^2 + \omega^2}.$$

It is real and even, as it must be for a real and even signal.

**Gaussian.** For $x(t) = e^{-at^2}$, $a > 0$, completing the square in the
exponent gives

$$X(\omega) = \sqrt{\frac{\pi}{a}}\;e^{-\omega^2/(4a)}.$$

The transform of a Gaussian is a Gaussian. A narrow pulse in time (large $a$) is
wide in frequency, and the reverse.

**Worked example: a delayed pulse.** Find the transform of a pulse of height 1
that switches on at $t = 0$ and off at $t = 4$. Directly,

$$X(\omega) = \int_0^4 e^{-j\omega t}\,dt = \frac{1 - e^{-4j\omega}}{j\omega} = e^{-2j\omega}\,\frac{e^{2j\omega} - e^{-2j\omega}}{j\omega} = 4\,\mathrm{sinc}(2\omega)\,e^{-2j\omega}.$$

The factor $4\,\mathrm{sinc}(2\omega)$ is the transform of $\mathrm{rect}(t/4)$;
the factor $e^{-2j\omega}$ records the delay of 2 s to the pulse centre. Section
4 obtains this in one line.

**Common error.** Writing $e^{-at}u(t) \leftrightarrow 1/(a + j\omega)$ for
$a \le 0$. *How to detect it:* for $a \le 0$ the signal does not decay and the
integral diverges; the formula still gives a finite number, which is the trap.
Check the condition before quoting the pair.

---

## 3 · Transforms that exist only as distributions

**The question.** The impulse, the step and a pure cosine are the signals we use
most. None of them is absolutely integrable. In what sense do they have
transforms?

**The idea.** We treat $\delta(\omega)$ operationally: an infinitely narrow
spike of unit area, defined by what it does inside an integral,
$\int f(\omega)\,\delta(\omega - \omega_0)\,d\omega = f(\omega_0)$. Each pair
below is the limit of ordinary pairs. The rigorous treatment (distribution
theory) is outside the scope of this course; the limits are what we rely on.

**Impulse.** Take Gaussians of unit area and width $s$. Their transforms are
$e^{-\omega^2 s^2/2}$, which tend to 1 for every $\omega$ as $s \to 0$. So

$$\delta(t) \leftrightarrow 1.$$

An impulse contains every frequency with equal weight.

**Unit step.** Take $e^{-\varepsilon t}u(t) \leftrightarrow 1/(\varepsilon + j\omega)$
and let $\varepsilon \to 0$. Writing

$$\frac{1}{\varepsilon + j\omega} = \frac{\varepsilon}{\varepsilon^2 + \omega^2} - \frac{j\omega}{\varepsilon^2 + \omega^2},$$

the second term tends to $1/(j\omega)$ for $\omega \ne 0$. The first term tends
to zero for $\omega \ne 0$, but its area is $\pi$ for every $\varepsilon$: in the
limit it is $\pi\,\delta(\omega)$. Therefore

$$u(t) \leftrightarrow \pi\,\delta(\omega) + \frac{1}{j\omega}.$$

The impulse at $\omega = 0$ carries the step's average value of $\tfrac{1}{2}$.

**Cosine.** Windowing $\cos(\omega_0 t)$ by an ever wider Gaussian concentrates
its spectrum at $\pm\omega_0$, with area $\pi$ around each:

$$\cos(\omega_0 t) \leftrightarrow \pi\left[\delta(\omega - \omega_0) + \delta(\omega + \omega_0)\right].$$

**Worked example: why the step needs the impulse.** Suppose we dropped the
$\pi\,\delta(\omega)$ and kept $U(\omega) = 1/(j\omega)$. That function is odd,
so its inverse transform would be an odd function of time. But $u(t)$ is not
odd: $u(t) = \tfrac{1}{2} + \tfrac{1}{2}\,\mathrm{sgn}(t)$. The $1/(j\omega)$ term
is exactly the transform of $\tfrac{1}{2}\,\mathrm{sgn}(t)$, and the
$\pi\,\delta(\omega)$ term is the transform of the constant $\tfrac{1}{2}$
(since $1 \leftrightarrow 2\pi\,\delta(\omega)$).

**Common error.** Computing $\int_0^\infty e^{-j\omega t}\,dt$ "directly" and
reporting $1/(j\omega)$. *How to detect it:* the integral does not converge, so
any value obtained from it is a guess. Check the even part of the signal: if it
has a nonzero average, its transform must have an impulse at $\omega = 0$.

---

## 4 · Properties

**The question.** How can we obtain new transforms without integrating again?

Each property below holds whenever the transforms involved exist. They are
listed with the operation in time on the left and its effect on the spectrum on
the right.

| Operation | Time | Frequency |
|---|---|---|
| Linearity | $a\,x(t) + b\,y(t)$ | $a\,X(\omega) + b\,Y(\omega)$ |
| Time shift | $x(t - t_0)$ | $e^{-j\omega t_0}\,X(\omega)$ |
| Scaling ($a \ne 0$) | $x(at)$ | $\dfrac{1}{\lvert a\rvert}\,X\!\left(\dfrac{\omega}{a}\right)$ |
| Modulation | $x(t)\cos(\omega_0 t)$ | $\tfrac{1}{2}\left[X(\omega - \omega_0) + X(\omega + \omega_0)\right]$ |
| Differentiation | $\dfrac{dx}{dt}$ | $j\omega\,X(\omega)$ |
| Duality | $X(t)$ | $2\pi\,x(-\omega)$ |
| Real signal | $x(t)$ real | $X(-\omega) = \overline{X(\omega)}$ |

**Why the shift works.** Substitute $\tau = t - t_0$:
$\int x(t - t_0)\,e^{-j\omega t}\,dt = e^{-j\omega t_0}\int x(\tau)\,e^{-j\omega\tau}\,d\tau$.
A delay leaves the magnitude unchanged and adds a phase that grows linearly
with frequency.

**Why the scaling has $1/|a|$.** With $\tau = at$ the integral picks up $1/a$;
for $a < 0$ the limits also swap, which turns $1/a$ into $1/|a|$. Compressing a
signal in time ($|a| > 1$) stretches its spectrum and lowers its height.

**Worked example: the delayed pulse in one line.** The pulse on $[0, 4]$ is
$\mathrm{rect}((t - 2)/4)$. From section 1, $\mathrm{rect}(t/4) \leftrightarrow 4\,\mathrm{sinc}(2\omega)$;
the shift by 2 multiplies by $e^{-2j\omega}$. The result,
$4\,\mathrm{sinc}(2\omega)\,e^{-2j\omega}$, matches the direct integration of
section 2.

**Worked example: duality.** From $e^{-a|t|} \leftrightarrow 2a/(a^2 + \omega^2)$,
duality gives

$$\frac{2a}{a^2 + t^2} \leftrightarrow 2\pi\,e^{-a|\omega|}.$$

A transform we could not easily integrate directly comes for free.

**Common error.** Writing the shift as $e^{+j\omega t_0}$. *How to detect it:* a
delay ($t_0 > 0$) must make the phase decrease as $\omega$ increases. Check with
the delayed pulse: its phase at small $\omega$ is $-2\omega$, not $+2\omega$.

---

## 5 · The convolution theorem and LTI systems

**The question.** Convolution in time is hard to compute. Is there a domain in
which an LTI system does something simpler?

**The result.** If $y = x * h$, that is
$y(t) = \int_{-\infty}^{\infty} x(\tau)\,h(t - \tau)\,d\tau$, then

$$Y(\omega) = X(\omega)\,H(\omega).$$

The proof is to substitute the convolution into the definition, swap the order
of integration, and apply the shift property to the inner integral. It holds
when $x$ and $h$ are absolutely integrable. $H(\omega)$ is the **frequency
response** of the system: it scales and rotates each frequency component
independently.

**Parseval's theorem.** For a signal of finite energy,

$$\int_{-\infty}^{\infty} |x(t)|^2\,dt = \frac{1}{2\pi}\int_{-\infty}^{\infty} |X(\omega)|^2\,d\omega.$$

Energy can be counted in either domain, and $|X(\omega)|^2/2\pi$ tells us how it
is distributed over frequency.

**Worked example: an RC circuit.** A first-order RC low-pass filter with
$RC = 0.5$ s has impulse response
$h(t) = \frac{1}{RC}e^{-t/RC}u(t) = 2e^{-2t}u(t)$, so
$H(\omega) = 2/(2 + j\omega)$. The input is $x(t) = e^{-t}u(t)$, with
$X(\omega) = 1/(1 + j\omega)$. Then

$$Y(\omega) = \frac{2}{(1 + j\omega)(2 + j\omega)} = \frac{2}{1 + j\omega} - \frac{2}{2 + j\omega},$$

by partial fractions in the variable $j\omega$. Reading each term off the
one-sided exponential pair,

$$y(t) = 2\left(e^{-t} - e^{-2t}\right)u(t).$$

*Check in the time domain:* $y(0) = 0$, as it must be, since the capacitor
voltage cannot jump; and $y(t) \to 0$ as $t \to \infty$, because the input
decays.

**Common error.** Multiplying the time functions instead of the spectra:
writing $y(t) = x(t)\,h(t)$. *How to detect it:* for the RC example, the product
$2e^{-3t}u(t)$ jumps to 2 at $t = 0$, which a capacitor voltage cannot do.

---

## Summary table

Each line is checked numerically by the function named on its right, in
`verificacion/comprobaciones.py`.

| Pair or property | Condition | Check |
|---|---|---|
| $c_k = X(k\omega_0)/T_0$ (series as samples) | $x$ one period of a periodic signal | `par_serie_muestras` |
| $\mathrm{rect}(t/T) \leftrightarrow T\,\mathrm{sinc}(\omega T/2)$ | $T > 0$ | `par_rect` |
| $e^{-at}u(t) \leftrightarrow 1/(a + j\omega)$ | $a > 0$ | `par_exp_causal` |
| $e^{-a\lvert t\rvert} \leftrightarrow 2a/(a^2 + \omega^2)$ | $a > 0$ | `par_exp_bilateral` |
| $e^{-at^2} \leftrightarrow \sqrt{\pi/a}\,e^{-\omega^2/4a}$ | $a > 0$ | `par_gaussiana` |
| $\delta(t) \leftrightarrow 1$ | distribution | `par_delta` |
| $u(t) \leftrightarrow \pi\delta(\omega) + 1/(j\omega)$ | distribution | `par_escalon` |
| $\tfrac{1}{2}\mathrm{sgn}(t) \leftrightarrow 1/(j\omega)$ | distribution | `par_signo` |
| $\cos(\omega_0 t) \leftrightarrow \pi[\delta(\omega - \omega_0) + \delta(\omega + \omega_0)]$ | distribution | `par_coseno` |
| $2a/(a^2 + t^2) \leftrightarrow 2\pi e^{-a\lvert\omega\rvert}$ (duality) | $a > 0$ | `par_dualidad_lorentz`, `par_dualidad_asimetrica` |
| Linearity, shift, scaling, modulation, differentiation, real signal | transforms exist | `prop_*` |
| Convolution theorem | absolutely integrable | `prop_convolucion`, `prop_convolucion_directa` |
| Parseval | finite energy | `prop_parseval` |
| Inverse transform | as above | `prop_inversa`, `prop_inversa_asimetrica` |
| $\sigma_t\,\sigma_\omega = \tfrac{1}{2}$ for the Gaussian; larger for three other shapes checked (the general bound is stated, not proved) | finite energy | `problema_gauss_ancho`, `problema_cota_anchos` |

---

## Tutorial sheet

Attempt all problems before the tutorial. Problems 1 to 4 apply the lecture;
5 asks you to interpret a result, and 6 to decide what a result allows.

1. Find the Fourier transform of $x(t) = e^{-3|t - 1|}$ using a pair and one
   property. Sketch $|X(\omega)|$ and the phase of $X(\omega)$.
2. A system has frequency response $H(\omega) = 1/(3 + j\omega)$ and the input
   is $x(t) = e^{-t}u(t)$. Find the output $y(t)$, and check your answer at
   $t = 0$ and as $t \to \infty$.
3. The triangle $\mathrm{tri}(t)$ equals $1 - |t|$ for $|t| \le 1$ and zero
   otherwise. Show that $\mathrm{tri}(t) = \mathrm{rect}(t) * \mathrm{rect}(t)$
   and use the convolution theorem to find its transform. Compare how fast
   $|X(\omega)|$ decays with the decay for $\mathrm{rect}(t)$, and explain the
   difference in terms of the smoothness of each signal.
4. Use the modulation property to find the transform of
   $e^{-t}\cos(5t)\,u(t)$. Where are the peaks of $|X(\omega)|$, and why?
5. For $x(t) = e^{-t}u(t)$, compute the total energy, and the fraction of the
   energy in the band $|\omega| \le 1$ rad/s. What bandwidth would you quote for
   this signal, and why is the answer a choice rather than a fact?
6. For the Gaussian $x(t) = e^{-at^2}$, let $\sigma_t$ be the standard deviation
   of $|x(t)|^2$ (treated as a distribution over $t$) and $\sigma_\omega$ that of
   $|X(\omega)|^2$. Compute $\sigma_t\,\sigma_\omega$. Does the result depend on
   $a$? What does that say about designing a pulse that is short in time and
   narrow in frequency?

---

## Solutions

**1.** From $e^{-3|t|} \leftrightarrow 6/(9 + \omega^2)$ and a shift of 1,
$X(\omega) = \dfrac{6}{9 + \omega^2}\,e^{-j\omega}$. The magnitude is the
bell-shaped $6/(9 + \omega^2)$, with peak $\tfrac{2}{3}$ at $\omega = 0$; the
phase is the straight line $-\omega$. The shift changes the phase only.

**2.** $Y(\omega) = \dfrac{1}{(1 + j\omega)(3 + j\omega)} = \dfrac{1/2}{1 + j\omega} - \dfrac{1/2}{3 + j\omega}$,
so $y(t) = \tfrac{1}{2}\left(e^{-t} - e^{-3t}\right)u(t)$. At $t = 0$,
$y = 0$; as $t \to \infty$, $y \to 0$. Both agree with a first-order system
driven by a decaying input.

**3.** The convolution of two unit pulses is the length of their overlap as one
slides past the other, which rises linearly from 0 at $t = -1$ to 1 at $t = 0$
and falls back to 0 at $t = 1$: that is $\mathrm{tri}(t)$. With
$\mathrm{rect}(t) \leftrightarrow \mathrm{sinc}(\omega/2)$,
$\mathrm{tri}(t) \leftrightarrow \mathrm{sinc}^2(\omega/2)$. The pulse spectrum
decays like $1/|\omega|$ and the triangle's like $1/\omega^2$. The pulse has
jumps; the triangle is continuous with jumps only in its slope. The smoother the
signal, the faster its spectrum decays.

**4.** With $e^{-t}u(t) \leftrightarrow 1/(1 + j\omega)$,

$$X(\omega) = \frac{1}{2}\left[\frac{1}{1 + j(\omega - 5)} + \frac{1}{1 + j(\omega + 5)}\right] = \frac{1 + j\omega}{(1 + j\omega)^2 + 25}.$$

The magnitude peaks near $\omega = \pm 5$: modulation moves the spectrum of the
envelope to the carrier frequency, and the decay rate 1 sets the width of each
peak.

**5.** The total energy is $\int_0^\infty e^{-2t}\,dt = \tfrac{1}{2}$. By
Parseval, the energy in $|\omega| \le 1$ is
$\frac{1}{2\pi}\int_{-1}^{1} \frac{d\omega}{1 + \omega^2} = \frac{1}{\pi}\arctan 1 = \frac{1}{4}$,
half of the total. The spectrum has no edge: any bandwidth is a choice of what
fraction of the energy we agree to keep. Quoting "the bandwidth" without that
fraction is incomplete.

**6.** $|x(t)|^2 = e^{-2at^2}$, a Gaussian with $\sigma_t^2 = 1/(4a)$.
$|X(\omega)|^2 \propto e^{-\omega^2/(2a)}$, with $\sigma_\omega^2 = a$. Hence
$\sigma_t\,\sigma_\omega = \tfrac{1}{2}$, for every $a$. Making the pulse shorter
widens its spectrum in exact proportion. It can be shown (we do not prove it here) that
$\sigma_t\,\sigma_\omega \ge \tfrac{1}{2}$ for every signal of finite energy,
with equality only for the Gaussian; the two-sided exponential, the triangle
and $1/(1 + t^2)^2$ all give a larger product. This is why the Gaussian is used
when both short duration and narrow bandwidth matter.
