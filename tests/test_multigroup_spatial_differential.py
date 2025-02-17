from popari.model import Popari
from popari.util import clustering_louvain_nclust

import os
import pandas as pd
import pytest
import torch
from tqdm.auto import tqdm, trange
from pathlib import Path
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, adjusted_rand_score

@pytest.fixture(scope="module")
def popari_with_neighbors():
    path2dataset = Path('tests/test_data/multigroup')
    K=11
    lambda_Sigma_x_inv = 1e-4 # Spatial affinity regularization hyperparameter
    torch_context = dict(device='cuda:0', dtype=torch.float64) # Context for PyTorch tensor instantiation
    replicate_names = ["top", "bottom", "central"]
    spatial_affinity_groups = {
        "vertical_gradient": ["top", "bottom"],
        "central": ["central"]
    }

    obj = Popari(
        K=K,
        lambda_Sigma_x_inv=lambda_Sigma_x_inv,
        dataset_path=path2dataset/ "multigroup_spatial_noise_dataset.h5ad",
        replicate_names = replicate_names,
        spatial_affinity_groups=spatial_affinity_groups,
        spatial_affinity_mode="differential lookup",
        lambda_Sigma_bar=1,
        torch_context=torch_context,
        initial_context=torch_context
    )

    for iteration in range(1, 5):
        obj.estimate_parameters()
        obj.estimate_weights()
                
    return obj

def test_Sigma_x_inv(popari_with_neighbors):
    Sigma_x_inv = list(popari_with_neighbors.parameter_optimizer.spatial_affinity_state.values())[0].cpu().detach().numpy()
    np.save("tests/test_data/multigroup/outputs/Sigma_x_inv_spatial_differential.npy", Sigma_x_inv)
    test_Sigma_x_inv = np.load("tests/test_data/multigroup/outputs/Sigma_x_inv_spatial_differential.npy")
    assert np.allclose(test_Sigma_x_inv, Sigma_x_inv)

def test_M(popari_with_neighbors):
    M_bar = popari_with_neighbors.parameter_optimizer.metagene_state.metagenes.detach().cpu().numpy()
    np.save("tests/test_data/multigroup/outputs/M_bar_spatial_differential.npy", M_bar)
    test_M = np.load("tests/test_data/multigroup/outputs/M_bar_spatial_differential.npy")
    assert np.allclose(test_M, M_bar)

def test_X_0(popari_with_neighbors):
    X_0 = popari_with_neighbors.embedding_optimizer.embedding_state["top"].detach().cpu().numpy()
    np.save("tests/test_data/multigroup/outputs/X_0_spatial_differential.npy", X_0)
    test_X_0 = np.load("tests/test_data/multigroup/outputs/X_0_spatial_differential.npy")
    assert np.allclose(test_X_0, X_0)

def test_louvain_clustering(popari_with_neighbors):
    df_meta = []
    path2dataset = Path('tests/test_data/multigroup')
    repli_list = [0, 1]
    expected_aris = [0.7773584481376827, 0.7851558268629739, 0.7797035144162096]
    expected_silhouettes = [0.3364204109220141, 0.30696366760999366, 0.31038299322010154]
    
    for index, (r, X) in enumerate(popari_with_neighbors.embedding_optimizer.embedding_state.items()):
    #     df = pd.read_csv(path2dataset / 'files' / f'meta_{r}.csv')
        df = popari_with_neighbors.datasets[index].obs
        df['repli'] = r
        df['cell_type'] = pd.Categorical(df['cell_type'], categories=np.unique(df['cell_type']))
        df_meta.append(df)

        x = StandardScaler().fit_transform(X.cpu().numpy())
        
        y = clustering_louvain_nclust(
            x.copy(), 8,
            kwargs_neighbors=dict(n_neighbors=10),
            kwargs_clustering=dict(),
            resolution_boundaries=(.1, 1.),
        )
        
        df['label Popari'] = y
        ari = adjusted_rand_score(*df[['cell_type', 'label Popari']].values.T)
        print(ari)
        assert expected_aris[index] == pytest.approx(ari)
            
        silhouette = silhouette_score(x, df['cell_type'])
        print(silhouette)
        assert expected_silhouettes[index]  == pytest.approx(silhouette)

    # df_meta = pd.concat(df_meta, axis=0).reset_index(drop=True)
    # df_meta['cell type'] = pd.Categorical(df_meta['cell type'], categories=np.unique(df_meta['cell type']))

    # Xs = [X.cpu().numpy() for X in popari_with_neighbors.Xs]

    # x = np.concatenate(Xs, axis=0)
    # x = StandardScaler().fit_transform(x)
    # 
    # y = clustering_louvain_nclust(
    #     x.copy(), 8,
    #     kwargs_neighbors=dict(n_neighbors=10),
    #     kwargs_clustering=dict(),
    #     resolution_boundaries=(.1, 1.),
    # )
    # 
    # df_meta['label Popari'] = y
    # ari = adjusted_rand_score(*df_meta[['cell type', 'label Popari']].values.T)
    # print(ari)
    # assert 0.3731545260146673 == pytest.approx(ari)
    #     
    # silhouette = silhouette_score(x, df_meta['cell type'])
    # print(silhouette)
    # assert 0.029621144756674767  == pytest.approx(silhouette)
# def test_project2simplex():
#     project2simplex(x, dim=0)

if __name__ == "__main__":
    test_Sigma_x_inv(example_popari_run)
    test_M()
    test_X_0()
    
    test_louvain_clustering()

