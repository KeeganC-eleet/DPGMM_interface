import numpy as np
import pandas as pd
from sklearn.mixture import BayesianGaussianMixture
from sklearn.preprocessing import StandardScaler
import joblib
from pathlib import Path

class RegimeDPGMM:
    def __init__(self, max_regimes: int = 10, weight_prior: float = 0.001, random_state: int = 42):
        self.max_regimes = max_regimes
        self.scaler = StandardScaler()
        self.model = BayesianGaussianMixture(
            n_components=max_regimes,
            weight_concentration_prior_type='dirichlet_process',
            weight_concentration_prior=weight_prior,
            covariance_type='full',
            max_iter=1000,
            n_init=5,
            random_state=random_state,
            tol=1e-3
        )
        self.active_regimes_ = 0
        self.active_weights_ = []

    def fit(self, features: pd.DataFrame):
        """Scales features, fits the DPGMM, and prunes empty states."""
        print(f"Scaling {len(features.columns)} features and training DPGMM...")
        
        # Scale features to mean=0, std=1 so macro data doesn't overpower price data
        scaled_features = self.scaler.fit_transform(features.values)
        
        self.model.fit(scaled_features)
        
        weight_threshold = 0.01
        self.active_weights_ = self.model.weights_[self.model.weights_ > weight_threshold]
        self.active_regimes_ = len(self.active_weights_)
        
        print(f"Training converged. DPGMM settled on {self.active_regimes_} active regimes.")
        
    def predict(self, features: pd.DataFrame) -> pd.Series:
        if not hasattr(self.model, 'converged_') or not self.model.converged_:
            raise ValueError("Model must be fitted before predicting.")
            
        scaled_features = self.scaler.transform(features.values)
        states = self.model.predict(scaled_features)
        return pd.Series(states, index=features.index, name="Regime")
        
    def predict_proba(self, features: pd.DataFrame) -> pd.DataFrame:
        scaled_features = self.scaler.transform(features.values)
        probs = self.model.predict_proba(scaled_features)
        
        active_indices = np.where(self.model.weights_ > 0.01)[0]
        active_probs = probs[:, active_indices]
        
        cols = [f"Regime_{i}_Prob" for i in active_indices]
        return pd.DataFrame(active_probs, index=features.index, columns=cols)

    def save_model(self, filepath: str):
        """Saves both the DPGMM and the Scaler as a single bundle."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        bundle = {
            'scaler': self.scaler,
            'model': self.model,
            'active_regimes': self.active_regimes_
        }
        joblib.dump(bundle, path)
        print(f"Model and scaler bundle saved to {path}")

    def load_model(self, filepath: str):
        bundle = joblib.load(filepath)
        self.scaler = bundle['scaler']
        self.model = bundle['model']
        self.active_regimes_ = bundle['active_regimes']
        print(f"Model and scaler loaded from {filepath}")

def calculate_transition_matrix(regime_series: pd.Series) -> pd.DataFrame:
    """
    Empirically calculates the transition probability matrix from a time-series of states.
    Rows represent the Current State, Columns represent the Next State.
    """
    # Create a dataframe of today's regime and tomorrow's regime
    transitions = pd.DataFrame({
        'Current': regime_series, 
        'Next': regime_series.shift(-1)
    }).dropna()
    
    # Count the raw occurrences of each state transition
    transition_counts = pd.crosstab(transitions['Current'], transitions['Next'])
    
    # Normalize rows to sum to 1.0 (probabilities)
    transition_matrix = transition_counts.div(transition_counts.sum(axis=1), axis=0)
    
    # Fill any NaN values (e.g., if a state was never left) with 0
    return transition_matrix.fillna(0.0)

