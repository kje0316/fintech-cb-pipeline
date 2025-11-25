import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.base import BaseEstimator, TransformerMixin
from typing import Dict, Any
import numpy as np

# =============================================================================
# Base VAE Wrapper Class (scikit-learn compatible)
# =============================================================================
class TabularVAE(BaseEstimator, TransformerMixin):
    """
    A scikit-learn compatible wrapper for a PyTorch Variational Autoencoder (VAE).
    """
    def __init__(self, input_dim: int, latent_dim: int = 10, hidden_dim: int = 64, 
                 epochs: int = 30, batch_size: int = 256, lr: float = 0.001, 
                 random_state: int = 42):
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        self.hidden_dim = hidden_dim
        self.epochs = epochs
        self.batch_size = batch_size
        self.lr = lr
        self.random_state = random_state
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        
        # Set seeds for reproducibility
        torch.manual_seed(self.random_state)
        np.random.seed(self.random_state)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(self.random_state)

    class _VAEModule(nn.Module):
        """The core PyTorch module for the VAE."""
        def __init__(self, inp_dim, hid_dim, lat_dim):
            super().__init__()
            self.fc1 = nn.Linear(inp_dim, hid_dim)
            self.fc_mu = nn.Linear(hid_dim, lat_dim)
            self.fc_logvar = nn.Linear(hid_dim, lat_dim)
            self.fc3 = nn.Linear(lat_dim, hid_dim)
            self.fc4 = nn.Linear(hid_dim, inp_dim)
            self.relu = nn.ReLU()
            
        def encode(self, x):
            h1 = self.relu(self.fc1(x))
            return self.fc_mu(h1), self.fc_logvar(h1)
            
        def reparameterize(self, mu, logvar):
            std = torch.exp(0.5 * logvar)
            eps = torch.randn_like(std)
            return mu + eps * std
            
        def decode(self, z):
            h3 = self.relu(self.fc3(z))
            return self.fc4(h3)
            
        def forward(self, x):
            mu, logvar = self.encode(x)
            z = self.reparameterize(mu, logvar)
            return self.decode(z), mu, logvar

    def _loss_function(self, recon_x, x, mu, logvar):
        """Reconstruction + KL divergence losses."""
        MSE = nn.MSELoss(reduction='sum')(recon_x, x)
        KLD = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
        return MSE + KLD

    def fit(self, X, y=None):
        X_tensor = torch.FloatTensor(X).to(self.device)
        dataset = TensorDataset(X_tensor)
        dataloader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)
        
        self.model = self._VAEModule(self.input_dim, self.hidden_dim, self.latent_dim).to(self.device)
        optimizer = optim.Adam(self.model.parameters(), lr=self.lr)
        
        print(f"5. Training VAE on {self.device}...")
        self.model.train()
        for epoch in range(self.epochs):
            for (batch_x,) in dataloader:
                optimizer.zero_grad()
                recon, mu, logvar = self.model(batch_x)
                loss = self._loss_function(recon, batch_x, mu, logvar)
                loss.backward()
                optimizer.step()
        print("VAE training complete.")
        return self

    def transform(self, X):
        if self.model is None:
            raise RuntimeError("The model has not been fitted yet. Call fit() first.")
        self.model.eval()
        X_tensor = torch.FloatTensor(X).to(self.device)
        with torch.no_grad():
            mu, _ = self.model.encode(X_tensor)
        return mu.cpu().numpy()

# =============================================================================
# Beta-VAE variant
# =============================================================================
class BetaVAE(TabularVAE):
    """
    A Beta-VAE variant that puts a higher weight on the KL-divergence term
    to encourage disentanglement.
    """
    def __init__(self, input_dim: int, latent_dim: int = 16, hidden_dim: int = 64,
                 epochs: int = 50, batch_size: int = 256, lr: float = 0.001,
                 beta: float = 4.0, random_state: int = 42):
        super().__init__(input_dim, latent_dim, hidden_dim, epochs, batch_size, lr, random_state)
        self.beta = beta

    def _loss_function(self, recon_x, x, mu, logvar):
        """Reconstruction + weighted KL divergence losses."""
        MSE = nn.MSELoss(reduction='sum')(recon_x, x)
        KLD = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
        return MSE + self.beta * KLD

    def fit(self, X, y=None):
        X_tensor = torch.FloatTensor(X).to(self.device)
        dataset = TensorDataset(X_tensor)
        dataloader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)
        
        self.model = self._VAEModule(self.input_dim, self.hidden_dim, self.latent_dim).to(self.device)
        optimizer = optim.Adam(self.model.parameters(), lr=self.lr)
        
        print(f"5. Training Beta-VAE (beta={self.beta}) on {self.device}...")
        self.model.train()
        for epoch in range(self.epochs):
            for (batch_x,) in dataloader:
                optimizer.zero_grad()
                recon, mu, logvar = self.model(batch_x)
                loss = self._loss_function(recon, batch_x, mu, logvar)
                loss.backward()
                optimizer.step()
        print("Beta-VAE training complete.")
        return self

def get_model(config: Dict[str, Any], input_dim: int):
    """
    Factory function to get the specified VAE model from the config.
    """
    model_type = config['modeling']['vae_type']
    
    if model_type == 'beta':
        params = config['modeling']['beta_vae']
        return BetaVAE(input_dim=input_dim, **params)
    elif model_type == 'vae':
        params = config['modeling']['vae']
        return TabularVAE(input_dim=input_dim, **params)
    else:
        raise ValueError(f"Unknown model type specified in config: {model_type}")
