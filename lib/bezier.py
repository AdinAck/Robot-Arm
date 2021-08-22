import numpy as np


def bezier(x0, y0, x1, y1, x2, y2, x3, y3, x):
    """
    Finds x intersection of a cubic bezier curve
    """
    # Coefficients of polynomial form
    a = x3-3*x2+3*x1-x0
    b = 3*x2-6*x1+3*x0
    c = 3*x1-3*x0
    d = x0-x

    # Numpy root finder
    f = [a, b, c, d]
    t = np.roots(f)
    t = t[np.isreal(t)][0].real
    y = t**3*(y3-3*y2+3*y1-y0)+t**2*(3*y2-6*y1+3*y0)+t*(3*y1-3*y0)+y0
    return y


if __name__ == '__main__':
    bezier(0, 0, 0.5, 0, 0.5, 1, 1, 1, 0.25)
