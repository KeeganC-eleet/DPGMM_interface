# PyMC Debugging Report

## 1\. Label Switching & Symmetry Breaking

**Issue:** NUTS sampler stalled at 0 step size with 255 gradient evaluations. **Root Cause:** Bayesian mixture models suffer from label switching where regimes dynamically swap identities, creating infinite geometric ridges. **Resolution:** Applied `pymc.distributions.transforms.ordered` to the first feature (mean return) to anchor Regime 0 as the lowest return and Regime N as the highest.

## 2\. Initialization Failure (-inf)

**Issue:** PyMC threw a `-inf` probability error before sampling began. **Root Cause:** The random starting values violated the strict `ordered` constraint (e.g., initializing `[0.6, -0.2, 1.1]`). **Resolution:** Hardcoded an evenly spaced `initval` (e.g., `[-1, 0, 1]`) to guarantee valid mathematical starting conditions.

## 3\. High-Dimensional Covariance Stalling

**Issue:** Sampler speed dropped to 6-9 seconds per draw with step sizes collapsing to 0.000. **Root Cause:** The LKJ Cholesky covariance prior struggles to converge using MCMC NUTS in multi-dimensional mixture models due to extreme parameter correlation. **Resolution:** Transitioning from MCMC to Automatic Differentiation Variational Inference (ADVI).