import numpy as np
from Modules_FIB import ImageProcessing as ImPr

# Définir la taille de la matrice
nombre_lignes = 3
nombre_colonnes = 4

# Créer une matrice aléatoire de taille (nombre_lignes, nombre_colonnes) avec des valeurs entre 0 et 1
matrice_random = np.random.rand(nombre_lignes, nombre_colonnes)

print("Matrice aléatoire :")
print(matrice_random)
ImPr.normalize(matrice_random)
print(matrice_random)