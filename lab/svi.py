import matplotlib.cm as cm
import matplotlib.pyplot as plt
import numpy as np
from scipy.special import digamma, gamma
from numpy.random import *


class VariationalGaussianMixture(object):

    def __init__(self, n_component=10, alpha0=1.):
        self.n_component = n_component
        self.alpha0 = alpha0

    def init_params(self, X):
        self.sample_size, self.ndim = X.shape
        self.alpha0 = np.ones(self.n_component) * self.alpha0
        self.m0 = np.zeros(self.ndim)
        self.W0 = np.eye(self.ndim)
        self.nu0 = self.ndim
        self.beta0 = 1.

        self.component_size = self.sample_size / self.n_component + np.zeros(self.n_component)
        self.alpha = self.alpha0 + self.component_size
        self.beta = self.beta0 + self.component_size
        indices = np.random.choice(self.sample_size, self.n_component, replace=False)
        self.m = X[indices].T
        self.W = np.tile(self.W0, (self.n_component, 1, 1)).T
        self.nu = self.nu0 + self.component_size
        self.log_likelihoods = []
        self.rho = 0.01

    def get_params(self):
        return self.alpha, self.beta, self.m, self.W, self.nu

    def fit(self, X, iter_max=100):
        self.init_params(X)
        for i in range(iter_max):
            params = np.hstack([array.flatten() for array in self.get_params()])
            r = self.e_like_step(X)
            alpha_, beta_, m_, W_, nu_ = self.m_like_step(X, r)
            self.alpha = self.update_stochastic_param(alpha_, self.alpha, i)
            self.beta = self.update_stochastic_param(beta_, self.beta, i)
            self.m = self.update_stochastic_param(m_, self.m, i)
            self.W = self.update_stochastic_param(W_, self.W, i)
            self.nu = self.update_stochastic_param(nu_, self.nu, i)
            a = self.calc_loglikelihood(X)
            self.log_likelihoods.append(a)
        #     if np.allclose(params, np.hstack([array.ravel() for array in self.get_params()])):
        #         break
        # else:
        #     print("parameters may not have converged")

    def e_like_step(self, X):
        d = X[:, :, None] - self.m
        gauss = np.exp(
            -0.5 * self.ndim / self.beta
            - 0.5 * self.nu * np.sum(
                np.einsum('ijk,njk->nik', self.W, d) * d,
                axis=1)
        )
        pi = np.exp(digamma(self.alpha) - digamma(self.alpha.sum()))
        Lambda = np.exp(digamma(self.nu - np.arange(self.ndim)[:, None]).sum(axis=0) + self.ndim * np.log(2) + np.linalg.slogdet(self.W.T)[1])
        r = pi * np.sqrt(Lambda) * gauss
        r /= np.sum(r, axis=-1, keepdims=True)
        r[np.isnan(r)] = 1. / self.n_component
        return r

    def m_like_step(self, X, r):
        self.component_size = r.sum(axis=0)
        # (t-1)の変数を保存しておく
        alpha_ = self.alpha
        beta_ = self.beta
        m_ = self.m
        W_  = self.W
        nu_ = self.nu
        Xm = X.T.dot(r) / self.component_size
        d = X[:, :, None] - Xm
        S = np.einsum('nik,njk->ijk', d, r[:, None, :] * d) / self.component_size
        self.alpha = self.alpha0 + self.component_size
        self.beta = self.beta0 + self.component_size
        self.m = (self.beta0 * self.m0[:, None] + self.component_size * Xm) / self.beta
        d = Xm - self.m0[:, None]
        self.W = np.linalg.inv(
            np.linalg.inv(self.W0)
            + (self.component_size * S).T
            + (self.beta0 * self.component_size * np.einsum('ik,jk->ijk', d, d) / (self.beta0 + self.component_size)).T).T
        self.nu = self.nu0 + self.component_size
        return alpha_, beta_, m_, W_, nu_

    def update_stochastic_param(self, param_, param, iter):
        self.rho += 1 / (100 + iter)
        update_param = (1 - self.rho) * param_ + self.rho * param
        return update_param

    def predict_proba(self, X):
        covs = self.nu * self.W
        precisions = np.linalg.inv(covs.T).T
        d = X[:, :, None] - self.m
        exponents = np.sum(np.einsum('nik,ijk->njk', d, precisions) * d, axis=1)
        gausses = np.exp(-0.5 * exponents) / np.sqrt(np.linalg.det(covs.T).T * (2 * np.pi) ** self.ndim)
        gausses *= (self.alpha0 + self.component_size) / (self.n_component * self.alpha0 + self.sample_size)
        return np.sum(gausses, axis=-1)

    def classify(self, X):
        return np.argmax(self.e_like_step(X), 1)

    def student_t(self, X):
        nu = self.nu + 1 - self.ndim
        L = nu * self.beta * self.W / (1 + self.beta)
        d = X[:, :, None] - self.m
        maha_sq = np.sum(np.einsum('nik,ijk->njk', d, L) * d, axis=1)
        return (
            gamma(0.5 * (nu + self.ndim))
            * np.sqrt(np.linalg.det(L.T))
            * (1 + maha_sq / nu) ** (-0.5 * (nu + self.ndim))
            / (gamma(0.5 * nu) * (nu * np.pi) ** (0.5 * self.ndim)))

    def predict_dist(self, X):
        return (self.alpha * self.student_t(X)).sum(axis=-1) / self.alpha.sum()

    def calc_loglikelihood(self, X):
        d = X[:, :, None] - self.m
        gauss = np.exp(
            -0.5 * self.ndim / self.beta
            - 0.5 * self.nu * np.sum(
                np.einsum('ijk,njk->nik', self.W, d) * d,
                axis=1)
        )
        ave_alpha = self.alpha / np.mean(self.alpha)
        # print(ave_alpha)
        p_i = ave_alpha * gauss
        # print(p_i)
        p_1 = np.sum(p_i, axis=1)
        p_2 = np.sum(p_1)
        log_likelihood = np.log(p_2)
        print(log_likelihood)
        return log_likelihood


def create_toy_data():
    mu = np.array([[5, 5], [20, 20], [50, 10]])
    sigma = np.array([[[3, 1], 
                       [1, 3]],
                       [[3, 1],
                       [1, 3]],
                       [[3, 1],
                       [1, 3]]])
    data = []
    for i in range(len(mu)):
        values = multivariate_normal(mu[i], sigma[i], 100)
        data.extend(values)
    data = np.array(data)
    return data


def main():
    np.random.seed(11)
    X = create_toy_data()
    model = VariationalGaussianMixture(n_component=10, alpha0=0.01)
    model.fit(X, iter_max=25)
    labels = model.classify(X)
    x_test, y_test = np.meshgrid(
        np.linspace(-10, 10, 100), np.linspace(-10, 10, 100))
    X_test = np.array([x_test, y_test]).reshape(2, -1).transpose()
    probs = model.predict_dist(X_test)
    plt.scatter(X[:, 0], X[:, 1], c=labels, cmap=cm.get_cmap())
    # plt.contour(x_test, y_test, probs.reshape(100, 100))
    plt.show()
    plt.plot(model.log_likelihoods, color='#4169e1', linestyle='solid')
    plt.show()


if __name__ == '__main__':
    main()