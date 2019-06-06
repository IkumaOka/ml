import numpy as np
import sys
import matplotlib.pyplot as plt
from scipy.special import digamma, gamma, loggamma
from scipy.misc import logsumexp
import math

def create_data(N, K):
    loc = np.array([1.0, 3.0]) # 平均の初期値
    scale = np.array([1.0, 2.0]) # 標準偏差の初期値
    X, mu_star, sigma_star = [], [], []
    for i in range(K):
        X = np.append(X, np.random.normal(loc = loc[i], scale = scale[i], size = int(N / K)))
        mu_star = np.append(mu_star, loc[i])
        sigma_star = np.append(sigma_star, scale[i])
    return (X, mu_star, sigma_star)

def gaussian(mu, sigma):
    def f(x):
        return np.exp(-0.5 * (x - mu) ** 2 / sigma) / np.sqrt(2 * np.pi * sigma)
    return f

# 負担率を計算
# ηを計算する式（式7.29参照）PRMLだと式10.46
# 式7.29第1項において、多変量では正規-ウィシャート分布を使うが、一変量の場合は正規-ガンマ分布を使う
def estimate_posterior_likelihood(X):
    # 正規-ガンマ分布の期待値を求める(wiki参照)
    ex_T = kappa / xi
    ex_T_X = psi * kappa / xi
    ex_T_X_2 = 1 / beta + psi ** 2 * kappa / xi
    eta = []
    for i in range(len(X)):
        elm = ( X[i]*ex_T - 2*X[i]*ex_T_X + ex_T_X_2 ) / 2 + digamma(dir_param) - digamma(dir_param.sum(axis=0))
        eta.append(elm)

    eta = np.array(eta)
    # print(eta)
    r = []
    for i in range(len(eta)):
        a = eta[i] / eta[i].sum()
        r.append(a)
    r = np.array(r)
    # print(r)
    return r

# Mステップ
def estimate_gmm_parameter(X, r, psi, beta, kappa, xi, dir_param):
    # 負担率の総和
    n_j = r.sum(axis=0)
    # 負担率による観測値の重み付き平均
    barx_j = np.dot(X.T, r) / n_j

    # q(π)のパラメータを更新(式7.44)
    dir_param = dir_param + n_j

    #q(μ,λ)のパラメータを更新(式7.54)
    psi = ( n_j * barx_j + beta * psi ) / ( n_j + beta )
    beta = n_j + beta
    kappa = n_j / 2 + kappa
    xi = ( n_j * barx_j + (n_j * beta + ((barx_j - psi) ** 2 / (n_j + beta))) / 2 ) + xi
    return psi, beta, kappa, xi, dir_param

def calc_log_likelihood(X, psi, beta, kappa, xi, r):
    a = []
    for i in range(len(X)):
        diff = X[i] - psi
        a.append(diff)
    a = np.array(a)
    log_u = np.log(beta * a**2 / 2 * (1 + beta) + xi)
    elm1 = np.log(r)
    elm2 = np.log(beta / (2 * math.pi * (1 + beta))) / 2
    elm3 = kappa * np.log(xi)
    elm4 = (kappa + 0.5) * log_u
    elm5 = loggamma(kappa + 0.5) - loggamma(kappa)
    s = elm1 + elm2 + elm3 - elm4 + elm5
    print(s)
    log_likelihood = logsumexp(s)
    return log_likelihood

np.random.seed(19)
K = 2 # クラス数
N = 1000 * K # データ数
# π,μ,σの値を初期化
pi = np.random.rand(K)
mu = np.random.randn(K)
sigma = np.abs(np.random.randn(K))
lamda = 1.0 / sigma
X, mu_star, sigma_star = create_data(N, K)
# 正規-ガンマ分布のパラメータを定義
psi = np.array([0.0, 0.0])
beta = np.array([1.0, 0.9])
kappa = np.array([1.0, 0.9])
xi = np.array([1.0, 0.9])
# ディリクレ分布のパラメータを定義
dir_param = np.array([10.0, 8.0]) # [1.0, 0.1]だとdigammaに代入した時にマイナスになる
log_likelihoods = []
for iter in range(1000):
    r = estimate_posterior_likelihood(X)
    for i, elm in enumerate(r):
        for j in elm:
            if j < 0:
                elm[np.argmax(elm)] = 0.99
                elm[np.argmin(elm)] = 0.01
    psi, beta, kappa, xi, dir_param = estimate_gmm_parameter(X, r, psi, beta, kappa, xi, dir_param)
    ave_dir_param = np.average(dir_param)
    ave_sigma = xi / kappa # 後でσを使うから期待値の逆数をとった
    gf = gaussian(psi, ave_sigma)
    log_likelihood = calc_log_likelihood(X, psi, beta, kappa, xi, r)
    # print(log_likelihood)
    log_likelihoods.append(log_likelihood)

log_likelihoods = np.array(log_likelihoods)

plt.plot(log_likelihoods, color='#4169e1', linestyle='solid')
plt.show()


