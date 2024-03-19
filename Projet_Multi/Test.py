# -*- coding: utf-8 -*-
"""
Created on Sat Feb 10 22:52:09 2024

@author: Thomas
"""

import ImageProcessing as ImPr

matrice = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
]
px=len(matrice)

print("Matrice originale :")
for ligne in matrice:
    print(ligne)

ImPr.triangle_scanning(matrice,px)

print("\nMatrice avec lignes inversées :")
for ligne in matrice:
    print(ligne)