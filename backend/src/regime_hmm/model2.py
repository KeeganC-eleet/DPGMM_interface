import pymc as pm
import pymc.distributions.transforms as tr
import pytensor.tensor as pt
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import joblib
from pathlib import Path

class RegimeDPGMMFat:
    def __init__(self, max_regimes: int = 5, weight_prior: float = 0.1, draws: int = 1000, tune: int = 1000):
        """
        Initializes the Student's t-Mixture Model using PyMC.
        
        Args:
            max_regimes: Upper bound of regimes. Kept smaller (5) for MCMC sampling efficiency.
            weight_prior: Alpha for the Dirichlet prior.
            draws: Number of MCMC samples to draw.
            tune: Number of tuning steps for the NUTS sampler.
        """
        self.max_regimes = max_regimes
        self.weight_prior = weight_prior
        self.draws = draws
        self.tune = tune
        self.scaler = StandardScaler()
        self.trace_ = None
        self.model_ = None

    def fit(self, features: pd.DataFrame):
        """Builds the probabilistic graph and samples the posterior distribution."""
        print(f"Scaling {len(features.columns)} features and compiling PyMC graph...")
        scaled_features = self.scaler.fit_transform(features.values)
        N, D = scaled_features.shape

        with pm.Model() as self.model_:
            # Dirichlet prior for mixture weights (penalizes unused regimes)
            w = pm.Dirichlet('w', a=np.ones(self.max_regimes) * self.weight_prior)
            
            # Degrees of freedom for each regime's t-distribution (controls tail thickness)
            # Lower values = fatter tails. Gamma(2, 0.1) favors values between 5 and 30.
            nu = pm.Gamma('nu', alpha=2.0, beta=0.1, shape=self.max_regimes)
            
            # 1. Order the regimes strictly by the first feature (log_return)
            # We provide a strictly increasing initval (e.g., [-1.0, 0.0, 1.0]) so the sampler doesn't crash on startup
            mu_0 = pm.Normal(
                'mu_0', 
                mu=0, 
                sigma=2, 
                shape=self.max_regimes, 
                transform=tr.ordered,
                initval=np.linspace(-1, 1, self.max_regimes)
            )
            # 2. Leave the remaining features (volatility, spread, etc.) unconstrained
            mu_rest = pm.Normal('mu_rest', mu=0, sigma=2, shape=(self.max_regimes, D - 1))
            
            # 3. Combine them into the final (max_regimes, D) matrix for the likelihood
            mu = pm.Deterministic('mu', pt.concatenate([mu_0[:, None], mu_rest], axis=1))
            
            # Cholesky decomposition for stable covariance matrices per regime
            comp_dists = []
            for i in range(self.max_regimes):
                chol, corr, stds = pm.LKJCholeskyCov(
                    f'chol_{i}', n=D, eta=2.0, sd_dist=pm.HalfNormal.dist(2.5), compute_corr=True
                )
                comp_dists.append(pm.MvStudentT.dist(nu=nu[i], mu=mu[i], chol=chol))
                
            # The Mixture likelihood
            obs = pm.Mixture('obs', w=w, comp_dists=comp_dists, observed=scaled_features)
            
            print("Optimizing posterior distributions using ADVI...")
            mean_field = pm.fit(method='advi', n=30000, obj_optimizer=pm.adam(learning_rate=0.01))
            
            # Draw samples from the optimized approximation
            trace = mean_field.sample(self.draws)
            self.trace_ = pm.to_inference_data(trace)
        print("ADVI optimization complete. Model fitted.")

    def save_model(self, filepath: str):
        """Serializes the scaler and the MCMC trace."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        bundle = {
            'scaler': self.scaler,
            'trace': self.trace_
        }
        joblib.dump(bundle, path)
        print(f"PyMC trace and scaler saved to {path}")

    def load_model(self, filepath: str):
        bundle = joblib.load(filepath)
        self.scaler = bundle['scaler']
        self.trace_ = bundle['trace']
        print(f"Model loaded from {filepath}")

    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """Assigns regimes to new data based on posterior distribution means."""
        if self.trace_ is None:
            raise ValueError("Model must be fitted before calling predict.")
            
        scaled_features = self.scaler.transform(features.values)
        
        # Extract the average parameter values from the MCMC posterior trace
        post = self.trace_.posterior
        mu_mean = post['mu'].mean(dim=['chain', 'draw']).values
        
        # Simplified prediction: Assign data points to the closest regime mean mathematically
        from scipy.spatial.distance import cdist
        distances = cdist(scaled_features, mu_mean, metric='euclidean')
        
        return np.argmin(distances, axis=1)